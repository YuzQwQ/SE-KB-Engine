#!/usr/bin/env python
"""分析 DFD 案例复杂度"""

import json
from pathlib import Path

examples_dir = Path('se_kb/diagrams/dfd/examples')
results = []

for f in examples_dir.glob('*.json'):
    try:
        data = json.loads(f.read_text(encoding='utf-8'))
        dfd = data.get('dfd_elements', {})
        ee = len(dfd.get('external_entities', []))
        p = len(dfd.get('processes', []))
        ds = len(dfd.get('data_stores', []))
        df = len(dfd.get('data_flows', []))
        total = ee + p + ds + df
        name = data.get('case_name', f.stem)[:40]
        results.append({
            'total': total,
            'ee': ee,
            'p': p,
            'ds': ds,
            'df': df,
            'name': name,
            'file': f.name
        })
    except Exception as e:
        print(f"Error reading {f}: {e}")

# 按复杂度排序
results.sort(key=lambda x: x['total'])

print("DFD Examples Complexity Analysis")
print("=" * 100)
print(f"{'Case Name':<42} {'Total':>5} {'EE':>4} {'P':>4} {'DS':>4} {'DF':>4}  Suggestion")
print("-" * 100)

to_delete = []
to_keep = []

for r in results:
    total = r['total']
    if total < 15:
        suggest = "[DELETE] Too simple"
        to_delete.append(r['file'])
    elif total < 22:
        suggest = "[MAYBE]  Consider"
        to_delete.append(r['file'])  # 也加入删除列表
    else:
        suggest = "[KEEP]   Complex enough"
        to_keep.append(r['file'])
    
    print(f"{r['name']:<42} {total:>5} {r['ee']:>4} {r['p']:>4} {r['ds']:>4} {r['df']:>4}  {suggest}")

print("-" * 100)
print(f"Total: {len(results)} examples")
print(f"To keep: {len(to_keep)}")
print(f"To delete: {len(to_delete)}")

print("\n" + "=" * 50)
print("Files to DELETE:")
print("=" * 50)
for f in to_delete:
    print(f"  {f}")

