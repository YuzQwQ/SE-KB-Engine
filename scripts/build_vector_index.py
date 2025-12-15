#!/usr/bin/env python
"""
构建向量索引

使用示例:
    # 构建完整索引
    python scripts/build_vector_index.py
    
    # 重置并重建索引
    python scripts/build_vector_index.py --reset
    
    # 查看当前索引状态
    python scripts/build_vector_index.py --stats
"""

import sys
import os
import argparse
import json
from pathlib import Path
from datetime import datetime

# 添加项目根目录
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 加载 .env
def load_env():
    env_path = project_root / '.env'
    if env_path.exists():
        for line in env_path.read_text(encoding='utf-8').splitlines():
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            if '=' in line:
                k, v = line.split('=', 1)
                k, v = k.strip(), v.strip()
                if k and v and os.getenv(k) is None:
                    os.environ[k] = v

load_env()

from vectorizer import VectorConfig
from vectorizer.indexer import KnowledgeIndexer


def colored(text: str, color: str) -> str:
    """终端颜色"""
    colors = {
        "green": "\033[92m",
        "yellow": "\033[93m",
        "red": "\033[91m",
        "blue": "\033[94m",
        "cyan": "\033[96m",
        "reset": "\033[0m"
    }
    return f"{colors.get(color, '')}{text}{colors['reset']}"


def print_banner():
    print(colored("""
╔═══════════════════════════════════════════════════════════════╗
║              SE-KB 向量索引构建工具                            ║
║                                                               ║
║  将 JSON 知识库转换为向量索引，支持语义检索                      ║
╚═══════════════════════════════════════════════════════════════╝
""", "cyan"))


def print_stats(stats: dict):
    """打印统计信息"""
    print(colored("\n📊 索引统计", "blue"))
    print("=" * 50)
    print(f"总文档数: {colored(str(stats['total_documents']), 'green')}")
    print("\n各 Collection:")
    for name, count in stats['collections'].items():
        bar = "█" * min(count // 5, 30)
        print(f"  {name:<20} {count:>5}  {colored(bar, 'cyan')}")


def main():
    parser = argparse.ArgumentParser(
        description="SE-KB 向量索引构建工具",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument(
        "--reset", "-r",
        action="store_true",
        help="重置并重建所有索引"
    )
    parser.add_argument(
        "--stats", "-s",
        action="store_true",
        help="仅显示当前索引统计"
    )
    parser.add_argument(
        "--quiet", "-q",
        action="store_true",
        help="安静模式"
    )
    
    args = parser.parse_args()
    
    if not args.quiet:
        print_banner()
    
    # 创建配置和索引器
    config = VectorConfig()
    
    log_fn = (lambda x: None) if args.quiet else print
    indexer = KnowledgeIndexer(config, log_callback=log_fn)
    
    if args.stats:
        # 仅显示统计
        stats = indexer.get_index_stats()
        print_stats(stats)
        return
    
    # 构建索引
    start_time = datetime.now()
    
    stats = indexer.build_full_index(reset=args.reset)
    
    # 打印最终统计
    if not args.quiet:
        print_stats(indexer.get_index_stats())
        
        duration = (datetime.now() - start_time).total_seconds()
        print(colored(f"\n✅ 索引构建完成! 耗时: {duration:.1f} 秒", "green"))
        
        if stats.errors:
            print(colored(f"\n⚠️ 有 {len(stats.errors)} 个错误:", "yellow"))
            for err in stats.errors[:5]:
                print(f"  - {err}")


if __name__ == "__main__":
    main()
