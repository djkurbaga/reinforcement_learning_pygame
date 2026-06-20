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



Dosya Yapısı:
GameScene/

├── README.md          ← bu dosya

├── arena.py           ← arena, platformlar, lava, çizim

├── player.py          ← oyuncu karakter mekanikleri

├── boss.py            ← patron, eller, kafa, saldırı setleri, state machine

├── game.py            ← ana oyun döngüsü, HUD, giriş/çıkış, ölçekleme

└── .vscode/

    └── settings.json  ← VS Code Local History ayarları

Dosya Açıklamaları

arena.py

Dövüş alanını tanımlar:
Tuval: 960 × 540 piksel (16:9 oranı)
Zemin: Tabana yayılı turuncu lava (oyuncu lavaya düşerse 2 can kaybeder ve mevcut bir platforma ışınlanır)
Platformlar: 5 adet, 108 px (6 birim × 18 px) genişliğinde, lavanın üstünde sıralı
orta_platform_x(): Mevcut (batık olmayan) platformlardan ortadaki birini döndürür. Patron platformları lavaya gömdüğünde oyuncu güvenli bir yere ışınlanır.

player.py

Oyuncunun tüm mekaniklerini içerir:

Hareket:
Sol/sağ koşma (A/D veya analog stick)
Değişken zıplama (Space basılı tutarak yükseklik kontrolü)
Dash (Shift / RT) — 1.5 platform menzilli, havadayken bir kez kilitli, 0.3 sn cooldown
Koşu modu (Shift basılı tutarak) — dash sonrası baktığı yönde otomatik koşar
Süzülme (paraşüt) — havada Space basılı tutunca düşüş hızı azalır (16 → 3.5)

Saldırı:
Yumruk (J veya X) — yönlü saldırı (W=yukarı, S=aşağı, varsayılan=yatay), 0.18 sn süre + 0.4 sn cooldown
Silkspear (K veya LT) — 0.3 sn asılı kalış (windup) + anlık 160 px yatay çubuk (0.1 sn görünür hitbox), 3 silk maliyeti, 0.75 sn cooldown, 25 hasar
Heal (B) — 1.5 sn odaklan (havada da yapılabilir), 6 silk → 3 can. Hasar alınca iptal olur, silk geri gelmez.


Silk kaynağı:
Patrona vurunca +1 silk kazanılır (0.2 sn cooldown ile çoklu silk bug'ı engellenmiş)
Maksimum 6 silk taşınabilir


Hasar/Ölüm:
5 can ile başlar
Hasar aldığında 2 sn dokunulmazlık devreye girer (lavada etkisiz)
0 can → oyuncu ölür, R ile yeniden başlanır


Debug:
F — silk +1
G — ölümsüzlük modu (toggle, HUD'da [OLUMSUZ] görünür)

boss.py
Patron mantığının tamamı — kafa, 4 el, can sistemi, faz geçişleri, saldırı setleri ve state machine bu dosyada.

Fazlar

Faz     Can     Hız         Saldırılar Arası       Aktif Saldırılar
                Çarpanı     Bekleme                 
1       120     1.00×       1.0                     snalt_swing, ust_slam
                                                    alt_alkis (3)
2       150     1.15×hızlı  0.7 sn                  + dort_slam (%40 olasılık) → 4 saldırı

3       200     1.30×hızlı  0.4 sn                  + yagmur_kaya → 5 saldırı

Fazlardaki değerler geliştirme aşamasında değişiklik gösterebilir

game.py

Ana oyun döngüsü:

Pygame başlatma, tam ekran ve pencere modu (F11 ile geçiş)
Oyuncu, patron ve arena nesnelerinin her kare güncellenip çizilmesi
HUD: oyuncu canları, silk göstergesi, patron can barı, aktif saldırı adı, debug bayrakları
Klavye/joystick girişleri
R tuşu ile oyun yeniden başlatma (oyuncu öldüğünde veya patron yenildiğinde): arena, oyuncu ve patron sıfırdan yaratılır
