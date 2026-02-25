"""
Type Registry - 知识类型注册表
定义所有可抽取的知识类型，每种类型包含一句话描述、Schema 路径、专用提示词路径等
"""

import json
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass, field


@dataclass
class KnowledgeType:
    """知识类型定义"""
    type_id: str                      # 类型标识: dfd, concepts, rules...
    name: str                         # 显示名称
    brief: str                        # 一句话描述（用于 Routing）
    description: str                  # 详细描述
    schema_path: Optional[str]        # JSON Schema 路径
    prompt_path: Optional[str]        # 专用提示词路径
    examples: List[str] = field(default_factory=list)  # 示例关键词
    enabled: bool = True              # 是否启用
    min_confidence: float = 0.6       # 最低置信度阈值


# 默认知识类型定义（空，SE-KB 类型由 _load_se_kb_types 加载）
DEFAULT_KNOWLEDGE_TYPES: List[KnowledgeType] = []


class TypeRegistry:
    """知识类型注册表 - 严格对应 se_kb/ 目录结构"""
    
    def __init__(self):
        self._types: Dict[str, KnowledgeType] = {}
        self._load_se_kb_types()
    
    def _load_se_kb_types(self):
        """加载 SE-KB 类型定义"""
        try:
            from .se_kb_types import get_se_kb_types
            for kt in get_se_kb_types():
                self._types[kt.type_id] = kt
        except ImportError as e:
            print(f"[TypeRegistry] 无法加载 SE-KB 类型: {e}")
    
    def register(self, knowledge_type: KnowledgeType):
        """注册新类型"""
        self._types[knowledge_type.type_id] = knowledge_type
    
    def get(self, type_id: str) -> Optional[KnowledgeType]:
        """获取类型定义"""
        return self._types.get(type_id)
    
    def get_enabled(self) -> List[KnowledgeType]:
        """获取所有启用的类型"""
        return [kt for kt in self._types.values() if kt.enabled]
    
    def get_all(self) -> List[KnowledgeType]:
        """获取所有类型"""
        return list(self._types.values())
    
    def get_routing_briefs(self) -> Dict[str, str]:
        """获取用于 Routing 的类型简介"""
        return {kt.type_id: kt.brief for kt in self.get_enabled()}
    
    def get_routing_prompt_section(self) -> str:
        """生成用于 Routing 的类型描述文本"""
        lines = []
        for kt in self.get_enabled():
            lines.append(f"- **{kt.type_id}**: {kt.brief}")
            if kt.examples:
                lines.append(f"  关键词示例: {', '.join(kt.examples[:5])}")
        return "\n".join(lines)
    
    def load_from_file(self, path: str):
        """从 JSON 文件加载类型定义"""
        try:
            data = json.loads(Path(path).read_text(encoding='utf-8'))
            for item in data.get('types', []):
                kt = KnowledgeType(
                    type_id=item['type_id'],
                    name=item['name'],
                    brief=item['brief'],
                    description=item.get('description', ''),
                    schema_path=item.get('schema_path'),
                    prompt_path=item.get('prompt_path'),
                    examples=item.get('examples', []),
                    enabled=item.get('enabled', True),
                    min_confidence=item.get('min_confidence', 0.6),
                )
                self.register(kt)
        except Exception as e:
            print(f"[TypeRegistry] 加载类型定义失败: {e}")


# 单例
_registry_instance: Optional[TypeRegistry] = None


def get_type_registry() -> TypeRegistry:
    """获取类型注册表单例"""
    global _registry_instance
    if _registry_instance is None:
        _registry_instance = TypeRegistry()
    return _registry_instance
