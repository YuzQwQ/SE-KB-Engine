#!/usr/bin/env python3
import json
import os
import sys
from datetime import datetime
from pathlib import Path

# Ensure project root is on sys.path when running from scripts/
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from utils.image_analyzer import analyze_images, build_vision_model


def load_parsed_json(path: str) -> dict:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Parsed JSON not found: {path}")
    with p.open('r', encoding='utf-8') as f:
        return json.load(f)


def save_results(parsed_path: str, results: list) -> str:
    src = Path(parsed_path)
    base = src.stem
    out_dir = src.parent
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    out_file = out_dir / f"{base}_vision_{ts}.json"
    with out_file.open('w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    return str(out_file)


def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/test_vision_from_parsed.py <parsed_json_path> [limit]", file=sys.stderr)
        sys.exit(1)

    parsed_json_path = sys.argv[1]
    limit = int(sys.argv[2]) if len(sys.argv) > 2 else 5

    data = load_parsed_json(parsed_json_path)
    base_url = data.get('source_url') or None
    images = data.get('images') or []

    # Preview provider configuration
    vm = build_vision_model(options=None)
    provider_info = {
        'provider': vm.__class__.__name__,
        'base_url': getattr(vm, 'base_url', None),
        'model': getattr(vm, 'model', None),
    }
    print(json.dumps({'provider': provider_info, 'images_in_json': len(images)}, ensure_ascii=False))

    # Prepare inputs for analysis (respect limit)
    inputs = []
    for img in images[:limit]:
        inputs.append({
            'alt': img.get('alt', ''),
            'title': img.get('caption', ''),
            'src': img.get('src', ''),
            'abs_url': img.get('src', ''),  # analyzer accepts either
        })

    results = analyze_images(inputs, base_url=base_url, options=None)

    # Attach source to each result for clarity
    enriched = []
    for i, r in enumerate(results):
        src_url = inputs[i].get('abs_url') or ''
        r2 = {
            'src': src_url,
            'alt': r.get('alt', ''),
            'title': r.get('title', ''),
            'ocr': r.get('ocr', []),
            'description': r.get('description', ''),
            'dfd': r.get('dfd'),
        }
        enriched.append(r2)

    saved_path = save_results(parsed_json_path, enriched)

    # Print summary
    summary = {
        'status': 'done',
        'parsed_json_path': parsed_json_path,
        'source_url': base_url,
        'analyzed_images': len(enriched),
        'output_file': saved_path,
        'note': 'Configure .env or config/vision_model.json for real model output.'
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()