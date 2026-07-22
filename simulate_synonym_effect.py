import csv
import json
from collections import Counter
from pathlib import Path

from normalizer import EventNormalizer

ROOT = Path(__file__).resolve().parent
UNKNOWN_CSV = ROOT / 'logs' / 'unknown_events.csv'
RULE_FILE = ROOT / 'rules' / 'clinical_events.json'

# load known events
known = set()
with RULE_FILE.open('r', encoding='utf-8') as f:
    data = json.load(f)
    for sev, cats in data.items():
        if isinstance(cats, dict):
            for cat, events in cats.items():
                if isinstance(events, list):
                    for e in events:
                        known.add(e.lower().strip())

normalizer = EventNormalizer()

resolved = 0
total = 0
unresolved_counter = Counter()
resolved_counter = Counter()

with UNKNOWN_CSV.open('r', encoding='utf-8-sig') as f:
    reader = csv.DictReader(f)
    for row in reader:
        total += 1
        raw = (row.get('event') or '').strip()
        desc = (row.get('description') or '').strip()
        if not raw:
            # try to find mapping from description using synonyms/known events
            found = False
            text = desc.lower()
            for k in sorted(normalizer.synonyms.keys(), key=len, reverse=True):
                if k and k in text:
                    newcanon = normalizer.normalize(k)
                    if newcanon in known:
                        resolved += 1
                        resolved_counter[newcanon] += 1
                        found = True
                        break
            if found:
                continue
            # try known events directly
            for ev in sorted(normalizer.known_events, key=len, reverse=True):
                if ev and ev in text:
                    resolved += 1
                    resolved_counter[ev] += 1
                    found = True
                    break
            if not found:
                unresolved_counter['<empty_raw>'] += 1
            continue
        newcanon = normalizer.normalize(raw)
        if newcanon in known:
            resolved += 1
            resolved_counter[newcanon] += 1
        else:
            unresolved_counter[newcanon] += 1

print(f'Total unknown rows: {total}')
print(f'Would be resolved by new synonyms: {resolved} ({resolved/total*100:.2f}%)')
print('\nTop 20 newly-resolved events:')
for e,cnt in resolved_counter.most_common(20):
    print(f'  {e:40} {cnt:6}')

print('\nTop 20 remaining unmapped canonical events after normalization:')
for e,cnt in unresolved_counter.most_common(20):
    print(f'  {e:40} {cnt:6}')
