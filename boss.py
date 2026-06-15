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
BEKLE_SURE = 1.0

# ============================================================
# 1. HAREKET — ALT SWING
# ============================================================
# Alt el bir yöne (sağ ya da sol) gidip diğer uca süpürür.
# Süre = 2 sn (oyuncu el üstünden zıplayıp atlamalı).
# El "platform üstüne çarpacak yükseklikte" iner -> y = ZEMIN_Y - oyuncu_yuk/2
# Yani el yatay ortalama, dikey olarak oyuncunun yan vurma seviyesinde.
SWING_SURE = 2.0           # toplam saldırı süresi
SWING_HAZIRLIK_ORAN = 0.20 # ilk %20: el baslangic konumdan swing baslangicina gider
SWING_SUPURME_ORAN = 0.60  # orta %60: gercek supurme
SWING_DONUS_ORAN = 0.20    # son %20: el swing sonundan baslangic konumuna doner
SWING_Y = arena.ZEMIN_Y - 26   # platformun üstünden 26 px yukarı (oyuncu yarısı)
# Süpürme uç noktaları (sahnenin sol/sağ kenarına yakın)
SWING_SOL_X = 60
SWING_SAG_X = arena.TUVAL_GENISLIK - 60   # 900
# Kafa hareketi (swing sırasında elin yönüne doğru biraz kayar + aşağı eğilir)
KAFA_SWING_KAYMA = 60
KAFA_SWING_EGILME = 60

# ============================================================
# 2. HAREKET — UST SLAM
# ============================================================
# Ust el rastgele 2 KOMSU platform secer, ustlerinde 0.6 sn telegraflanir
# (el parlar, hedef platformlarda uyari cercevesi), sonra 0.2 sn hizli
# inisle vurur. Platformlar 5 sn batik kalir (lavaya gomulur). El sonra
# 0.5 sn'lik donusle baslangic konumuna yumusakca doner.
#
# Kafa: telegrafta yukari kalkar, vurma aninda elle beraber asagi
# savrulur, donus sirasinda eski yerine doner.
SLAM_TELEGRAF_SURE = 0.6
SLAM_INIS_SURE = 0.2
SLAM_BATIK_SURE = 5.0
SLAM_DONUS_SURE = 0.5
SLAM_INIS_Y = arena.ZEMIN_Y - 4   # platform ustune cok yakin (vurus noktasi)
KAFA_SLAM_KALKMA = 80             # telegrafta yukari kalkma
KAFA_SLAM_SAVRULMA = 100        # vurma aninda asagi savrulma

# ============================================================
# 3. HAREKET — ALT ALKIS
# ============================================================
# Iki alt el once disa acilir (sol sola, sag saga), sonra telegraf
# pozisyonunda bekler, sonra hizla merkeze gelip alkis yaparlar,
# alkis pozunda 1.5 sn beklerler, sonra eski konumlarina dönerler.
# Kafa: acilma+telegraf sirasinda yukari kalkar, alkis aninda asagi
# savrulur, tutma boyunca yavasca eski konumuna doner.
ALKIS_ACILMA_SURE = 0.4
ALKIS_TELEGRAF_SURE = 0.6
ALKIS_VURUS_SURE = 0.3
ALKIS_TUTMA_SURE = 1.5
ALKIS_DONUS_SURE = 0.5
ALKIS_DIS_OFFSET = 110            # baslangic konumundan disa kayma miktari
ALKIS_BULUSMA_SOL_X = arena.TUVAL_GENISLIK // 2 - EL_GENISLIK // 2  # 444
ALKIS_BULUSMA_SAG_X = arena.TUVAL_GENISLIK // 2 + EL_GENISLIK // 2  # 516
ALKIS_Y = arena.ZEMIN_Y - 26      # oyuncu seviyesinde (swing y ile ayni)

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
    def __init__(self, arena_obj=None):
        self._son_arena = arena_obj   # slam icin platform listesine erisim
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
        # alt_swing:
        self.swing_t = 0.0
        self.swing_el_index = -1
        self.swing_baslangic_x = 0
        self.swing_bitis_x = 0
        # ust_slam:
        self.slam_t = 0.0
        self.slam_el_index = -1
        self.slam_hedef_x = 0
        self.slam_hedef_platformlar = []
        self.slam_batik_platformlar = []
        self.slam_batik_zamanlar = []
        # alt_alkis:
        self.alkis_t = 0.0


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
        # Faz gecisinde batik platformlari hemen geri ekle (temiz baslangic)
        if self._son_arena is not None:
            for plat in self.slam_batik_platformlar:
                if plat not in self._son_arena.platformlar:
                    self._son_arena.platformlar.append(plat)
        self.slam_batik_platformlar = []
        self.slam_batik_zamanlar = []

    # ============================================================
    # STATE MACHINE
    # ============================================================
    def _sonraki_saldiriyi_sec(self):
        """Rastgele bir saldırı seçer."""
        secenekler = ["alt_swing", "ust_slam", "alt_alkis"]
        secim = random.choice(secenekler)
        if secim == "alt_swing":
            self._alt_swing_baslat()
        elif secim == "ust_slam":
            self._ust_slam_baslat()
        elif secim == "alt_alkis":
            self._alt_alkis_baslat()

    # ------------------------------------------------------------
    # 1. HAREKET: ALT SWING
    # ------------------------------------------------------------
    def _alt_swing_baslat(self):
        """Rastgele bir alt el seçilir. El, başlangıç konumunda KALIR;
        hazırlık fazında yumuşakça swing başlangıç noktasına gidecek."""
        self.durum = "alt_swing"
        self.aktif_hareket = "Alt swing"
        self.swing_t = 0.0
        self.swing_el_index = random.choice([2, 3])
        el = self.eller[self.swing_el_index]
        el.aktif = True
        # Sol alt -> sağa süpürür, Sağ alt -> sola süpürür
        if el.isim == "sol_alt":
            self.swing_baslangic_x = SWING_SOL_X
            self.swing_bitis_x = SWING_SAG_X
        else:
            self.swing_baslangic_x = SWING_SAG_X
            self.swing_bitis_x = SWING_SOL_X
        # Eli konumunda BIRAK - ışınlanma yok

    def _alt_swing_guncelle(self, dt):
        self.swing_t += dt
        ham = self.swing_t / SWING_SURE

        if ham >= 1.0:
            # Bitti - güvenlik için el başlangıcına ince ayar, bekleme moduna geç
            el = self.eller[self.swing_el_index]
            el.rect.center = el.baslangic_konum
            el.aktif = False
            self.kafa_merkez = list(self.kafa_temel)
            self.durum = "bekle"
            self.bekle_kalan = BEKLE_SURE
            self.aktif_hareket = ""
            return

        el = self.eller[self.swing_el_index]
        ebx, eby = el.baslangic_konum
        sbx, sby = self.swing_baslangic_x, SWING_Y
        bx, by = self.swing_bitis_x, SWING_Y
        yon = 1 if self.swing_bitis_x > self.swing_baslangic_x else -1

        # === EL KONUMU (3 fazlı, ışınlanma yok) ===
        if ham < SWING_HAZIRLIK_ORAN:
            # Faz A — HAZIRLIK: başlangıç konumundan swing başlangıcına yumuşak in
            lt = _ease_in_out(ham / SWING_HAZIRLIK_ORAN)
            x = ebx + (sbx - ebx) * lt
            y = eby + (sby - eby) * lt
            egilme = lt   # kafa aşağı eğilmeye başlar
        elif ham < SWING_HAZIRLIK_ORAN + SWING_SUPURME_ORAN:
            # Faz B — SÜPÜRME
            lt_raw = (ham - SWING_HAZIRLIK_ORAN) / SWING_SUPURME_ORAN
            lt = _ease_in_out(lt_raw)
            x = sbx + (bx - sbx) * lt
            y = sby
            egilme = 1.0
        else:
            # Faz C — DÖNÜŞ
            lt = _ease_in_out(
                (ham - SWING_HAZIRLIK_ORAN - SWING_SUPURME_ORAN)
                / SWING_DONUS_ORAN)
            x = bx + (ebx - bx) * lt
            y = by + (eby - by) * lt
            egilme = 1.0 - lt

        el.rect.center = (int(x), int(y))

        # === KAFA YATAY KAYMA: yay gerip atan adam gibi ===
        # Hazırlık: 0 -> -1 (ELİN GELECEĞİ YÖNÜN TERSİ, "geri çekilme")
        # Sweep ilk yarı: -1 -> 0 (merkeze geri)
        # Sweep ikinci yarı: 0 -> +1 (SWEEP YÖNÜNE, "savrulma")
        # Dönüş: +1 -> 0 (merkeze geri)
        haz_son = SWING_HAZIRLIK_ORAN                    # 0.2
        sweep_orta = haz_son + SWING_SUPURME_ORAN / 2    # 0.5
        sweep_son = haz_son + SWING_SUPURME_ORAN         # 0.8
        if ham < haz_son:
            kayma_carpan = -_ease_in_out(ham / haz_son)
        elif ham < sweep_orta:
            kayma_carpan = -1.0 + _ease_in_out(
                (ham - haz_son) / (sweep_orta - haz_son))
        elif ham < sweep_son:
            kayma_carpan = _ease_in_out(
                (ham - sweep_orta) / (sweep_son - sweep_orta))
        else:
            kayma_carpan = 1.0 - _ease_in_out(
                (ham - sweep_son) / SWING_DONUS_ORAN)

        self.kafa_merkez[0] = (self.kafa_temel[0]
                               + yon * KAFA_SWING_KAYMA * kayma_carpan)
        self.kafa_merkez[1] = self.kafa_temel[1] + KAFA_SWING_EGILME * egilme

    # ------------------------------------------------------------
    # 2. HAREKET: UST SLAM
    # ------------------------------------------------------------
    def _ust_slam_baslat(self):
        """Rastgele bir ust el secer; arena'nin platform listesinden 2
        komsu platform secip onlari hedef alir. El kendi yerinde kalir,
        telegraf fazinda hedef ustune yumusak in."""
        self.durum = "ust_slam"
        self.aktif_hareket = "Ust slam"
        self.slam_t = 0.0
        self.slam_el_index = random.choice([0, 1])
        el = self.eller[self.slam_el_index]
        el.aktif = True

        # Komşu 2 platform seç (indeks 0-1, 1-2, 2-3, 3-4)
        # Komsu 2 platform sec (mevcut, batik olmayanlardan)
        mevcut = list(self._son_arena.platformlar)
        if len(mevcut) < 3:
            # Yetersiz platform - oyuncu yere basacak yer kalmamali
            # Slam iptal, alt_swing'e gec
            self.durum = "bekle"
            self.bekle_kalan = BEKLE_SURE
            self.aktif_hareket = ""
            el.aktif = False
            return
        # Mevcut platformlari x'e gore sirala (komsu icin)
        mevcut.sort(key=lambda r: r.x)
        ilk = random.randint(0, len(mevcut) - 2)
        self.slam_hedef_platformlar = [mevcut[ilk], mevcut[ilk + 1]]
        # Vurus orta noktasi (iki platformun orta noktalari arasi)
        p1 = self.slam_hedef_platformlar[0]
        p2 = self.slam_hedef_platformlar[1]
        self.slam_hedef_x = (p1.centerx + p2.centerx) // 2

    def _ust_slam_guncelle(self, dt, arena_obj):
        self.slam_t += dt
        el = self.eller[self.slam_el_index]
        ebx, eby = el.baslangic_konum
        hx = self.slam_hedef_x
        # Telegraf hedef y: platform ustunun biraz uzerinde, vurmaya hazirlanir
        telegraf_y = arena.ZEMIN_Y - 80
        inis_y = SLAM_INIS_Y

        # Faz sinirlari
        t_telegraf_son = SLAM_TELEGRAF_SURE
        t_inis_son = t_telegraf_son + SLAM_INIS_SURE
        t_donus_son = t_inis_son + SLAM_DONUS_SURE

        if self.slam_t < t_telegraf_son:
            # TELEGRAF: el baslangic konumdan hedefin ustune yumusak in
            lt = _ease_in_out(self.slam_t / SLAM_TELEGRAF_SURE)
            x = ebx + (hx - ebx) * lt
            y = eby + (telegraf_y - eby) * lt
            el.rect.center = (int(x), int(y))
            # Kafa: yukari kalk (lt 0->1)
            self.kafa_merkez[0] = self.kafa_temel[0]
            self.kafa_merkez[1] = self.kafa_temel[1] - KAFA_SLAM_KALKMA * lt
        elif self.slam_t < t_inis_son:
            # INIS: el hizli aşağı (hızlı interpolasyon)
            lt_raw = (self.slam_t - t_telegraf_son) / SLAM_INIS_SURE
            # Daha hızlı bir egri: kare (vurma hissi)
            lt = lt_raw * lt_raw
            x = hx
            y = telegraf_y + (inis_y - telegraf_y) * lt
            el.rect.center = (int(x), int(y))
            # Kafa: yukaridan asagi savrulma
            self.kafa_merkez[0] = self.kafa_temel[0]
            self.kafa_merkez[1] = (self.kafa_temel[1]
                                   - KAFA_SLAM_KALKMA * (1 - lt)
                                   + KAFA_SLAM_SAVRULMA * lt)

        elif self.slam_t < t_donus_son:
            # Donus fazinin BASLANGICINDA platformlari gom (tek seferlik)
            # Bayrak olarak hedef listesi kullanilir; gomme sonunda temizlenir
            if self.slam_hedef_platformlar:
                self._slam_platformlari_gom(arena_obj)
            # DONUS: el vurus noktasindan baslangic konumuna yumusak don
            lt = _ease_in_out(
                (self.slam_t - t_inis_son) / SLAM_DONUS_SURE)
            x = hx + (ebx - hx) * lt
            y = inis_y + (eby - inis_y) * lt
            el.rect.center = (int(x), int(y))
            # Kafa: savrulmadan eski yerine yumusak
            self.kafa_merkez[0] = self.kafa_temel[0]
            self.kafa_merkez[1] = (self.kafa_temel[1]
                                   + KAFA_SLAM_SAVRULMA * (1 - lt))
        else:
            # Bitti
            el.rect.center = el.baslangic_konum
            el.aktif = False
            self.kafa_merkez = list(self.kafa_temel)
            self.durum = "bekle"
            self.bekle_kalan = BEKLE_SURE
            self.aktif_hareket = ""
            # NOT: batik platformlar bekle modunda da geri gelecek

    def _slam_platformlari_gom(self, arena_obj):
        """Hedef platformlari arena'nin platform listesinden cikar; geri
        gelmeleri icin geri sayim baslat. Sonra hedef listesini temizle ki
        ayni slam tekrar gomme yapmasin."""
        for plat in self.slam_hedef_platformlar:
            if plat in arena_obj.platformlar:
                arena_obj.platformlar.remove(plat)
                self.slam_batik_platformlar.append(plat)
                self.slam_batik_zamanlar.append(SLAM_BATIK_SURE)
        # Bayrak temizle
        self.slam_hedef_platformlar = []

    def _batik_platformlari_guncelle(self, dt, arena_obj):
        """Her kare cagrilir. Batik platformlarin geri sayim suresini azaltir;
        bitince platformu arena'ya geri ekler."""
        if not self.slam_batik_platformlar:
            return
        yeni_p = []
        yeni_z = []
        for plat, kalan in zip(self.slam_batik_platformlar,
                               self.slam_batik_zamanlar):
            kalan -= dt
            if kalan <= 0:
                # Geri ekle (orijinal listede dogru sirada olmayabilir; basit
                # yontem: sonuna ekle, sira gorseli etkilemez cunku Rect'ler
                # mutlak konumlu)
                arena_obj.platformlar.append(plat)
            else:
                yeni_p.append(plat)
                yeni_z.append(kalan)
        self.slam_batik_platformlar = yeni_p
        self.slam_batik_zamanlar = yeni_z


    # ------------------------------------------------------------
    # 3. HAREKET: ALT ALKIS
    # ------------------------------------------------------------
    def _alt_alkis_baslat(self):
        """Iki alt el aktiflesir; konumlari _alt_alkis_guncelle'de fazlara
        gore yumusakca degisir, isinlanma yok."""
        self.durum = "alt_alkis"
        self.aktif_hareket = "Alt alkis"
        self.alkis_t = 0.0
        self.eller[2].aktif = True  # sol_alt
        self.eller[3].aktif = True  # sag_alt

    def _alt_alkis_guncelle(self, dt):
        self.alkis_t += dt
        sol = self.eller[2]
        sag = self.eller[3]
        sbx, sby = sol.baslangic_konum
        gbx, gby = sag.baslangic_konum

        # Faz hedef noktalari
        sol_acik = (sbx - ALKIS_DIS_OFFSET, sby)
        sag_acik = (gbx + ALKIS_DIS_OFFSET, gby)
        sol_alkis = (ALKIS_BULUSMA_SOL_X, ALKIS_Y)
        sag_alkis = (ALKIS_BULUSMA_SAG_X, ALKIS_Y)

        # Faz sinir zamanlari
        t1 = ALKIS_ACILMA_SURE
        t2 = t1 + ALKIS_TELEGRAF_SURE
        t3 = t2 + ALKIS_VURUS_SURE
        t4 = t3 + ALKIS_TUTMA_SURE
        t5 = t4 + ALKIS_DONUS_SURE

        if self.alkis_t < t1:
            # FAZ 1 - Acilma: baslangic -> acik konum
            lt = _ease_in_out(self.alkis_t / ALKIS_ACILMA_SURE)
            sol_x = sbx + (sol_acik[0] - sbx) * lt
            sol_y = sby + (sol_acik[1] - sby) * lt
            sag_x = gbx + (sag_acik[0] - gbx) * lt
            sag_y = gby + (sag_acik[1] - gby) * lt
            kafa_y_off = -KAFA_SLAM_KALKMA * lt
        elif self.alkis_t < t2:
            # FAZ 2 - Telegraf: acik konumda bekle
            sol_x, sol_y = sol_acik
            sag_x, sag_y = sag_acik
            kafa_y_off = -KAFA_SLAM_KALKMA
        elif self.alkis_t < t3:
            # FAZ 3 - Vurus (alkis): acik -> alkis konumu (hizlanan)
            lt_raw = (self.alkis_t - t2) / ALKIS_VURUS_SURE
            lt = lt_raw * lt_raw   # hizlanan egri
            sol_x = sol_acik[0] + (sol_alkis[0] - sol_acik[0]) * lt
            sol_y = sol_acik[1] + (sol_alkis[1] - sol_acik[1]) * lt
            sag_x = sag_acik[0] + (sag_alkis[0] - sag_acik[0]) * lt
            sag_y = sag_acik[1] + (sag_alkis[1] - sag_acik[1]) * lt
            # Kafa: yukaridan asagi savrulma
            kafa_y_off = (-KAFA_SLAM_KALKMA
                          + (KAFA_SLAM_KALKMA + KAFA_SLAM_SAVRULMA) * lt)
        elif self.alkis_t < t4:
            # FAZ 4 - Tutma: alkis pozunda sabit, kafa yavas yavas geri 0
            sol_x, sol_y = sol_alkis
            sag_x, sag_y = sag_alkis
            lt = (self.alkis_t - t3) / ALKIS_TUTMA_SURE
            kafa_y_off = KAFA_SLAM_SAVRULMA * (1 - _ease_in_out(lt))
        elif self.alkis_t < t5:
            # FAZ 5 - Donus: alkis -> baslangic
            lt = _ease_in_out((self.alkis_t - t4) / ALKIS_DONUS_SURE)
            sol_x = sol_alkis[0] + (sbx - sol_alkis[0]) * lt
            sol_y = sol_alkis[1] + (sby - sol_alkis[1]) * lt
            sag_x = sag_alkis[0] + (gbx - sag_alkis[0]) * lt
            sag_y = sag_alkis[1] + (gby - sag_alkis[1]) * lt
            kafa_y_off = 0.0
        else:
            # Bitti
            sol.rect.center = sol.baslangic_konum
            sag.rect.center = sag.baslangic_konum
            sol.aktif = False
            sag.aktif = False
            self.kafa_merkez = list(self.kafa_temel)
            self.durum = "bekle"
            self.bekle_kalan = BEKLE_SURE
            self.aktif_hareket = ""
            return

        sol.rect.center = (int(sol_x), int(sol_y))
        sag.rect.center = (int(sag_x), int(sag_y))
        self.kafa_merkez[0] = self.kafa_temel[0]
        self.kafa_merkez[1] = self.kafa_temel[1] + kafa_y_off

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

        # Arena referansini guncelle (her kare; ilk frame'de set olur)
        self._son_arena = self._son_arena if self._son_arena else None

        # State machine ilerlet
        if self.durum == "bekle":
            self.bekle_kalan -= dt
            if self.bekle_kalan <= 0:
                self._sonraki_saldiriyi_sec()
        elif self.durum == "alt_swing":
            self._alt_swing_guncelle(dt)
        elif self.durum == "ust_slam":
            self._ust_slam_guncelle(dt, self._son_arena)
        elif self.durum == "alt_alkis":
            self._alt_alkis_guncelle(dt)

        # Batık platformlar (slam sonrasi) her kare geri sayim
        self._batik_platformlari_guncelle(dt, self._son_arena)

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

        # Slam telegraf cercevesi (hedef platformlarda sari yanip sonen)
        if self.durum == "ust_slam" and self.slam_t < SLAM_TELEGRAF_SURE:
            yanip_son = (math.sin(self.slam_t * 18) + 1) / 2  # 0..1
            renk_alpha = int(120 + 100 * yanip_son)
            for plat in self.slam_hedef_platformlar:
                cerceve = pygame.Surface(
                    (plat.width + 6, plat.height + 6), pygame.SRCALPHA)
                pygame.draw.rect(
                    cerceve, (250, 180, 60, renk_alpha),
                    cerceve.get_rect(), width=3, border_radius=4)
                tuval.blit(cerceve, (plat.x - 3, plat.y - 3))

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