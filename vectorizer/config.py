"""
向量化配置
"""

import os
from pathlib import Path
from dataclasses import dataclass, field
from typing import Dict, List


@dataclass
class VectorConfig:
    """向量化配置"""
    
    # 路径配置
    kb_root: Path = field(default_factory=lambda: Path("se_kb"))
    vector_store_path: Path = field(default_factory=lambda: Path("se_kb/vector_store"))
    embedding_cache_path: Path = field(default_factory=lambda: Path("data/embedding_cache"))
    
    # 嵌入模型配置
    embedding_api_base: str = field(default_factory=lambda: os.getenv("EMBEDDING_BASE_URL", "https://api.siliconflow.cn/v1"))
    embedding_api_key: str = field(default_factory=lambda: os.getenv("EMBEDDING_API_KEY", ""))
    embedding_model_id: str = field(default_factory=lambda: os.getenv("EMBEDDING_MODEL_ID", "Qwen/Qwen3-Embedding-8B"))
    embedding_dimension: int = 4096
    
    # Collection 配置
    collections: Dict[str, Dict] = field(default_factory=lambda: {
        "se_kb_dfd_concepts": {
            "description": "DFD 概念定义（外部实体、处理、数据流、数据存储等）",
            "source_dirs": ["diagrams/dfd/concepts"],
            "chunk_type": "element"
        },
        "se_kb_dfd_examples": {
            "description": "DFD 完整案例及数据流模式",
            "source_dirs": ["diagrams/dfd/examples"],
            "chunk_type": "case"
        },
        "se_kb_dfd_rules": {
            "description": "DFD 建模规则和校验规则",
            "source_dirs": ["diagrams/dfd/rules", "diagrams/dfd/validation"],
            "chunk_type": "rule"
        },
        "se_kb_dfd_templates": {
            "description": "DFD 模板库",
            "source_dirs": ["diagrams/dfd/templates"],
            "chunk_type": "template"
        },
        "se_kb_dfd_levels": {
            "description": "DFD 层次分解原则",
            "source_dirs": ["diagrams/dfd/levels"],
            "chunk_type": "principle"
        },
        "se_kb_theory": {
            "description": "软件工程理论知识",
            "source_dirs": ["theory"],
            "chunk_type": "concept"
        },
        "se_kb_domain": {
            "description": "领域知识",
            "source_dirs": ["domain"],
            "chunk_type": "domain"
        }
    })
    
    # 检索配置
    default_top_k: int = 5
    similarity_threshold: float = 0.2
    
    def __post_init__(self):
        """确保路径存在"""
        self.vector_store_path.mkdir(parents=True, exist_ok=True)
        self.embedding_cache_path.mkdir(parents=True, exist_ok=True)


# 知识类型到 Collection 的映射
TYPE_TO_COLLECTION = {
    "diagrams.dfd.concepts": "se_kb_dfd_concepts",
    "diagrams.dfd.examples": "se_kb_dfd_examples",
    "diagrams.dfd.rules": "se_kb_dfd_rules",
    "diagrams.dfd.validation": "se_kb_dfd_rules",
    "diagrams.dfd.templates": "se_kb_dfd_templates",
    "diagrams.dfd.levels": "se_kb_dfd_levels",
    "theory": "se_kb_theory",
    "domain": "se_kb_domain",
    "mappings": "se_kb_theory",
    "schema": "se_kb_theory",
}

