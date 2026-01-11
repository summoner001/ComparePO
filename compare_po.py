#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unified PO Tool (Egyesített PO Eszköz)

Egyesíti az extractpo.py, tegezodes.py és comparepo.py funkcióit egyetlen,
korszerűsített eszközben.

Főbb funkciók:
- Szövegkinyerés (Extract)
- Intelligens tegeződés-ellenőrzés (Spacy NLP alapon)
- Összehasonlítás (Compare)
- Kitöltés (Fill iOS/Android között)
- Formátum és helyesírás-ellenőrzés
- Merge HU-EN fájlok
"""
from __future__ import annotations
import sys
import re
import os
import html
import unicodedata
import ast
import argparse
import glob
import json
import yaml
from typing import Dict, List, Tuple, Optional, Set, Any
from datetime import datetime
from difflib import SequenceMatcher

# --- Konfiguráció és színek ---
RESET = "\033[0m"
BOLD = "\033[1m"
RED = "\033[31m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
BLUE = "\033[34m"
MAGENTA = "\033[35m"
CYAN = "\033[36m"
SIMILARITY_THRESHOLD = 0.70

# --- HTML CSS Template (A tegezodes.py alapján, kiegészítve a diff stílusokkal) ---
HTML_TEMPLATE_FULL = """<!DOCTYPE html>
<html lang="hu">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <style>
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            line-height: 1.6;
            margin: 0;
            padding: 20px;
            background-color: #f5f5f5;
            color: #2c3e50;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background-color: white;
            padding: 30px;
            border-radius: 10px;
            box-shadow: 0 0 20px rgba(0,0,0,0.1);
        }}
        h1 {{
            color: #2c3e50;
            border-bottom: 3px solid #3498db;
            padding-bottom: 10px;
        }}
        h2 {{
            color: #34495e;
            margin-top: 30px;
            font-size: 1.2em;
        }}
        /* ENTRY STÍLUSOK (Tegezodes.py stílus + Comparepo kiegészítések) */
        .entry {{
            background-color: #f8f9fa;
            border-left: 4px solid #3498db;
            padding: 15px;
            margin-bottom: 20px;
            border-radius: 0 5px 5px 0;
            overflow: hidden;
        }}
        .entry-header {{ 
            /* Comparepo kompatibilitás */
            font-weight: bold; font-size: 14px; color: #57606a; margin-bottom: 5px;
        }}
        .entry-body {{ 
            /* Comparepo kompatibilitás */
            font-family: monospace; font-size: 14px; white-space: pre-wrap; word-break: break-all; 
        }}
        
        .msgid {{
            color: #7f8c8d;
            font-weight: bold;
            margin-bottom: 10px;
            padding: 8px;
            background-color: #ecf0f1;
            border-radius: 4px;
            display: block;
        }}
        .msgstr {{
            color: #2c3e50;
            margin-bottom: 10px;
            padding: 8px;
            background-color: white;
            border: 1px solid #ddd;
            border-radius: 4px;
            line-height: 1.8;
            display: block;
        }}
        
        /* Tegeződés specifikus */
        .tegezo {{
            background-color: #ffebee;
            color: #c62828;
            font-weight: bold;
            padding: 2px 4px;
            border-radius: 3px;
            border: 1px solid #ffcdd2;
        }}
        .highlight {{
            background-color: #fff3cd;
            padding: 10px;
            border-left: 4px solid #ffc107;
            margin: 10px 0;
        }}
        
        /* Stats Block */
        .stats {{
            background-color: #e8f4fc;
            padding: 15px;
            border-radius: 5px;
            margin-bottom: 20px;
        }}
        .count {{
            display: inline-block;
            background-color: #3498db;
            color: white;
            padding: 3px 8px;
            border-radius: 12px;
            font-size: 0.9em;
            margin-left: 10px;
        }}
        .warning {{
            background-color: #fff3cd;
            border-left: 4px solid #ffc107;
            padding: 15px;
            margin: 20px 0;
            border-radius: 0 5px 5px 0;
        }}

        /* COMPARE / DIFF STÍLUSOK (A comparepo-ból integrálva) */
        .diff-row {{ display: flex; flex-direction: column; gap: 5px; }}
        .diff-line {{ display: block; padding: 2px 5px; }}
        .del-line {{ color: #24292f; }}
        .add-line {{ color: #24292f; }}
        .diff-del {{ background-color: #ffebe9; color: #cf222e; text-decoration: inherit; }}
        .diff-add {{ background-color: #dafbe1; color: #1a7f37; text-decoration: inherit; }}
        .label {{ display: inline-block; width: 150px; font-weight: bold; color: #57606a; user-select: none; }}
        
        .issue-item {{ color: #cf222e; margin-left: 20px; }}
        .highlight-err {{ background-color: #ffebe9; color: #cf222e; font-weight: bold; border-bottom: 2px solid #cf222e; }}

        footer {{
            margin-top: 40px;
            text-align: center;
            color: #7f8c8d;
            font-size: 0.9em;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>{title}</h1>
        
        {stats_block}
        
        <div class="report-content">
            {content_html}
        </div>

        <footer>
            Előállítva: {timestamp} | Unified PO Tool
        </footer>
    </div>
</body>
</html>
"""

# --- Regexek és beállítások ---
WORD_RE = re.compile(r"[\w]+(?:-[\w]+)*", re.UNICODE)
PLACEHOLDER_PATTERNS = [r"%\d+\$[sd@]", r"%lld", r"%[sd@u%]"]
PLACEHOLDER_RE = re.compile("|".join(f"(?:{p})" for p in PLACEHOLDER_PATTERNS))
PLACEHOLDER_TOKEN = "{PH}"
MARKDOWN_HTML_TAG_RE = re.compile(r'<[^>]+>|<!\[CDATA\[|\]\]>|(\*\*|__|\*|_|`|~~)')

# --- SPELLCHECK FILTEREK ---
ICON_EMOJI_RE = re.compile(r':[\w]+:')
COLOR_TAG_RE = re.compile(r'\[(?:accent|red|lightgray|green|blue|yellow|orange|purple|cyan|magenta|gray|black|white)?\]')
ANNOTATION_RE = re.compile(r'@[\wáéíóöőúüűÁÉÍÓÖŐÚÜŰ]+')
COLOR_CODE_RE = re.compile(r'%[0-9a-fA-F]{6}')

# --- Hunspell inicializálás ---
try:
    import hunspell
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
                continue
    if not HS_OBJ:
        pass # Később jelezzük, ha kell
except ImportError:
    HS_OBJ = None

# --- Spacy / Polib inicializálás (Lazy load where needed, but imported here) ---
try:
    import polib
except ImportError:
    polib = None

# Spacy-t a TegezoChecker osztályban töltjük be, hogy ne lassítsa a többi funkciót, ha nincs rá szükség.

# =============================================================================
# TEGEZŐDÉS CHECKER OSZTÁLY (tegezodes.py alapján)
# =============================================================================

class TegezoChecker:
    def __init__(self):
        """Előkészíti a HuSpaCy NLP modellt"""
        import spacy
        print(f"{CYAN}⏳ HuSpaCy modell betöltése…{RESET}")
        try:
            self.nlp = spacy.load("hu_core_news_lg")
            print(f"{GREEN}✅ Modell betöltve{RESET}")
        except Exception as e:
            print(f"{RED}❌ Hiba a modell betöltésekor: {e}{RESET}")
            print(f"{YELLOW}Telepítse: python -m spacy download hu_core_news_lg{RESET}")
            sys.exit(1)
    
    def find_tegezo_words(self, text):
        """Megkeresi a tegező szavakat egy szövegben"""
        if not text or not text.strip():
            return [], text
        
        doc = self.nlp(text)
        tegezo_words = []
        positions = []
        
        for token in doc:
            morph = token.morph.to_dict()
            
            # 1. Második személyű igék (te/ti)
            if token.pos_ in ("VERB", "AUX"):
                if morph.get("Person") == "2":
                    tegezo_words.append(token.text)
                    positions.append((token.idx, token.idx + len(token.text)))
            
            # 2. Második személyű birtokos főnevek (te/ti)
            elif token.pos_ in ("NOUN", "PROPN", "PRON"):
                if (morph.get("Number[psor]") == "Sing" and 
                    morph.get("Person[psor])") == "2"):
                    tegezo_words.append(token.text)
                    positions.append((token.idx, token.idx + len(token.text)))
            
            # 3. Felszólító mód (második személy)
            elif morph.get("Mood") == "Imp":
                tegezo_words.append(token.text)
                positions.append((token.idx, token.idx + len(token.text)))
        
        # Kiemelés alkalmazása
        if positions:
            positions.sort()
            merged_positions = []
            current_start, current_end = positions[0]
            
            for start, end in positions[1:]:
                if start <= current_end:
                    current_end = max(current_end, end)
                else:
                    merged_positions.append((current_start, current_end))
                    current_start, current_end = start, end
            merged_positions.append((current_start, current_end))
            
            highlighted_text = text
            for start, end in reversed(merged_positions):
                word = text[start:end]
                highlighted = f'<span class="tegezo">{word}</span>'
                highlighted_text = highlighted_text[:start] + highlighted + highlighted_text[end:]
            
            return tegezo_words, highlighted_text
        
        return tegezo_words, text
    
    def process_po_file(self, po_file_path):
        """Feldolgoz egy PO-fájlt"""
        if not polib:
            print(f"{RED}Hiba: 'polib' modul hiányzik.{RESET}")
            return None

        print(f"📖 PO-fájl betöltése: {po_file_path}")
        try:
            po = polib.pofile(po_file_path)
        except Exception as e:
            print(f"{RED}❌ Hiba a PO-fájl betöltésekor: {e}{RESET}")
            return None
        
        results = []
        total_entries = len(po)
        tegezo_entries_count = 0
        total_tegezo_words = 0
        
        print(f"🔍 {total_entries} bejegyzés ellenőrzése...")
        
        for i, entry in enumerate(po, 1):
            if i % 100 == 0:
                print(f"  Ellenőrzött bejegyzések: {i}/{total_entries}", end='\r')
            
            entry_result = {
                'msgid': entry.msgid,
                'msgstr': entry.msgstr,
                'msgstr_plural': entry.msgstr_plural if hasattr(entry, 'msgstr_plural') else {},
                'tegezo_words': [],
                'has_tegezo': False,
                'highlighted_msgstr': entry.msgstr,
                'highlighted_plural': {}
            }
            
            # Egyes szám
            if entry.msgstr:
                words, highlighted = self.find_tegezo_words(entry.msgstr)
                if words:
                    entry_result['tegezo_words'].extend(words)
                    entry_result['has_tegezo'] = True
                    entry_result['highlighted_msgstr'] = highlighted
            
            # Többes szám
            if hasattr(entry, 'msgstr_plural') and entry.msgstr_plural:
                for key, text in entry.msgstr_plural.items():
                    if text:
                        words, highlighted = self.find_tegezo_words(text)
                        if words:
                            entry_result['tegezo_words'].extend(words)
                            entry_result['has_tegezo'] = True
                            entry_result['highlighted_plural'][key] = highlighted
            
            if entry_result['has_tegezo']:
                tegezo_entries_count += 1
                total_tegezo_words += len(entry_result['tegezo_words'])
                results.append(entry_result)
        
        print(f"\n✅ Kész! Találatok:")
        print(f"   • Összes bejegyzés: {total_entries}")
        print(f"   • Tegező bejegyzések: {tegezo_entries_count}")
        print(f"   • Talált tegező szavak: {total_tegezo_words}")
        
        return {
            'results': results,
            'stats': {
                'total_entries': total_entries,
                'tegezo_entries': tegezo_entries_count,
                'total_tegezo_words': total_tegezo_words,
                'filename': os.path.basename(po_file_path)
            }
        }

    def escape_html(self, text):
        if not text: return ""
        return html.escape(text)


# =============================================================================
# SEGÉDFÜGGVÉNYEK (comparepo.py + extractpo.py)
# =============================================================================

def colored(text: str, color: str) -> str:
    if not text: return ""
    return f"{color}{text}{RESET}"

def save_html_report_unified(filename: str, title: str, content_html: str, stats_block: str = ""):
    """A közös, modern HTML sablont használó mentési függvény."""
    ts = datetime.now().strftime('%Y.%m.%d. %H:%M:%S')
    full_html = HTML_TEMPLATE_FULL.format(
        title=title,
        stats_block=stats_block,
        content_html=content_html,
        timestamp=ts
    )
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(full_html)
        print(colored(f"HTML jelentés elmentve: {filename}", GREEN))
    except Exception as e:
        print(colored(f"Hiba a HTML mentésekor: {e}", RED))

def ask_to_save_report(html_content_entries: List[str], filename_base: str, title: str, stats_html: str = ""):
    """Kérdőív a lista elmentéséről."""
    if not html_content_entries:
        return
    try:
        user_input = input(colored(f"Elmenti a fenti listát HTML-formátumban? (Y/n) ", CYAN)).strip().lower()
    except (EOFError, KeyboardInterrupt):
        user_input = ''
        
    if user_input in ['', 'y', 'i', 'igen']:
        ts = datetime.now().strftime('%Y%m%d_%H%M%S')
        html_filename = f"{filename_base}_{ts}.html"
        joined_html = "\n".join(html_content_entries)
        save_html_report_unified(html_filename, title, joined_html, stats_html)
    elif user_input == 'n':
        print(colored("A lista elmentése kihagyva.", YELLOW))
        return  # Csak kilép, nem kér további Entert
    else:
        # Default: auto-mentés
        ts = datetime.now().strftime('%Y%m%d_%H%M%S')
        html_filename = f"{filename_base}_{ts}.html"
        joined_html = "\n".join(html_content_entries)
        save_html_report_unified(html_filename, title, joined_html, stats_html)

def get_diff_viz(s1: str, s2: str) -> Tuple[str, str, str, str]:
    """Karakter-szintű diff előállítása ANSI és HTML-formátumban."""
    matcher = SequenceMatcher(None, s1, s2)
    ansi_s1, ansi_s2 = [], []
    html_s1, html_s2 = [], []

    for op, i1, i2, j1, j2 in matcher.get_opcodes():
        text1 = s1[i1:i2]
        text2 = s2[j1:j2]
        safe_text1 = html.escape(text1)
        safe_text2 = html.escape(text2)

        if op == 'equal':
            ansi_s1.append(text1); ansi_s2.append(text2)
            html_s1.append(safe_text1); html_s2.append(safe_text2)
        elif op == 'replace':
            ansi_s1.append(colored(text1, RED)); ansi_s2.append(colored(text2, GREEN))
            html_s1.append(f'<span class="diff-del">{safe_text1}</span>')
            html_s2.append(f'<span class="diff-add">{safe_text2}</span>')
        elif op == 'delete':
            ansi_s1.append(colored(text1, RED))
            html_s1.append(f'<span class="diff-del">{safe_text1}</span>')
        elif op == 'insert':
            ansi_s2.append(colored(text2, GREEN))
            html_s2.append(f'<span class="diff-add">{safe_text2}</span>')

    return "".join(ansi_s1), "".join(ansi_s2), "".join(html_s1), "".join(html_s2)

def strip_formatting_and_normalize_ws(s: Optional[str]) -> str:
    if not s: return ""
    s = re.sub(r'<!\[CDATA\[(.*?)\]\]>', r'\1', s, flags=re.DOTALL)
    s = html.unescape(s)
    s = MARKDOWN_HTML_TAG_RE.sub('', s)
    s = unicodedata.normalize("NFKC", s)
    return ' '.join(s.split()).strip()

def extract_visible_text(s: Optional[str]) -> str:
    if not s: return ""
    parts = re.findall(r'<!\[CDATA\[(.*?)\]\]>', s, flags=re.DOTALL)
    txt = " ".join(parts) if parts else s
    txt = re.sub(r'<[^>]+>', ' ', txt)
    txt = html.unescape(txt)
    txt = unicodedata.normalize("NFKC", txt)
    return ' '.join(txt.split()).strip()

def normalize_placeholders(s: str) -> str:
    return PLACEHOLDER_RE.sub(PLACEHOLDER_TOKEN, s)

def remove_placeholders(s: str) -> str:
    cleaned = PLACEHOLDER_RE.sub(" ", s or "")
    return ' '.join(cleaned.split()).strip()

def extract_placeholders_list(s: str) -> List[str]:
    if not s: return []
    return [m.group(0) for m in PLACEHOLDER_RE.finditer(s)]

def _normalize_end_punctuation_except_q(s: str) -> Tuple[str, bool]:
    if not s: return "", False
    s_clean = strip_formatting_and_normalize_ws(s)
    if not s_clean: return "", False
    ends_with_q = s_clean.endswith('?')
    if ends_with_q:
        s_base = s_clean[:-1].rstrip()
    else:
        s_base = re.sub(r'[.\!…\s]+$', '', s_clean)
    return s_base, ends_with_q

def canonicalize_msgid(original_msgid: str) -> Tuple[str, str]:
    if not original_msgid: return "", ""
    stripped = strip_formatting_and_normalize_ws(original_msgid)
    display = stripped
    ph_normalized = normalize_placeholders(stripped)
    base_text_ph_normalized, ends_with_q = _normalize_end_punctuation_except_q(ph_normalized)
    canonical = base_text_ph_normalized.lower()
    if ends_with_q: canonical += "{Q}"
    canonical = ' '.join(canonical.split())
    return canonical, display

def get_word_count_from_display(display: str) -> int:
    if not display: return 0
    cleaned_no_ph = PLACEHOLDER_RE.sub(" ", display)
    words = WORD_RE.findall(cleaned_no_ph)
    return len([w for w in words if w])

def _placeholder_stripped_equal(s1: str, s2: str) -> bool:
    ph_list1 = extract_placeholders_list(s1)
    ph_list2 = extract_placeholders_list(s2)
    if len(ph_list1) != len(ph_list2): return False
    s1_base, s1_end = _normalize_end_punctuation_except_q(remove_placeholders(s1))
    s2_base, s2_end = _normalize_end_punctuation_except_q(remove_placeholders(s2))
    if s1_end != s2_end: return False
    return s1_base.lower() == s2_base.lower()

def get_word_set(translation: Optional[str]) -> Set[str]:
    if not translation: return set()
    cleaned = strip_formatting_and_normalize_ws(translation)
    cleaned_no_ph = remove_placeholders(cleaned)
    words = WORD_RE.findall(cleaned_no_ph)
    return {word.lower() for word in words if word}

def check_divergence(msgstr1: str, msgstr2: str, debug: bool = False) -> Tuple[bool, float]:
    if _placeholder_stripped_equal(msgstr1, msgstr2): return False, 1.0
    words1 = get_word_set(msgstr1)
    words2 = get_word_set(msgstr2)
    if not words1 and not words2: return False, 1.0
    intersection = words1.intersection(words2)
    union = words1.union(words2)
    jaccard = len(intersection) / len(union) if union else 0.0
    return jaccard < SIMILARITY_THRESHOLD, jaccard

def adapt_placeholders_using_msgids(source_msgstr: str, source_msgid: str, target_msgid: str) -> str:
    if not source_msgstr or not source_msgid or not target_msgid: return source_msgstr
    stripped_source = strip_formatting_and_normalize_ws(remove_placeholders(source_msgid))
    stripped_target = strip_formatting_and_normalize_ws(remove_placeholders(target_msgid))
    if stripped_source != stripped_target: return source_msgstr
    source_msgstr_ph = list(PLACEHOLDER_RE.finditer(source_msgstr))
    target_id_ph_list = extract_placeholders_list(target_msgid)
    if not source_msgstr_ph or not target_id_ph_list: return source_msgstr
    if len(source_msgstr_ph) != len(target_id_ph_list): return source_msgstr
    out = []
    last = 0
    for idx, m in enumerate(source_msgstr_ph):
        out.append(source_msgstr[last:m.start()])
        out.append(target_id_ph_list[idx])
        last = m.end()
    out.append(source_msgstr[last:])
    return ''.join(out)

def po_escape(s: str) -> str:
    if s is None: s = ""
    s = s.replace('\\', '\\\\').replace('"', '\\"').replace('\r\n', '\n').replace('\r', '\n')
    s = s.replace('\n', '\\n').replace('\t', '\\t')
    return f'"{s}"'

# --- PO Olvasás / Írás ---

def _parse_po_string(line: str) -> str:
    line = line.strip()
    if len(line) >= 2 and line.startswith('"') and line.endswith('"'):
        content = line[1:-1]
        try:
            return ast.literal_eval(f'"{content}"')
        except Exception:
            return content.replace('\\"', '"').replace('\\n', '\n').replace('\\t', '\t').replace('\\\\', '\\')
    return ""

def load_po_simple(path: str) -> Dict[str, str]:
    entries: Dict[str, str] = {}
    current_msgid = []
    current_msgstr = []
    current_msgstr_0 = []
    state = None
    
    def process_entry():
        nonlocal current_msgid, current_msgstr, current_msgstr_0, state
        if current_msgid:
            fid = "".join(_parse_po_string(l) for l in current_msgid)
            fstr = "".join(_parse_po_string(l) for l in current_msgstr)
            fstr0 = "".join(_parse_po_string(l) for l in current_msgstr_0)
            final_str = fstr if fstr else fstr0
            if fid: entries[fid] = final_str or ""
        current_msgid = []; current_msgstr = []; current_msgstr_0 = []; state = None

    try:
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                ls = line.strip()
                if not ls or ls.startswith('#'): continue
                if ls.startswith("msgid "):
                    process_entry(); state = 'msgid'; current_msgid.append(ls[len("msgid "):])
                elif ls.startswith("msgstr[0]"):
                    state = 'msgstr0'; current_msgstr_0.append(ls[len("msgstr[0] "):])
                elif ls.startswith("msgstr "):
                    state = 'msgstr'; current_msgstr.append(ls[len("msgstr "):])
                elif ls.startswith("msgstr["):
                    state = None
                elif ls.startswith('"') and ls.endswith('"'):
                    if state == 'msgid': current_msgid.append(ls)
                    elif state == 'msgstr': current_msgstr.append(ls)
                    elif state == 'msgstr0': current_msgstr_0.append(ls)
                else:
                    process_entry(); state = None
        process_entry()
    except Exception:
        return {}
    return entries

def load_po(path: str) -> Dict[str, str]:
    if polib:
        try:
            po = polib.pofile(path, encoding='utf-8')
            entries = {}
            for e in po:
                if not e.msgid or getattr(e, "obsolete", False): continue
                tr = e.msgstr or ""
                if not tr and getattr(e, "msgstr_plural", None):
                    if isinstance(e.msgstr_plural, dict) and '0' in e.msgstr_plural: tr = e.msgstr_plural['0']
                    elif isinstance(e.msgstr_plural, (list,tuple)) and len(e.msgstr_plural)>0: tr = e.msgstr_plural[0]
                entries[e.msgid] = tr or ""
            return entries
        except Exception:
            return load_po_simple(path)
    return load_po_simple(path)

def build_canonical_map(entries: Dict[str, str]) -> Dict[str, Tuple[str, str, str]]:
    d = {}
    for orig_id, orig_str in entries.items():
        if not orig_id: continue
        key, disp = canonicalize_msgid(orig_id)
        if key: d[key] = (orig_id, orig_str or "", disp)
    return d

def build_translation_map_for_fill(path: str) -> Dict[str, Tuple[str, str]]:
    entries = load_po(path)
    result = {}
    for msgid, msgstr in entries.items():
        key, _ = canonicalize_msgid(msgid)
        if key: result[key] = (msgid, msgstr or "")
    return result

def split_file_into_entries(lines: List[str]) -> Tuple[List[str], List[List[str]]]:
    msgid_indices = [idx for idx, ln in enumerate(lines) if ln.lstrip().startswith("msgid ")]
    if not msgid_indices: return (lines, [])
    preamble = lines[:msgid_indices[0]]
    blocks = []
    for i, start in enumerate(msgid_indices):
        end = msgid_indices[i+1] if i+1 < len(msgid_indices) else len(lines)
        blocks.append(lines[start:end])
    return preamble, blocks

def parse_entry_block(block: List[str]) -> Tuple[str, str, Dict[int, str]]:
    msgid, msgstr = [], []
    plurals = {}
    state = None
    curr_plural = -1
    for ln in block:
        s = ln.strip()
        if not s or s.startswith("#"): continue
        if s.startswith("msgid "): state="msgid"; msgid.append(s[len("msgid "):])
        elif s.startswith("msgstr["):
            state="msgstrplural"; m=re.match(r'msgstr\[(\d+)\]\s*(.*)',s)
            if m: curr_plural=int(m.group(1)); plurals.setdefault(curr_plural,[]).append(m.group(2) or '')
            else: curr_plural=-1
        elif s.startswith("msgstr "): state="msgstr"; msgstr.append(s[len("msgstr "):])
        elif s.startswith('"') and s.endswith('"'):
            if state=="msgid": msgid.append(s)
            elif state=="msgstr": msgstr.append(s)
            elif state=="msgstrplural" and curr_plural!=-1: plurals[curr_plural].append(s)
        else: state=None; curr_plural=-1
    
    full_id = "".join(_parse_po_string(l) for l in msgid) if msgid else ""
    full_str = "".join(_parse_po_string(l) for l in msgstr) if msgstr else ""
    full_plurals = {k: "".join(_parse_po_string(l) for l in p) for k,p in plurals.items()}
    return full_id, full_str, full_plurals

def replace_msgstr_in_block(block: List[str], new_msgstr: Optional[str], plural_index: Optional[int]=None) -> List[str]:
    out = []
    i = 0
    replaced = False
    target = f"msgstr[{plural_index}] " if plural_index is not None else "msgstr "
    while i < len(block):
        ln = block[i]
        s = ln.lstrip()
        if s.startswith(target):
            out.append(ln[:len(ln)-len(s)] + target + po_escape(new_msgstr or "") + "\n")
            replaced = True; i += 1
            while i < len(block) and block[i].lstrip().startswith('"'): i += 1
            continue
        out.append(ln); i += 1
    
    if not replaced:
        # Beszúrás
        esc = po_escape(new_msgstr or "")
        line_to_add = f"{target}{esc}\n"
        res = []
        i = 0; inserted = False
        while i < len(out):
            res.append(out[i])
            ln = out[i]; s = ln.lstrip()
            if s.startswith("msgid ") or (s.startswith('"') and i>0 and (out[i-1].lstrip().startswith("msgid ") or out[i-1].lstrip().startswith('"'))):
                 j = i + 1
                 while j < len(out) and out[j].lstrip().startswith('"'): res.append(out[j]); j+=1
                 res.append(line_to_add); inserted = True; i = j; continue
            i+=1
        if not inserted: out.append(line_to_add)
        else: out = res
    return out

def ensure_fuzzy_flag(block: List[str]) -> List[str]:
    fuzzy_found = False
    flags_idx = -1
    first_code = 0
    for i, ln in enumerate(block):
        ls = ln.lstrip()
        if not ls.startswith("#"): first_code=i; break
        if ls.startswith("#,"):
            flags_idx = i
            if "fuzzy" in ls.split(','): fuzzy_found=True; break
    else: first_code = len(block)
    
    if fuzzy_found: return block
    if flags_idx != -1:
        ln = block[flags_idx]; ls = ln.lstrip()
        indent = ln[:len(ln)-len(ls)]
        exist = ls[2:].strip()
        block[flags_idx] = f"{indent}#, fuzzy, {exist}\n" if exist else f"{indent}#, fuzzy\n"
    else:
        # Beszúrás az elejére, de a kommentek közé ha van
        indent = ""
        if block: indent = block[0][:len(block[0])-len(block[0].lstrip())]
        insert_idx = 0
        if first_code > 0 and block[0].startswith("#"): pass # Kommentek után? Inkább elé
        block.insert(insert_idx, f"{indent}#, fuzzy\n")
    return block

def write_po_file(path: str, preamble: List[str], blocks: List[List[str]], orig_lines: List[str]):
    out = []
    out.extend(preamble)
    for b in blocks: out.extend(b)
    if orig_lines and orig_lines[-1].strip() == "" and (not out or out[-1].strip() != ""):
        out.append("\n")
    try:
        with open(path, "w", encoding="utf-8", newline="\n") as f: f.writelines(out)
        return True
    except Exception as e:
        print(f"{RED}Hiba íráskor: {e}{RESET}"); return False

# --- Issue Checks ---
def check_cdata_balance(s): return "CDATA hiba" if s and s.count('<![CDATA[')!=s.count(']]>') else None
def check_markdown_balance(s):
    if not s or '<![CDATA[' in s or re.search(r'<[^>]+>', s): return None
    v = extract_visible_text(s)
    for m in ['`', '**', '__', '~~']:
        if v.count(m)%2!=0: return f"Markdown hiba: {m}"
    if v.count('*')%2!=0: return "Markdown hiba: *"
    return None
def check_html_tag_balance(s):
    if not s or '<![CDATA[' in s: return None
    tags = re.findall(r'<\s*(/)?\s*([a-zA-Z][a-zA-Z0-9:-]*)[^>]*>', s)
    cnt = {}
    for cl, n in tags:
        if n.lower() in ["br","img","hr","input","meta","link"]: continue
        cnt.setdefault(n.lower(),0); cnt[n.lower()] += -1 if cl else 1
    err = [n for n,c in cnt.items() if c!=0]
    return f"HTML tag hiba: {', '.join(err)}" if err else None
def check_ellipsis_usage(s): return "ASCII ellipszis (...)" if s and '...' in extract_visible_text(s) and '…' not in s else None
def check_quotes_usage(s):
    if not s: return None
    v = extract_visible_text(s)
    if ('"' in v or "'" in v) and not ('„' in v or '”' in v): return "Egyenes idézőjel"
    return None

def collect_issues_for_entry(msgid: str, msgstr: str, checks: Set[str]) -> List[str]:
    issues = []
    for lbl, txt in (("msgid", msgid), ("msgstr", msgstr)):
        if not txt: continue
        if 'format' in checks:
            for f in [check_cdata_balance, check_markdown_balance, check_html_tag_balance]:
                r = f(txt)
                if r: issues.append(f"{lbl}: {r}")
        if lbl == "msgstr":
            if 'irasjel' in checks:
                for f in [check_ellipsis_usage, check_quotes_usage]:
                    r = f(txt)
                    if r: issues.append(f"{lbl}: {r}")
            # Tegeződés itt már NINCS, mert külön Spacy-s logika van
    return issues


# =============================================================================
# FUNKCIÓK (Extract, Lint, Tegeződés, Compare, Fill, Merge)
# =============================================================================

def run_extract_translations(input_pattern: str):
    """Az extractpo.py funkciója: fordítások kinyerése txt fájlba."""
    if not polib:
        print(f"{RED}Hiba: 'polib' nincs telepítve. (pip install polib){RESET}")
        return 1
        
    files = glob.glob(input_pattern)
    if not files:
        print(f"{YELLOW}Nem található fájl a mintára: {input_pattern}{RESET}")
        return 1

    success = 0
    for input_file in files:
        if not os.path.isfile(input_file): continue
        try:
            po = polib.pofile(input_file)
            base_name = os.path.splitext(os.path.basename(input_file))[0]
            output_file = f"Extracted_{base_name}.txt"
            
            with open(output_file, 'w', encoding='utf-8') as f:
                for idx, entry in enumerate(po):
                    if entry.msgid and entry.msgstr and entry.msgid.strip():
                        f.write(f"msgid({idx+1}) = {entry.msgid}\n")
                        f.write(f"msgstr({idx+1}) = {entry.msgstr}\n")
            
            print(f"{GREEN}Kinyerve: {output_file}{RESET}")
            success += 1
        except Exception as e:
            print(f"{RED}Hiba ({input_file}): {e}{RESET}")
    
    print(f"Kész. {success}/{len(files)} fájl feldolgozva.")
    return 0

def run_tegezodes_spacy(path: str):
    """A tegezodes.py funkciója: Spacy alapú elemzés és HTML riport."""
    checker = TegezoChecker() # Ez betölti a Spacy-t
    result_data = checker.process_po_file(path)
    
    if not result_data:
        return 1
        
    data = result_data['results']
    stats = result_data['stats']
    filename = stats['filename']

    # Konzol kimenet
    if not data:
        print(f"{GREEN}🎉 Nem található tegező szó!{RESET}")
    else:
        print(f"\n{'='*60}")
        print(f"TEGEZŐ SZAVAK ({len(data)} találat)")
        print(f"{'='*60}\n")
        for i, entry in enumerate(data, 1):
            print(f"{'-'*60}")
            print(f"msgid: {entry['msgid'][:80]}{'...' if len(entry['msgid']) > 80 else ''}")
            print(f"msgstr: {entry['msgstr']}")
            if entry['tegezo_words']:
                highlighted = entry['msgstr']
                for w in set(entry['tegezo_words']):
                    highlighted = re.sub(r'\b'+re.escape(w)+r'\b', colored(w, RED), highlighted)
                print(f"tegező: {highlighted}")
            print(f"{'-'*60}\n")

    # HTML generálás
    if data:
        html_entries = []
        for i, entry in enumerate(data, 1):
            rows = f"""
            <div class="entry">
                <div class="entry-header">#{i} Msgid: {html.escape(entry['msgid'])}</div>
                <div class="entry-body">
                    <div class="msgstr">{entry['highlighted_msgstr']}</div>
            """
            if entry['highlighted_plural']:
                 rows += '<div style="margin-top:5px"><b>Plurál:</b></div>'
                 for k, t in entry['highlighted_plural'].items():
                     rows += f'<div class="msgstr">[{k}]: {t}</div>'
            
            unique_words = sorted(set(entry['tegezo_words']))
            rows += f"""
                    <div class="highlight">
                        <strong>Tegező szavak:</strong> {', '.join(unique_words)}
                    </div>
                </div>
            </div>
            """
            html_entries.append(rows)

        stats_html = f"""
        <div class="stats">
            <strong>Fájl:</strong> {filename}<br>
            <strong>Összes bejegyzés:</strong> {stats['total_entries']}<br>
            <strong>Tegező bejegyzések:</strong> {stats['tegezo_entries']}<br>
            <strong>Talált tegező szavak:</strong> {stats['total_tegezo_words']}
        </div>
        <div class="warning">
            <strong>⚠️ Figyelem:</strong> Pirossal kiemelve a tegező szavak. (Spacy NLP)
        </div>
        """
        
        ask_to_save_report(html_entries, f"tegezodes_{filename}", f"Tegeződés: {filename}", stats_html)
    return 0

def run_lint_mode(path: str, checks: Set[str], debug: bool = False):
    """Formátum-ellenőrzés (kivéve tegeződés, ami külön fut)."""
    fn = os.path.basename(path)
    entries = load_po(path)
    if not entries: return 1
    
    print(f"Fájl ellenőrzése: {fn} (Keresés: {', '.join(checks)})")
    problems = 0
    html_entries = []

    for orig_id, orig_str in entries.items():
        issues = collect_issues_for_entry(orig_id, orig_str, checks)
        if issues:
            problems += 1
            clean_id = strip_formatting_and_normalize_ws(orig_id)
            
            # Konzol kimenet
            print(f"{'-'*60}")
            print(f"msgid: {clean_id}")
            print(f"msgstr: {orig_str}")
            for p in issues:
                print(f"probléma: {p}")
            print(f"{'-'*60}\n")
            
            # HTML kimenet
            issue_html = "".join([f'<div class="issue-item">⚠ {html.escape(p)}</div>' for p in issues])
            html_entries.append(f"""
            <div class="entry">
                <div class="entry-header">#{problems} Msgid: {html.escape(clean_id)}</div>
                <div class="entry-body">
                    <div><b>Msgstr:</b> {html.escape(orig_str or "")}</div>
                    <div style="margin-top:10px;">{issue_html}</div>
                </div>
            </div>
            """)

    print(f"Problémás bejegyzések: {problems}")
    
    if problems > 0:
        stats_html = f'<div class="stats"><strong>Fájl:</strong> {fn}<br><strong>Hibák száma:</strong> {problems}</div>'
        ask_to_save_report(html_entries, f"lint_{fn}", f"Format Check: {fn}", stats_html)
    return 0

# --- JSON/YML/PROPERTIES fájlbetöltés spellcheck-hez ---
def load_texts_from_file(path: str) -> Dict[str, str]:
    """Különböző fájlformátumokból betölti a szövegeket."""
    ext = os.path.splitext(path)[1].lower()
    texts = {}
    
    try:
        if ext == '.json':
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            def extract_from_dict(d, prefix=""):
                for k, v in d.items():
                    full_key = f"{prefix}.{k}" if prefix else k
                    if isinstance(v, dict):
                        extract_from_dict(v, full_key)
                    elif isinstance(v, str) and v.strip():
                        texts[full_key] = v.strip()
                    elif isinstance(v, list):
                        for i, item in enumerate(v):
                            if isinstance(item, str) and item.strip():
                                texts[f"{full_key}[{i}]"] = item.strip()
            
            extract_from_dict(data)
            
        elif ext in ['.yml', '.yaml']:
            with open(path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
                
            def extract_from_yaml(data, prefix=""):
                if isinstance(data, dict):
                    for k, v in data.items():
                        full_key = f"{prefix}.{k}" if prefix else k
                        if isinstance(v, dict):
                            extract_from_yaml(v, full_key)
                        elif isinstance(v, str) and v.strip():
                            texts[full_key] = v.strip()
                        elif isinstance(v, list):
                            for i, item in enumerate(v):
                                if isinstance(item, str) and item.strip():
                                    texts[f"{full_key}[{i}]"] = item.strip()
                                elif isinstance(item, dict):
                                    extract_from_yaml(item, f"{full_key}[{i}]")
                elif isinstance(data, list):
                    for i, item in enumerate(data):
                        if isinstance(item, str) and item.strip():
                            texts[f"{prefix}[{i}]"] = item.strip()
                        elif isinstance(item, dict):
                            extract_from_yaml(item, f"{prefix}[{i}]")
            
            extract_from_yaml(data)
            
        elif ext == '.properties':
            with open(path, 'r', encoding='utf-8') as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue
                    if '=' in line:
                        key, value = line.split('=', 1)
                        key = key.strip()
                        value = value.strip()
                        if value:
                            texts[key] = value
        else:
            print(f"{RED}Ismeretlen fájlformátum: {ext}{RESET}")
            return {}
            
    except Exception as e:
        print(f"{RED}Hiba a fájl betöltésekor ({path}): {e}{RESET}")
        return {}
    
    return texts

def load_spellcheck_blacklist() -> Dict[str, List[str]]:
    """Betölti a spellcheck_blacklist.txt fájlt, ha létezik."""
    blacklist_file = "spellcheck_blacklist.txt"
    blacklist = {}
    
    if not os.path.exists(blacklist_file):
        return blacklist
    
    try:
        with open(blacklist_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        current_file = None
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Fájlnév keresése (elválasztó sor)
            if line.startswith('----'):
                continue
            
            # Fájlnév sor (amely nem tartalmaz szavakat vesszővel elválasztva)
            if not ',' in line and '.' in line:
                current_file = line
                blacklist[current_file] = []
            elif current_file and ',' in line:
                # Szavak feldolgozása
                words = [w.strip() for w in line.split(',')]
                for word in words:
                    if word and word not in blacklist[current_file]:
                        blacklist[current_file].append(word)
    
    except Exception as e:
        print(f"{YELLOW}Figyelmeztetés: Nem sikerült betölteni a blacklistet: {e}{RESET}")
    
    # Globális szavak összegyűjtése (minden fájlból)
    global_words = set()
    for words in blacklist.values():
        global_words.update(words)
    
    # Átalakítás set-é a gyorsabb kereséshez
    result = {}
    for file_name, words in blacklist.items():
        result[file_name] = set(words)
    result['GLOBAL'] = global_words
    
    return result

def save_to_spellcheck_blacklist(fn: str, misspelled_words: Set[str]):
    """Hozzáadja a hibás szavakat a blacklist fájlhoz."""
    blacklist_file = "spellcheck_blacklist.txt"
    
    # Betöltjük a meglévő blacklistet
    existing_data = {}
    if os.path.exists(blacklist_file):
        try:
            with open(blacklist_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Feldolgozzuk a meglévő tartalmat
            sections = content.split('\n\n')
            for section in sections:
                lines = section.strip().split('\n')
                if len(lines) >= 2:
                    file_name = lines[0]
                    if '----' in lines[1]:
                        words_line = lines[2] if len(lines) > 2 else ''
                    else:
                        words_line = lines[1]
                    
                    if words_line:
                        words = [w.strip() for w in words_line.split(',')]
                        existing_words = set(words)
                        existing_data[file_name] = existing_words
        except Exception as e:
            print(f"{YELLOW}Figyelmeztetés: Nem sikerült betölteni a blacklistet: {e}{RESET}")
            existing_data = {}
    
    # Frissítjük az adott fájl szavait
    if fn in existing_data:
        existing_data[fn].update(misspelled_words)
    else:
        existing_data[fn] = misspelled_words
    
    # ABC sorrendbe rendezzük a szavakat
    for file_name in existing_data:
        sorted_words = sorted(existing_data[file_name], key=lambda x: x.lower())
        existing_data[file_name] = sorted_words
    
    # Kiírjuk a fájlt
    try:
        with open(blacklist_file, 'w', encoding='utf-8') as f:
            for file_name in sorted(existing_data.keys()):
                words = existing_data[file_name]
                if words:
                    f.write(f"{file_name}\n")
                    f.write("-" * 33 + "\n")
                    f.write(", ".join(words) + "\n\n")
        
        print(f"{GREEN}Blacklist frissítve: {blacklist_file}{RESET}")
        return True
    except Exception as e:
        print(f"{RED}Hiba a blacklist mentésekor: {e}{RESET}")
        return False

def filter_special_syntax(text: str) -> str:
    """Kiszűri a speciális szintaxist a szövegből."""
    if not text:
        return text
    
    # 0. TELJES MARKUP BLOKKOK ELTÁVOLÍTÁSA (krítikus!)
    #    pl: [accent]felfedezhetsz[] → felfedezhetsz
    text = re.sub(
        r'\[(?:accent|red|lightgray|green|blue|yellow|orange|purple|cyan|magenta|gray|black|white)\](.*?)\[\]',
        r' \1 ',
        text,
        flags=re.DOTALL
    )
    
    # 1. Ikonok/emoji szintaxis (teljesen eltávolítjuk)
    text = ICON_EMOJI_RE.sub(' ', text)
    
    # 2. Színezések (most már csak a maradékokat)
    text = COLOR_TAG_RE.sub(' ', text)
    
    # 3. Annotációk
    text = ANNOTATION_RE.sub(' ', text)
    
    # 4. Színkódok
    text = COLOR_CODE_RE.sub(' ', text)
    
    # 5. Hex kódok (uf859, ue813 stb) - ezeket is teljesen eltávolítjuk
    text = re.sub(r'\b[uf]e?[0-9a-fA-F]{3,}\b', ' ', text)
    
    # 6. Egyéb speciális karakterek, amelyek hibás tokeneket okozhatnak
    #    A / karaktert szóelválasztóvá alakítjuk
    text = re.sub(r'/', ' ', text)
    # Csak a \.betű mintát távolítjuk el (pl. .draw, .puffer)
    text = re.sub(r'[\\]\.[a-zA-Z]', ' ', text)
    
    # 7. ÜRES ZÁRÓJELEK eltávolítása (pl. []) - biztonsági háló
    text = re.sub(r'\[\]', ' ', text)
    
    return text

def run_spellcheck_multiformat(path: str, debug: bool = False):
    """Helyesírás-ellenőrzés PROPERTIES/JSON/YML/PO fájlokra, kötőjel-barát módban."""
    if not HS_OBJ:
        print(f"{RED}Hiba: Hunspell nincs beállítva.{RESET}")
        return 1
    
    fn = os.path.basename(path)
    ext = os.path.splitext(path)[1].lower()
    
    if ext == '.po':
        entries = load_po(path)
        texts = {k: v for k, v in entries.items() if v}
    else:
        texts = load_texts_from_file(path)
    
    if not texts:
        print(f"{YELLOW}Nem található szöveg: {path}{RESET}")
        return 1
    
    blacklist = load_spellcheck_blacklist()
    global_blacklist = blacklist.get('GLOBAL', set())
    
    problems = 0
    all_misspelled_words = set()
    html_entries = []
    
    # SPECIÁLIS REGEX: Megtartja a betűket és a szavakon belüli kötőjeleket is
    # Így a "Wi-Fi-n" vagy "zip-fájl" egyetlen szó marad.
    HUN_WORD_RE = re.compile(r'[a-zA-ZáéíóöőúüűÁÉÍÓÖŐÚÜŰ0-9]+(?:-[a-zA-ZáéíóöőúüűÁÉÍÓÖŐÚÜŰ0-9]+)*')

    print(f"Helyesírás-ellenőrzés: {fn} ({len(texts)} szöveg)")
    
    for key, text in texts.items():
        if not text:
            continue
            
        # 1. HTML unescape
        vis = html.unescape(text)
        
        # 2. Zavaró elemek cseréje szóközre (hogy ne tapadjanak össze a szomszédos szavak)
        vis = vis.replace('\\n', ' ')
        vis = re.sub(r'[\r\n]+', ' ', vis)
        vis = re.sub(r'\[[^\]]*\]', ' ', vis) # [szín]
        vis = re.sub(r':[a-z0-9_-]+:', ' ', vis) # :ikon:
        
        # 3. Speciális szintaxis szűrése (eredeti filterek, pl. printf formátumok)
        filtered_vis = filter_special_syntax(vis)

        # 4. Szavak kinyerése a javított regex-szel
        tokens = HUN_WORD_RE.findall(filtered_vis)
        misspelled = []
        
        for w in tokens:
            # Rövid kódok vagy tiszta számok átugrása
            if len(w) < 2 or w.isdigit():
                continue
            if w.lower() in global_blacklist:
                continue
            if fn in blacklist and w.lower() in blacklist[fn]:
                continue
            
            # Ellenőrzés (Hunspell)
            if not HS_OBJ.spell(w) and not (w.istitle() and HS_OBJ.spell(w.lower())):
                # Ha kötőjeles szó, megnézzük a részeit is (pl. Wi-Fi esetén a Wi és Fi-t)
                # Ez segít, ha a szótár nem ismeri a kötőjeles formát, de a részeit igen.
                if '-' in w:
                    parts = [p for p in w.split('-') if len(p) > 1]
                    if all(HS_OBJ.spell(p) or (p.istitle() and HS_OBJ.spell(p.lower())) for p in parts):
                        continue

                misspelled.append(w)
                all_misspelled_words.add(w.lower())
        
        if misspelled:
            problems += 1
            term_text = text
            for w in sorted(set(misspelled), key=len, reverse=True):
                term_text = re.sub(r'\b'+re.escape(w)+r'\b', colored(w, RED), term_text)

            print(f"{'-'*60}")
            print(f"kulcs: {key}")
            print(f"szöveg: {term_text}")
            print(f"Helyesírási hiba: {', '.join(colored(w, RED) for w in sorted(set(misspelled)))}")
            print(f"{'-'*60}\n")
            
            # HTML kimenet
            hl_html = html.escape(text)
            for w in sorted(set(misspelled), key=len, reverse=True):
                esc = html.escape(w)
                hl_html = re.sub(r'\b'+re.escape(esc)+r'\b', f'<span class="highlight-err">{esc}</span>', hl_html)
            
            html_entries.append(f"""
            <div class="entry">
                <div class="entry-header">#{problems} Kulcs: {html.escape(key)}</div>
                <div class="entry-body">
                    {hl_html}
                    <div style="color:#cf222e;font-size:12px;margin-top:5px">Hibás: {', '.join(sorted(set(misspelled)))}</div>
                </div>
            </div>
            """)

    print(f"{GREEN}Kész. Hibák száma: {problems}{RESET}")
    
    if problems > 0:
        print(colored("\nMit szeretne tenni?", CYAN))
        print("1) Mentés HTML-be")
        print("2) Mentés blacklistbe")
        print("3) Kilépés")
        
        try:
            choice = input(colored("Válasszon (1-3): ", CYAN)).strip()
        except (EOFError, KeyboardInterrupt):
            choice = '3'
        
        if choice == '1':
            stats_html = f'<div class="stats"><strong>Fájl:</strong> {fn}<br><strong>Hibák:</strong> {problems}</div>'
            ts = datetime.now().strftime('%Y%m%d_%H%M%S')
            save_html_report_unified(f"spellcheck_{fn}_{ts}.html", f"Helyesírás: {fn}", "\n".join(html_entries), stats_html)
        elif choice == '2':
            if all_misspelled_words:
                save_to_spellcheck_blacklist(fn, all_misspelled_words)
    
    return 0

def run_irasjelek_fix(path: str, debug: bool = False):
    print(f"Írásjel-javítás: {path}")
    try:
        with open(path, "r", encoding="utf-8") as f: lines = f.readlines()
    except Exception as e:
        print(f"{RED}Hiba: {e}{RESET}"); return 1
    
    preamble, blocks = split_file_into_entries(lines)
    updated_blocks = []
    total_fixed = 0
    
    q_dbl_open = re.compile(r"(\s|^|\[)''")
    q_dbl_close = re.compile(r"''(\s|[,.]|\]|$)")
    ellipsis = re.compile(r'\.\.\.(?!\.)')
    dash = re.compile(r'[–—]')

    def fix_text(t):
        if not t: return t
        fixed = q_dbl_open.sub(r'\1„', t)
        fixed = q_dbl_close.sub(r'”\1', fixed)
        if fixed.count('"') > 0 and fixed.count('"') % 2 == 0:
            s = ""; o = True
            for c in fixed:
                if c=='"': s += "„" if o else "”"; o = not o
                else: s+=c
            fixed = s
        fixed = ellipsis.sub('…', fixed)
        fixed = dash.sub('-', fixed)
        return fixed

    for block in blocks:
        fid, fstr, plurals = parse_entry_block(block)
        if not fid: updated_blocks.append(block); continue
        
        mod = False
        new_b = list(block)
        
        if fstr:
            fx = fix_text(fstr)
            if fx != fstr:
                mod = True; new_b = replace_msgstr_in_block(new_b, fx)
        
        for i, pstr in plurals.items():
            if pstr:
                fx = fix_text(pstr)
                if fx != pstr:
                    mod = True; new_b = replace_msgstr_in_block(new_b, fx, plural_index=i)
        
        if mod:
            total_fixed += 1
            new_b = ensure_fuzzy_flag(new_b)
        updated_blocks.append(new_b)

    if total_fixed == 0:
        print("Nincs javítandó."); return 0
    
    out = f"javitott_irasjelek_{os.path.basename(path)}"
    if write_po_file(out, preamble, updated_blocks, lines):
        print(f"{GREEN}Kész! Javítva: {total_fixed}. Új fájl: {out}{RESET}")
    return 0

def run_compare(path1: str, path2: str, debug: bool = False):
    fn1, fn2 = os.path.basename(path1), os.path.basename(path2)
    e1, e2 = load_po(path1), load_po(path2)
    m1, m2 = build_canonical_map(e1), build_canonical_map(e2)
    common = set(m1.keys()) & set(m2.keys())
    diffs = 0
    html_entries = []
    
    print(f"Összehasonlítás: {fn1} vs {fn2} (Közös: {len(common)})")
    
    for k in sorted(common):
        orig1, str1, d1 = m1[k]
        orig2, str2, d2 = m2[k]
        if not str1 and not str2: continue
        
        div, sim = check_divergence(str1, str2)
        if not div: continue
        
        diffs += 1
        ansi1, ansi2, hs1, hs2 = get_diff_viz(str1 or "", str2 or "")
        
        # Konzol kimenet
        print(f"{'-'*60}")
        print(f"msgid: {d1}")
        print(f"{fn1}: {ansi1}")
        print(f"{fn2}: {ansi2}")
        print(f"hasonlóság: {int(sim*100)}%")
        print(f"{'-'*60}\n")
        
        # HTML kimenet
        html_entries.append(f"""
        <div class="entry">
            <div class="entry-header">Msgid: {html.escape(d1)}</div>
            <div class="entry-body diff-row">
                <div class="diff-line del-line"><span class="label">- {html.escape(fn1)}:</span>{hs1}</div>
                <div class="diff-line add-line"><span class="label">+ {html.escape(fn2)}:</span>{hs2}</div>
            </div>
            <div style="font-size:12px; color:#999; margin-top:5px">Hasonlóság: {int(sim*100)}%</div>
        </div>
        """)

    print(f"Eltérő fordítások: {diffs}")
    if diffs > 0:
        stats_html = f'<div class="stats"><strong>Összehasonlítás:</strong> {fn1} vs {fn2}<br><strong>Eltérések:</strong> {diffs}</div>'
        ask_to_save_report(html_entries, f"compare_{fn1}_{fn2}", f"Compare: {fn1} vs {fn2}", stats_html)
    return 0

def run_fill(source_po: str, target_po: str, debug: bool = False, out_filename: Optional[str] = None, egyszavas: bool = False):
    if not os.path.isfile(source_po) or not os.path.isfile(target_po): return 2
    src_map = build_translation_map_for_fill(source_po)
    s_fn, t_fn = os.path.basename(source_po), os.path.basename(target_po)
    
    try:
        with open(target_po, "r", encoding="utf-8") as f: lines = f.readlines()
    except Exception: return 1
    
    preamble, blocks = split_file_into_entries(lines)
    updated_blocks = []
    updated_count = 0
    divergence_list = []
    
    print(f"Kitöltés: {s_fn} -> {t_fn}")
    
    for block in blocks:
        fid, fstr, plurals = parse_entry_block(block)
        if not fid: updated_blocks.append(block); continue
        
        key, disp = canonicalize_msgid(fid)
        target_empty = not fstr.strip() and (not plurals or not any(v.strip() for v in plurals.values()))
        
        if key not in src_map:
            updated_blocks.append(block); continue
            
        src_orig, src_str = src_map[key]
        
        if not target_empty:
            div, sim = check_divergence(src_str, fstr)
            if div:
                divergence_list.append((disp, src_str, fstr))
            updated_blocks.append(block); continue
            
        if not src_str.strip(): updated_blocks.append(block); continue
        
        if not egyszavas and get_word_count_from_display(disp) <= 1:
            updated_blocks.append(block); continue

        # Kitöltés
        try:
            if len(extract_placeholders_list(src_orig)) == len(extract_placeholders_list(fid)):
                src_str = adapt_placeholders_using_msgids(src_str, src_orig, fid)
        except: pass
        
        new_b = list(block)
        has_plural = any(l.lstrip().startswith("msgstr[0]") for l in block)
        new_b = replace_msgstr_in_block(new_b, src_str, 0 if has_plural else None)
        new_b = ensure_fuzzy_flag(new_b)
        updated_blocks.append(new_b)
        updated_count += 1
        
    print(f"Kitöltve: {updated_count}. Eltérés (nem felülírt): {len(divergence_list)}")
    
    if updated_count > 0:
        out = out_filename or f"{os.path.splitext(target_po)[0]}_kiegeszitett.po"
        write_po_file(out, preamble, updated_blocks, lines)
        print(f"{GREEN}Létrehozva: {out}{RESET}")
    
    if divergence_list:
        html_entries = []
        # Konzol kimenet
        print(f"\n{'='*60}")
        print(f"ELTÉRÉSEK ({len(divergence_list)} találat)")
        print(f"{'='*60}\n")
        
        for disp, s1, s2 in divergence_list:
            ansi1, ansi2, hs1, hs2 = get_diff_viz(s1, s2)
            # Konzol
            print(f"{'-'*60}")
            print(f"msgid: {disp}")
            print(f"{s_fn}: {ansi1}")
            print(f"{t_fn}: {ansi2}")
            print(f"{'-'*60}\n")
            
            # HTML
            html_entries.append(f"""
            <div class="entry">
                <div class="entry-header">Msgid: {html.escape(disp)}</div>
                <div class="entry-body diff-row">
                    <div class="diff-line del-line"><span class="label">{html.escape(s_fn)}:</span>{hs1}</div>
                    <div class="diff-line add-line"><span class="label">{html.escape(t_fn)}:</span>{hs2}</div>
                </div>
            </div>
            """)
        stats_html = f'<div class="stats"><strong>Forrás:</strong> {s_fn}<br><strong>Cél:</strong> {t_fn}<br><strong>Eltérések:</strong> {len(divergence_list)}</div>'
        ask_to_save_report(html_entries, f"divergence_{t_fn}_{s_fn}", f"Divergencia: {t_fn} vs {s_fn}", stats_html)

    return 0

# --- Új Merge funkció ---
def run_merge_enhu(eng_file: str, hu_file: str, output_file: Optional[str] = None):
    """Angol és magyar fájlok összefésülése PO formátumba."""
    # Fájlformátum ellenőrzés
    eng_ext = os.path.splitext(eng_file)[1].lower()
    hu_ext = os.path.splitext(hu_file)[1].lower()
    
    if eng_ext != hu_ext:
        print(f"{RED}Hiba: A fájlok kiterjesztése nem egyezik: {eng_ext} vs {hu_ext}{RESET}")
        return 1
    
    # Fájlok betöltése
    eng_texts = load_texts_from_file(eng_file)
    hu_texts = load_texts_from_file(hu_file)
    
    if not eng_texts or not hu_texts:
        print(f"{RED}Hiba: Nem sikerült betölteni a fájlokat{RESET}")
        return 1
    
    # Kulcsok összehasonlítása
    eng_keys = set(eng_texts.keys())
    hu_keys = set(hu_texts.keys())
    
    if eng_keys != hu_keys:
        missing_in_hu = eng_keys - hu_keys
        missing_in_eng = hu_keys - eng_keys
        
        if missing_in_hu:
            print(f"{YELLOW}Figyelmeztetés: A magyar fájl hiányzó kulcsai: {missing_in_hu}{RESET}")
        if missing_in_eng:
            print(f"{YELLOW}Figyelmeztetés: Az angol fájl hiányzó kulcsai: {missing_in_eng}{RESET}")
        
        # Csak a közös kulcsokkal dolgozunk
        common_keys = eng_keys & hu_keys
        if not common_keys:
            print(f"{RED}Hiba: Nincs közös kulcs a fájlok között{RESET}")
            return 1
    else:
        common_keys = eng_keys
    
    # Output fájl nevének meghatározása
    if not output_file:
        base_name = os.path.splitext(hu_file)[0]
        output_file = f"{base_name}_merged.po"
    
    # PO fájl létrehozása
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            # PO header
            f.write('msgid ""\n')
            f.write('msgstr ""\n')
            f.write('"Project-Id-Version: \\n"\n')
            f.write('"POT-Creation-Date: \\n"\n')
            f.write('"PO-Revision-Date: \\n"\n')
            f.write('"Last-Translator: \\n"\n')
            f.write('"Language-Team: \\n"\n')
            f.write('"Language: hu\\n"\n')
            f.write('"MIME-Version: 1.0\\n"\n')
            f.write('"Content-Type: text/plain; charset=UTF-8\\n"\n')
            f.write('"Content-Transfer-Encoding: 8bit\\n"\n')
            f.write('"X-Generator: \\n"\n')
            f.write('\n')
            
            # Bejegyzések
            for key in sorted(common_keys):
                eng_text = eng_texts[key]
                hu_text = hu_texts[key]
                
                if not eng_text or not hu_text:
                    continue
                
                # msgctxt
                f.write(f'msgctxt "{key}"\n')
                
                # msgid (angol)
                f.write(f'msgid "{eng_text}"\n')
                
                # msgstr (magyar)
                f.write(f'msgstr "{hu_text}"\n')
                f.write('\n')
        
        print(f"{GREEN}Kész! Összefésült PO fájl: {output_file}{RESET}")
        return 0
        
    except Exception as e:
        print(f"{RED}Hiba az összefésülés során: {e}{RESET}")
        return 1

# =============================================================================
# MAIN
# =============================================================================

def print_help():
    print(f"""
{BOLD}Unified PO Tool v2.0 - Használat{RESET}

{YELLOW}Szövegkinyerés:{RESET}
  {sys.argv[0]} {CYAN}-extract{RESET} "*.po"    PO fájlok fordításainak kinyerése txt fájlokba.

{YELLOW}Egy fájl műveletek:{RESET}
  {sys.argv[0]} <fájl.po> [kapcsoló]

  {CYAN}-formatcheck{RESET}   Formátum (CDATA, HTML tag, Markdown) ellenőrzése.
  {CYAN}-irasjelek{RESET}     Idézőjelek („”), ellipszisek (…), kötőjelek (-) javítása.
  {CYAN}-spellcheck{RESET}    Helyesírás-ellenőrzés (Hunspell) PO, JSON, YML, PROPERTIES fájlokra.
                  Blacklist támogatás (spellcheck_blacklist.txt)
                  Menü: 1) HTML export, 2) Blacklist frissítés, 3) Kilépés
  {CYAN}-tegezodes{RESET}     {BOLD}NLP alapú{RESET} tegeződés-ellenőrzés (Spacy).
                  Igék, birtokosok, felszólító mód keresése.
                  Gyönyörű HTML riportot készít.

{YELLOW}Két fájl műveletek:{RESET}
  {sys.argv[0]} <fájl1.po> <fájl2.po> [kapcsoló]

  {CYAN}-compare{RESET}       Diff-szerű összehasonlítás.
  {CYAN}-fillios{RESET}       Android -> iOS kitöltés (fájl2 a cél).
  {CYAN}-filland{RESET}       iOS -> Android kitöltés (fájl2 a cél).
  {CYAN}-egyszavas{RESET}     Egyszavas bejegyzések átvitelének engedélyezése (-fill*-hez).

{YELLOW}Merge funkció (új):{RESET}
  {sys.argv[0]} {CYAN}-mergeenhu{RESET} <fájl1> <fájl2> [output_fájl]
                  Két fájl összefésülése PO formátumba.
                  Első fájl → msgid (általában angol)
                  Második fájl → msgstr (általában magyar)
                  msgctxt → az eredeti kulcs neve
                  Támogatott formátumok: .json, .yml, .properties
""")

def main():
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("-h", action="store_true")
    parser.add_argument("--debug", action="store_true")
    
    # Extract
    parser.add_argument("-extract", nargs="?", const="*.po", help="Pattern")

    # Single File
    parser.add_argument("-formatcheck", action="store_true")
    parser.add_argument("-irasjelek", action="store_true")
    parser.add_argument("-spellcheck", action="store_true")
    parser.add_argument("-tegezodes", action="store_true")
    
    # Two Files
    parser.add_argument("-compare", action="store_true")
    parser.add_argument("-filland", action="store_true")
    parser.add_argument("-fillios", action="store_true")
    parser.add_argument("-egyszavas", action="store_true")
    
    # Merge
    parser.add_argument("-mergeenhu", action="store_true")
    
    parser.add_argument("files", nargs="*")
    
    args, unknown = parser.parse_known_args()
    
    # Extract kezelése
    if args.extract:
        pattern = args.extract
        if args.extract == "*.po" and args.files:
            pattern = args.files[0]
        return run_extract_translations(pattern)

    if args.h or not args.files:
        print_help()
        return 0

    files = args.files
    debug = args.debug

    if len(files) == 1:
        path = files[0]
        if args.tegezodes: return run_tegezodes_spacy(path)
        if args.formatcheck: return run_lint_mode(path, {"format"}, debug)
        if args.spellcheck: return run_spellcheck_multiformat(path, debug)
        if args.irasjelek: return run_irasjelek_fix(path, debug)
        print(f"{RED}Egy fájl esetén válasszon kapcsolót!{RESET}")
        print_help()
        return 1

    if len(files) == 2:
        p1, p2 = files
        if args.compare: return run_compare(p1, p2, debug)
        if args.fillios: 
            return run_fill(p1, p2, debug, f"fillios_{'egyszavas_' if args.egyszavas else ''}{os.path.basename(p2)}", args.egyszavas)
        if args.filland:
            return run_fill(p1, p2, debug, f"filland_{'egyszavas_' if args.egyszavas else ''}{os.path.basename(p2)}", args.egyszavas)
    
    # Merge funkció kezelése (2 vagy 3 fájl)
    if args.mergeenhu:
        if len(files) < 2:
            print(f"{RED}Hiba: -mergeenhu-hez legalább 2 fájl kell{RESET}")
            print_help()
            return 1
        
        eng_file = files[0]
        hu_file = files[1]
        output_file = files[2] if len(files) > 2 else None
        
        return run_merge_enhu(eng_file, hu_file, output_file)
    
    print(f"{RED}Hibás paraméterek.{RESET}")
    print_help()
    return 1

if __name__ == "__main__":
    sys.exit(main())
