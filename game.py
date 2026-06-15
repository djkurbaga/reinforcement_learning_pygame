"""
game.py - Ana oyun döngüsü. Tam ekran + 16:9 ölçekleme.

Kontroller:
    Hareket: Sol/Sağ veya A/D     (Xbox: analog/D-pad)
    Zıpla:   Space                (Xbox: A)
    Nişan:   W = yukarı, S = aşağı
    Saldır:  J                    (Xbox: X)
    Dash:    Shift                (Xbox: RT)         basılı tut = koşu
    Heal:    B                    (Xbox: B)
    Spear:   K                    (Xbox: LT)
    DEBUG:   F = silk +1,  G = olumsuzluk modu toggle
    F11 tam ekran,  R tekrar (ölünce),  ESC çıkış
"""

import sys
import pygame

import arena
from player import Player, MAKS_CAN, MAKS_SILK
from boss import Boss

ANALOG_ESIK = 0.4
XBOX_A = 0
XBOX_B = 1
XBOX_X = 2
XBOX_LT = 4    # sol omuz tuşu (LB de olabilir, kola göre değişir)
XBOX_RT = 5    # sağ omuz tuşu
# Tetik analoglarını da destekleyelim (bazı kollar LT/RT'yi eksen olarak verir)
XBOX_LT_EKSEN = 4
XBOX_RT_EKSEN = 5

PENCERE_BASLANGIC = (960, 540)


def kol_bagla():
    pygame.joystick.init()
    if pygame.joystick.get_count() > 0:
        kol = pygame.joystick.Joystick(0)
        kol.init()
        print(f"Oyun kolu bagli: {kol.get_name()}")
        return kol
    return None


def _eksen_var(kol, idx):
    try:
        return kol.get_numaxes() > idx
    except pygame.error:
        return False


def _btn_var(kol, idx):
    try:
        return kol.get_numbuttons() > idx
    except pygame.error:
        return False


def girdi_oku(kol, onceki):
    """
    onceki: bir önceki karenin "basılı mı" durumları (kenar algılama için)
    Döner: (girdi sözlüğü, yeni onceki sözlüğü)
    """
    t = pygame.key.get_pressed()
    sol = t[pygame.K_LEFT] or t[pygame.K_a]
    sag = t[pygame.K_RIGHT] or t[pygame.K_d]
    yukari = t[pygame.K_w]
    asagi = t[pygame.K_s]
    space_basili = t[pygame.K_SPACE]
    saldir = t[pygame.K_j]
    dash_basili = t[pygame.K_LSHIFT] or t[pygame.K_RSHIFT]
    heal_basili = t[pygame.K_b]
    spear_basili = t[pygame.K_k]
    debug_silk = t[pygame.K_f]

    if kol is not None:
        try:
            ex = kol.get_axis(0)
            if ex < -ANALOG_ESIK: sol = True
            if ex > ANALOG_ESIK: sag = True
            ey = kol.get_axis(1)
            if ey < -ANALOG_ESIK: yukari = True
            if ey > ANALOG_ESIK: asagi = True
            if kol.get_numhats() > 0:
                hx, hy = kol.get_hat(0)
                if hx < 0: sol = True
                if hx > 0: sag = True
                if hy > 0: yukari = True
                if hy < 0: asagi = True

            if _btn_var(kol, XBOX_A) and kol.get_button(XBOX_A):
                space_basili = True
            if _btn_var(kol, XBOX_X) and kol.get_button(XBOX_X):
                saldir = True
            if _btn_var(kol, XBOX_B) and kol.get_button(XBOX_B):
                heal_basili = True

            # RT: önce buton olarak dene, yoksa eksen (tetik)
            if _btn_var(kol, XBOX_RT) and kol.get_button(XBOX_RT):
                dash_basili = True
            elif _eksen_var(kol, XBOX_RT_EKSEN):
                # tetikler genelde -1 -> +1, yarısı geçince basılı say
                if kol.get_axis(XBOX_RT_EKSEN) > 0.3:
                    dash_basili = True
            # LT
            if _btn_var(kol, XBOX_LT) and kol.get_button(XBOX_LT):
                spear_basili = True
            elif _eksen_var(kol, XBOX_LT_EKSEN):
                if kol.get_axis(XBOX_LT_EKSEN) > 0.3:
                    spear_basili = True
        except pygame.error:
            pass

    # Kenar algılama: bu kare yeni basıldı mı?
    zipla = space_basili and not onceki["space"]
    dash = dash_basili and not onceki["dash"]
    heal = heal_basili and not onceki["heal"]
    spear = spear_basili and not onceki["spear"]
    debug = debug_silk and not onceki["debug"]

    girdi = {
        "sol": sol, "sag": sag,
        "zipla": zipla, "zipla_basili": space_basili,
        "yukari": yukari, "asagi": asagi,
        "saldir": saldir,
        "dash": dash, "dash_basili": dash_basili,
        "heal": heal,
        "silkspear": spear,
        "debug_silk": debug,
    }
    yeni_onceki = {
        "space": space_basili, "dash": dash_basili,
        "heal": heal_basili, "spear": spear_basili,
        "debug": debug_silk,
    }
    return girdi, yeni_onceki


def hud_ciz(tuval, oyuncu, font):
    # Can (kırmızı kutular)
    for i in range(MAKS_CAN):
        x = 20 + i * 30
        renk = (220, 60, 60) if i < oyuncu.can else (70, 50, 50)
        pygame.draw.rect(tuval, renk, (x, 18, 24, 24), border_radius=5)
        pygame.draw.rect(tuval, (30, 20, 20), (x, 18, 24, 24),
                         width=2, border_radius=5)
    # Silk (mavi-beyaz kutular, can altında)
    for i in range(MAKS_SILK):
        x = 20 + i * 22
        dolu = i < oyuncu.silk
        renk = (180, 220, 255) if dolu else (50, 60, 80)
        pygame.draw.rect(tuval, renk, (x, 52, 18, 14), border_radius=3)
        pygame.draw.rect(tuval, (30, 40, 55), (x, 52, 18, 14),
                         width=1, border_radius=3)
    # Durum yazıları
    bilgi = f"Nisan: {oyuncu.nisan}   Bakis: {oyuncu.bakis}"
    if oyuncu.kosuyor: bilgi += "   [KOSU]"
    if oyuncu.suzuluyor: bilgi += "   [SUZULME]"
    if oyuncu.dash_kalan > 0: bilgi += "   [DASH]"
    if oyuncu.olumsuz: bilgi += "   [OLUMSUZ]"
    if oyuncu.heal_kalan > 0: bilgi += f"   [HEAL {oyuncu.heal_kalan:.1f}]"
    tuval.blit(font.render(bilgi, True, (200, 200, 210)), (20, 76))




def boss_hud_ciz(tuval, patron, font):
    """Patron can barı + faz numarası."""
    bar_w = 360
    bar_h = 16
    x = (arena.TUVAL_GENISLIK - bar_w) // 2
    y = 18
    pygame.draw.rect(tuval, (40, 24, 24), (x, y, bar_w, bar_h),
                     border_radius=4)
    oran = patron.can / patron.maks_can if patron.maks_can > 0 else 0
    dolu_w = int(bar_w * oran)
    if dolu_w > 0:
        pygame.draw.rect(tuval, (200, 60, 60), (x, y, dolu_w, bar_h),
                         border_radius=4)
    pygame.draw.rect(tuval, (110, 80, 80), (x, y, bar_w, bar_h),
                     width=2, border_radius=4)

    faz_yazi = font.render(
        f"Patron - Faz {patron.faz + 1}/3   ({patron.can}/{patron.maks_can})",
        True, (220, 200, 200))
    tuval.blit(faz_yazi, (x, y + bar_h + 4))

    # Aktif hareket adı (ortada, can barının altında)
    if patron.aktif_hareket:
        hareket_yazi = font.render(
            f"-- {patron.aktif_hareket.upper()} --",
            True, (255, 200, 100))
        tuval.blit(hareket_yazi,
                   (arena.TUVAL_GENISLIK // 2 - hareket_yazi.get_width() // 2,
                    y + bar_h + 24))

    if patron.faz_gecis_kalan > 0:
        gecis = font.render("FAZ DEGISIYOR...", True, (210, 195, 255))
        tuval.blit(gecis,
                   (arena.TUVAL_GENISLIK // 2 - gecis.get_width() // 2, 60))


def olcekli_bas(ekran, tuval):
    ew, eh = ekran.get_size()
    tw, th = tuval.get_size()
    olcek = min(ew / tw, eh / th)
    yeni_w, yeni_h = int(tw * olcek), int(th * olcek)
    olcekli = pygame.transform.smoothscale(tuval, (yeni_w, yeni_h))
    ekran.fill((0, 0, 0))
    ekran.blit(olcekli, ((ew - yeni_w) // 2, (eh - yeni_h) // 2))


def main():
    pygame.init()
    ekran = pygame.display.set_mode(PENCERE_BASLANGIC, pygame.RESIZABLE)
    pygame.display.set_caption("Patron Dovusu")
    tuval = pygame.Surface((arena.TUVAL_GENISLIK, arena.TUVAL_YUKSEKLIK))
    saat = pygame.time.Clock()
    font = pygame.font.SysFont("consolas", 18)
    buyuk = pygame.font.SysFont("consolas", 44, bold=True)

    arena_obj = arena.Arena()
    kol = kol_bagla()
    oyuncu = Player(arena_obj.orta_platform_x(), arena.ZEMIN_Y)
    patron = Boss()

    tam_ekran = False
    onceki = {"space": False, "dash": False, "heal": False,
              "spear": False, "debug": False}
    calisiyor = True
    while calisiyor:
        dt = saat.tick(arena.FPS) / 1000.0

        for olay in pygame.event.get():
            if olay.type == pygame.QUIT:
                calisiyor = False
            elif olay.type == pygame.VIDEORESIZE and not tam_ekran:
                ekran = pygame.display.set_mode((olay.w, olay.h),
                                                pygame.RESIZABLE)
            elif olay.type == pygame.KEYDOWN:
                if olay.key == pygame.K_ESCAPE:
                    calisiyor = False
                elif olay.key == pygame.K_F11:
                    tam_ekran = not tam_ekran
                    ekran = (pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
                             if tam_ekran else
                             pygame.display.set_mode(PENCERE_BASLANGIC,
                                                     pygame.RESIZABLE))
                elif olay.key == pygame.K_r and (oyuncu.olu or patron.olu):
                    oyuncu.tam_sifirla()
                    patron = Boss()
                elif olay.key == pygame.K_g:
                    oyuncu.olumsuz = not oyuncu.olumsuz

        girdi, onceki = girdi_oku(kol, onceki)

        # DEBUG: F ile silk +1 (patron gelince bu blok kaldırılacak)
        if girdi["debug_silk"]:
            oyuncu.silk_kazan(1)

        oyuncu.guncelle(girdi, arena_obj, dt)
        patron.guncelle(oyuncu, dt)

        # Çizim
        arena_obj.ciz(tuval)
        patron.ciz(tuval)
        oyuncu.ciz(tuval)
        oyuncu.ciz_saldirilar_ust(tuval)   # saldırı kutusu/silkspear: en üst
        hud_ciz(tuval, oyuncu, font)
        boss_hud_ciz(tuval, patron, font)

        if oyuncu.olu:
            t1 = buyuk.render("OYUN BITTI", True, (250, 160, 50))
            t2 = font.render("R = tekrar dene", True, (220, 220, 220))
            tuval.blit(t1, (arena.TUVAL_GENISLIK // 2 - t1.get_width() // 2, 210))
            tuval.blit(t2, (arena.TUVAL_GENISLIK // 2 - t2.get_width() // 2, 264))
        elif patron.olu:
            t1 = buyuk.render("ZAFER!", True, (180, 220, 255))
            t2 = font.render("R = tekrar oyna", True, (220, 220, 220))
            tuval.blit(t1, (arena.TUVAL_GENISLIK // 2 - t1.get_width() // 2, 210))
            tuval.blit(t2, (arena.TUVAL_GENISLIK // 2 - t2.get_width() // 2, 264))

        olcekli_bas(ekran, tuval)
        pygame.display.flip()

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()