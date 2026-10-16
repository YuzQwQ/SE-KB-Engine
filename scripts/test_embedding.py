#!/usr/bin/env python
"""
测试嵌入模型配置是否正确
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

from refiner.embedder import SemanticEmbedder


def main():
    print("=" * 50)
    print("嵌入模型测试")
    print("=" * 50)
    
    # 检查配置
    print("\n📋 配置检查:")
    base_url = os.getenv("EMBEDDING_BASE_URL", "")
    api_key = os.getenv("EMBEDDING_API_KEY", "")
    model_id = os.getenv("EMBEDDING_MODEL_ID", "")
    
    print(f"  EMBEDDING_BASE_URL: {base_url[:50] + '...' if len(base_url) > 50 else base_url or '❌ 未设置'}")
    print(f"  EMBEDDING_API_KEY: {'✅ 已设置 (' + api_key[:8] + '...)' if api_key else '❌ 未设置'}")
    print(f"  EMBEDDING_MODEL_ID: {model_id or '❌ 未设置'}")
    
    if not all([base_url, api_key, model_id]):
        print("\n❌ 配置不完整，请在 .env 文件中设置以上环境变量")
        return
    
    # 创建嵌入器
    embedder = SemanticEmbedder()
    
    if not embedder.is_available():
        print("\n❌ 嵌入服务不可用")
        return
    
    print("\n✅ 配置完整，开始测试...")
    
    # 测试文本
    texts = [
        "数据流图中的外部实体是指位于系统边界之外，与系统进行数据交互的人员、组织或其他系统",
        "外部实体是DFD图中表示系统外部参与者的元素，用矩形表示",
        "数据存储是系统中保存数据的地方，用开口矩形或平行线表示",
        "Python是一种解释型高级编程语言，广泛用于人工智能和数据科学领域"
    ]
    
    print("\n📝 测试文本:")
    for i, text in enumerate(texts):
        print(f"  [{i+1}] {text[:50]}...")
    
    # 获取嵌入向量
    print("\n🔄 获取嵌入向量...")
    embeddings = embedder.get_embeddings_batch(texts)
    
    for i, emb in enumerate(embeddings):
        if emb:
            print(f"  [{i+1}] 维度: {len(emb)}, 前3个值: {emb[:3]}")
        else:
            print(f"  [{i+1}] ❌ 获取失败")
    
    # 计算相似度
    print("\n📊 语义相似度矩阵:")
    print("      ", end="")
    for i in range(len(texts)):
        print(f"  [{i+1}]  ", end="")
    print()
    
    for i in range(len(texts)):
        print(f"  [{i+1}] ", end="")
        for j in range(len(texts)):
            if embeddings[i] and embeddings[j]:
                sim = embedder.cosine_similarity(embeddings[i], embeddings[j])
                print(f" {sim:.2f} ", end="")
            else:
                print("  -   ", end="")
        print()
    
    # 解读结果
    print("\n📖 解读:")
    if embeddings[0] and embeddings[1]:
        sim_01 = embedder.cosine_similarity(embeddings[0], embeddings[1])
        print(f"  文本1 vs 文本2 (都关于外部实体): {sim_01:.2f}")
        if sim_01 > 0.8:
            print("    → 高相似度，应识别为语义重复 ✅")
        else:
            print("    → 相似度较低，阈值建议调整")
    
    if embeddings[0] and embeddings[3]:
        sim_03 = embedder.cosine_similarity(embeddings[0], embeddings[3])
        print(f"  文本1 vs 文本4 (DFD vs Python): {sim_03:.2f}")
        if sim_03 < 0.5:
            print("    → 低相似度，不相关内容 ✅")
        else:
            print("    → 相似度偏高，可能存在问题")
    
    print("\n✅ 测试完成!")


if __name__ == "__main__":
    main()


