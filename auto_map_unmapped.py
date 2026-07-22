import csv
import json
import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent
TOP_UNMAPPED = ROOT / 'logs' / 'top_unmapped.csv'
RULE_FILE = ROOT / 'rules' / 'clinical_events.json'
SYN_FILE = ROOT / 'rules' / 'synonyms.json'

# Load known events
known = set()
with RULE_FILE.open('r', encoding='utf-8') as f:
    data = json.load(f)
    for sev, cats in data.items():
        if isinstance(cats, dict):
            for cat, events in cats.items():
                if isinstance(events, list):
                    for e in events:
                        known.add(e.lower().strip())

# Read top unmapped
if not TOP_UNMAPPED.exists():
    print('No top_unmapped.csv found')
    raise SystemExit(1)

unmapped = []
with TOP_UNMAPPED.open('r', encoding='utf-8-sig') as f:
    reader = csv.reader(f)
    headers = next(reader)
    for row in reader:
        if not row:
            continue
        canon = row[0].strip().lower()
        count = int(row[1]) if len(row) > 1 and row[1].isdigit() else 0
        unmapped.append((canon, count))

# Heuristic: token overlap with known events
mapping = {}
for canon, cnt in unmapped:
    # skip empty
    if not canon:
        continue
    # normalize tokens
    toks = re.split(r"[,&/()]+|\band\b", canon)
    toks = [t.strip() for t in toks if t.strip()]
    # try exact token match
    best = None
    best_score = 0
    for k in known:
        k_toks = set(k.split())
        for t in toks:
            t_toks = set(t.split())
            score = len(k_toks & t_toks)
            if score > best_score:
                best_score = score
                best = k
    if best_score > 0:
        mapping[canon] = best

# Filter mappings that are likely OK (count threshold optional)
print(f'Proposed mappings for {len(mapping)} entries')

# Append to synonyms.json
if mapping:
    with SYN_FILE.open('r', encoding='utf-8') as f:
        content = f.read()
    # prepare insertion text
    insert_lines = []
    for k, v in mapping.items():
        # ensure keys are JSON safe
        insert_lines.append(f'    "{k}": "{v}",')
    insert_text = '\n'.join(insert_lines)
    # insert before final closing brace
    if content.rstrip().endswith('}'):
        new_content = content.rstrip()[:-1].rstrip() + '\n' + insert_text + '\n}\n'
        with SYN_FILE.open('w', encoding='utf-8') as f:
            f.write(new_content)
        print(f'Appended {len(mapping)} mappings to {SYN_FILE}')
    else:
        print('Unexpected synonyms.json format - cannot append')
else:
    print('No mappings proposed')
