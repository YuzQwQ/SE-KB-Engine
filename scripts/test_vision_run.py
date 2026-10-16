#!/usr/bin/env python3
import json
import re
import sys
import os

# Ensure project root is on sys.path when running from scripts/
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from utils.webpage_crawler import WebpageCrawler


def main():
    url = sys.argv[1] if len(sys.argv) > 1 else 'https://en.wikipedia.org/wiki/Data-flow_diagram'
    crawler = WebpageCrawler()
    parsed = crawler.crawl_and_parse(url, save_data=True)

    images = parsed.get('images') or []
    sample = []
    for img in images[:3]:
        sample.append({
            'alt': img.get('alt', ''),
            'title': img.get('title', ''),
            'ocr': img.get('ocr', []),
            'description': img.get('description', ''),
            'dfd': img.get('dfd', None),
        })

    md = parsed.get('markdown_content') or ''
    has_img_links = bool(re.search(r"!\[.*?\]\(.*?\)", md))

    out = {
        'status': 'done',
        'url': url,
        'title': parsed.get('title'),
        'images_count': len(images),
        'images_sample': sample,
        'markdown_has_image_links': has_img_links,
        'parsed_file_path': parsed.get('parsed_file_path'),
    }
    print(json.dumps(out, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()