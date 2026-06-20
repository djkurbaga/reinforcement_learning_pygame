"""
player.py - Oyuncu karakteri.

Mekanikler:
- 5 can, lava 2 can + orta platforma ışınlanma + 2 sn dokunulmazlık (patron için)
- Değişken zıplama (Space basılı tutuldukça yükselir)
- Yönlü saldırı (J / X tuşu) - cooldown'lu
- Bakış (sol/sağ) ve nişan (yukarı/aşağı/yatay W-S)
- Dash (RT tap): 1.5 platform anlık atılma, 0.3 sn cooldown
- Koşu (RT basılı tut): dash sonrası, normalden hızlı yatay hareket
- Silk sistemi: 0-6 silk, patrona her vuruşta +1 (DEBUG: F tuşuyla +1)
- Heal (B): 6 silk harca, 1.5 sn odaklan, 3 can yenile. Hasar alınca iptal + silk gider.
- Silkspear (K/LT): 3 silk, yatay atış, 2 platform menzil, 0.3 sn asılı kalır,
                    0.75 sn cooldown.
"""

import pygame
import arena

# ============================================================
# OYUNCU SABITLERI
# ============================================================

GENISLIK = 24
YUKSEKLIK = 36

# Hareket
YATAY_HIZ = 4.5
KOSU_HIZ = 6.8        # RT basılı tutarken (dash sonrası)
ZIPLAMA_HIZI = -13.0
ZIPLAMA_KESME = -4.0
YERCEKIMI = 0.6
MAKS_DUSME = 16.0
SUZULME_MAKS_DUSME = 3.5   # Space basılı + düşerken: yavaş süzülme

LAVA_KURTULMA_PAYI = 14

# Can ve hasar
MAKS_CAN = 5
LAVA_HASAR = 2
DOKUNULMAZLIK_SURE = 2.0

# Saldırı
SALDIRI_SURE = 0.18
SALDIRI_BEKLEME = 0.4

# Dash + koşu
DASH_HIZ = 12.0
DASH_SURE = 0.18        # ≈ 1.5 platform (12 * 0.18 * 60fps ≈ 130px)
DASH_BEKLEME = 0.3

# Silk
MAKS_SILK = 6
HEAL_SURE = 1.5         # saniye odaklanma
HEAL_MALIYET = 6
HEAL_MIKTAR = 3         # can kazanımı

# Silkspear (anlık yatay çubuk saldırı, mermi değil)
SILKSPEAR_UZUNLUK = 300  # 2 platform
SILKSPEAR_KALINLIK = 25
SILKSPEAR_GORUNUR = 0.005  # çubuk ne kadar süre görünür (çok anlık)
SILKSPEAR_ASKI = 0.2    # oyuncu bu süre havada asılı
SILKSPEAR_BEKLEME = 0.005
SILKSPEAR_MALIYET = 3

# Renkler
RENK = (210, 230, 245)
RENK_KENAR = (120, 150, 180)
RENK_BEYAZ = (255, 255, 255)
RENK_SALDIRI = (245, 220, 120)
RENK_DASH = (200, 220, 255)
RENK_SILK_DOLU = (180, 220, 255)
RENK_SILK_BOS = (50, 60, 80)
RENK_SILKSPEAR = (220, 240, 255)
RENK_HEAL_HALE = (200, 230, 255)


class Player:
    def __init__(self, x, y):
        self.rect = pygame.Rect(0, 0, GENISLIK, YUKSEKLIK)
        self.rect.centerx = x
        self.rect.bottom = y
        self.isinma_x = x

        # Hareket
        self.vx = 0.0
        self.vy = 0.0
        self.yerde = False
        self.bakis = "sag"
        self.nisan = "yatay"

        # Can / hasar
        self.can = MAKS_CAN
        self.olu = False
        self.dokunulmaz = 0.0

        # Saldırı
        self.saldiri_zaman = 0.0
        self.saldiri_bekleme = 0.0

        # Dash + koşu
        self.dash_kalan = 0.0     # >0 ise dash modunda
        self.dash_yon = 1         # +1 / -1
        self.dash_bekleme = 0.0
        self.dash_kullanildi = False  # havada dash kullanılınca True; yere değince False
        self.kosuyor = False
        self.suzuluyor = False

        # Silk
        self.silk = MAKS_SILK     # DEBUG: patron gelince 0 yap
        self.silk_bekleme = 0.0   # aynı vuruşta çoklu silk kazanmayı engeller
        self.heal_kalan = 0.0     # >0 ise odaklanıyor
        self.heal_baslangic_can = 0

        # Silkspear (anlık çubuk - askı bitince çıkar)
        self.silkspear_zaman = 0.0    # >0 ise çubuk görünür
        self.silkspear_yon = 1        # +1 sağ, -1 sol
        self.silkspear_bekleme = 0.0
        self.silkspear_aski = 0.0     # >0 ise basıştan sonra asılı (windup)
        self._spear_bekliyor = False  # askı bittiğinde çubuk doğsun

        # DEBUG: ölümsüzlük modu (G tuşu ile toggle)
        self.olumsuz = False

    # --- yardımcılar ---
    def tam_sifirla(self):
        self.rect.centerx = self.isinma_x
        self.rect.bottom = arena.ZEMIN_Y
        self.vx = self.vy = 0.0
        self.can = MAKS_CAN
        self.olu = False
        self.dokunulmaz = 0.0
        self.saldiri_zaman = self.saldiri_bekleme = 0.0
        self.dash_kalan = self.dash_bekleme = 0.0
        self.dash_kullanildi = False
        self.kosuyor = False
        self.silk = MAKS_SILK   # DEBUG
        self.silk_bekleme = 0.0
        self.heal_kalan = 0.0
        self.silkspear_zaman = 0.0
        self.silkspear_bekleme = self.silkspear_aski = 0.0
        self._spear_bekliyor = False

    def isinla_orta(self, arena_obj=None):
        # Eğer arena verildiyse mevcut (batık olmayan) platformlardan birini
        # hedef al; yoksa sabit isinma_x'i kullan (oyun başlangıcı vb.).
        if arena_obj is not None:
            self.rect.centerx = arena_obj.orta_platform_x()
        else:
            self.rect.centerx = self.isinma_x
        self.rect.bottom = arena.ZEMIN_Y
        self.vx = self.vy = 0.0
        # Lavadan ışınlanınca heal/dash/spear modları iptal olur
        self.heal_kalan = 0.0
        self.dash_kalan = 0.0
        self.silkspear_aski = 0.0

    def silk_kazan(self, miktar=1):
        # Saldırı kısmi tüketim sırasında bir-iki kare daha çarpışma
        # tetiklenebilir; kısa bir cooldown ile aynı vuruşun çoklu silk
        # vermesini engelle.
        if self.silk_bekleme <= 0:
            self.silk = min(MAKS_SILK, self.silk + miktar)
            self.silk_bekleme = 0.2

    def saldir(self):
        if self.saldiri_bekleme <= 0:
            self.saldiri_zaman = SALDIRI_SURE
            self.saldiri_bekleme = SALDIRI_BEKLEME

    def dash_baslat(self):
        # Havadayken zaten bir dash kullanıldıysa engelle (yere değmek lazım)
        if self.dash_kullanildi and not self.yerde:
            return
        if self.dash_bekleme <= 0 and self.dash_kalan <= 0:
            self.dash_kalan = DASH_SURE
            self.dash_bekleme = DASH_BEKLEME
            self.dash_yon = 1 if self.bakis == "sag" else -1
            self.dash_kullanildi = True

    def heal_baslat(self):
        if (self.heal_kalan <= 0 and self.silk >= HEAL_MALIYET
                and self.can < MAKS_CAN):
            self.heal_kalan = HEAL_SURE
            self.heal_baslangic_can = self.can

    def silkspear_at(self):
        # Basışta sadece "asılı kalma" başlar. Çubuk, askı bittiği kare çıkar.
        if (self.silkspear_bekleme <= 0 and self.silk >= SILKSPEAR_MALIYET
                and self.silkspear_aski <= 0
                and self.silkspear_zaman <= 0):
            self.silk -= SILKSPEAR_MALIYET
            self.silkspear_bekleme = SILKSPEAR_BEKLEME
            self.silkspear_aski = SILKSPEAR_ASKI
            self.silkspear_yon = 1 if self.bakis == "sag" else -1
            self._spear_bekliyor = True   # askı bitince çubuğu çıkar

    # --- ana güncelleme ---
    def guncelle(self, girdi, arena_obj, dt):
        if self.olu:
            return

        # Zamanlayıcıları azalt
        for attr in ("dokunulmaz", "saldiri_zaman", "saldiri_bekleme",
                     "dash_kalan", "dash_bekleme",
                     "silkspear_bekleme", "silkspear_aski",
                     "silkspear_zaman", "silk_bekleme"):
            v = getattr(self, attr)
            if v > 0:
                setattr(self, attr, max(0.0, v - dt))

        # Silkspear askısı bittiyse çubuğu doğur (asılı kalma sona erdi -> ŞİMŞEK)
        if self._spear_bekliyor and self.silkspear_aski <= 0:
            self.silkspear_zaman = SILKSPEAR_GORUNUR
            self._spear_bekliyor = False

        # === HEAL (odaklanma) — diğer her şeyi kilitler ===
        if self.heal_kalan > 0:
            self.heal_kalan = max(0.0, self.heal_kalan - dt)
            # Hareketsiz, asılı kalır
            self.vx = 0.0
            self.vy = 0.0
            # Bittiyse silk harca ve can ver
            if self.heal_kalan <= 0:
                self.silk -= HEAL_MALIYET
                self.can = min(MAKS_CAN, self.can + HEAL_MIKTAR)
            # heal sırasında lavaya düşme kontrolü en altta zaten var (iptal eder)
            self._lava_kontrol(arena_obj)
            return

        # === SILKSPEAR ASKISI — kısa süre havada asılı ===
        if self.silkspear_aski > 0:
            self.vx = 0.0
            self.vy = 0.0
            self._lava_kontrol(arena_obj)
            return

        # === NORMAL GİRDİ ===
        # Nişan
        if girdi.get("yukari"):
            self.nisan = "yukari"
        elif girdi.get("asagi"):
            self.nisan = "asagi"
        else:
            self.nisan = "yatay"

        # Dash başlatma (RT yeni basıldı)
        if girdi.get("dash"):
            self.dash_baslat()

        # Heal başlatma (B yeni basıldı)
        if girdi.get("heal"):
            self.heal_baslat()
            if self.heal_kalan > 0:
                # bu kareden itibaren heal modu, kalan kodu çalıştırma
                self._lava_kontrol(arena_obj)
                return

        # Silkspear (K/LT yeni basıldı)
        if girdi.get("silkspear"):
            self.silkspear_at()
            if self.silkspear_aski > 0:
                self._lava_kontrol(arena_obj)
                return

        # Saldırı
        if girdi.get("saldir"):
            self.saldir()

        # --- Yatay hareket ---
        if self.dash_kalan > 0:
            # Dash modu: sabit yüksek hız, dash yönünde
            self.vx = DASH_HIZ * self.dash_yon
        else:
            self.kosuyor = False
            hiz = YATAY_HIZ
            # RT basılı tutuluyorsa ve dash bitmişse koşu
            kosu_modu = (girdi.get("dash_basili")
                         and self.dash_bekleme < DASH_BEKLEME - 0.05)
            if kosu_modu:
                hiz = KOSU_HIZ
                self.kosuyor = True

            self.vx = 0.0
            if girdi.get("sol"):
                self.vx = -hiz
                self.bakis = "sol"
            elif girdi.get("sag"):
                self.vx = hiz
                self.bakis = "sag"
            elif kosu_modu:
                # RT basılı ama sol/sağ basılı değil -> baktığı yönde otomatik koş
                self.vx = hiz * (1 if self.bakis == "sag" else -1)

        # --- Zıplama (dash sırasında yok) ---
        if self.dash_kalan <= 0:
            if girdi.get("zipla") and self.yerde:
                self.vy = ZIPLAMA_HIZI
                self.yerde = False
            if not girdi.get("zipla_basili") and self.vy < ZIPLAMA_KESME:
                self.vy = ZIPLAMA_KESME

        # --- Yer çekimi (dash sırasında yok) ---
        if self.dash_kalan > 0:
            self.vy = 0.0
        else:
            self.vy = min(self.vy + YERCEKIMI, MAKS_DUSME)
            # Paraşüt: havada, düşerken, Space basılıysa süzülme
            if (not self.yerde and self.vy > 0
                    and girdi.get("zipla_basili")):
                self.vy = min(self.vy, SUZULME_MAKS_DUSME)
                self.suzuluyor = True
            else:
                self.suzuluyor = False

        # --- Hareketi uygula ---
        self.rect.x += int(self.vx)
        onceki_bottom = self.rect.bottom
        self.rect.y += int(self.vy)
        self.yerde = False
        for plat in arena_obj.platformlar:
            if self.rect.colliderect(plat):
                if self.vy >= 0 and onceki_bottom <= plat.top + LAVA_KURTULMA_PAYI:
                    self.rect.bottom = plat.top
                    self.vy = 0.0
                    self.yerde = True
        if not self.yerde and self.vy >= 0:
            for plat in arena_obj.platformlar:
                if (abs(self.rect.bottom - plat.top) <= 1
                        and plat.left < self.rect.centerx < plat.right):
                    self.rect.bottom = plat.top
                    self.vy = 0.0
                    self.yerde = True
                    break

        # Yere değdiyse dash hakkı yenilenir
        if self.yerde:
            self.dash_kullanildi = False

        self._lava_kontrol(arena_obj)

    def _lava_kontrol(self, arena_obj):
        if arena_obj.lavaya_dustu_mu(self.rect):
            if self.olumsuz:
                self.isinla_orta(arena_obj)
                return
            self.can -= LAVA_HASAR
            if self.can <= 0:
                self.can = 0
                self.olu = True
            else:
                self.isinla_orta(arena_obj)
                self.dokunulmaz = DOKUNULMAZLIK_SURE

    def it(self, vx, vy):
        """Knockback: dış kuvvet uygula (örn. patron ellerine vurunca)."""
        if self.olu:
            return
        self.vx = vx
        self.vy = vy
        if vy < 0:
            self.yerde = False

    def hasar_al(self, miktar=1):
        """Patron saldırılarından gelen hasar. Dokunulmazsa engellenir."""
        if self.dokunulmaz > 0 or self.olu or self.olumsuz:
            return
        # Heal sırasında hasar alırsa: silk gider, heal iptal
        if self.heal_kalan > 0:
            self.silk = 0
            self.heal_kalan = 0.0
        self.can -= miktar
        if self.can <= 0:
            self.can = 0
            self.olu = True
        else:
            self.dokunulmaz = DOKUNULMAZLIK_SURE

    # --- saldırı vuruş kutusu (patron için) ---
    def saldiri_kutusu(self):
        if self.saldiri_zaman <= 0:
            return None
        menzil = 38
        if self.nisan == "yukari":
            return pygame.Rect(self.rect.x - 4, self.rect.top - menzil,
                               self.rect.width + 8, menzil)
        if self.nisan == "asagi":
            return pygame.Rect(self.rect.x - 4, self.rect.bottom,
                               self.rect.width + 8, menzil)
        if self.bakis == "sag":
            return pygame.Rect(self.rect.right, self.rect.y - 2, menzil,
                               self.rect.height + 4)
        return pygame.Rect(self.rect.left - menzil, self.rect.y - 2, menzil,
                           self.rect.height + 4)

    # --- silkspear vurus kutusu (patron icin) ---
    def silkspear_kutusu(self):
        """Aktif silkspear cubugunun dikdortgeni (yoksa None)."""
        if self.silkspear_zaman <= 0:
            return None
        y = self.rect.centery - SILKSPEAR_KALINLIK // 2
        if self.silkspear_yon > 0:
            return pygame.Rect(self.rect.right, y,
                               SILKSPEAR_UZUNLUK, SILKSPEAR_KALINLIK)
        else:
            return pygame.Rect(self.rect.left - SILKSPEAR_UZUNLUK, y,
                               SILKSPEAR_UZUNLUK, SILKSPEAR_KALINLIK)

    # --- çizim ---
    def ciz(self, tuval):
        renk = RENK
        # Dash sırasında parlak iz
        if self.dash_kalan > 0:
            renk = RENK_DASH
        # Dokunulmazken yanıp sönme
        elif self.dokunulmaz > 0:
            if int(self.dokunulmaz * 12) % 2 == 0:
                renk = RENK_BEYAZ
        # Heal sırasında parlak hale
        if self.heal_kalan > 0:
            t = (HEAL_SURE - self.heal_kalan) / HEAL_SURE  # 0->1
            yaricap = int(20 + 14 * t)
            hale = pygame.Surface((yaricap * 2, yaricap * 2), pygame.SRCALPHA)
            pygame.draw.circle(hale, (*RENK_HEAL_HALE, 60),
                               (yaricap, yaricap), yaricap)
            tuval.blit(hale, (self.rect.centerx - yaricap,
                              self.rect.centery - yaricap))
            renk = RENK_HEAL_HALE

        pygame.draw.rect(tuval, renk, self.rect, border_radius=4)
        pygame.draw.rect(tuval, RENK_KENAR, self.rect, width=2, border_radius=4)

        # NOT: saldırı kutusu ve silkspear çubuğu artık ayrı bir metodla
        # her şeyin EN ÜSTÜNE çizilir (game.py'den sonra çağrılır).

    def ciz_saldirilar_ust(self, tuval):
        """Saldırı kutusu ve silkspear çubuğunu HER ŞEYİN üstüne çizer.
        game.py bunu en son çağırır - patron elleri/kafa gibi şeylerin üstünde
        görünür."""
        sk = self.saldiri_kutusu()
        if sk is not None:
            pygame.draw.rect(tuval, RENK_SALDIRI, sk, border_radius=3)
        ssk = self.silkspear_kutusu()
        if ssk is not None:
            pygame.draw.rect(tuval, RENK_SILKSPEAR, ssk, border_radius=4)