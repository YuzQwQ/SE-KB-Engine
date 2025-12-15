#!/usr/bin/env python
"""
知识库查询工具

使用示例:
    # 通用查询
    python scripts/query_knowledge.py "什么是外部实体"
    
    # 指定类型查询
    python scripts/query_knowledge.py "医疗系统" --type example
    
    # 交互模式
    python scripts/query_knowledge.py --interactive
"""

import sys
import os
import argparse
import json
from pathlib import Path

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
from vectorizer.retriever import KnowledgeRetriever, QueryIntent


def colored(text: str, color: str) -> str:
    """终端颜色"""
    colors = {
        "green": "\033[92m",
        "yellow": "\033[93m",
        "red": "\033[91m",
        "blue": "\033[94m",
        "cyan": "\033[96m",
        "magenta": "\033[95m",
        "reset": "\033[0m",
        "bold": "\033[1m"
    }
    return f"{colors.get(color, '')}{text}{colors['reset']}"


def print_banner():
    print(colored("""
╔═══════════════════════════════════════════════════════════════╗
║              SE-KB 知识库语义检索工具                          ║
╚═══════════════════════════════════════════════════════════════╝
""", "cyan"))


def print_result(result, index: int):
    """打印单个结果"""
    score_color = "green" if result.score > 0.7 else ("yellow" if result.score > 0.5 else "red")
    
    print(f"\n{colored(f'[{index}]', 'bold')} {colored(f'Score: {result.score:.2f}', score_color)} | {colored(result.collection, 'magenta')}")
    
    # 打印元数据
    meta_items = []
    for key in ["element_id", "case_name", "rule_id", "template_id", "concept_name"]:
        if key in result.metadata and result.metadata[key]:
            meta_items.append(f"{key}={result.metadata[key]}")
    if meta_items:
        print(f"    {colored('Meta:', 'blue')} {', '.join(meta_items)}")
    
    # 打印文本（截断）
    text = result.text.replace('\n', ' ')
    if len(text) > 200:
        text = text[:200] + "..."
    print(f"    {text}")


def run_query(retriever: KnowledgeRetriever, query: str, 
              intent_type: str = None, top_k: int = 5):
    """执行查询"""
    # 解析意图类型
    intent = None
    if intent_type:
        intent_map = {
            "concept": QueryIntent.CONCEPT,
            "example": QueryIntent.EXAMPLE,
            "rule": QueryIntent.RULE,
            "template": QueryIntent.TEMPLATE,
            "theory": QueryIntent.THEORY
        }
        intent = intent_map.get(intent_type.lower())
    
    print(f"\n{colored('Query:', 'blue')} {query}")
    
    # 执行检索
    response = retriever.retrieve(query, top_k=top_k, intent=intent)
    
    print(f"{colored('Intent:', 'blue')} {response.intent.value}")
    print(f"{colored('Found:', 'blue')} {response.total_found} results")
    
    if not response.results:
        print(colored("\n  No results found.", "yellow"))
        return
    
    print(colored(f"\nTop {len(response.results)} Results:", "green"))
    print("-" * 60)
    
    for i, result in enumerate(response.results, 1):
        print_result(result, i)
    
    print("-" * 60)


def interactive_mode(retriever: KnowledgeRetriever):
    """交互模式"""
    print(colored("\n进入交互模式 (输入 'quit' 退出, 'help' 查看帮助)", "cyan"))
    
    while True:
        try:
            query = input(colored("\n🔍 Query> ", "green")).strip()
        except (KeyboardInterrupt, EOFError):
            print("\n再见!")
            break
        
        if not query:
            continue
        
        if query.lower() == 'quit':
            print("再见!")
            break
        
        if query.lower() == 'help':
            print("""
命令帮助:
  <query>           - 直接输入查询内容
  /concept <query>  - 搜索概念定义
  /example <query>  - 搜索案例
  /rule <query>     - 搜索规则
  /template <query> - 搜索模板
  /stats            - 显示索引统计
  quit              - 退出
""")
            continue
        
        if query.lower() == '/stats':
            stats = retriever.get_stats()
            print(f"\n索引统计: {stats['total_documents']} 文档")
            for name, count in stats['collections'].items():
                print(f"  - {name}: {count}")
            continue
        
        # 解析命令
        intent_type = None
        if query.startswith('/'):
            parts = query.split(' ', 1)
            cmd = parts[0][1:].lower()
            query = parts[1] if len(parts) > 1 else ""
            
            if cmd in ['concept', 'example', 'rule', 'template', 'theory']:
                intent_type = cmd
            else:
                print(f"未知命令: {cmd}")
                continue
        
        if query:
            run_query(retriever, query, intent_type)


def main():
    parser = argparse.ArgumentParser(
        description="SE-KB 知识库语义检索工具",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument(
        "query",
        nargs="?",
        help="查询内容"
    )
    parser.add_argument(
        "--type", "-t",
        choices=["concept", "example", "rule", "template", "theory"],
        help="指定查询类型"
    )
    parser.add_argument(
        "--top-k", "-k",
        type=int,
        default=5,
        help="返回结果数量 (默认: 5)"
    )
    parser.add_argument(
        "--interactive", "-i",
        action="store_true",
        help="交互模式"
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="JSON 格式输出"
    )
    parser.add_argument(
        "--stats",
        action="store_true",
        help="显示索引统计"
    )
    
    args = parser.parse_args()
    
    print_banner()
    
    # 创建检索器
    config = VectorConfig()
    retriever = KnowledgeRetriever(config)
    
    if args.stats:
        stats = retriever.get_stats()
        print(f"索引统计: {stats['total_documents']} 文档")
        for name, count in stats['collections'].items():
            print(f"  - {name}: {count}")
        return
    
    if args.interactive:
        interactive_mode(retriever)
        return
    
    if not args.query:
        parser.print_help()
        return
    
    if args.json:
        response = retriever.retrieve(args.query, top_k=args.top_k)
        print(json.dumps(response.to_dict(), ensure_ascii=False, indent=2))
    else:
        run_query(retriever, args.query, args.type, args.top_k)


if __name__ == "__main__":
    main()

