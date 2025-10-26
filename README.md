compare_po.py — leírás
=======================

A script a Gemini és a Copilot MI felhasználásával Vibe Coding készült!
Éles környezetben tesztelve.
---------

Mire való
---------
A script .po (gettext) fájlok ellenőrzésére és összehasonlítására szolgál. Két üzemmódban működik:
- Összehasonlító mód (compare): két .po fájlt hasonlít össze, azonos (kanonizált) msgid-eket párosít, és kiírja azokat a bejegyzéseket, ahol a fordítások (msgstr-ek) szóalapú összehasonlításban eltérnek.
- Lint / egyfájl-ellenőrzés (single-file): egy .po fájlt átvizsgál hibás/gyanus formázásokra (hibás vagy egyensúlytalan Markdown, nem lezárt CDATA, HTML tag egyensúlyhiány, ASCII ellipszis használata a magyar „…” helyett, egyenes idézőjelek a magyar tipográfia helyett), valamint tegeződő/utasító kifejezésekre egy beépített szótár alapján.

Röviden: segít megtalálni fordítási inkonzisztenciákat és stilisztikai/technikai hibákat, amelyek lokalizációs vagy platformközi problémákhoz vezethetnek.

Működés (hogyan dolgozik)
-------------------------
- Betölti a .po fájlokat: ha telepítve van a polib, azt használja; ha nincs, akkor egy beépített, robusztusabb egyszerű parserrel dolgozik (többsoros msgid/msgstr és plurál msgstr[0] támogatás).
- Minden msgid-hez létrehoz egy kanonikus kulcsot:
  - eltávolítja a CDATA/HTML/Markdown formázás jelölőit (a látható szöveget megtartva),
  - normalizálja a whitespace-et,
  - a helyőrzőket (%s, %@, %1$s, %lld, %d, %%) egy {PH} tokenre normalizálja a párosításhoz — így a különböző placeholder-szintaxisok párosíthatók.
- A fordításokat (msgstr) szóhalmazra bontja: először eltávolítja a formázást és a helyőrzőket, majd Unicode-normalizálás + kisbetűsítés után tokenizál (unicode-érzékeny szó-regex).
- Ha egy párosított msgid esetén a két fordítás szóhalmazai különböznek, azt találatként visszaadja.
- A lint-mód külön, context-aware ellenőrzéseket futtat minden bejegyzésen:
  - CDATA nyitó/záró párosítás ellenőrzése
  - Markdown jelölők (pl. `*`, `**`, `` ` ``, `~~`) páratlanságának keresése (ha nincs CDATA/HTML jelen)
  - HTML tagek egyszerű egyensúly-ellenőrzése (CDATA esetén kikapcsolható)
  - Ellipsis ellenőrzés: a látható szöveget ellenőrzi; ha tipográfiai ellipszis (U+2026, „…”) van, NEM riaszt; ha csak ASCII '...' van, riaszt
  - Idézőjelek: ha a látható szövegben egyenes idézőjelek (' vagy ") vannak tipográfiai helyett, riaszt
  - Tegező/utasító szavak: a beépített TEGEZODES_WORDS listát használva ellenőrzi a látható szövegben szereplő teljes szavakat; találat esetén figyelmeztet
- A script context-aware módon dolgozik: először kibontja a CDATA-t és eltávolítja a HTML tageket, és csak a “látható” text node-okon végzi a stilisztikai ellenőrzéseket — így pl. a href="%@" nem okoz idézőjel- vagy ellipszis-figyelmeztetést.

Funkciók (összefoglalva)
------------------------
- Kétfájl-összehasonlítás (msgid alapú párosítás, placeholder-normalizálással)
- Egyszeri fájl lint (format / typográfia / tegező szavak detektálása)
- Placeholder-kezelés: %s, %@, %1$s, %lld, %d, %% stb. felismerése és normalizálása
- CDATA/HTML/Markdown-sensitív feldolgozás (context-aware)
- ANSI színek a terminál-kimenethez: címek/leírások kiemelése (piros, sárga, kék, magenta, cián)
- --debug mód: részletes debug információk, repr() kimenetek a problémás bejegyzésekről
- Könnyen szerkeszthető TEGEZODES_WORDS list a script tetején (magad bővítheted)
- polib támogatás (ha telepítve van), különben beépített parser, kezel plurál msgstr[0] eseteket is

Telepítés
---------
1. Python 3.x megléte (ajánlott: 3.8+)
   - Arch Linuxon általában előre telepített: python --version vagy python3 --version
2. polib (nem kötelező, de ajánlott):
   - Arch Linux pacman csomag: sudo pacman -S python-polib
   - vagy pip: python3 -m pip install --user polib
3. Mentsd el a scriptet compare_po.py néven UTF-8 kódolással (a fájl tartalmát a te scripttel pótold)
   - pl. nano compare_po.py → beillesztés → Ctrl+O, Ctrl+X
4. Adj futtathatóságot (opcionális):
   - chmod +x compare_po.py

Függőségek
-----------
- Kötelező: Python 3 (standard könyvtár modulok: re, os, unicodedata, html, ast, typing)
- Ajánlott: polib (jobb .po kezelés, plurálok, edge-case-ek)
- (Opcióként) ha további HTML parsingra van szükség, be lehet építeni BeautifulSoup-ot, de a jelenlegi script regex alapú tisztítást használ.

Futtatás
--------
- Egy fájl (lint ellenőrzés):
  - python3 compare_po.py path/to/file.po
  - vagy ./compare_po.py path/to/file.po (ha futtathatóvá tetted)
- Két fájl (összehasonlítás):
  - python3 compare_po.py path/to/first.po path/to/second.po

Kapcsolók / opciók
------------------
- --debug
  - Részletesebb kimenetet ad: repr() formában is kiírja az eredeti msgid/msgstr stringeket, a kanonikus kulcsot és a szóhalmazokat. Hasznos rejtett karakterek, escape-ek és egyéb furcsaságok vizsgálatához.
  - Példa: python3 compare_po.py and.po ios.po --debug
- Visszatérési kódok:
  - 0: sikeresen lefutott (lehet, hogy talált eltérést, de a script normálisan lefutott)
  - >0: hiba (pl. hiányzó fájl, parser hiba stb.)
- Színek:
  - A script ANSI escape kódokat használ; GNOME Terminál, Konsole, iTerm2 és hasonlóokban működik. Ha a terminálod nem támogatja, a színek kódokban fognak megjelenni (nem veszélyes, csak kevésbé olvasható).

Szerkeszthető pontok a scriptben
-------------------------------
- TEGEZODES_WORDS: a fájl tetején található halmaz — ide tehetsz további szavakat, törölhetsz vagy módosíthatsz.
- PLACEHOLDER_PATTERNS: ha más placeholder-formátumokat használsz, itt bővítheted a mintákat.
- MARKDOWN/HTML viselkedés: a check_markdown_balance és check_html_tag_balance függvények egyszerű heuristikákat használnak — ha finomítani szeretnéd (pl. specifikus tagek figyelése), ott nyugodtan módosíthatsz.

Példa használat és tippek
------------------------
- Gyors lint egyetlen fájlon:
  - python3 compare_po.py and.po
  - Ha sok a találat, futtasd --debug-kal a részletekért.
- Összehasonlítás két platform között (Android vs iOS):
  - python3 compare_po.py and.po ios.po
  - A kimenet megmutatja a közös kanonikus msgid-k számát és az eltérő fordítások listáját színekkel.
- Ha lásd, hogy valami hamis-pozitív jön (pl. CDATA-val kapcsolatos): futtasd --debug és nézd meg a repr() sorokat — gyakran rejtett escape vagy eltérő placeholder a hibaforrás.

Mi történik, ha találsz hibát a kimenetben?
------------------------------------------
- Single-file módban a script megmutatja a problémás bejegyzéseket és a talált hibák listáját (pl. msgstr: ASCII ellipszis ('...')...). Ellenőrizd a kiírt msgstr-et; ha a probléma jogos, javítsd a .po fájlban (cseréld '...' → '…', vagy a " és ' → „ ”), majd futtasd újra.
- Két-fájl összehasonlításnál a script felsorolja az eltéréseket; ha sok olyan eltérést látsz, amelyet nem szeretnél figyelembe venni, finomíthatod a PLACEHOLDER_PATTERNS-et vagy a canonicalize logic-ot.

Záró gondolatok
--------------
Ez a script célzottan arra készült, hogy a fordítások és a platformok közötti különbségeket (formázás, placeholder-ek, stilisztika) könnyebben megtaláld. A tegező-szótár rugalmasan szerkeszthető a script tetején. Ha szeretnéd, beépíthetek még opciókat (például JSON/CSV export a találatokhoz, külső szótár betöltése fájlból, vagy finomított HTML-parsing BeautifulSoup-pal), és beállíthatunk egy „ignore list”-et is, ha bizonyos msgid-kat automatikusan át szeretnél ugrani.
