"""
知识去重与精炼模块

三层去重策略：
1. 语义相似度检测（嵌入向量）- 快速筛选语义相近的内容
2. 结构化字段匹配 - 精确判断是否描述同一对象
3. 增量知识检测 - 判断是否有新增价值
"""

from .knowledge_refiner import KnowledgeRefiner, RefineStats
from .deduplicator import StructuralDeduplicator
from .embedder import SemanticEmbedder, SemanticDeduplicator
from .merger import LLMMerger

__all__ = [
    "KnowledgeRefiner",
    "RefineStats",
    "StructuralDeduplicator",
    "SemanticEmbedder",
    "SemanticDeduplicator",
    "LLMMerger",
]
