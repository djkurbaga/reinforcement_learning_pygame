"""
boss.py - Patron: kafa + 4 el + state machine + hareket setleri.

State machine (durum):
    "bekle"          - 3 sn bekler, ardından bir hareket seçer (rastgele)
    "alt_swing"      - alt el bir taraftan diğerine süpürür (1. hareket)
    "ust_slam"       - üst el 2 komşu platformu lavaya gömer (2. hareket, henüz yok)
    "alt_alkis"      - iki alt el merkezde alkış yapar (3. hareket, henüz yok)
    "faz_gecisi"     - faz değişimi animasyonu
    "olu"            - patron öldü

Henüz uygulanan: 1. hareket (alt_swing). Diğerleri sonra eklenecek.
"""

import math
import random
import pygame
import arena

# ============================================================
# KONUM SABITLERI
# ============================================================
KAFA_X = arena.TUVAL_GENISLIK // 2
KAFA_Y = 135
KAFA_YARI = 55

SOL_UST_X = 320
SAG_UST_X = 640
UST_Y = 115

SOL_ALT_X = 230
SAG_ALT_X = 730
ALT_Y = 235

EL_GENISLIK = 72
EL_YUKSEKLIK = 44

# ============================================================
# CAN / HASAR / GENEL
# ============================================================
FAZ_CANLARI = [120, 150, 200]
FAZ_GECIS_SURE = 1.8

EL_TEMAS_HASAR = 1
OYUNCU_YUMRUK_HASAR = 5
OYUNCU_SILKSPEAR_HASAR = 10

KNOCKBACK_DIKEY = -13.0
KNOCKBACK_YATAY = 7.0

# Saldırılar arası bekleme
BEKLE_SURE = 3.0

# ============================================================
# 1. HAREKET — ALT SWING
# ============================================================
# Alt el bir yöne (sağ ya da sol) gidip diğer uca süpürür.
# Süre = 2 sn (oyuncu el üstünden zıplayıp atlamalı).
# El "platform üstüne çarpacak yükseklikte" iner -> y = ZEMIN_Y - oyuncu_yuk/2
# Yani el yatay ortalama, dikey olarak oyuncunun yan vurma seviyesinde.
SWING_SURE = 2.0
SWING_Y = arena.ZEMIN_Y - 26   # platformun üstünden 26 px yukarı (oyuncu yarısı)
# Süpürme uç noktaları (sahnenin sol/sağ kenarına yakın)
SWING_SOL_X = 60
SWING_SAG_X = arena.TUVAL_GENISLIK - 60   # 900
# Kafa hareketi (swing sırasında elin yönüne doğru biraz kayar + aşağı eğilir)
KAFA_SWING_KAYMA = 30
KAFA_SWING_EGILME = 18

# ============================================================
# RENKLER
# ============================================================
RENK_KAFA = (60, 52, 137)
RENK_KAFA_KENAR = (38, 33, 92)
RENK_KAFA_VURUS = (210, 195, 255)
RENK_GOZ = (250, 160, 50)
RENK_GOZ_PARLAK = (255, 220, 130)
RENK_EL = (96, 84, 168)
RENK_EL_KENAR = (52, 44, 110)
RENK_EL_AKTIF = (170, 140, 255)   # saldıran el için biraz parlak ton
RENK_FAZ_HALE = (200, 180, 255)


def _ease_in_out(t):
    """t: 0..1; 0..1 arası yumuşak (slow-in, slow-out) eğri."""
    return 0.5 - 0.5 * math.cos(math.pi * max(0.0, min(1.0, t)))


class Hand:
    def __init__(self, cx, cy, isim):
        self.rect = pygame.Rect(0, 0, EL_GENISLIK, EL_YUKSEKLIK)
        self.rect.center = (cx, cy)
        self.isim = isim
        self.baslangic_konum = (cx, cy)
        self.aktif = False   # şu an saldırı yapıyor mu (görsel için)

    def ciz(self, tuval):
        renk = RENK_EL_AKTIF if self.aktif else RENK_EL
        pygame.draw.rect(tuval, renk, self.rect, border_radius=6)
        pygame.draw.rect(tuval, RENK_EL_KENAR, self.rect, width=2,
                         border_radius=6)


class Boss:
    def __init__(self):
        # Kafa
        self.kafa_temel = (KAFA_X, KAFA_Y)
        self.kafa_merkez = list(self.kafa_temel)
        self.kafa_yari = KAFA_YARI
        self.kafa_rect = pygame.Rect(
            KAFA_X - KAFA_YARI, KAFA_Y - KAFA_YARI,
            KAFA_YARI * 2, KAFA_YARI * 2
        )

        # Eller
        self.eller = [
            Hand(SOL_UST_X, UST_Y, "sol_ust"),
            Hand(SAG_UST_X, UST_Y, "sag_ust"),
            Hand(SOL_ALT_X, ALT_Y, "sol_alt"),
            Hand(SAG_ALT_X, ALT_Y, "sag_alt"),
        ]

        # Can / faz
        self.faz = 0
        self.maks_can = FAZ_CANLARI[0]
        self.can = self.maks_can

        # State machine
        self.durum = "bekle"
        self.bekle_kalan = BEKLE_SURE   # ilk başta bekle
        self.aktif_hareket = ""         # HUD için ad

        # Hareket-içi zamanlayıcılar
        self.swing_t = 0.0              # 0..SWING_SURE
        self.swing_el_index = -1        # 2 (sol_alt) ya da 3 (sag_alt)
        self.swing_baslangic_x = 0
        self.swing_bitis_x = 0

        # Animasyon
        self.faz_gecis_kalan = 0.0
        self.kafa_hit_flash = 0.0
        self.olu = False

    # ============================================================
    # HASAR
    # ============================================================
    def hasar_al(self, miktar):
        if self.olu or self.faz_gecis_kalan > 0:
            return
        if self.kafa_hit_flash > 0:
            return
        self.can -= miktar
        self.kafa_hit_flash = 0.15
        if self.can <= 0:
            self.can = 0
            if self.faz >= len(FAZ_CANLARI) - 1:
                self.olu = True
                self.durum = "olu"
            else:
                self.faz += 1
                self.maks_can = FAZ_CANLARI[self.faz]
                self.can = self.maks_can
                self.faz_gecis_kalan = FAZ_GECIS_SURE
                self.durum = "faz_gecisi"
                self._tum_elleri_pasif_konuma_dondur()

    def _tum_elleri_pasif_konuma_dondur(self):
        for el in self.eller:
            el.rect.center = el.baslangic_konum
            el.aktif = False
        self.kafa_merkez = list(self.kafa_temel)
        self.aktif_hareket = ""

    # ============================================================
    # STATE MACHINE
    # ============================================================
    def _sonraki_saldiriyi_sec(self):
        """Şu an sadece alt_swing tanımlı. Diğerleri eklenince listeye girer."""
        # Şimdilik tek seçenek - sonraki hareketler eklenince listeye eklenecek
        secenekler = ["alt_swing"]
        secim = random.choice(secenekler)
        if secim == "alt_swing":
            self._alt_swing_baslat()

    # ------------------------------------------------------------
    # 1. HAREKET: ALT SWING
    # ------------------------------------------------------------
    def _alt_swing_baslat(self):
        """Rastgele bir alt el seçilir, karşı yönden giriş yapar."""
        self.durum = "alt_swing"
        self.aktif_hareket = "Alt swing"
        self.swing_t = 0.0
        # Rastgele alt el seç (indeks 2 veya 3)
        self.swing_el_index = random.choice([2, 3])
        el = self.eller[self.swing_el_index]
        el.aktif = True
        # El, başlangıç konumundan KARŞI uca süpürür.
        # Sol alt (sol kenarda başlar) -> sağ uca gider
        # Sağ alt (sağ kenarda başlar) -> sol uca gider
        if el.isim == "sol_alt":
            self.swing_baslangic_x = SWING_SOL_X
            self.swing_bitis_x = SWING_SAG_X
        else:
            self.swing_baslangic_x = SWING_SAG_X
            self.swing_bitis_x = SWING_SOL_X
        # Eli süpürme y'sine getir
        el.rect.center = (self.swing_baslangic_x, SWING_Y)

    def _alt_swing_guncelle(self, dt):
        self.swing_t += dt
        if self.swing_t >= SWING_SURE:
            # Bitti - eli eski konuma döndür, bekleme moduna geç
            el = self.eller[self.swing_el_index]
            el.rect.center = el.baslangic_konum
            el.aktif = False
            self.kafa_merkez = list(self.kafa_temel)
            self.durum = "bekle"
            self.bekle_kalan = BEKLE_SURE
            self.aktif_hareket = ""
            return

        # İlerleme oranı (0 -> 1), yumuşak
        ham = self.swing_t / SWING_SURE
        t = _ease_in_out(ham)
        # El konumu (yatay interpolasyon)
        x = self.swing_baslangic_x + (self.swing_bitis_x - self.swing_baslangic_x) * t
        el = self.eller[self.swing_el_index]
        el.rect.center = (int(x), SWING_Y)

        # Kafa hareketi: elin yönüne doğru biraz kayar + aşağı eğilir.
        # Tepe noktası ortada (t=0.5), sonra geri döner.
        yon = 1 if self.swing_bitis_x > self.swing_baslangic_x else -1
        # Salınım egrisi: 0 -> 1 -> 0 (sin pi*t)
        salinim = math.sin(math.pi * ham)
        self.kafa_merkez[0] = self.kafa_temel[0] + yon * KAFA_SWING_KAYMA * salinim
        self.kafa_merkez[1] = self.kafa_temel[1] + KAFA_SWING_EGILME * salinim

    # ============================================================
    # ANA GÜNCELLEME
    # ============================================================
    def guncelle(self, oyuncu, dt):
        # Hit flash
        if self.kafa_hit_flash > 0:
            self.kafa_hit_flash = max(0.0, self.kafa_hit_flash - dt)

        # Faz geçişi
        if self.faz_gecis_kalan > 0:
            self.faz_gecis_kalan = max(0.0, self.faz_gecis_kalan - dt)
            if self.faz_gecis_kalan <= 0:
                self.durum = "bekle"
                self.bekle_kalan = BEKLE_SURE
            return

        if self.olu:
            return

        # State machine ilerlet
        if self.durum == "bekle":
            self.bekle_kalan -= dt
            if self.bekle_kalan <= 0:
                self._sonraki_saldiriyi_sec()
        elif self.durum == "alt_swing":
            self._alt_swing_guncelle(dt)

        # Kafa rect'i her kare merkeze göre güncelle
        self.kafa_rect.center = (int(self.kafa_merkez[0]),
                                 int(self.kafa_merkez[1]))

        # === Oyuncu -> Boss kafa hasar ===
        sk = oyuncu.saldiri_kutusu()
        if sk is not None and sk.colliderect(self.kafa_rect):
            self.hasar_al(OYUNCU_YUMRUK_HASAR)
            oyuncu.silk_kazan(1)
            if oyuncu.saldiri_zaman > 0.05:
                oyuncu.saldiri_zaman = 0.05
        ssk = oyuncu.silkspear_kutusu()
        if ssk is not None and ssk.colliderect(self.kafa_rect):
            self.hasar_al(OYUNCU_SILKSPEAR_HASAR)
            oyuncu.silk_kazan(1)
            if oyuncu.silkspear_zaman > 0.05:
                oyuncu.silkspear_zaman = 0.05

        # === Oyuncu -> El knockback (hasar yok) ===
        if sk is not None:
            for el in self.eller:
                if sk.colliderect(el.rect):
                    if oyuncu.nisan == "yukari":
                        oyuncu.it(0, KNOCKBACK_DIKEY)
                    elif oyuncu.nisan == "asagi":
                        oyuncu.it(0, KNOCKBACK_DIKEY * 0.6)
                    else:
                        yon = -1 if oyuncu.bakis == "sag" else 1
                        oyuncu.it(KNOCKBACK_YATAY * yon, -4.0)
                    if oyuncu.saldiri_zaman > 0.05:
                        oyuncu.saldiri_zaman = 0.05
                    break
        if ssk is not None:
            for el in self.eller:
                if ssk.colliderect(el.rect):
                    yon = -1 if oyuncu.bakis == "sag" else 1
                    oyuncu.it(KNOCKBACK_YATAY * yon, -6.0)
                    if oyuncu.silkspear_zaman > 0.05:
                        oyuncu.silkspear_zaman = 0.05
                    break

        # === El -> Oyuncu hasar ===
        for el in self.eller:
            if el.rect.colliderect(oyuncu.rect):
                oyuncu.hasar_al(EL_TEMAS_HASAR)
                break

    # ============================================================
    # ÇİZİM
    # ============================================================
    def ciz(self, tuval):
        if self.faz_gecis_kalan > 0:
            t = self.faz_gecis_kalan / FAZ_GECIS_SURE
            yaricap = int(KAFA_YARI + 25 + 30 * (1 - t))
            hale = pygame.Surface((yaricap * 2, yaricap * 2), pygame.SRCALPHA)
            alpha = int(110 * t)
            pygame.draw.circle(hale, (*RENK_FAZ_HALE, alpha),
                               (yaricap, yaricap), yaricap)
            tuval.blit(hale, (int(self.kafa_merkez[0]) - yaricap,
                              int(self.kafa_merkez[1]) - yaricap))

        self._ciz_kafa(tuval, solgun=self.olu)
        for el in self.eller:
            el.ciz(tuval)

    def _ciz_kafa(self, tuval, solgun=False):
        renk = RENK_KAFA
        goz_renk = RENK_GOZ
        if self.kafa_hit_flash > 0:
            renk = RENK_KAFA_VURUS
            goz_renk = RENK_GOZ_PARLAK
        if solgun:
            renk = (40, 36, 70)
            goz_renk = (90, 70, 30)
        merkez = (int(self.kafa_merkez[0]), int(self.kafa_merkez[1]))
        pygame.draw.circle(tuval, renk, merkez, KAFA_YARI)
        pygame.draw.circle(tuval, RENK_KAFA_KENAR, merkez, KAFA_YARI, width=3)
        goz_y = merkez[1] - 6
        pygame.draw.circle(tuval, goz_renk, (merkez[0] - 22, goz_y), 9)
        pygame.draw.circle(tuval, goz_renk, (merkez[0] + 22, goz_y), 9)