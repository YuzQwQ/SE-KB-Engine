#!/usr/bin/env python
"""
知识去重与精炼命令行工具

使用示例:
    # 预览今天的 artifacts
    python scripts/refine_knowledge.py --date 2025/12/11 --preview

    # 精炼指定日期的 artifacts
    python scripts/refine_knowledge.py --date 2025/12/11

    # 精炼指定时间段的 artifacts
    python scripts/refine_knowledge.py --date 2025/12/11 --time 14_30

    # 试运行（不保存）
    python scripts/refine_knowledge.py --date 2025/12/11 --dry-run

    # 精炼所有 artifacts
    python scripts/refine_knowledge.py --all
"""

import sys
import json
import argparse
from pathlib import Path

# 添加项目根目录到 path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from refiner import KnowledgeRefiner


def colored(text: str, color: str) -> str:
    """简单的终端颜色支持"""
    colors = {
        "green": "\033[92m",
        "yellow": "\033[93m",
        "red": "\033[91m",
        "blue": "\033[94m",
        "cyan": "\033[96m",
        "reset": "\033[0m",
    }
    return f"{colors.get(color, '')}{text}{colors['reset']}"


def print_banner():
    """打印横幅"""
    print(
        colored(
            """
╔═══════════════════════════════════════════════════════════════╗
║           知识去重与精炼工具 (Knowledge Refiner)                ║
║                                                               ║
║  功能: 扫描 artifacts → 检测重复 → 智能融合 → 输出到知识库       ║
╚═══════════════════════════════════════════════════════════════╝
""",
            "cyan",
        )
    )


def print_preview(preview: dict):
    """打印预览信息"""
    print(colored("\n📊 预览结果", "blue"))
    print("=" * 50)

    print(f"\n总 artifact 数: {colored(str(preview['total_artifacts']), 'green')}")

    print(colored("\n📁 按类型分布:", "blue"))
    for type_id, info in preview.get("by_type", {}).items():
        artifact_count = info.get("artifact_count", 0)
        existing_count = info.get("existing_count", 0)
        print(f"  • {type_id}")
        print(f"      待处理: {artifact_count}, 已有: {existing_count}")

    duplicates = preview.get("potential_duplicates", {})
    if duplicates:
        print(colored("\n⚠️  潜在重复:", "yellow"))
        for type_id, items in duplicates.items():
            print(f"  [{type_id}]")
            for item in items:
                status = "📝 有增量" if item["has_increment"] else "🔄 纯重复"
                print(f"    • {item['file']}")
                print(f"      相似度: {item['similarity']:.2f}, {status}")
    else:
        print(colored("\n✅ 未发现明显重复", "green"))


def print_stats(stats: dict):
    """打印统计信息"""
    print(colored("\n📈 精炼统计", "blue"))
    print("=" * 50)

    print(f"\n总 artifact 数: {stats['total_artifacts']}")
    print(f"发现重复: {colored(str(stats['duplicates_found']), 'yellow')}")
    print(f"执行融合: {colored(str(stats['merged_count']), 'green')}")
    print(f"纯重复跳过: {stats['skipped_count']}")
    print(f"新增内容: {colored(str(stats['new_count']), 'cyan')}")

    if stats.get("errors"):
        print(colored(f"\n❌ 错误: {len(stats['errors'])}", "red"))
        for err in stats["errors"][:5]:  # 最多显示5个错误
            print(f"  • {err}")


def main():
    parser = argparse.ArgumentParser(
        description="知识去重与精炼工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python scripts/refine_knowledge.py --date 2025/12/11 --preview
  python scripts/refine_knowledge.py --date 2025/12/11
  python scripts/refine_knowledge.py --all --dry-run
        """,
    )

    parser.add_argument("--date", "-d", help="日期过滤，格式: YYYY/MM/DD 或 YYYY-MM-DD")
    parser.add_argument("--time", "-t", help="时间过滤，格式: HH_MM 或 HH:MM")
    parser.add_argument("--all", "-a", action="store_true", help="处理所有 artifacts（不过滤日期）")
    parser.add_argument("--preview", "-p", action="store_true", help="仅预览，不执行实际操作")
    parser.add_argument("--dry-run", action="store_true", help="试运行，执行分析但不保存结果")
    parser.add_argument("--threshold", type=float, default=0.6, help="去重相似度阈值，默认 0.6")
    parser.add_argument("--json", action="store_true", help="以 JSON 格式输出结果")
    parser.add_argument("--quiet", "-q", action="store_true", help="安静模式，只输出结果")

    args = parser.parse_args()

    # 检查参数
    if not args.all and not args.date:
        print(colored("错误: 请指定 --date 或 --all", "red"))
        parser.print_help()
        sys.exit(1)

    if not args.quiet:
        print_banner()

    # 日志回调
    log_func = (lambda x: None) if args.quiet or args.json else print

    # 创建精炼器
    refiner = KnowledgeRefiner(similarity_threshold=args.threshold, log_callback=log_func)

    date_filter = args.date if not args.all else None

    if args.preview:
        # 预览模式
        preview = refiner.preview(date_filter, args.time)

        if args.json:
            print(json.dumps(preview, ensure_ascii=False, indent=2))
        else:
            print_preview(preview)
    else:
        # 执行精炼
        stats = refiner.run(date_filter, args.time, args.dry_run)

        if args.json:
            print(json.dumps(stats.to_dict(), ensure_ascii=False, indent=2))
        elif not args.quiet:
            print_stats(stats.to_dict())

    print(colored("\n✅ 完成!", "green"))


if __name__ == "__main__":
    main()
