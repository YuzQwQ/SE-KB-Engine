import os
import json
import re
from pathlib import Path

DATA_DIR = Path(os.path.join(os.path.dirname(__file__), '..', 'data', 'universal_knowledge'))
TARGET_FILE = DATA_DIR / 'cnblogs_awei040519_18619550.kb.json'
OUTPUT_SUFFIX = '.titled.kb.json'


def refine_concept_name(name: str) -> str:
    if not name:
        return ''
    n = name.strip()
    n = re.sub(r'^(?:第\s*\d+[章节条]\s*|[一二三四五六七八九十百千]+[、.、]\s*|[一二三四五六七八九十百千]+\s+|\d+[、.、]\s*|\d+\s+)', '', n)
    for suf in ['的定义', '的区别', '的目标', '的原则', '的过程', '简介', '概述', '总结', '说明', '介绍']:
        n = re.sub(suf + r'$', '', n)
    n = re.sub(r'的$', '', n) if len(n) > 2 else n
    n = re.sub(r'\s+', ' ', n)
    return n[:20] if len(n) > 20 else n


def is_valid_concept_name(name: str) -> bool:
    if not name or len(name.strip()) < 2:
        return False
    name = name.strip()
    invalid_patterns = [
        r'^\d+[、.]', r'^\d+\s', r'^[一二三四五六七八九十百千]+[、.]', r'^[一二三四五六七八九十百千]+\s',
        r'http[s]?://', r'www\.', r'^[第\s]*\d+[章节步骤]', r'^\s*[（(].*[）)]\s*$', r'^\s*["] .* ["]\s*$',
    ]
    for pattern in invalid_patterns:
        if re.search(pattern, name):
            return False
    special_char_count = sum(1 for c in name if c in '{}[]"\':,;()（）【】')
    if len(name) > 0 and special_char_count / len(name) > 0.3:
        return False
    return len(name) <= 50


def summarize_title_from_definition(definition: str) -> str:
    text = (definition or '').strip()
    if not text:
        return ''
    text = re.sub(r'^(关于|本文|这篇|介绍|总结|概述|定义|说明|什么是)\s*', '', text)
    connectors = ['是指', '是', '为', '指', '表示', '属于', '包括', '包含', '主要', '一般']
    pos_candidates = [text.find(c) for c in connectors if c in text]
    pos = min(pos_candidates) if pos_candidates else -1
    if pos != -1 and pos > 0:
        candidate = text[:pos]
    else:
        if '：' in text:
            candidate = text.split('：', 1)[0]
        elif ':' in text:
            candidate = text.split(':', 1)[0]
        else:
            candidate = re.split(r'[，。,、；;！!？?]', text)[0]
    candidate = refine_concept_name(candidate)
    if not is_valid_concept_name(candidate):
        candidate = re.sub(r'\s+', ' ', re.split(r'[，。,、；;！!？?]', text)[0]).strip()
        candidate = refine_concept_name(candidate)
    return candidate[:18] if candidate and len(candidate) > 18 else candidate


def auto_title(name: str, definition: str) -> str:
    n = (name or '').strip()
    d = (definition or '').strip()
    if not d:
        return n
    looks_listy = bool(re.search(r'[，、；;]', n))
    too_long = len(n) > 16
    weak_signals = ['包括','包含','一般','主要','可以','需要','用于','通过','以及','比如']
    if too_long or looks_listy or any(s in n for s in weak_signals):
        summarized = summarize_title_from_definition(d)
        if summarized and is_valid_concept_name(summarized):
            return summarized
    return n


def process_file(path: Path) -> Path:
    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    concepts = data.get('generation_knowledge', {}).get('concepts', [])
    before_after = []
    for c in concepts:
        old = c.get('name', '')
        definition = c.get('definition', '')
        new = summarize_title_from_definition(definition) or auto_title(old, definition)
        if new and is_valid_concept_name(new):
            c['name'] = new
        before_after.append((old, c.get('name', old)))
    out_path = path.with_name(path.stem + OUTPUT_SUFFIX)
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f'Processed: {path.name} -> {out_path.name}')
    print('Preview of name changes (first 10):')
    for i, (old, new) in enumerate(before_after[:10], start=1):
        print(f'  {i:02d}. "{old}" => "{new}"')
    return out_path


def main():
    if not TARGET_FILE.exists():
        print(f'Target file not found: {TARGET_FILE}')
        return
    process_file(TARGET_FILE)


if __name__ == '__main__':
    main()