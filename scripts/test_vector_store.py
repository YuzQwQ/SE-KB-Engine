#!/usr/bin/env python
"""
测试向量库基础设施
"""

import sys
import os
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

from vectorizer import VectorConfig, VectorStore, KnowledgeChunker


def main():
    print("=" * 60)
    print("向量库基础设施测试")
    print("=" * 60)
    
    # 1. 测试配置
    print("\n[1] 测试配置...")
    config = VectorConfig()
    print(f"  KB Root: {config.kb_root}")
    print(f"  Vector Store Path: {config.vector_store_path}")
    print(f"  Embedding Model: {config.embedding_model_id}")
    print(f"  Collections: {list(config.collections.keys())}")
    
    # 2. 测试向量存储初始化
    print("\n[2] 初始化向量存储...")
    try:
        store = VectorStore(config)
        print("  ✅ VectorStore 初始化成功")
    except Exception as e:
        print(f"  ❌ VectorStore 初始化失败: {e}")
        return
    
    # 3. 测试 Collection 创建
    print("\n[3] 检查 Collections...")
    stats = store.get_stats()
    print(f"  总文档数: {stats['total_documents']}")
    for name, count in stats['collections'].items():
        print(f"  - {name}: {count} 文档")
    
    # 4. 测试分块器
    print("\n[4] 测试分块器...")
    chunker = KnowledgeChunker()
    
    # 找一个概念文件测试
    concepts_dir = config.kb_root / "diagrams" / "dfd" / "concepts"
    test_files = list(concepts_dir.glob("*.json"))[:1]
    
    if test_files:
        test_file = test_files[0]
        print(f"  测试文件: {test_file.name}")
        
        chunks = chunker.chunk_file(test_file, "concepts")
        print(f"  生成 {len(chunks)} 个块:")
        for chunk in chunks[:3]:
            print(f"    - ID: {chunk.id}")
            print(f"      Text: {chunk.text[:80]}...")
            print(f"      Metadata: {chunk.metadata}")
    else:
        print("  未找到测试文件")
    
    # 5. 测试添加和查询
    print("\n[5] 测试添加和查询...")
    
    # 添加测试文档
    test_docs = [
        "外部实体是数据流图中表示系统外部的数据源或数据终点",
        "处理过程是对数据进行变换、计算或逻辑操作的功能单元",
        "数据流表示数据在系统内从一个元素流向另一个元素的路径",
    ]
    test_metas = [
        {"element_id": "external_entity", "chunk_type": "test"},
        {"element_id": "process", "chunk_type": "test"},
        {"element_id": "data_flow", "chunk_type": "test"},
    ]
    test_ids = ["test_1", "test_2", "test_3"]
    
    success = store.add_documents(
        "se_kb_concepts",
        test_docs,
        test_metas,
        test_ids
    )
    
    if success:
        print("  ✅ 添加测试文档成功")
        
        # 测试查询
        print("\n  测试查询: '什么是外部实体？'")
        results = store.query("se_kb_concepts", "什么是外部实体？", n_results=3)
        
        if results.get("documents") and results["documents"][0]:
            print(f"  找到 {len(results['documents'][0])} 个结果:")
            for i, doc in enumerate(results["documents"][0]):
                distance = results["distances"][0][i] if results.get("distances") else 0
                print(f"    [{i+1}] 距离={distance:.4f}: {doc[:50]}...")
        else:
            print("  未找到结果")
    else:
        print("  ❌ 添加测试文档失败")
    
    # 6. 最终统计
    print("\n[6] 最终统计...")
    stats = store.get_stats()
    print(f"  总文档数: {stats['total_documents']}")
    
    print("\n" + "=" * 60)
    print("✅ 向量库基础设施测试完成!")
    print("=" * 60)


if __name__ == "__main__":
    main()

