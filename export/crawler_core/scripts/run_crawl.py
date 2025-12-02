#!/usr/bin/env python3
import argparse
import json
import os
import sys
from pathlib import Path

# Ensure parent directory (crawler_core) is on sys.path
sys.path.append(str(Path(__file__).resolve().parent.parent))

from utils.webpage_crawler_core import WebpageCrawlerCore


def build_image_options_from_env() -> dict:
    provider = os.getenv('VISUAL_MODEL_PROVIDER')
    if not provider:
        return {}
    provider = provider.lower()
    if provider == 'siliconflow':
        return {
            'provider': 'siliconflow',
            'base_url': os.getenv('VISUAL_MODEL_BASE_URL', 'https://api.siliconflow.cn/v1'),
            'api_key': os.getenv('VISUAL_MODEL_API_KEY', ''),
            'model': os.getenv('VISUAL_MODEL', ''),
            'timeout': int(os.getenv('VISUAL_MODEL_TIMEOUT', '60')),
        }
    if provider == 'http':
        return {
            'provider': 'http',
            'endpoint': os.getenv('VISUAL_MODEL_ENDPOINT', ''),
            'api_key': os.getenv('VISUAL_MODEL_API_KEY', ''),
            'timeout': int(os.getenv('VISUAL_MODEL_TIMEOUT', '30')),
            'request_schema': {
                'url_field': os.getenv('VISUAL_MODEL_REQ_URL_FIELD', 'image_url'),
                'base64_field': os.getenv('VISUAL_MODEL_REQ_B64_FIELD', 'image_base64'),
                'tasks_field': os.getenv('VISUAL_MODEL_REQ_TASKS_FIELD', 'tasks'),
            },
            'response_schema': {
                'ocr_field': os.getenv('VISUAL_MODEL_RESP_OCR_FIELD', 'ocr'),
                'description_field': os.getenv('VISUAL_MODEL_RESP_DESCRIPTION_FIELD', 'description'),
                'dfd_field': os.getenv('VISUAL_MODEL_RESP_DFD_FIELD', 'dfd'),
            },
            'default_tasks': ['ocr', 'description', 'dfd'],
        }
    return {}


def main():
    # Load .env from export/crawler_core if present
    env_path = Path(__file__).resolve().parent.parent / ".env"
    if env_path.exists():
        try:
            for line in env_path.read_text(encoding="utf-8").splitlines():
                s = line.strip()
                if not s or s.startswith('#'):
                    continue
                if '=' in s:
                    key, val = s.split('=', 1)
                    key = key.strip()
                    val = val.strip()
                    if key:
                        os.environ.setdefault(key, val)
        except Exception as e:
            print(f"[warn] 加载 .env 失败：{e}")
    parser = argparse.ArgumentParser(description='Run single-page crawl and save results')
    parser.add_argument('url', help='Target URL to crawl')
    parser.add_argument('--images', action='store_true', help='Enable image textualization (requires remote model)')
    args = parser.parse_args()

    crawler = WebpageCrawlerCore()
    image_opts = build_image_options_from_env() if args.images else None
    result = crawler.crawl_and_parse(args.url, save_data=True, image_analysis_options=image_opts)

    # Print summary
    raw = result.get('raw_data', {})
    parsed = result.get('parsed_data', {})
    print('=== Crawl Summary ===')
    print(f"Source: {raw.get('source')}  Status: {raw.get('status_code')}")
    print(f"Title: {parsed.get('title')}  Words: {parsed.get('word_count')}")
    if parsed.get('images'):
        print(f"Images: {len(parsed.get('images'))} (textualized: {'ocr' in parsed.get('images')[0]})")
    files = result.get('file_paths', {})
    print('Raw JSON:   ', files.get('raw_file'))
    print('Parsed JSON:', files.get('parsed_file'))

    # Show snippet of parsed JSON
    if parsed:
        print('\n=== Parsed JSON snippet ===')
        try:
            snippet = json.dumps(parsed, ensure_ascii=False, indent=2)
            # Truncate for console readability
            print(snippet[:1000] + ('...' if len(snippet) > 1000 else ''))
        except Exception:
            pass


if __name__ == '__main__':
    main()