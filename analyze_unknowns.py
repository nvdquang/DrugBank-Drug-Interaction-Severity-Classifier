import csv
import json
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent
UNKNOWN_CSV = ROOT / 'logs' / 'unknown_events.csv'
RULE_FILE = ROOT / 'rules' / 'clinical_events.json'
OUT_CSV = ROOT / 'logs' / 'top_unmapped.csv'

# Load known canonical events from rules
known_events = set()
with RULE_FILE.open('r', encoding='utf-8') as f:
    data = json.load(f)
    for severity, cats in data.items():
        if isinstance(cats, dict):
            for cat, events in cats.items():
                if isinstance(events, list):
                    for e in events:
                        known_events.add(e.lower().strip())

# Read unknowns
canon_counter = Counter()
raw_counter = Counter()
pattern_counter = Counter()
desc_samples = defaultdict(list)
empty_canon = 0
row_count = 0

with UNKNOWN_CSV.open('r', encoding='utf-8-sig') as f:
    reader = csv.DictReader(f)
    for row in reader:
        row_count += 1
        canon = (row.get('canonical_event') or '').strip().lower()
        raw = (row.get('event') or '').strip().lower()
        pattern = (row.get('pattern') or '').strip().lower()
        desc = (row.get('description') or '').strip()

        if not canon:
            empty_canon += 1
        else:
            canon_counter[canon] += 1

        raw_counter[raw] += 1
        pattern_counter[pattern] += 1

        # store sample descriptions for top canonical_event
        if len(desc_samples[canon]) < 5:
            desc_samples[canon].append(desc)

# Find unmapped canonical events (present in unknowns but not in known_events)
unmapped = [(c, cnt) for c, cnt in canon_counter.most_common() if c not in known_events]

# Write top unmapped to CSV
with OUT_CSV.open('w', encoding='utf-8-sig', newline='') as f:
    writer = csv.writer(f)
    writer.writerow(['canonical_event', 'count', 'sample_description_1', 'sample_description_2'])
    for c, cnt in unmapped[:200]:
        samples = desc_samples.get(c, [])
        writer.writerow([c, cnt, samples[0] if len(samples) > 0 else '', samples[1] if len(samples) > 1 else ''])

# Print summary
print(f'Total unknown rows: {row_count}')
print(f'Empty canonical_event count: {empty_canon}')
print('\nTop 20 canonical_event values (overall, including mapped ones):')
for c, cnt in canon_counter.most_common(20):
    mapped = 'YES' if c in known_events else 'NO'
    print(f'  {c:40} {cnt:6}  mapped: {mapped}')

print('\nTop 20 unmapped canonical_event values:')
for c, cnt in unmapped[:20]:
    print(f'  {c:40} {cnt:6}')

print('\nTop 20 raw extracted event strings:')
for r, cnt in raw_counter.most_common(20):
    print(f'  {r:40} {cnt:6}')

print('\nPattern counts:')
for p, cnt in pattern_counter.most_common():
    print(f'  {p:30} {cnt:6}')

print(f'\nTop unmapped rows exported to: {OUT_CSV}')
