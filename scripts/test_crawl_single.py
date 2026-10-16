#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
单页爬取测试脚本
使用 utils.webpage_crawler.WebpageCrawler 抓取并解析指定网页，并启用图片文本化分析。

运行示例：
    python scripts/test_crawl_single.py "https://blog.csdn.net/..."
"""

import sys
import json
import os
from typing import Any, Dict
from pathlib import Path

# 确保可以导入项目根目录下的 utils 模块
ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

# 自动加载项目根目录下的 .env（用于视觉模型等）
try:
    from dotenv import load_dotenv
    env_file = ROOT_DIR / ".env"
    if env_file.exists():
        load_dotenv(dotenv_path=str(env_file))
except Exception:
    pass

from utils.webpage_crawler import WebpageCrawler


def summarize_result(result: Dict[str, Any]) -> str:
    success = result.get('success')
    raw_data = result.get('raw_data', {})
    parsed = result.get('parsed_data', {})
    metrics = result.get('metrics', {})
    files = result.get('file_paths', {})

    lines = []
    lines.append(f"success: {success}")
    lines.append(f"source: {raw_data.get('source')} status_code: {raw_data.get('status_code')}")

    # 解析字段
    title = parsed.get('title') or '(无标题)'
    author = parsed.get('author') or ''
    publish_time = parsed.get('publish_time') or ''
    tags = parsed.get('tags') or []
    word_count = parsed.get('word_count') or 0
    images = parsed.get('images') or []

    lines.append(f"title: {title}")
    if author:
        lines.append(f"author: {author}")
    if publish_time:
        lines.append(f"publish_time: {publish_time}")
    if tags:
        lines.append(f"tags: {', '.join(tags)}")
    lines.append(f"word_count: {word_count}")

    # 回退信息
    fallback_used = metrics.get('fallback_used', False)
    lines.append(f"fallback_used: {fallback_used}")

    # 图片文本化摘要
    if isinstance(images, list) and images:
        lines.append(f"images_textualized: {len(images)}")
        for i, img in enumerate(images[:3]):
            alt = img.get('alt') or ''
            desc = img.get('description') or ''
            ocr = img.get('ocr') or []
            dfd = img.get('dfd')
            lines.append(f"  [{i+1}] alt='{alt}' desc_len={len(desc)} ocr_len={len(ocr)} dfd={bool(dfd)}")
    else:
        lines.append("images_textualized: 0")

    # 保存文件路径
    raw_file = files.get('raw_file')
    parsed_file = files.get('parsed_file')
    if raw_file:
        lines.append(f"saved_raw: {raw_file}")
    if parsed_file:
        lines.append(f"saved_parsed: {parsed_file}")

    return "\n".join(lines)


def main(url: str):
    crawler = WebpageCrawler()

    # 确保图片文本化启用，使用 ENV 中的硅基流动配置
    image_analysis_options = {
        "provider": "siliconflow"
    }

    result = crawler.crawl_and_parse(
        url=url,
        save_data=True,
        image_analysis_options=image_analysis_options
    )

    print("=== Crawl Summary ===")
    print(summarize_result(result))
    print("\n=== Full JSON (truncated) ===")
    try:
        # 打印部分 JSON 方便快速查看
        snippet = {
            "raw_data": {
                "status_code": result.get('raw_data', {}).get('status_code'),
                "source": result.get('raw_data', {}).get('source')
            },
            "parsed_keys": list((result.get('parsed_data') or {}).keys())[:12],
            "metrics": result.get('metrics', {}),
            "file_paths": result.get('file_paths', {})
        }
        print(json.dumps(snippet, ensure_ascii=False, indent=2))
    except Exception:
        pass


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python scripts/test_crawl_single.py <URL>")
        sys.exit(1)
    test_url = sys.argv[1].strip()

    # 友好提醒：ENV 中 BASE_URL、OPENAI_API_KEY/VISUAL_MODEL_API_KEY、VISUAL_MODEL
    # 应该已在 .env 中配置，以启用图片文本化。
    base_url = os.getenv("BASE_URL", "")
    api_key = os.getenv("VISUAL_MODEL_API_KEY") or os.getenv("OPENAI_API_KEY") or os.getenv("SILICONFLOW_API_KEY")
    model = os.getenv("VISUAL_MODEL", "")
    print(f"Env visual provider ready: base_url={'set' if base_url else 'unset'}, api_key={'set' if api_key else 'unset'}, model={'set' if model else 'unset'}")

    main(test_url)