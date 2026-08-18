import json
import re

with open('backend/app/services/fixtures/synthetic_decision_lenses.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

for p in data['profiles']:
    text = json.dumps(p)
    if '>=' in text or '\u2265' in text:
        print(f"FOUND in {p['id']}: {p['title']}")
        for i, line in enumerate(text.split('\n')):
            if '>=' in line or '\u2265' in line:
                print(f"  Line {i}: {line[:120]}")

# Also check for any non-ASCII chars
all_text = json.dumps(data)
non_ascii = set(c for c in all_text if ord(c) > 127)
print(f"\nNon-ASCII chars found: {sorted([hex(ord(c)) for c in non_ascii])}")
