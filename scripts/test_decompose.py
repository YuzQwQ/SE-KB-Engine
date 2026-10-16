import sys
import os
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Load environment variables
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

from vectorizer import VectorConfig, KnowledgeRetriever, QueryPlanner

def test_decomposition():
    print("Initializing KnowledgeRetriever...")
    retriever = KnowledgeRetriever(VectorConfig())
    
    print("Initializing QueryPlanner...")
    planner = QueryPlanner(retriever)
    
    query = "企业考勤管理系统需求 包含员工打卡 请假 审批 统计"
    print(f"\nDecomposing query: {query}")
    
    try:
        sub_queries = planner.decompose(query)
        print(f"\nResult ({len(sub_queries)} sub-queries):")
        for i, sq in enumerate(sub_queries, 1):
            print(f"{i}. [{sq.intent}] {sq.query} (weight: {sq.weight})")
        print("\nSUCCESS ✅")
    except Exception as e:
        print(f"\nFAILED ❌: {e}")

if __name__ == "__main__":
    test_decomposition()
