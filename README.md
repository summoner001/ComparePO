compare_po.py — leírás
=======================

A script a Gemini és a Copilot MI felhasználásával Vibe Coding készült!
Éles környezetben tesztelve.
---------

# 🇭🇺 PO Tool v1.2 Dokumentáció

**Korábbi fájlnév: `comparepo.py`**

Ez a dokumentum a fordítási segédeszköz használatát, működését és Arch Linux-os telepítését mutatja be.

---

## 📝 Áttekintés

### Mire való

A **PO Tool** egy sokoldalú Python szkript, amelyet kifejezetten a Gettext `.po` (Portable Object) fordítási fájlok minőség-ellenőrzésére és karbantartására fejlesztettek. Célja, hogy automatizálja a gyakori fordítási feladatokat és biztosítsa a következetességet, különösen a platformok közötti (pl. Android, iOS) fordítások szinkronizálásakor és a magyar tipográfiai szabályok betartásakor.

### Működés

A szkript a megadott `.po` fájl(oka)t Python bejegyzésekké (entitásokká) dolgozza fel.

1.  **Kanonikus Azonosítás:** A stringek összehasonlítása előtt a szkript megtisztítja az `msgid` (eredeti) szövegeket a formázásoktól (HTML, CDATA, Markdown) és a helyőrzőket (`%s`, `%d`, `%1$s`, `@`) egy egységes tokenné (`{PH}`) alakítja. Ez teszi lehetővé a megbízható összehasonlítást és adatátvitelt a `-compare` és `-fill*` funkcióknál.
2.  **Javítások és `fuzzy` jelölés:** A módosító funkciók (pl. `-irasjelek`, `-filland`) **új fájlt** hoznak létre. Minden változtatással érintett bejegyzést automatikusan **`#, fuzzy`** flagekkel jelöl meg, jelezve, hogy a fordítás emberi ellenőrzést igényel.

---

## 🧩 Funkciók (Kapcsolók Használata)

### PO Tool v1.2 - Használat

| Kapcsoló | Leírás |
| :--- | :--- |
| **`-h`** | Megjeleníti ezt a súgót. |
| **`--debug`** | Bővebb kimenetet biztosít a szkript működéséről és a belső változókról. |

### Egy fájl csatolásakor:

**Formátum:** `./po_tool.py <fájl.po> [kapcsoló]`

| Kapcsoló | Leírás |
| :--- | :--- |
| **`-formatcheck`** | **Formázási Hibaellenőrzés.** Ellenőrzi az `msgid` és `msgstr` bejegyzéseket a következőkre: **CDATA** blokkok egyensúlya (`<![CDATA[` vs `]]>`), **Markdown** jelölők egyensúlya (`**`, `__`, `~~`), és **HTML tag-ek** egyensúlya (nyitó vs. záró tag). |
| **`-irasjelek`** | **Tipográfiai Javítás.** Keresi és cseréli a következőket, majd új fájlt ír: <ul><li>Egyenes idézőjelek: `''` és `"` helyett a magyar tipográfiai megfelelője: **`„`** és **`”`**.</li><li>ASCII ellipszis: `...` helyett a tipográfiai **`…`** karakter.</li><li>Hosszú kötőjelek: **`–`** (en-dash) és **`—`** (em-dash) helyett a magyar **`-`** (kiskötőjel).</li></ul> **Kimeneti fájlnév:** `javitott_irasjelek_<fájlnév>.po` |
| **`-spellcheck`** | **Helyesírás-ellenőrzés.** A telepített Hunspell 'hu_HU' szótárral ellenőrzi az `msgstr` bejegyzések helyesírását. |
| **`-tegezodes`** | **Tegeződés/Utasítás Szűrő.** Megkeresi azokat az `msgstr` fordításokat, amelyek a szkriptben definiált `TEGEZODES_WORDS` listában szereplő szavakat tartalmazzák. (A szótár a szkript tetején szerkeszthető.) |

### Két fájl hozzáadásakor:

**Formátum:** `./po_tool.py <forrás.po> <cél.po> [kapcsoló]`

| Kapcsoló | Leírás |
| :--- | :--- |
| **`-compare`** | **Fordítások Összehasonlítása.** Összehasonlítja a két .po fájl fordításait, amelyek azonos kanonikus `msgid`-vel rendelkeznek. Eltérésnek számít, ha a két `msgstr` **szóhalmaza nem egyezik meg** (formázások és helyőrzők nélkül). |
| **`-fillios`** | **Android -> iOS Kitöltés.** Kitölti a **`<cél.po>`** (pl. iOS) üres fordításait a **`<forrás.po>`** (pl. Android) fordításaival, ha a kanonikus `msgid` szövegek tökéletesen megegyeznek. **Kimeneti fájlnév:** `fillios_<célfájlnév>.po` |
| **`-filland`** | **iOS -> Android Kitöltés.** Kitölti a **`<cél.po>`** (pl. Android) üres fordításait a **`<forrás.po>`** (pl. iOS) fordításaival, ha a kanonikus `msgid` szövegek tökéletesen megegyeznek. **Kimeneti fájlnév:** `filland_<célfájlnév>.po` |
| **`-egyszavas`** | **Kiegészítő opció!** A `-filland` vagy `-fillios` kapcsolóval együtt használva **átviszi** az egyszavas és csak helyőrzőkből álló stringeket (pl.: `"remove"` vagy `"%s"`), amelyeket a szkript alapértelmezetten kihagy. **Kimeneti fájlnév:** `fillx_egyszavas_<célfájlnév>.po` |

---

## 💻 Telepítés és Futtatás (Arch Linux)

### Függőségek (Arch Linux)

A szkript futtatásához szükséges Arch Linux csomagok és Python modulok:

| Elem | Arch Csomag | Telepítési Parancs | Cél |
| :--- | :--- | :--- | :--- |
| **Python 3** | `python` | `sudo pacman -S python` | A szkript futtatásához. |
| **Hunspell** | `python-hunspell` | `sudo pacman -S python-hunspell` | A Python Hunspell modul a `-spellcheck` funkcióhoz. |
| **Szótár** | `hunspell-hu` | `sudo pacman -S hunspell-hu` | A magyar szótárfájl a helyesírás-ellenőrzéshez. |
| **Polib (ajánlott)** | `polib` (pip) | `pip install polib` | Robusztusabb `.po` fájlkezeléshez. |

### Futtatás (Arch Linux)

1.  **Futtatási Jogosultság Beállítása:**
    ```bash
    chmod +x po_tool.py
    ```

2.  **Példák Futtatásra (Explicit Python 3 hívással):**

    | Feladat | Parancs |
    | :--- | :--- |
    | Helyesírás-ellenőrzés | `python3 ./po_tool.py android.po -spellcheck` |
    | Írásjelek javítása | `python3 ./po_tool.py ios.po -irasjelek` |
    | Kitöltés egyszavas opcióval | `python3 ./po_tool.py forras.po cel.po -fillios -egyszavas` |
