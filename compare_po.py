#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
compare_po.py

Két .po fájl összehasonlítása vagy egy .po fájl lint-ellenőrzése.
Funkciók:
 - formázás (CDATA/HTML/Markdown) figyelembevétele / eltávolítása a matchinghez
 - placeholder-normalizálás (%s, %@, %1$s, %lld, %d, %% -> {PH})
 - fordítások szóhalmaz-alapú összehasonlítása (placeholder-ek figyelmen kívül)
 - context-aware ellenőrzések: hibás markdown, nem lezárt CDATA, HTML tag egyensúly,
   ellipsis ('...' vs '…'), egyenes idézőjelek vs tipográfiai („”)
 - tegező/utasító szótár alapú figyelmeztetés (TEGEZODES_WORDS szerkeszthető a script tetején)
 - single-file lint mód: ./compare_po.py file.po
 - két-file compare mód: ./compare_po.py file1.po file2.po
 - --debug opció részletes repr-kimenettel

Használat:
    python3 compare_po.py file1.po file2.po [--debug]
    python3 compare_po.py file.po [--debug]
"""
from __future__ import annotations
import sys
import re
import os
import unicodedata
import html
import ast
from typing import Dict, Tuple, List, Set, Optional

# --- Konfiguráció és színek ---
RESET = "\033[0m"
BOLD = "\033[1m"
RED = "\033[31m"
YELLOW = "\033[33m"
BLUE = "\033[34m"
MAGENTA = "\033[35m"
CYAN = "\033[36m"

# Szó regex: Unicode betűk/számok, kötőjeles tokenek
WORD_RE = re.compile(r"[\w]+(?:-[\w]+)*", re.UNICODE)

# Placeholder minták (a felhasználó listája alapján)
PLACEHOLDER_PATTERNS = [
    r"%\d+\$[sd@]",      # %1$s, %2$@, %1$d stb.
    r"%lld",             # %lld
    r"%[sd@u%]",          # %s, %d, %@, %u, %%
]
PLACEHOLDER_RE = re.compile("|".join(f"(?:{p})" for p in PLACEHOLDER_PATTERNS))

PLACEHOLDER_TOKEN = "{PH}"

# Markdown / HTML tagek regex egy egyszerű tisztításhoz
MARKDOWN_HTML_TAG_RE = re.compile(r'<[^>]+>|<!\[CDATA\[|\]\]>|(\*\*|__|\*|_|`|~~)')

# --- TEGEZŐDÉS / UTASÍTÓ SZÓTÁR ---
# Itt módosíthatod a tegező/utasító szavak listáját.
TEGEZODES_WORDS = {
"adakozz","add","adj","adataid","adatbázisod","adatbázisodat","adhatsz","adminisztrál","akarod","akarsz",
"aktuális","aktiváld","alkalmazd","applikáció","archiváld","archiválod","állítsd","általad","átnevezed",
"beállításaid","beimportál","beintegrál","beléphetsz","belépsz","beléptél","betöltöd","beszúrod","bezárhatod",
"bezárod","bezártad","blokkold","blokkolhatod","blokkoltad","blokkoltak","címed","csatlakozz","csatlakoztál",
"csevegéseid","csevegj","csoportjaid","csoportod","csoportodhoz","csúsztasd","dekódol","dekódolás","dokumentumaid",
"elfelejtetted","elfogadd","elfogadod","elfogadtad","elküldöd","ellenőrizd","elment","elmented","elolvasod",
"elolvasom","eltávolítottak","elutasítsd","elutasítod","email","emoji","engedélyezd","engedélyezheted","erősítsd",
"eszközeid","eszközöd","eszközödön","értesítésed","exportáld","exportálod","fájljaid","feladod","felcsatol",
"felhasználóneved","felhasználónevedet","feloldottad","feltelepít","felülírod","felvitel","felvitele","fejleszd",
"figyelj","fiókod","fiókodhoz","font","foglald","folytasd","frissíted","frissítsd","generál","generálás","gépeld",
"gépelj","gyártsd","győződj","hagyd","használhatsz","használhatod","használd","használj","hitelesítsd","hozd",
"húzd","igazolj","illeszd","illesztened","implementációja","implementálás","importáld","importálod","indítsd",
"irányítószámod","írd","írj","jelszavad","jelentsd","jelentetted","jelentheted","jelöld","javítod","javítsd",
"kapcsolataid","kapcsolódj","kapcsold","kattints","keresd","kerül","kezdd","képeid","kérd","kérj","kérjük",
"kérlek","készíts","készítsd","készítened","készülék","készülj","kiexportál","kiléphetsz","kilépsz","kimásol",
"kirúgtak","kitöltötted","kivágod","kívánod","kívánja","komponens","koppints","követed","közzéteszed",
"küldd","küldj","landolj","leellenőriz","lecseréled","legenerál","legyél","legyőzted","letilthatod",
"letöltöd","link","lépj","maradj","másolnod","meghívóid","meghódítottad","megnézem","megnézed","megnyitod","megosztod",
"megtapasztal","megtekinted","megváltoztathatod","megváltoztattad","mented","mentésed","mentsd","menj","metódus",
"módosításaid","módosíthatod","módosítottad","módosítsd","mégsem","neved","névjegyeid","nézd","nyisd","nyomd","nyomj",
"oldd","olvasd","opció","opciók","opcionális","permanens","problémáid","profilod","próbáld","próbálsz","pusztítsd",
"reagáltál","rejtsd","relé","rólunk","script","segítség","semmisítsd","számítógéped","számodra",
"szerkesztetted","szerkeszd","szeretnéd","szeretnél","szerver","szerverei","szervereid","szerverek","szobáid","szúrd",
"szüneteltesd","találhatod","találhatsz","találtál","támogasd","távolítsd","te","telefonod","termelj","tied",
"tilthatod","tiltsd","titkosítsd","töltsd","törlöd","töröld","töröljük","törölnöd","üdvözöllek","ügyelj","üzeneted",
"ütköztél","üss","válaszd","válassz","változtasd","vedd","vegyél","verziód","vesd","vidd","videóid","vigyázz",
"visszafejleszted","vonhatod","zárd","zárold"
}

# --- Segédfüggvények és feldolgozás ---


def strip_formatting_and_normalize_ws(s: Optional[str]) -> str:
    """Eltávolítja CDATA/HTML/Markdown jelöléseket (szöveg megtartásával), normalizálja whitespace-t."""
    if not s:
        return ""
    # CDATA kibontása
    s = re.sub(r'<!\[CDATA\[(.*?)\]\]>', r'\1', s, flags=re.DOTALL)
    # HTML entitások feloldása
    s = html.unescape(s)
    # HTML/Markdown tagek és jelölők egyszerű eltávolítása (csak a jelölőket töröljük)
    s = MARKDOWN_HTML_TAG_RE.sub('', s)
    # Unicode normalizálás
    s = unicodedata.normalize("NFKC", s)
    # NOTE: nem cseréljük a '…' karaktert '...' három ponttá, mert ez hamis riasztást okozott korábban
    # Whitespace normalizálás
    s = ' '.join(s.split())
    return s.strip()


def extract_visible_text(s: Optional[str]) -> str:
    """
    Kiveszi a felhasználónak látható szöveget:
    - ha CDATA van, kibontja a belsőt,
    - eltávolítja a HTML tageket (és így az attribútum-értékeket is),
    - dekódolja az HTML entitásokat,
    - normalizálja a whitespace-t.
    Ennek alapján végzünk nyelvi ellenőrzéseket (idézőjel, ellipszis, tegező szavak stb.).
    """
    if not s:
        return ""
    # Ha több CDATA van, összefűzzük a belső részeket
    parts = re.findall(r'<!\[CDATA\[(.*?)\]\]>', s, flags=re.DOTALL)
    if parts:
        txt = " ".join(parts)
    else:
        txt = s
    # Távolítsuk el a HTML tageket (ez eltávolítja az attribútumokat is, pl. href="%@")
    txt = re.sub(r'<[^>]+>', ' ', txt)
    # HTML entitások feloldása
    txt = html.unescape(txt)
    # Unicode normalizálás és whitespace
    txt = unicodedata.normalize("NFKC", txt)
    txt = ' '.join(txt.split())
    return txt.strip()


def normalize_placeholders(s: str) -> str:
    """Placeholder-ek normalizálása tokenné a párosításhoz."""
    return PLACEHOLDER_RE.sub(PLACEHOLDER_TOKEN, s)


def remove_placeholders(s: str) -> str:
    """Eltávolítja a placeholder-eket és normalizálja a whitespace-t."""
    cleaned = PLACEHOLDER_RE.sub(" ", s)
    return ' '.join(cleaned.split()).strip()


def canonicalize_msgid(original_msgid: str) -> Tuple[str, str]:
    """Kanonikus kulcs és display verzió előállítása a msgid-ből."""
    if not original_msgid:
        return "", ""
    stripped = strip_formatting_and_normalize_ws(original_msgid)
    display = stripped  # megtartjuk a helyőrzők jellegét a display-ben
    canonical = normalize_placeholders(stripped).lower()
    canonical = ' '.join(canonical.split())
    return canonical, display


def get_word_set(translation: Optional[str]) -> Set[str]:
    """Kinyeri a szavak halmazát egy fordításból (helyőrzők nélkül, kisbetűsítve)."""
    if not translation:
        return set()
    cleaned = strip_formatting_and_normalize_ws(translation)
    cleaned_no_ph = remove_placeholders(cleaned)
    words = WORD_RE.findall(cleaned_no_ph.lower())
    return {w for w in words if w}


# --- .po fájl beolvasó (polib használat ha elérhető, fallback egyszerű parser) ---


def _parse_po_string(line: str) -> str:
    """Segéd: '\"...\"' sor tartalmának megbízható kicsomagolása (escape-k kezelése)."""
    line = line.strip()
    if len(line) >= 2 and line.startswith('"') and line.endswith('"'):
        content = line[1:-1]
        try:
            return ast.literal_eval(f'"{content}"')
        except Exception:
            return content.replace('\\"', '"').replace('\\n', '\n').replace('\\t', '\t').replace('\\\\', '\\')
    return ""


def load_po_simple(path: str) -> Dict[str, str]:
    """Egyszerű .po parser: msgid -> msgstr, plurál msgstr[0] fallback."""
    entries: Dict[str, str] = {}
    current_msgid: List[str] = []
    current_msgstr: List[str] = []
    current_msgstr_plural_0: List[str] = []
    state = None
    def process_entry():
        nonlocal current_msgid, current_msgstr, current_msgstr_plural_0, state
        if current_msgid:
            full_msgid = "".join(_parse_po_string(l) for l in current_msgid)
            full_msgstr = "".join(_parse_po_string(l) for l in current_msgstr)
            full_msgstr0 = "".join(_parse_po_string(l) for l in current_msgstr_plural_0)
            final_msgstr = full_msgstr if full_msgstr else full_msgstr0
            if full_msgid:
                entries[full_msgid] = final_msgstr or ""
        current_msgid = []
        current_msgstr = []
        current_msgstr_plural_0 = []
        state = None

    try:
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                ls = line.strip()
                if not ls or ls.startswith('#'):
                    continue
                if ls.startswith("msgid "):
                    process_entry()
                    state = 'msgid'
                    current_msgid.append(ls[len("msgid "):])
                elif ls.startswith("msgstr[0]"):
                    state = 'msgstr0'
                    current_msgstr_plural_0.append(ls[len("msgstr[0] "):])
                elif ls.startswith("msgstr "):
                    state = 'msgstr'
                    current_msgstr.append(ls[len("msgstr "):])
                elif ls.startswith("msgstr["):
                    state = None
                elif ls.startswith('"') and ls.endswith('"'):
                    if state == 'msgid':
                        current_msgid.append(ls)
                    elif state == 'msgstr':
                        current_msgstr.append(ls)
                    elif state == 'msgstr0':
                        current_msgstr_plural_0.append(ls)
                else:
                    process_entry()
                    state = None
        process_entry()
    except FileNotFoundError:
        print(f"{RED}Hiba: a fájl nem található: {path}{RESET}", file=sys.stderr)
        return {}
    except Exception as e:
        print(f"{RED}Hiba a fájl olvasása közben ({path}): {e}{RESET}", file=sys.stderr)
        return {}
    return entries


def load_po(path: str) -> Dict[str, str]:
    """Polib-ot használjuk, ha elérhető; különben a simple parser-t."""
    polib_mod = None
    try:
        import polib as polib_mod
    except ImportError:
        polib_mod = None
    if polib_mod:
        try:
            po = polib_mod.pofile(path, encoding='utf-8')
            entries: Dict[str, str] = {}
            for e in po:
                if not e.msgid or getattr(e, "obsolete", False):
                    continue
                translation = e.msgstr or ""
                if not translation and getattr(e, "msgstr_plural", None):
                    try:
                        if isinstance(e.msgstr_plural, dict) and '0' in e.msgstr_plural:
                            translation = e.msgstr_plural.get('0', '')
                    except Exception:
                        pass
                entries[e.msgid] = translation or ""
            return entries
        except Exception:
            return load_po_simple(path)
    else:
        return load_po_simple(path)


# --- Issue detektálások (context-aware) ---


def check_cdata_balance(s: str) -> Optional[str]:
    if not s:
        return None
    opens = s.count('<![CDATA[')
    closes = s.count(']]>')
    if opens != closes:
        return "CDATA nincs megfelelően lezárva (<![CDATA[ vs ]]> szám nem egyezik)."
    return None


def check_markdown_balance(s: str) -> Optional[str]:
    """
    Markdown jelölők vizsgálata: de HA a bemenet HTML tageket vagy CDATA-t tartalmaz,
    akkor kihagyjuk a markdown-ellenőrzést (ezeknél gyakori, hogy a * vagy ** máshol fordul elő).
    """
    if not s:
        return None
    # Ha van HTML tag vagy CDATA, ne fussunk markdown-ellenőrzéssel
    if re.search(r'<[^>]+>', s) or '<![CDATA[' in s:
        return None
    visible = extract_visible_text(s)
    if not visible:
        return None
    markers = ['`', '**', '__', '~~']
    for m in markers:
        count = visible.count(m)
        if count % 2 != 0:
            return f"Hibás vagy egyensúlytalan Markdown/Code jelölő: '{m}' páratlan darabszámban található."
    star_count = visible.count('*')
    if star_count % 2 != 0:
        return "Hibás Markdown: '*' karakterek páratlan számú előfordulása (lehet hibás formázás)."
    return None


def check_html_tag_balance(s: str) -> Optional[str]:
    """
    HTML tagek egyensúly-ellenőrzése.
    Ha a bejegyzés CDATA-t tartalmaz, akkor a vizsgálatot elhagyjuk
    (CDATA belsejében gyakran van HTML, ami nem feltétlenül hiba).
    """
    if not s:
        return None
    if '<![CDATA[' in s:
        return None
    tags = re.findall(r'<\s*(/)?\s*([a-zA-Z][a-zA-Z0-9:-]*)[^>]*>', s)
    if not tags:
        return None
    counts = {}
    for closing, name in tags:
        if name.lower() in ["br", "img", "hr", "input", "meta", "link"]:
            continue
        counts.setdefault(name.lower(), 0)
        if closing:
            counts[name.lower()] -= 1
        else:
            counts[name.lower()] += 1
    unbalanced = [name for name, cnt in counts.items() if cnt != 0]
    if unbalanced:
        return f"HTML tagek egyensúlyhiánya: nem záródó/nyitó tagek lehetnek: {', '.join(unbalanced)}"
    return None


def check_ellipsis_usage(s: str) -> Optional[str]:
    """
    Ellipszis ellenőrzése: először megvizsgáljuk a nyers szöveget (s),
    majd a felhasználónak látható szöveget (extract_visible_text).
    Ha bármelyikben találunk tipográfiai ellipszist ('…'), akkor nem riasztunk.
    Csak akkor riasztunk, ha nincs '…' és van ASCII '...' a látható szövegben vagy a nyers szövegben.
    """
    if not s:
        return None

    # Ha a nyers szövegben van tipográfiai ellipszis -> OK
    if '…' in s:
        return None

    # Látható szöveg kinyerése (CDATA/HTML eltávolítva)
    visible = extract_visible_text(s)

    # Ha a látható szövegben van tipográfiai ellipszis -> OK
    if '…' in visible:
        return None

    # Ha nincs tipográfiai ellipszis, de van három ASCII pont a látható részen vagy a nyers szövegben -> riasztás
    if '...' in visible or '...' in s:
        return "ASCII ellipszis ('...') található; magyar lokalizációban javasolt az '…' karakter használata."
    return None


def check_quotes_usage(s: str) -> Optional[str]:
    """
    Idézőjelek ellenőrzése: csak a látható szövegben nézünk rá a straight quotes használatra.
    Ez kizárja az attribútumokban (pl. href=\"%@\") lévő idézőjeleket.
    """
    if not s:
        return None
    visible = extract_visible_text(s)
    straight_double = '"' in visible
    straight_single = "'" in visible
    typographic_double = '„' in visible or '”' in visible or '“' in visible
    typographic_single = '‚' in visible or '’' in visible or '‘' in visible
    if (straight_double or straight_single) and not (typographic_double or typographic_single):
        return "Egyenes idézőjelek (' vagy \") találhatók a látható szövegben; magyarban javasolt a tipográfiai idézőjelek („” )."
    return None


def check_tegezodes_usage(s: str) -> Optional[str]:
    """Ellenőrzi, hogy a szöveg tartalmaz-e a TEGEZODES_WORDS bármelyik szavát (teljes szavak)."""
    if not s:
        return None
    visible = extract_visible_text(s).lower()
    if not visible:
        return None
    # tokenizálás a WORD_RE alapján, hogy teljes szó egyezés legyen
    tokens = set(WORD_RE.findall(visible))
    found = tokens & {w.lower() for w in TEGEZODES_WORDS}
    if found:
        return f"Fordítás tegező/utasító szavakat tartalmaz: {', '.join(sorted(found))}"
    return None


def collect_issues_for_entry(msgid: str, msgstr: str) -> List[str]:
    """Végrehajt minden vizsgálatot egy bejegyzésre, visszaadja a problémák listáját."""
    issues: List[str] = []
    for label, text in (("msgid", msgid), ("msgstr", msgstr)):
        if not text:
            continue
        # CDATA
        c = check_cdata_balance(text)
        if c:
            issues.append(f"{label}: {c}")
        # Markdown (context-aware)
        m = check_markdown_balance(text)
        if m:
            issues.append(f"{label}: {m}")
        # HTML tagek (context-aware)
        h = check_html_tag_balance(text)
        if h:
            issues.append(f"{label}: {h}")
        # Ellipsis és idézőjelek elsősorban fordításnál releváns (magyar)
        if label == "msgstr":
            e = check_ellipsis_usage(text)
            if e:
                issues.append(f"{label}: {e}")
            q = check_quotes_usage(text)
            if q:
                issues.append(f"{label}: {q}")
            t = check_tegezodes_usage(text)
            if t:
                issues.append(f"{label}: {t}")
    return issues


# --- Canonical map és összehasonlító (zaj csökkentve) ---


def build_canonical_map(entries: Dict[str, str], filename: str, debug: bool = False) -> Dict[str, Tuple[str, str, str]]:
    d: Dict[str, Tuple[str, str, str]] = {}
    for orig_id, orig_str in entries.items():
        if not orig_id:
            continue
        key, disp = canonicalize_msgid(orig_id)
        if not key:
            continue
        d[key] = (orig_id, orig_str or "", disp)
    return d


def compare_po_files(path1: str, path2: str, debug: bool = False) -> List[Dict]:
    fn1 = os.path.basename(path1)
    fn2 = os.path.basename(path2)
    entries1 = load_po(path1)
    entries2 = load_po(path2)
    if not entries1 or not entries2:
        return []
    map1 = build_canonical_map(entries1, fn1, debug=debug)
    map2 = build_canonical_map(entries2, fn2, debug=debug)
    common = set(map1.keys()) & set(map2.keys())
    differences: List[Dict] = []
    for key in sorted(common):
        orig1, msgstr1, disp1 = map1[key]
        orig2, msgstr2, disp2 = map2[key]
        if not msgstr1 and not msgstr2:
            continue
        words1 = get_word_set(msgstr1)
        words2 = get_word_set(msgstr2)
        if words1 != words2:
            display_msgid = disp1 or disp2 or key
            differences.append({
                "key": key,
                "display_msgid": display_msgid,
                "file1": fn1,
                "orig_msgid1": orig1,
                "msgstr1": msgstr1,
                "words1": words1,
                "file2": fn2,
                "orig_msgid2": orig2,
                "msgstr2": msgstr2,
                "words2": words2,
            })
    return differences


# --- Egyfájl ellenőrzés (lint-szerű) ---


def lint_single_file(path: str, debug: bool = False) -> List[Dict]:
    fn = os.path.basename(path)
    entries = load_po(path)
    results: List[Dict] = []
    if not entries:
        return results
    for orig_id, orig_str in entries.items():
        issues = collect_issues_for_entry(orig_id, orig_str)
        # biztosítás: futtassuk a tegező ellenőrzést is a fordításon
        t = check_tegezodes_usage(orig_str)
        if t and f"msgstr: {t.split(': ',1)[1]}" not in issues:
            issues.append(f"msgstr: {t}")
        if issues:
            entry = {
                "display_msgid": strip_formatting_and_normalize_ws(orig_id),
                "orig_msgid": orig_id,
                "msgstr": orig_str,
                "issues": issues,
            }
            if debug:
                entry["reprs"] = {
                    "repr_msgid": repr(orig_id),
                    "repr_msgstr": repr(orig_str),
                }
            results.append(entry)
    return results


# --- Kimenet segéd és main ---


def colored(text: str, color: str) -> str:
    if not text:
        return ""
    return f"{color}{text}{RESET}"


def print_summary_header(common_count: int, diff_count: int):
    print("\n" + "=" * 60)
    print(f"{BOLD}{colored('Közös kanonikus msgid-k száma: ' + str(common_count), YELLOW)}")
    print(f"{BOLD}{colored('Eltérő fordítások száma: ' + str(diff_count), RED)}{RESET}")
    print("=" * 60 + "\n")


def main(argv):
    debug = False
    if "--debug" in argv:
        debug = True
        argv.remove("--debug")

    if len(argv) not in (2, 3):
        print(f"Használat:\n  Összehasonlítás: python3 {os.path.basename(argv[0])} file1.po file2.po [--debug]\n  Egy fájl ellenőrzése: python3 {os.path.basename(argv[0])} file.po [--debug]")
        sys.exit(2)

    # Single-file mód
    if len(argv) == 2:
        path = argv[1]
        if not os.path.isfile(path):
            print(f"{RED}Hiba: nem található a fájl: {path}{RESET}", file=sys.stderr)
            sys.exit(1)
        print(f"Fájl ellenőrzése: {os.path.basename(path)}")
        issues = lint_single_file(path, debug=debug)
        total_entries = len(load_po(path))
        problems = len(issues)
        # Kimenet: összegzés
        print("\n" + "=" * 60)
        print(f"{BOLD}{colored('Bejegyzések száma: ' + str(total_entries), YELLOW)}")
        print(f"{BOLD}{colored('Talált problémás bejegyzések: ' + str(problems), RED)}{RESET}")
        print("=" * 60 + "\n")
        if problems == 0:
            return 0
        for i, it in enumerate(issues, 1):
            print(f"--- Probléma #{i} ---")
            print(f"Msgid (tiszta): {colored(it['display_msgid'], RED)}")
            print(f"Msgid (eredeti): {colored(it['orig_msgid'], YELLOW)}")
            print(f"Msgstr: {colored(it['msgstr'] or '<üres>', BLUE)}")
            print(f"{CYAN}Talált problémák:{RESET}")
            for p in it['issues']:
                print(f"  - {p}")
            if debug and 'reprs' in it:
                print(f"{CYAN}Debug reprs:{RESET} msgid={it['reprs']['repr_msgid']}, msgstr={it['reprs']['repr_msgstr']}")
            print("-" * 60)
        return 0

    # Két fájl összehasonlítása
    path1, path2 = argv[1], argv[2]
    if not os.path.isfile(path1):
        print(f"{RED}Hiba: nem található a fájl: {path1}{RESET}", file=sys.stderr)
        sys.exit(1)
    if not os.path.isfile(path2):
        print(f"{RED}Hiba: nem található a fájl: {path2}{RESET}", file=sys.stderr)
        sys.exit(1)

    diffs = compare_po_files(path1, path2, debug=debug)
    # Közös kanonikus kulcsok száma
    entries1 = load_po(path1)
    entries2 = load_po(path2)
    map1 = build_canonical_map(entries1, os.path.basename(path1), debug=debug)
    map2 = build_canonical_map(entries2, os.path.basename(path2), debug=debug)
    common_count = len(set(map1.keys()) & set(map2.keys()))
    diff_count = len(diffs)

    print_summary_header(common_count, diff_count)

    if diff_count == 0:
        return 0

    fn1 = os.path.basename(path1)
    fn2 = os.path.basename(path2)
    for i, d in enumerate(diffs, 1):
        print(f"--- Eltérés #{i} ---")
        print(f"Msgid (Tiszta): {colored(d['display_msgid'], RED)}")
        print(f"Msgid ({fn1}):  {colored(d['orig_msgid1'], YELLOW)}")
        print(f"Msgstr ({fn1}): {colored(d['msgstr1'] or '<üres>', BLUE)}")
        print(f"Msgid ({fn2}):  {colored(d['orig_msgid2'], YELLOW)}")
        print(f"Msgstr ({fn2}): {colored(d['msgstr2'] or '<üres>', MAGENTA)}")

        # Tegező/utasító szó-figyelmeztetés (ha bármelyik fordítás tartalmazza a szótár szavát)
        t1 = check_tegezodes_usage(d['msgstr1'] or "")
        t2 = check_tegezodes_usage(d['msgstr2'] or "")
        if t1 or t2:
            combined = "; ".join([t for t in (t1, t2) if t])
            print(f"{CYAN}Megjegyzés: {combined}{RESET}")

        # Heurisztikus megjegyzés
        is_potential_false_positive = False
        reason = ""
        o1 = (d['orig_msgid1'] or "").strip()
        o2 = (d['orig_msgid2'] or "").strip()
        if o1.lower() == o2.lower() and o1 != o2 and (bool(d['msgstr1']) != bool(d['msgstr2'])):
            is_potential_false_positive = True
            reason = "Eltérő kis/nagybetű az eredeti msgid-ben és az egyik fordítás üres."
        display_no_ph = remove_placeholders(d['display_msgid']).strip()
        if not is_potential_false_positive and ' ' not in display_no_ph and 0 < len(display_no_ph) <= 10:
            if len(d['words1']) <= 3 and len(d['words2']) <= 3:
                is_potential_false_positive = True
                reason = "Rövid, egyszavas msgid (gyakran kontextusfüggő), rövid fordításokkal."

        if is_potential_false_positive:
            print(f"{CYAN}Megjegyzés: Lehetséges kontextusfüggő eltérés (nem feltétlenül hiba).{RESET}")
            if debug and reason:
                print(f"  {CYAN}Oka: {reason}{RESET}")

        if debug:
            print(f"{CYAN}Debug - Kanonikus kulcs: '{d['key']}'{RESET}")
            print(f"{CYAN}Debug - Szavak ({fn1}): {sorted(list(d['words1']))}{RESET}")
            print(f"{CYAN}Debug - Szavak ({fn2}): {sorted(list(d['words2']))}{RESET}")

        print("-" * 60)

    return 0


if __name__ == "__main__":
    exit_code = main(sys.argv)
    sys.exit(exit_code)
