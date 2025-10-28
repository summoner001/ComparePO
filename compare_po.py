#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
po_tool.py

Egyesített .po eszköz a formátum-ellenőrzéshez, helyesírás-ellenőrzéshez,
írásjelek javításához, tegeződés-szűréshez és platformok közötti
fordítás-kitöltéshez (Android <-> iOS).

Használat:
  ./po_tool.py -h
  ./po_tool.py file.po [kapcsoló]
  ./po_tool.py file1.po file2.po [kapcsoló]
"""
from __future__ import annotations
import sys
import re
import os
import html
import unicodedata
import ast
import argparse
from typing import Dict, List, Tuple, Optional, Set

# --- Konfiguráció és színek ---
RESET = "\033[0m"
BOLD = "\033[1m"
RED = "\033[31m"
YELLOW = "\033[33m"
BLUE = "\033[34m"
MAGENTA = "\033[35m"
CYAN = "\033[36m"

# --- Regexek és beállítások ---
WORD_RE = re.compile(r"[\w]+(?:-[\w]+)*", re.UNICODE)

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
"megtapasztal","megtekinted","megváltoztathatod","megváltoztattad","módosításaid","módosíthatod","módosítottad","módosítsd","mented","mentésed","mentsd","menj","metódus",
"mégsem","neved","névjegyeid","nézd","nyisd","nyomd","nyomj",
"oldd","olvasd","opció","opciók","opcionális","permanens","problémáid","profilod","próbáld","próbálsz","pusztítsd",
"reagáltál","rejtsd","relé","rólunk","script","segítség","semmisítsd","számítógéped","számodra",
"szerkesztetted","szerkeszd","szeretnéd","szeretnél","szerver","szerverei","szervereid","szerverek","szobáid","szúrd",
"szüneteltesd","találhatod","találhatsz","találtál","támogasd","távolítsd","te","telefonod","termelj","tied",
"tilthatod","tiltsd","titkosítsd","töltsd","törlöd","töröld","töröljük","törölnöd","üdvözöllek","ügyelj","üzeneted",
"ütköztél","üss","válaszd","válassz","változtasd","vedd","vegyél","verziód","vesd","vidd","videóid","vigyázz",
"visszafejleszted","vonhatod","zárd","zárold"
}

# --- Hunspell inicializálás ---
try:
    import hunspell
    # Általános elérési utak Linux/macOS rendszereken
    HUNSPELL_PATHS = [
        ('/usr/share/hunspell/hu_HU.dic', '/usr/share/hunspell/hu_HU.aff'),
        ('/usr/share/myspell/dicts/hu_HU.dic', '/usr/share/myspell/dicts/hu_HU.aff'),
        ('/Library/Spelling/hu_HU.dic', '/Library/Spelling/hu_HU.aff'),
    ]
    HS_OBJ = None
    for dic_path, aff_path in HUNSPELL_PATHS:
        if os.path.isfile(dic_path) and os.path.isfile(aff_path):
            try:
                HS_OBJ = hunspell.HunSpell(dic_path, aff_path)
                break
            except Exception:
                continue # Hiba esetén próbáljuk a következőt
    if not HS_OBJ:
        # Ez a figyelmeztetés jelenik meg, ha a szótárfájlok hiányoznak
        print(f"{YELLOW}Figyelmeztetés: Hunspell 'hu_HU' szótár nem található.{RESET}", file=sys.stderr)
        print(f"{YELLOW}A '-spellcheck' funkció nem lesz elérhető.{RESET}", file=sys.stderr)
except ImportError:
    HS_OBJ = None
    # Ez a figyelmeztetés jelenik meg, ha a Python hunspell csomag hiányzik
    print(f"{YELLOW}Figyelmeztetés: 'hunspell' Python csomag nincs telepítve.{RESET}", file=sys.stderr)
    print(f"{YELLOW}A '-spellcheck' funkció nem lesz elérhető. Telepítés: pip install hunspell{RESET}", file=sys.stderr)


# --- Segédfüggvények (Egyesítve) ---

def colored(text: str, color: str) -> str:
    """Szöveg színezése."""
    if not text:
        return ""
    return f"{color}{text}{RESET}"

def strip_formatting_and_normalize_ws(s: Optional[str]) -> str:
    """Eltávolítja CDATA/HTML/Markdown jelöléseket (szöveg megtartásával), normalizálja whitespace-t."""
    if not s:
        return ""
    s = re.sub(r'<!\[CDATA\[(.*?)\]\]>', r'\1', s, flags=re.DOTALL)
    s = html.unescape(s)
    s = MARKDOWN_HTML_TAG_RE.sub('', s)
    s = unicodedata.normalize("NFKC", s)
    s = ' '.join(s.split())
    return s.strip()

def extract_visible_text(s: Optional[str]) -> str:
    """Kiveszi a felhasználónak látható szöveget (CDATA-ból, HTML-tagek nélkül)."""
    if not s:
        return ""
    parts = re.findall(r'<!\[CDATA\[(.*?)\]\]>', s, flags=re.DOTALL)
    if parts:
        txt = " ".join(parts)
    else:
        txt = s
    txt = re.sub(r'<[^>]+>', ' ', txt) # HTML tagek eltávolítása
    txt = html.unescape(txt)
    txt = unicodedata.normalize("NFKC", txt)
    txt = ' '.join(txt.split())
    return txt.strip()

def normalize_placeholders(s: str) -> str:
    """Placeholder-ek normalizálása tokenné a párosításhoz."""
    return PLACEHOLDER_RE.sub(PLACEHOLDER_TOKEN, s)

def remove_placeholders(s: str) -> str:
    """Eltávolítja a placeholder-eket és normalizálja a whitespace-t."""
    cleaned = PLACEHOLDER_RE.sub(" ", s or "")
    return ' '.join(cleaned.split()).strip()

def extract_placeholders_list(s: str) -> List[str]:
    """Kigyűjti a helyőrzőket egy listába, sorrendben."""
    if not s:
        return []
    return [m.group(0) for m in PLACEHOLDER_RE.finditer(s)]

def canonicalize_msgid(original_msgid: str) -> Tuple[str, str]:
    """Kanonikus kulcs és display verzió előállítása a msgid-ből."""
    if not original_msgid:
        return "", ""
    stripped = strip_formatting_and_normalize_ws(original_msgid)
    display = stripped
    canonical = normalize_placeholders(stripped).lower()
    canonical = ' '.join(canonical.split())
    return canonical, display

def get_word_count_from_display(display: str) -> int:
    """Megszámolja a 'valódi' szavakat a display stringben (helyőrzők nélkül)."""
    if not display:
        return 0
    # A 'display' már 'strip_formatting_and_normalize_ws'-n átesett a canonicalize_msgid-ben
    # Helyőrzők eltávolítása a szószámításhoz
    cleaned_no_ph = PLACEHOLDER_RE.sub(" ", display)
    words = WORD_RE.findall(cleaned_no_ph)
    return len([w for w in words if w])

def get_word_set(translation: Optional[str]) -> Set[str]:
    """Kinyeri a szavak halmazát egy fordításból (helyőrzők nélkül, kisbetűsítve)."""
    if not translation:
        return set()
    cleaned = strip_formatting_and_normalize_ws(translation)
    cleaned_no_ph = remove_placeholders(cleaned)
    words = WORD_RE.findall(cleaned_no_ph.lower())
    return {w for w in words if w}

def adapt_placeholders_using_msgids(source_msgstr: str, source_msgid: str, target_msgid: str) -> str:
    """
    Megpróbálja adaptálni a helyőrzőket a forrás fordításból (source_msgstr)
    a cél msgid (target_msgid) helyőrzőinek felhasználásával.
    """
    if not source_msgstr:
        return source_msgstr
    if not source_msgid or not target_msgid:
        return source_msgstr

    stripped_source_id = strip_formatting_and_normalize_ws(remove_placeholders(source_msgid))
    stripped_target_id = strip_formatting_and_normalize_ws(remove_placeholders(target_msgid))
    
    # Csak akkor cserélünk, ha a csupasz szövegek (PH nélkül) megegyeznek
    if stripped_source_id != stripped_target_id:
        return source_msgstr

    source_msgstr_ph = list(PLACEHOLDER_RE.finditer(source_msgstr))
    target_id_ph_list = extract_placeholders_list(target_msgid)

    if not source_msgstr_ph or not target_id_ph_list:
        return source_msgstr # Nincs mit cserélni

    if len(source_msgstr_ph) != len(target_id_ph_list):
        return source_msgstr # A helyőrzők száma nem egyezik

    # Helyőrzők cseréje sorrendben
    out: List[str] = []
    last = 0
    for idx, m in enumerate(source_msgstr_ph):
        out.append(source_msgstr[last:m.start()])
        out.append(target_id_ph_list[idx])
        last = m.end()
    out.append(source_msgstr[last:])
    return ''.join(out)

def po_escape(s: str) -> str:
    """Escape-eli a stringet a PO formátumnak megfelelően."""
    if s is None:
        s = ""
    s = s.replace('\\', '\\\\')
    s = s.replace('"', '\\"')
    s = s.replace('\r\n', '\n').replace('\r', '\n')
    s = s.replace('\n', '\\n')
    s = s.replace('\t', '\\t')
    return f'"{s}"'


# --- .po beolvasás (Read-only, 'compare'-hoz és 'lint'-hez) ---

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
                        # Polib dict-ként kezeli a többes számot
                        if isinstance(e.msgstr_plural, dict) and '0' in e.msgstr_plural:
                            translation = e.msgstr_plural.get('0', '')
                        # Néha listaként is előfordulhat (régebbi verziók?)
                        elif isinstance(e.msgstr_plural, (list, tuple)) and len(e.msgstr_plural) > 0:
                            translation = e.msgstr_plural[0]
                    except Exception:
                        pass
                entries[e.msgid] = translation or ""
            return entries
        except Exception:
            return load_po_simple(path) # Visszaesés simple parser-re
    else:
        return load_po_simple(path)

def build_canonical_map(entries: Dict[str, str]) -> Dict[str, Tuple[str, str, str]]:
    """Kanonikus térkép építése: key -> (orig_id, orig_str, display_id)"""
    d: Dict[str, Tuple[str, str, str]] = {}
    for orig_id, orig_str in entries.items():
        if not orig_id:
            continue
        key, disp = canonicalize_msgid(orig_id)
        if not key:
            continue
        d[key] = (orig_id, orig_str or "", disp)
    return d

def build_translation_map_for_fill(path: str) -> Dict[str, Tuple[str, str]]:
    """
    Kanonikus térkép építése a '-fill' parancsokhoz (a fillios.py logikája alapján).
    Visszatér: kanonikus_kulcs -> (eredeti_msgid, msgstr)
    """
    entries = load_po(path) 
    result: Dict[str, Tuple[str, str]] = {}
    for msgid, msgstr in entries.items():
        key, _ = canonicalize_msgid(msgid)
        if key: # Csak ha van érvényes kulcs
            result[key] = (msgid, msgstr or "")
    return result


# --- .po feldolgozás (Block-alapú, íráshoz) ---

def split_file_into_entries(lines: List[str]) -> Tuple[List[str], List[List[str]]]:
    """Szétvágja a fájlt preambulumra és bejegyzés-blokkokra."""
    msgid_indices = []
    for idx, ln in enumerate(lines):
        if ln.lstrip().startswith("msgid "):
            msgid_indices.append(idx)

    if not msgid_indices:
        # Ha nincs msgid, az egész fájl egy blokk (csak a fejléc?)
        return (lines, [])

    preamble = lines[:msgid_indices[0]]
    blocks: List[List[str]] = []
    
    for i, start_idx in enumerate(msgid_indices):
        end_idx = msgid_indices[i + 1] if i + 1 < len(msgid_indices) else len(lines)
        blocks.append(lines[start_idx:end_idx])

    return preamble, blocks

def parse_entry_block(block_lines: List[str]) -> Tuple[str, str, Dict[int, str]]:
    """Kinyeri a msgid-t, msgstr-t és a többes számú alakokat egy blokkból."""
    msgid_parts: List[str] = []
    msgstr_parts: List[str] = []
    plurals: Dict[int, List[str]] = {}
    state = None
    current_plural_index = -1

    for ln in block_lines:
        s = ln.strip()
        if not s or s.startswith("#"): # Kommentek átugrása
            continue

        if s.startswith("msgid "):
            state = "msgid"
            msgid_parts.append(s[len("msgid "):])
        elif s.startswith("msgstr["):
            state = "msgstrplural"
            m = re.match(r'msgstr\[(\d+)\]\s*(.*)', s)
            if m:
                current_plural_index = int(m.group(1))
                rest = m.group(2) or ''
                plurals.setdefault(current_plural_index, []).append(rest)
            else:
                 current_plural_index = -1
        elif s.startswith("msgstr "):
            state = "msgstr"
            msgstr_parts.append(s[len("msgstr "):])
        elif s.startswith('"') and s.endswith('"'): # Folytató sor
            if state == "msgid":
                msgid_parts.append(s)
            elif state == "msgstr":
                msgstr_parts.append(s)
            elif state == "msgstrplural" and current_plural_index != -1:
                plurals[current_plural_index].append(s)
        else:
             state = None
             current_plural_index = -1

    full_msgid = "".join(_parse_po_string(l) for l in msgid_parts) if msgid_parts else ""
    full_msgstr = "".join(_parse_po_string(l) for l in msgstr_parts) if msgstr_parts else ""
    full_plurals: Dict[int, str] = {}
    for k, parts in plurals.items():
        full_plurals[k] = "".join(_parse_po_string(l) for l in parts)

    return full_msgid, full_msgstr, full_plurals

def replace_msgstr_in_block(block_lines: List[str], new_msgstr: Optional[str], plural_index: Optional[int] = None) -> List[str]:
    """Kicseréli a msgstr (vagy msgstr[index]) tartalmát egy blokkon belül."""
    out: List[str] = []
    i = 0
    replaced = False
    target_line_start = f"msgstr[{plural_index}] " if plural_index is not None else "msgstr "

    while i < len(block_lines):
        ln = block_lines[i]
        s = ln.lstrip()

        if s.startswith(target_line_start):
            esc_str = po_escape(new_msgstr or "")
            indent = ln[:len(ln) - len(s)]
            out.append(indent + target_line_start + esc_str + "\n")
            replaced = True
            # Átugorjuk az eredeti msgstr folytató sorait
            i += 1
            while i < len(block_lines) and block_lines[i].lstrip().startswith('"'):
                i += 1
            continue

        out.append(ln)
        i += 1

    # Ha nem találtunk létező msgstr sort (pl. csak msgid volt), akkor hozzáadjuk
    if not replaced:
        inserted = False
        res: List[str] = []
        i = 0
        while i < len(out):
            res.append(out[i])
            ln = out[i]
            s = ln.lstrip()
            # Az utolsó msgid sor vagy annak folytatása után szúrjuk be
            if s.startswith("msgid ") or (s.startswith('"') and i > 0 and (out[i-1].lstrip().startswith("msgid ") or out[i-1].lstrip().startswith('"'))):
                 j = i + 1
                 while j < len(out) and out[j].lstrip().startswith('"'):
                     res.append(out[j])
                     j += 1

                 esc_str = po_escape(new_msgstr or "")
                 indent = ln[:len(ln) - len(s)]
                 res.append(indent + target_line_start + esc_str + "\n")
                 inserted = True
                 i = j
                 continue
            i += 1

        if not inserted:
            esc_str = po_escape(new_msgstr or "")
            out.append(target_line_start + esc_str + "\n")
        else:
             out = res

    return out

def ensure_fuzzy_flag(block_lines: List[str]) -> List[str]:
    """Biztosítja, hogy a blokk rendelkezzen '#, fuzzy' flag-gel."""
    fuzzy_found = False
    flags_line_index = -1
    first_non_comment_index = 0

    for i, ln in enumerate(block_lines):
        ls = ln.lstrip()
        if not ls.startswith("#"):
            first_non_comment_index = i
            break
        if ls.startswith("#,"):
            flags_line_index = i
            if "fuzzy" in ls.split(','):
                fuzzy_found = True
                break
    else:
        first_non_comment_index = len(block_lines)

    if fuzzy_found:
        return block_lines

    if flags_line_index != -1:
        ln = block_lines[flags_line_index]
        ls = ln.lstrip()
        indent = ln[:len(ln) - len(ls)]
        existing_flags = ls[2:].strip()
        if existing_flags:
            new_line = f"{indent}#, fuzzy, {existing_flags}\n"
        else:
            new_line = f"{indent}#, fuzzy\n"
        block_lines[flags_line_index] = new_line
        return block_lines
    else:
        indent = ""
        if block_lines:
            ln0 = block_lines[0]
            indent = ln0[:len(ln0) - len(ln0.lstrip())]
        
        insert_index = flags_line_index if flags_line_index != -1 else 0
        if flags_line_index == -1 and first_non_comment_index > 0:
            insert_index = first_non_comment_index
        elif flags_line_index == -1 and first_non_comment_index == 0:
            insert_index = 0 # Beszúrás a legelejére

        block_lines.insert(insert_index, f"{indent}#, fuzzy\n")
        return block_lines

def write_po_file(path: str, preamble: List[str], blocks: List[List[str]], original_lines: List[str]):
    """Kiírja a módosított .po fájlt."""
    out_lines: List[str] = []
    out_lines.extend(preamble)
    for b in blocks:
        out_lines.extend(b)
    
    try:
        # Biztosítjuk, hogy a fájl vége üres sor legyen, ha az eredetiben is az volt
        if original_lines and original_lines[-1].strip() == "":
             if not out_lines or out_lines[-1].strip() != "":
                  out_lines.append("\n")

        with open(path, "w", encoding="utf-8", newline="\n") as f:
            f.writelines(out_lines)
    except Exception as e:
        print(f"{RED}Hiba az íráskor ({path}): {e}{RESET}", file=sys.stderr)
        return False
    return True


# --- Issue detektálások (Linting / Formatcheck) ---

def check_cdata_balance(s: str) -> Optional[str]:
    if not s: return None
    if s.count('<![CDATA[') != s.count(']]>'):
        return "CDATA nincs megfelelően lezárva (<![CDATA[ vs ]]> szám nem egyezik)."
    return None

def check_markdown_balance(s: str) -> Optional[str]:
    if not s: return None
    if re.search(r'<[^>]+>', s) or '<![CDATA[' in s:
        return None # HTML/CDATA esetén kihagyjuk
    visible = extract_visible_text(s)
    if not visible: return None
    for m in ['`', '**', '__', '~~']:
        if visible.count(m) % 2 != 0:
            return f"Hibás Markdown/Code jelölő: '{m}' páratlan darabszámban."
    if visible.count('*') % 2 != 0:
        return "Hibás Markdown: '*' karakterek páratlan számban."
    return None

def check_html_tag_balance(s: str) -> Optional[str]:
    if not s: return None
    if '<![CDATA[' in s:
        return None # CDATA esetén kihagyjuk
    tags = re.findall(r'<\s*(/)?\s*([a-zA-Z][a-zA-Z0-9:-]*)[^>]*>', s)
    if not tags: return None
    counts = {}
    for closing, name in tags:
        if name.lower() in ["br", "img", "hr", "input", "meta", "link"]:
            continue
        counts.setdefault(name.lower(), 0)
        counts[name.lower()] += -1 if closing else 1
    unbalanced = [name for name, cnt in counts.items() if cnt != 0]
    if unbalanced:
        return f"HTML tagek egyensúlyhiánya: {', '.join(unbalanced)}"
    return None

def check_ellipsis_usage(s: str) -> Optional[str]:
    if not s: return None
    if '…' in s: return None # Már helyes
    visible = extract_visible_text(s)
    if '…' in visible: return None # Már helyes
    if '...' in visible or '...' in s:
        return "ASCII ellipszis ('...') található; javasolt az '…' karakter."
    return None

def check_quotes_usage(s: str) -> Optional[str]:
    if not s: return None
    visible = extract_visible_text(s)
    straight_double = '"' in visible
    straight_single = "'" in visible
    typographic_double = '„' in visible or '”' in visible or '“' in visible
    typographic_single = '‚' in visible or '’' in visible or '‘' in visible
    if (straight_double or straight_single) and not (typographic_double or typographic_single):
        return "Egyenes idézőjelek (' vagy \") találhatók; javasolt a tipográfiai („”)."
    return None

def check_tegezodes_usage(s: str) -> Optional[str]:
    """Ellenőrzi, hogy a szöveg tartalmaz-e a TEGEZODES_WORDS bármelyik szavát."""
    if not s: return None
    visible = extract_visible_text(s).lower()
    if not visible: return None
    tokens = set(WORD_RE.findall(visible))
    found = tokens & {w.lower() for w in TEGEZODES_WORDS}
    if found:
        return f"Tegező/utasító szavak: {', '.join(sorted(found))}"
    return None

def collect_issues_for_entry(msgid: str, msgstr: str, checks: Set[str]) -> List[str]:
    """Végrehajtja a kért vizsgálatokat egy bejegyzésre."""
    issues: List[str] = []
    
    for label, text in (("msgid", msgid), ("msgstr", msgstr)):
        if not text: continue
        
        if 'format' in checks:
            c = check_cdata_balance(text)
            if c: issues.append(f"{label}: {c}")
            m = check_markdown_balance(text)
            if m: issues.append(f"{label}: {m}")
            h = check_html_tag_balance(text)
            if h: issues.append(f"{label}: {h}")

        if label == "msgstr":
            if 'irasjel' in checks:
                e = check_ellipsis_usage(text)
                if e: issues.append(f"{label}: {e}")
                q = check_quotes_usage(text)
                if q: issues.append(f"{label}: {q}")
            
            if 'tegezodes' in checks:
                t = check_tegezodes_usage(text)
                if t: issues.append(f"{label}: {t}")
    return issues


# --- Súgó ---

def print_help():
    print(f"""
{BOLD}PO Tool v1.2 - Használat{RESET}
{CYAN}-h{RESET}              {BOLD}Megjeleníti ezt a súgót{RESET}

{YELLOW}Egy fájl csatolásakor:{RESET}
  {sys.argv[0]} <fájl.po> [kapcsoló]

  {CYAN}-formatcheck{RESET}   A CDATA, Markdown, HTML tag (pl. href) egyensúlyának ellenőrzése.
  {CYAN}-irasjelek{RESET}     Javítja az idézőjeleket ({BOLD}'', "" -> „”{RESET}), ellipszist ({BOLD}... -> …{RESET}),
                  és kötőjeleket ({BOLD}–, — -> -{RESET}). Új fájlt hoz létre:
                  {MAGENTA}javitott_irasjelek_<fájlnév>.po{RESET} (minden javítás {BOLD}fuzzy{RESET}-ként jelölve)
  {CYAN}-spellcheck{RESET}    Helyesírás-ellenőrzés (Hunspell 'hu_HU' szótárral).
  {CYAN}-tegezodes{RESET}     A tegező/utasító szavak keresése a fordításokban.
                  (A szótár: {BOLD}TEGEZODES_WORDS{RESET} a szkript elején szerkeszthető.)

{YELLOW}Két fájl hozzáadásakor:{RESET}
  {sys.argv[0]} <forrás.po> <cél.po> [kapcsoló]

  {CYAN}-compare{RESET}        Összehasonlítja a két .po fájl fordításait (szóhalmaz-alapú összehasonlítás
                  normalizált, lecsupaszított szövegeken).
  {CYAN}-fillios{RESET}        Kitölti a {BOLD}<cél.po>{RESET} (pl. iOS) üres fordításait a {BOLD}<forrás.po>{RESET} (pl. Android)
                  fordításaival, ha a kanonikus msgid szövegek tökéletesen megegyeznek.
                  {BOLD}Figyelem:{RESET} Alapértelmezetten kihagyja az egyszavas/csak-helyőrzős stringeket.
                  Új fájl: {MAGENTA}fillios_<célfájlnév>.po{RESET}
  {CYAN}-filland{RESET}        Kitölti a {BOLD}<cél.po>{RESET} (pl. Android) üres fordításait a {BOLD}<forrás.po>{RESET} (pl. iOS)
                  fordításaival, ha a kanonikus msgid szövegek tökéletesen megegyeznek.
                  {BOLD}Figyelem:{RESET} Alapértelmezetten kihagyja az egyszavas/csak-helyőrzős stringeket.
                  Új fájl: {MAGENTA}filland_<célfájlnév>.po{RESET}
  {CYAN}-egyszavas{RESET}      A {CYAN}-filland{RESET} vagy {CYAN}-fillios{RESET} kapcsolóval együtt használva
                  átviszi az egyszavas és csak-helyőrzőket is (pl.: "remove" vagy "%s").
                  Az új fájl neve ekkor: {MAGENTA}fillx_egyszavas_<célfájlnév>.po{RESET}
""")


# --- Fő funkciók (Kapcsolók) ---

def run_lint_mode(path: str, checks: Set[str], debug: bool = False):
    """Egyfájlos ellenőrző mód (format, tegezodes, irasjel-hiba)."""
    fn = os.path.basename(path)
    entries = load_po(path)
    if not entries:
        # Ha a load_po már kiírta a hibaüzenetet, itt nincs teendő
        return 1
    
    print(f"Fájl ellenőrzése: {fn} (Keresett hibák: {', '.join(checks)})")
    problems = 0
    total_entries = len(entries)

    for orig_id, orig_str in entries.items():
        issues = collect_issues_for_entry(orig_id, orig_str, checks)
        if issues:
            problems += 1
            print("-" * 60)
            print(f"Msgid (tiszta): {colored(strip_formatting_and_normalize_ws(orig_id), RED)}")
            print(f"Msgstr: {colored(orig_str or '<üres>', BLUE)}")
            print(f"{CYAN}Talált problémák:{RESET}")
            for p in issues:
                print(f"  - {p}")
            if debug:
                print(f"{CYAN}Debug reprs:{RESET} msgid={repr(orig_id)}, msgstr={repr(orig_str)}")

    print("\n" + "=" * 60)
    print(f"{BOLD}{colored('Bejegyzések száma: ' + str(total_entries), YELLOW)}")
    print(f"{BOLD}{colored('Problémás bejegyzések: ' + str(problems), RED)}{RESET}")
    print("=" * 60 + "\n")
    return 0

def run_spellcheck(path: str, debug: bool = False):
    """Helyesírás-ellenőrzés futtatása."""
    if not HS_OBJ:
        print(f"{RED}Hiba: Hunspell nincs megfelelően beállítva. A '-spellcheck' nem futtatható.{RESET}", file=sys.stderr)
        return 1
    
    fn = os.path.basename(path)
    entries = load_po(path)
    if not entries:
        # Ha a load_po már kiírta a hibaüzenetet, itt nincs teendő
        return 1

    print(f"Helyesírás-ellenőrzés: {fn}")
    problems = 0
    total_entries = len(entries)
    
    for orig_id, orig_str in entries.items():
        if not orig_str:
            continue
        
        visible_text = extract_visible_text(orig_str)
        if not visible_text:
            continue

        tokens = WORD_RE.findall(visible_text)
        misspelled = []
        for word in tokens:
            if not HS_OBJ.spell(word):
                # Próbáljuk meg nagybetűvel is, hátha tulajdonnév (pl. mondat eleje)
                if not (word.istitle() and HS_OBJ.spell(word.lower())):
                     misspelled.append(word)

        if misspelled:
            problems += 1
            print("-" * 60)
            print(f"Msgid: {colored(strip_formatting_and_normalize_ws(orig_id), YELLOW)}")
            
            # Hibás szavak kiemelése
            highlighted_msgstr = orig_str
            for word in sorted(set(misspelled), key=len, reverse=True):
                # Óvatos csere, hogy ne sérüljön a HTML/Markdown
                if word in visible_text:
                     highlighted_msgstr = re.sub(r'\b' + re.escape(word) + r'\b', colored(word, RED), highlighted_msgstr)

            print(f"Msgstr: {highlighted_msgstr}")
            if debug:
                 print(f"{CYAN}Debug (talált hibás szavak): {', '.join(set(misspelled))}{RESET}")

    print("\n" + "=" * 60)
    print(f"{BOLD}{colored('Bejegyzések száma: ' + str(total_entries), YELLOW)}")
    print(f"{BOLD}{colored('Helyesírási hibás bejegyzések: ' + str(problems), RED)}{RESET}")
    print("=" * 60 + "\n")
    return 0

def run_irasjelek_fix(path: str, debug: bool = False):
    """Írásjelek keresése és cseréje, majd új fájl írása."""
    print(f"Írásjel-javítás futtatása: {path}")
    try:
        with open(path, "r", encoding="utf-8") as f:
            lines = f.readlines()
    except Exception as e:
        print(f"{RED}Hiba a fájl olvasása közben ({path}): {e}{RESET}", file=sys.stderr)
        return 1

    preamble, blocks = split_file_into_entries(lines)
    updated_blocks: List[List[str]] = []
    total_fixed = 0
    
    # Idézőjel-cserélő regexek
    quote_double_apos_open_re = re.compile(r"(\s|^|\[)''")
    quote_double_apos_close_re = re.compile(r"''(\s|[,.]|\]|$)")
    quote_double_re = re.compile(r'"')
    ellipsis_re = re.compile(r'\.\.\.(?!\.)') # Három pont, de nem négy vagy több
    dash_re = re.compile(r'[–—]')

    for block in blocks:
        full_msgid, full_msgstr, plurals = parse_entry_block(block)
        if not full_msgid:
            updated_blocks.append(block)
            continue

        modified = False
        new_block = list(block) # Másolat

        # Sima msgstr javítása
        if full_msgstr:
            original = full_msgstr
            fixed = full_msgstr
            fixed = quote_double_apos_open_re.sub(r'\1„', fixed)
            fixed = quote_double_apos_close_re.sub(r'”\1', fixed)
            count = fixed.count('"')
            if count > 0 and count % 2 == 0:
                s = ""
                open_q = True
                for char in fixed:
                    if char == '"':
                        s += "„" if open_q else "”"
                        open_q = not open_q
                    else:
                        s += char
                fixed = s
            
            fixed = ellipsis_re.sub('…', fixed)
            fixed = dash_re.sub('-', fixed)

            if fixed != original:
                modified = True
                new_block = replace_msgstr_in_block(new_block, fixed, plural_index=None)
                if debug:
                    print(f"Msgid: {strip_formatting_and_normalize_ws(full_msgid)[:60]}...")
                    print(f"  Javítva (msgstr): ...{original[max(0, original.find('...'))-10 : original.find('...')+13]}... -> ...{fixed[max(0, fixed.find('…'))-10 : fixed.find('…')+13]}...")

        # Plurál alakok javítása
        for idx, p_msgstr in plurals.items():
            if not p_msgstr: continue
            original = p_msgstr
            fixed = p_msgstr
            fixed = quote_double_apos_open_re.sub(r'\1„', fixed)
            fixed = quote_double_apos_close_re.sub(r'”\1', fixed)
            count = fixed.count('"')
            if count > 0 and count % 2 == 0:
                s = ""
                open_q = True
                for char in fixed:
                    if char == '"':
                        s += "„" if open_q else "”"
                        open_q = not open_q
                    else:
                        s += char
                fixed = s
            
            fixed = ellipsis_re.sub('…', fixed)
            fixed = dash_re.sub('-', fixed)

            if fixed != original:
                modified = True
                new_block = replace_msgstr_in_block(new_block, fixed, plural_index=idx)
                if debug:
                    print(f"Msgid: {strip_formatting_and_normalize_ws(full_msgid)[:60]}...")
                    print(f"  Javítva (msgstr[{idx}]): ... -> …")

        if modified:
            total_fixed += 1
            new_block = ensure_fuzzy_flag(new_block)
        
        updated_blocks.append(new_block)

    if total_fixed == 0:
        print("Nem találtam javítandó írásjeleket.")
        return 0

    out_path = f"javitott_irasjelek_{os.path.basename(path)}"
    if write_po_file(out_path, preamble, updated_blocks, lines):
        print(f"\nKész: {total_fixed} bejegyzés lett javítva és fuzzy-ként megjelölve.")
        print(f"Új fájl: {MAGENTA}{out_path}{RESET}")
    else:
        print(f"{RED}Hiba történt az új fájl írása közben.{RESET}")
        return 1
    return 0

def run_compare(path1: str, path2: str, debug: bool = False):
    """Két fájl összehasonlítása (compare_po.py logika)."""
    fn1 = os.path.basename(path1)
    fn2 = os.path.basename(path2)
    entries1 = load_po(path1)
    entries2 = load_po(path2)
    if not entries1 or not entries2:
        # A load_po már kiírta a hibaüzenetet, ha szükséges volt
        return 1
        
    map1 = build_canonical_map(entries1)
    map2 = build_canonical_map(entries2)
    common_keys = set(map1.keys()) & set(map2.keys())
    common_count = len(common_keys)
    differences = 0

    print(f"Összehasonlítás: {fn1} vs {fn2}")
    print("\n" + "=" * 60)
    print(f"{BOLD}{colored('Közös kanonikus msgid-k száma: ' + str(common_count), YELLOW)}")
    
    diff_list = []
    
    for key in sorted(common_keys):
        orig1, msgstr1, disp1 = map1[key]
        orig2, msgstr2, disp2 = map2[key]
        
        if not msgstr1 and not msgstr2: # Mindkettő üres, átugorjuk
            continue
            
        words1 = get_word_set(msgstr1)
        words2 = get_word_set(msgstr2)
        
        if words1 != words2:
            differences += 1
            diff_list.append({
                "display_msgid": disp1 or disp2 or key,
                "orig_msgid1": orig1, "msgstr1": msgstr1, "words1": words1,
                "orig_msgid2": orig2, "msgstr2": msgstr2, "words2": words2,
                "key": key
            })

    print(f"{BOLD}{colored('Eltérő fordítások száma: ' + str(differences), RED)}{RESET}")
    print("=" * 60 + "\n")

    if differences == 0:
        return 0
        
    for i, d in enumerate(diff_list, 1):
        print(f"--- Eltérés #{i} ---")
        print(f"Msgid (Tiszta): {colored(d['display_msgid'], RED)}")
        print(f"Msgid ({fn1}):  {colored(d['orig_msgid1'], YELLOW)}")
        print(f"Msgstr ({fn1}): {colored(d['msgstr1'] or '<üres>', BLUE)}")
        print(f"Msgid ({fn2}):  {colored(d['orig_msgid2'], YELLOW)}")
        print(f"Msgstr ({fn2}): {colored(d['msgstr2'] or '<üres>', MAGENTA)}")

        t1 = check_tegezodes_usage(d['msgstr1'] or "")
        t2 = check_tegezodes_usage(d['msgstr2'] or "")
        if t1 or t2:
            combined = "; ".join([t.replace('Tegező/utasító szavak: ', f"({fn1}) ") if t == t1 else t.replace('Tegező/utasító szavak: ', f"({fn2}) ") for t in (t1, t2) if t])
            print(f"{CYAN}Megjegyzés: {combined}{RESET}")

        if debug:
            print(f"{CYAN}Debug - Kanonikus kulcs: '{d['key']}'{RESET}")
            print(f"{CYAN}Debug - Szavak ({fn1}): {sorted(list(d['words1']))}{RESET}")
            print(f"{CYAN}Debug - Szavak ({fn2}): {sorted(list(d['words2']))}{RESET}")
        print("-" * 60)
    return 0

def run_fill(source_po: str, target_po: str, debug: bool = False, out_filename: Optional[str] = None, egyszavas: bool = False):
    """
    Kitölti a target_po-t a source_po-ból.
    Ha egyszavas=False, kihagyja az 1 szavas vagy csak-helyőrző stringeket.
    """
    if not os.path.isfile(source_po):
        print(f"{RED}Hiba: Forrásfájl nem található: {source_po}{RESET}", file=sys.stderr)
        return 2
    if not os.path.isfile(target_po):
        print(f"{RED}Hiba: Célfájl nem található: {target_po}{RESET}", file=sys.stderr)
        return 2

    source_map = build_translation_map_for_fill(source_po)
    if debug:
        print(f"[DEBUG] Forrástérkép ({os.path.basename(source_po)}): {len(source_map)} kanonikus kulcs beolvasva.")

    try:
        with open(target_po, "r", encoding="utf-8") as f:
            lines = f.readlines()
    except Exception as e:
        print(f"{RED}Hiba a célfájl olvasása közben ({target_po}): {e}{RESET}", file=sys.stderr)
        return 1

    preamble, blocks = split_file_into_entries(lines)
    updated_blocks: List[List[str]] = []
    total_checked = 0
    updated_count = 0
    skipped_single_word = 0
    source_missing = 0
    source_empty = 0
    already_translated = 0

    for block_idx, block in enumerate(blocks):
        full_msgid, full_msgstr, plurals = parse_entry_block(block)

        if not full_msgid: # Üres msgid (pl. a fejléc) átugrása
            updated_blocks.append(block)
            continue

        total_checked += 1
        key, display = canonicalize_msgid(full_msgid)

        if not key:
            updated_blocks.append(block)
            continue

        # Ellenőrizzük, hogy a célfájlban már van-e fordítás
        target_is_empty = not full_msgstr.strip() and (not plurals or not any(v.strip() for v in plurals.values()))
        if not target_is_empty:
            already_translated +=1
            updated_blocks.append(block)
            if debug:
                 print(f"[DEBUG] Kihagyva (már lefordítva a célfájlban): '{display[:50]}...'")
            continue

        # --- EGYSZAVAS SZŰRÉS ---
        if not egyszavas: # Ha NINCS engedélyezve az egyszavas átvitel
            word_count = get_word_count_from_display(display)
            # A word_count 0 lesz, ha csak helyőrző, és 1, ha egy szó.
            if word_count <= 1:
                skipped_single_word += 1
                updated_blocks.append(block) # Hozzáadjuk az eredeti (üres) blokkot
                if debug:
                    print(f"[DEBUG] Kihagyva (egyszavas/helyőrző): '{display[:50]}...' (Szószám: {word_count})")
                continue # Ugrás a következő blokkra
        # -----------------------------

        # Megkeressük a forrástérképben
        if key not in source_map:
            source_missing += 1
            updated_blocks.append(block)
            if debug:
                print(f"[DEBUG] Kihagyva (nincs forrás megfelelő): '{display[:50]}...' (Kulcs: '{key}')")
            continue

        source_orig_msgid, source_msgstr = source_map[key]
        if not source_msgstr.strip(): # Ha a forrás fordítás üres
            source_empty += 1
            updated_blocks.append(block)
            if debug:
                 print(f"[DEBUG] Kihagyva (forrás fordítás üres): '{display[:50]}...'")
            continue

        # Placeholder-adaptáció
        adapted_msgstr = source_msgstr
        try:
            adapted_msgstr = adapt_placeholders_using_msgids(source_msgstr, source_orig_msgid, full_msgid)
            if debug and adapted_msgstr != source_msgstr:
                print(f"[DEBUG] Helyőrzők adaptálva: '{display[:50]}...'")
        except Exception as e:
            if debug:
                print(f"[DEBUG] Hiba a helyőrzők adaptálásakor msgid='{display[:50]}...': {e}")
            # Hiba esetén az eredeti forrás msgstr-t használjuk

        # Az új msgstr beillesztése a blokkba
        has_singular = any(ln.lstrip().startswith("msgstr ") for ln in block)
        has_plural_0 = any(ln.lstrip().startswith("msgstr[0]") for ln in block)

        new_block = list(block) # Másolatot készítünk
        if has_plural_0:
            new_block = replace_msgstr_in_block(new_block, adapted_msgstr, plural_index=0)
        elif has_singular:
             new_block = replace_msgstr_in_block(new_block, adapted_msgstr, plural_index=None)
        else: # Ha se sima msgstr, se msgstr[0] nem volt (csak msgid)
             new_block = replace_msgstr_in_block(new_block, adapted_msgstr, plural_index=None)

        # Megjelöljük fuzzy-vel
        new_block = ensure_fuzzy_flag(new_block)
        updated_blocks.append(new_block)
        updated_count += 1
        if debug:
            print(f"[DEBUG] Kitöltve (fuzzy): msgid='{display[:50]}...' -> msgstr a forrásból (Kulcs: '{key}')")

    if updated_count == 0:
        print("Nem találtam kitöltendő (üres) msgstr-eket.")
        if debug:
            print(f"[DEBUG] Összes ellenőrzött: {total_checked}, ebből már lefordítva: {already_translated}, forrásban hiányzó: {source_missing}, forrásban üres: {source_empty}, kihagyva (egyszavas): {skipped_single_word}")
        return 0

    # Kimeneti fájlnév meghatározása
    out_path = out_filename or os.path.splitext(target_po)[0] + "_kiegeszitett.po"
    
    if write_po_file(out_path, preamble, updated_blocks, lines):
        print(f"\nKész: {updated_count} bejegyzés lett kiegészítve (fuzzy-ként megjelölve).")
        print(f"Új fájl: {MAGENTA}{out_path}{RESET}")
        
        # --- FIGYELMEZTETÉS AZ EGYSZAVAS STRINGEK MIATT ---
        if not egyszavas and skipped_single_word > 0:
            print(colored(f"\nFigyelmeztetés: {skipped_single_word} bejegyzés (egyszavas vagy csak helyőrző) nem lett átmásolva.", YELLOW))
            print(colored(f"  Ha ezeket is át szeretné hozni, használja a '{CYAN}-egyszavas{YELLOW}' kapcsolót.", YELLOW))
        # ----------------------------------------------------

        if debug:
            print(f"[DEBUG] Összes ellenőrzött (érvényes msgid-vel): {total_checked}")
            print(f"[DEBUG] Már lefordítva a célfájlban: {already_translated}")
            print(f"[DEBUG] Forrásban hiányzó: {source_missing}")
            print(f"[DEBUG] Forrásban üres fordítás: {source_empty}")
            print(f"[DEBUG] Kihagyva (egyszavas/helyőrző): {skipped_single_word}")
    else:
        print(f"{RED}Hiba történt az új fájl írása közben.{RESET}")
        return 1
    return 0


# --- Fő (main) funkció ---

def main(argv: List[str]) -> int:
    print("--- SCRIPT INDUL ---") # <<< A KÉRT DIAGNOSZTIKAI SOR BEILLESZTVE
    
    # Argumentumok feldolgozása
    parser = argparse.ArgumentParser(description="PO Tool", add_help=False)
    
    # Kapcsolók
    parser.add_argument("-h", action="store_true", help="Súgó megjelenítése")
    parser.add_argument("--debug", action="store_true", help="Debug kimenet")
    
    # Egyfájlos kapcsolók
    single_file_group = parser.add_argument_group("Egyfájlos műveletek")
    single_file_group.add_argument("-formatcheck", action="store_true", help="Formátum-ellenőrzés (CDATA, MD, HTML)")
    single_file_group.add_argument("-irasjelek", action="store_true", help="Írásjelek javítása és új fájl írása")
    single_file_group.add_argument("-spellcheck", action="store_true", help="Helyesírás-ellenőrzés")
    single_file_group.add_argument("-tegezodes", action="store_true", help="Tegező/utasító szavak keresése")

    # Kétfájlos kapcsolók
    two_file_group = parser.add_argument_group("Kétfájlos műveletek")
    two_file_group.add_argument("-compare", action="store_true", help="Két fájl fordításainak összehasonlítása")
    two_file_group.add_argument("-filland", action="store_true", help="Kitöltés (pl. iOS -> Android)")
    two_file_group.add_argument("-fillios", action="store_true", help="Kitöltés (pl. Android -> iOS)")
    two_file_group.add_argument("-egyszavas", action="store_true", help="Egyszavas/helyőrző stringek átvitele -fill kapcsolókkal")

    # Fájlok (pozíciós)
    parser.add_argument("files", nargs="*", help=".po fájl(ok)")
    
    args = parser.parse_args(argv[1:])
    
    num_files = len(args.files)
    debug = args.debug

    # --- Súgó kezelése ---
    if args.h or (num_files == 0 and not any([args.formatcheck, args.irasjelek, args.spellcheck, args.tegezodes, args.compare, args.filland, args.fillios, args.egyszavas])):
        print_help()
        return 0

    # --- Fájlok számának ellenőrzése ---
    if num_files == 0:
        print(f"{RED}Hiba: Nem adott meg .po fájlt.{RESET}")
        print_help()
        return 1
        
    if num_files > 2:
        print(f"{RED}Hiba: Túl sok fájl megadva (maximum 2).{RESET}")
        print_help()
        return 1
    
    # --- Egyfájlos mód ---
    if num_files == 1:
        path = args.files[0]
        if not os.path.isfile(path):
            print(f"{RED}Hiba: A fájl nem található: {path}{RESET}", file=sys.stderr)
            return 1
            
        if args.formatcheck:
            return run_lint_mode(path, {"format"}, debug)
        elif args.tegezodes:
            return run_lint_mode(path, {"tegezodes"}, debug)
        elif args.spellcheck:
            return run_spellcheck(path, debug)
        elif args.irasjelek:
            return run_irasjelek_fix(path, debug)
        elif args.egyszavas or args.compare or args.filland or args.fillios:
            print(f"{RED}Hiba: A(z) '{argv[2]}' kapcsoló két fájlt igényel.{RESET}")
            print_help()
            return 1
        else:
            # Ha csak egy fájlt ad meg kapcsoló nélkül
            print(f"{RED}Hiba: Egy fájl esetén kötelező kapcsolót megadni.{RESET}")
            print_help()
            return 1

    # --- Kétfájlos mód ---
    if num_files == 2:
        path1, path2 = args.files
        if not os.path.isfile(path1):
            print(f"{RED}Hiba: A fájl nem található: {path1}{RESET}", file=sys.stderr)
            return 1
        if not os.path.isfile(path2):
            print(f"{RED}Hiba: A fájl nem található: {path2}{RESET}", file=sys.stderr)
            return 1

        if args.compare:
            return run_compare(path1, path2, debug)
        elif args.fillios:
            # file1 = Android (forrás), file2 = iOS (cél)
            target_base_name = os.path.basename(path2)
            # Név generálása: fillios_egyszavas_fajl.po vagy fillios_fajl.po
            out_name = f"fillios_{'egyszavas_' if args.egyszavas else ''}{target_base_name}"
            return run_fill(path1, path2, debug, out_name, egyszavas=args.egyszavas)
        elif args.filland:
            # file1 = iOS (forrás), file2 = Android (cél)
            target_base_name = os.path.basename(path2)
            out_name = f"filland_{'egyszavas_' if args.egyszavas else ''}{target_base_name}"
            return run_fill(path1, path2, debug, out_name, egyszavas=args.egyszavas)
        elif args.egyszavas: # Ha csak -egyszavas van megadva, de fill* nincs
            print(f"{RED}Hiba: A '-egyszavas' kapcsoló csak a '-fillios' vagy '-filland' kapcsolóval együtt érvényes.{RESET}")
            print_help()
            return 1
        else:
            # Ha két fájlt ad meg kapcsoló nélkül
            print(f"{RED}Hiba: Két fájl esetén kötelező kapcsolót megadni.{RESET}")
            print_help()
            return 1
            
    return 0

if __name__ == "__main__":
    exit_code = main(sys.argv)
    sys.exit(exit_code)
