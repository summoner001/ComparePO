compare_po.py — leírás
=======================

A script a Gemini és a Copilot MI felhasználásával Vibe Coding készült!
Éles környezetben tesztelve.
---------

Mire való
---------

A compare_po.py egy többfunkciós .po fájlokhoz készült eszköz. Segít a fordítási fájlok formátumellenőrzésében (CDATA/Markdown/HTML), írásjelek javításában, helyesírás-ellenőrzésben (magyar Hunspell szótárral), tegező/utasító szó-szűrésben, két .po fájl fordításainak összehasonlításában, valamint egyik platformról a másikra történő fordítás-kitöltésben (például Android ↔ iOS).
Működés (röviden)

Beolvassa a .po fájl bejegyzéseit (polib telepítve esetén polib-ot használja, különben van egy beépített, egyszerű parser).
A msgid-nek egy „kanonikus” kulcsot hoz létre (szöveg normalizálva, placeholder-ek tokenizálva), és ezen alapján párosítja/összehasonlítja bejegyzéseket különböző fájlok között.
Formátum-ellenőrzések: CDATA párosítás, Markdown/HTML tagek egyensúlya, ASCII ellipszis használat, egyenes idézőjelek stb.
Írásjelek javítása: idézőjelek (''/"" → tipográfiai „”), három pont → Unicode ellipszis (…), hosszú kötőjelek → egyszerű kötőjel (-); minden csere fuzzy flag-gel jelölhető a kimeneti fájlban.
Kitöltés (fill): ha két fájlt adsz meg (forrás és cél), az üres fordításokat a forrásból másolja át, adaptálja a placeholder-eket, és fuzzy-vel jelzi őket. Alapértelmezésben kihagyja az egyszavas vagy kizárólag helyőrzőket, hacsak nem adod meg a -egyszavas opciót.
Összehasonlítás: szóhalmaz-alapú ellenőrzés a normált fordítási szövegeken, így kis eltérések (pl. sorrend) helyett a tényleges tartalmi különbségeket emeli ki.
Funkciók (főbb)

formatcheck: CDATA/Markdown/HTML egyensúly-ellenőrzés.
irasjelek: írásjelek javítása, új fájl létrehozása (javitott_irasjelek_<fájlnév>.po), változtatások fuzzy megjelölése.
spellcheck: magyar helyesírás-ellenőrzés Hunspell-lal (hu_HU).
tegezodes: tegező/utasító szavak felderítése a fordításokban (szerkeszthető TEGEZODES_WORDS lista a script elején).
compare: két .po fordításainak összevetése kanonikus kulcs szerint, eltérések listázása.
fillios / filland: kitölti a cél .po fájl üres msgstr-jeit a forrás .po megfelelő fordításaival (iOS <-> Android átvitelt megkönnyítve), fuzzy jelöléssel.
egyszavas: kiegészíti a -fill* viselkedését, hogy egyszavas és csak-helyőrző stringeket is átmozgasson.
--debug: részletesebb, hibakeresést segítő kimenet.
Telepítés (Arch Linux)

Rendszerszintű csomagok:
---------

Frissítsd a rendszert: sudo pacman -Syu
Telepítsd a python3-at és hunspell-t: sudo pacman -S python hunspell
A magyar Hunspell szótár elérhetősége disztribúciótól függően:
Ha van hivatalos csomag (pl. hunspell-hu), telepítsd azt: sudo pacman -S hunspell-hu
Ha nincs a hivatalos tárolóban, két lehetőséged van: a) AUR-ból telepíteni (pl. aur/ hunspell-hu) az AUR segédprogrammal, b) vagy letölteni a hu_HU.aff / hu_HU.dic fájlokat (pl. LibreOffice / OpenOffice kiegészítésekből) és elhelyezni őket /usr/share/hunspell/ alá (root jogosultsággal).
Python-csomagok (ajánlott):

Használhatsz system-wide pacman csomagokat, de egyszerűbb a pip: python -m pip install --user polib hunspell
Megjegyzés: a python binding a hunspellhez (pip csomag neve egyszerűen hunspell) néha platformfüggő; ha pip telepítés nem működik, nézd meg, hogy van-e a disztribúciódhoz tartozó python-hunspell csomag vagy építsd az AUR-ból.
Függőségek (Arch Linux)

Kötelező/erősen ajánlott:
python (3.x)
hunspell (rendszerszintű bináris + .dic/.aff fájlok a hu_HU szótárhoz)
polib (python csomag, opcionális de kényelmes: kezeli a .po fájlokat)
python-hunspell (pip: hunspell) — a script ezt használhatja a helyesírás-ellenőrzéshez
Futtatás (Arch Linux)

A repository-ban: cd /útvonal/a/repo-hoz python3 compare_po.py -h
Példák:
Formátumellenőrzés egy fájlon: python3 compare_po.py lokalizacio.po -formatcheck
Írásjelek javítása: python3 compare_po.py lokalizacio.po -irasjelek -> új fájl: javitott_irasjelek_lokalizacio.po
Helyesírás-ellenőrzés: python3 compare_po.py lokalizacio.po -spellcheck
Tegező szavak keresése: python3 compare_po.py lokalizacio.po -tegezodes
Két fájl összehasonlítása: python3 compare_po.py forras.po cel.po -compare
Kitöltés (Android -> iOS) (forrás: Android, cél: iOS): python3 compare_po.py android.po ios.po -fillios
Kitöltés (iOS -> Android): python3 compare_po.py ios.po android.po -filland
Ha szeretnéd az egyszavasokat is átvinni: python3 compare_po.py forras.po cel.po -fillios -egyszavas
Hibakeresés részletes kimenettel: python3 compare_po.py lokalizacio.po -irasjelek --debug
Kapcsolók használata (összefoglalva) PO Tool v1.2 - Használat -h Megjeleníti ezt a súgót

Egy fájl csatolásakor: ./comparepo.py <fájl.po> [kapcsoló]

-formatcheck A CDATA, Markdown, HTML tag (pl. href) egyensúlyának ellenőrzése. -irasjelek Javítja az idézőjeleket ('', "" -> „”), ellipszist (... -> …), és kötőjeleket (–, — -> -). Új fájlt hoz létre: javitott_irasjelek_<fájlnév>.po (minden javítás fuzzy-ként jelölve) -spellcheck Helyesírás-ellenőrzés (Hunspell 'hu_HU' szótárral). -tegezodes A tegező/utasító szavak keresése a fordításokban. (A szótár: TEGEZODES_WORDS a szkript elején szerkeszthető.)

Két fájl hozzáadásakor: ./comparepo.py <forrás.po> <cél.po> [kapcsoló]

-compare Összehasonlítja a két .po fájl fordításait (szóhalmaz-alapú összehasonlítás normalizált, lecsupaszított szövegeken). -fillios Kitölti a <cél.po> (pl. iOS) üres fordításait a <forrás.po> (pl. Android) fordításaival, ha a kanonikus msgid szövegek tökéletesen megegyeznek. Figyelem: Alapértelmezetten kihagyja az egyszavas/csak-helyőrzős stringeket. Új fájl: fillios_<célfájlnév>.po -filland Kitölti a <cél.po> (pl. Android) üres fordításait a <forrás.po> (pl. iOS) fordításaival, ha a kanonikus msgid szövegek tökéletesen megegyeznek. Figyelem: Alapértelmezetten kihagyja az egyszavas/csak-helyőrzős stringeket. Új fájl: filland_<célfájlnév>.po -egyszavas A -filland vagy -fillios kapcsolóval együtt használva átviszi az egyszavas és csak-helyőrzőket is (pl.: "remove" vagy "%s"). Az új fájl neve ekkor: fillx_egyszavas_<célfájlnév>.po

--debug A hibakereséshez

Megjegyzések, tippek
---------

A script fuzzy-vel jelöli a program által módosított bejegyzéseket; ez általában kívánatos, mert jelezni akarod a fordítóknak, hogy a fordítás generált vagy automatikusan módosított.
A helyesírás-ellenőrzéshez szükség van a hunspell binárisra és a megfelelő hu_HU.dic / hu_HU.aff fájlokra; a Python binding önmagában nem elég.
Ha a polib nincs telepítve, a beépített parser is működik, de polib sok edge-case kezelésénél stabilabb.
A TEGEZODES_WORDS listát tetszőlegesen bővítheted a script elején, ha saját projekted stílusát máshogy akarod szabályozni.
A script elején a main() függvény indításakor egy diagnosztikai sor található ("--- SCRIPT INDUL ---"), ez segít CI-kimenetben vagy futtatási naplókban gyorsan észrevenni, hogy a script elindult.
