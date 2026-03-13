#!/usr/bin/env python
"""
手动网页爬取工具
允许用户输入 URL，爬取网页内容并保存到 data/manual 目录。
"""

import sys
import os
import argparse
from pathlib import Path
from urllib.parse import urlparse

# 添加项目根目录到路径
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# 加载环境变量
def load_env():
    env_path = PROJECT_ROOT / '.env'
    if env_path.exists():
        for line in env_path.read_text(encoding='utf-8').splitlines():
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            if '=' in line:
                k, v = line.split('=', 1)
                os.environ[k.strip()] = v.strip()

load_env()

from utils.webpage_crawler import WebpageCrawler

def colored(text: str, color: str) -> str:
    """终端颜色"""
    colors = {
        "green": "\033[92m",
        "yellow": "\033[93m",
        "red": "\033[91m",
        "blue": "\033[94m",
        "cyan": "\033[96m",
        "reset": "\033[0m",
        "bold": "\033[1m"
    }
    return f"{colors.get(color, '')}{text}{colors['reset']}"

def main():
    parser = argparse.ArgumentParser(description="手动网页爬取工具")
    parser.add_argument("url", nargs="?", help="要爬取的网页 URL")
    parser.add_argument("--output", "-o", default="data/manual", help="输出目录 (默认: data/manual)")
    
    args = parser.parse_args()
    
    print(colored("╔═══════════════════════════════════════════════════════════════╗", "cyan"))
    print(colored("║              SE-KB 手动网页爬取工具                            ║", "cyan"))
    print(colored("╚═══════════════════════════════════════════════════════════════╝", "cyan"))

    url = args.url
    if not url:
        try:
            url = input(colored("\n请输入要爬取的 URL: ", "green")).strip()
        except (KeyboardInterrupt, EOFError):
            print("\n再见!")
            return
            
    if not url:
        print(colored("URL 不能为空", "red"))
        return
        
    if not url.startswith("http"):
        url = "https://" + url
        
    print(f"\n{colored('Target:', 'blue')} {url}")
    print(f"{colored('Output:', 'blue')} {args.output}")
    print("-" * 60)
    
    crawler = WebpageCrawler(data_dir=args.output)
    
    try:
        print("正在爬取...")
        result = crawler.crawl_and_parse(url, save_data=True)
        
        if result.get("success"):
            print(colored("\n✅ 爬取成功!", "green"))
            
            parsed = result.get("parsed_data", {})
            title = parsed.get("title", "Unknown Title")
            word_count = parsed.get("word_count", 0)
            
            print(f"\n{colored('Title:', 'bold')} {title}")
            print(f"{colored('Words:', 'bold')} {word_count}")
            
            paths = result.get("file_paths", {})
            if paths.get("parsed_file"):
                print(f"{colored('Saved to:', 'bold')} {paths['parsed_file']}")
            
            # 显示简要内容预览
            content = parsed.get("clean_text", "")
            if content:
                preview = content[:200].replace("\n", " ") + "..."
                print(f"\n{colored('Preview:', 'bold')}\n{preview}")
        else:
            print(colored(f"\n❌ 爬取失败: {result.get('error')}", "red"))
            
    except Exception as e:
        print(colored(f"\n❌ 发生错误: {e}", "red"))
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
