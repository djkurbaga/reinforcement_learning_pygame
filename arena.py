"""
arena.py - Dövüş arenası: 16:9 sabit tuval, tabana yayılı lava, üstünde yüzen kaya platformlar.

Harita:
    # = kaya platform   (lavanın üstünde yüzen ada)
    o = lava boşluğu    (platformlar arası açıklık)

Lava arenanın TÜM tabanına yayılır (LAVA_UST_Y'den aşağısı). Kaya platformlar
bu lavanın LAVA_OFFSET kadar üstünde durur. Slam ile bir kaya battığında
altındaki lava açığa çıkar.
"""

import pygame

# ============================================================
# TUVAL (16:9 sabit iç çözünürlük; ekrana ölçeklenir)
# ============================================================
TUVAL_GENISLIK = 960
TUVAL_YUKSEKLIK = 540

# Birim -> piksel
BIRIM = 18
KAYA_BIRIM = 6
LAVA_BIRIM = 4
KAYA_GENISLIK = KAYA_BIRIM * BIRIM   # 80
LAVA_GENISLIK = LAVA_BIRIM * BIRIM   # 64

# Harita
HARITA = "oo#####oo"

# Dikey yerleşim
ZEMIN_Y = 380          # kaya platform üst yüzeyi
PLATFORM_KALINLIK = 44
LAVA_OFFSET = 64       # lava, kaya üstünden bu kadar aşağıda
LAVA_UST_Y = ZEMIN_Y + LAVA_OFFSET   # lavanın üst yüzeyi (tabana yayılır)

FPS = 60

# Renkler
RENK_ARKA = (24, 18, 28)
RENK_KAYA = (92, 80, 72)
RENK_KAYA_UST = (124, 108, 95)
RENK_KAYA_KENAR = (58, 48, 43)
RENK_LAVA = (200, 70, 25)
RENK_LAVA_PARLAK = (250, 160, 50)


class Arena:
    def __init__(self, harita=HARITA):
        self.harita = harita
        self.platformlar = []
        self._kur()

    def _kur(self):
        # Arenanın toplam genişliğini hesapla, sonra tuvale ortala
        toplam = 0
        for h in self.harita:
            toplam += KAYA_GENISLIK if h == "#" else LAVA_GENISLIK
        baslangic_x = (TUVAL_GENISLIK - toplam) // 2

        x = baslangic_x
        for hucre in self.harita:
            if hucre == "#":
                rect = pygame.Rect(x, ZEMIN_Y, KAYA_GENISLIK, PLATFORM_KALINLIK)
                self.platformlar.append(rect)
                x += KAYA_GENISLIK
            else:
                x += LAVA_GENISLIK

    def orta_platform_x(self):
        if not self.platformlar:
            return TUVAL_GENISLIK // 2
        orta = self.platformlar[len(self.platformlar) // 2]
        return orta.centerx

    def baslangic_x(self):
        return self.orta_platform_x()

    def lavaya_dustu_mu(self, oyuncu_rect):
        """Lava artık tüm tabanda: oyuncunun altı LAVA_UST_Y'yi geçtiyse lavadadır."""
        return oyuncu_rect.bottom >= LAVA_UST_Y

    def ciz(self, tuval):
        tuval.fill(RENK_ARKA)

        # Lava: tüm taban
        lava_rect = pygame.Rect(0, LAVA_UST_Y, TUVAL_GENISLIK,
                                TUVAL_YUKSEKLIK - LAVA_UST_Y)
        pygame.draw.rect(tuval, RENK_LAVA, lava_rect)
        # üst parıltı şeridi
        pygame.draw.rect(tuval, RENK_LAVA_PARLAK,
                         (0, LAVA_UST_Y, TUVAL_GENISLIK, 6))
        # derinlik gradyanı
        derinlik = pygame.Surface((TUVAL_GENISLIK, lava_rect.height),
                                  pygame.SRCALPHA)
        for i in range(lava_rect.height):
            a = int(150 * (i / max(1, lava_rect.height)))
            pygame.draw.line(derinlik, (60, 10, 0, a), (0, i),
                             (TUVAL_GENISLIK, i))
        tuval.blit(derinlik, (0, LAVA_UST_Y))

        # Atmosfer parıltısı (lava üstü hafif ışık)
        parilti = pygame.Surface((TUVAL_GENISLIK, 60), pygame.SRCALPHA)
        for i in range(60):
            a = int(50 * (1 - i / 60))
            pygame.draw.line(parilti, (200, 70, 20, a), (0, i),
                             (TUVAL_GENISLIK, i))
        tuval.blit(parilti, (0, LAVA_UST_Y - 60))

        # Kaya platformlar (yüzen adalar)
        for plat in self.platformlar:
            pygame.draw.rect(tuval, RENK_KAYA, plat)
            pygame.draw.rect(tuval, RENK_KAYA_UST,
                             (plat.x, plat.y, plat.width, 5))
            pygame.draw.rect(tuval, RENK_KAYA_KENAR, plat, width=2)