"""
结构化去重模块
基于关键字段匹配识别重复内容
"""

from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field


@dataclass
class DeduplicationResult:
    """去重结果"""

    is_duplicate: bool
    similar_item: Optional[Dict] = None
    similarity_score: float = 0.0
    has_increment: bool = False
    new_fields: List[str] = field(default_factory=list)


# 各知识类型的关键字段定义
# 这些字段用于判断两个知识条目是否描述同一对象
DEDUP_KEY_FIELDS = {
    "diagrams.dfd.concepts": {
        "primary": ["elements[].id", "elements[].name"],
        "secondary": ["description"],
    },
    "diagrams.dfd.rules": {
        "primary": ["rules[].id", "rules[].name"],
        "secondary": ["description"],
    },
    "diagrams.dfd.examples": {
        "primary": ["scenarios[].name", "scenarios[].domain"],
        "secondary": ["case_name", "description"],
    },
    "diagrams.dfd.templates": {
        "primary": ["categories[].templates[].id", "categories[].templates[].name"],
        "secondary": ["categories[].name"],
    },
    "diagrams.dfd.validation": {
        "primary": ["validation_rules[].id", "validation_rules[].name"],
        "secondary": ["description"],
    },
    "diagrams.dfd.levels": {
        "primary": ["leveling_principles[].id", "decomposition_rules[].id"],
        "secondary": ["description"],
    },
    "theory": {
        "primary": ["concepts[].id", "concepts[].name", "principles[].id"],
        "secondary": ["description"],
    },
    "mappings": {
        "primary": ["semantic_cues.*", "linguistic_patterns[].pattern"],
        "secondary": [],
    },
    "schema": {
        "primary": ["title", "properties.*"],
        "secondary": [],
    },
    "domain": {
        "primary": ["domain_id", "concepts[].name"],
        "secondary": ["description"],
    },
    "examples": {
        "primary": ["example_id", "title"],
        "secondary": ["description"],
    },
    "rules": {
        "primary": ["rule_id", "rules[].id"],
        "secondary": ["description"],
    },
}


class StructuralDeduplicator:
    """结构化去重器"""

    def __init__(self, similarity_threshold: float = 0.6):
        """
        Args:
            similarity_threshold: 相似度阈值，超过此值认为是重复
        """
        self.similarity_threshold = similarity_threshold

    def extract_nested_values(self, data: Dict, path: str) -> List[Any]:
        """
        从嵌套结构中提取值

        支持的路径格式:
        - "field" - 直接字段
        - "field[].subfield" - 数组中的子字段
        - "field.*" - 对象的所有键
        """
        if not data or not path:
            return []

        parts = path.split(".")
        return self._extract_recursive(data, parts)

    def _extract_recursive(self, data: Any, parts: List[str]) -> List[Any]:
        """递归提取值"""
        if not parts:
            if isinstance(data, (str, int, float, bool)):
                return [data]
            elif isinstance(data, list):
                return data
            elif isinstance(data, dict):
                return list(data.values())
            return []

        current = parts[0]
        remaining = parts[1:]

        # 处理数组访问: field[]
        if current.endswith("[]"):
            field_name = current[:-2]
            if isinstance(data, dict) and field_name in data:
                arr = data[field_name]
                if isinstance(arr, list):
                    results = []
                    for item in arr:
                        results.extend(self._extract_recursive(item, remaining))
                    return results
            return []

        # 处理通配符: *
        if current == "*":
            if isinstance(data, dict):
                return list(data.keys())
            return []

        # 普通字段访问
        if isinstance(data, dict) and current in data:
            return self._extract_recursive(data[current], remaining)

        return []

    def calculate_field_overlap(self, item1: Dict, item2: Dict, type_id: str) -> float:
        """
        计算两个知识条目的字段重合度

        Returns:
            重合度分数 [0, 1]
        """
        key_config = DEDUP_KEY_FIELDS.get(type_id, {"primary": [], "secondary": []})

        # 提取主要字段的值
        primary_paths = key_config.get("primary", [])

        if not primary_paths:
            return 0.0

        total_matches = 0.0
        total_fields = 0

        for path in primary_paths:
            vals1 = set(str(v).lower() for v in self.extract_nested_values(item1, path) if v)
            vals2 = set(str(v).lower() for v in self.extract_nested_values(item2, path) if v)

            if vals1 or vals2:
                total_fields += 1
                if vals1 and vals2:
                    # 计算 Jaccard 相似度
                    intersection = len(vals1 & vals2)
                    union = len(vals1 | vals2)
                    if union > 0:
                        total_matches += intersection / union

        return total_matches / total_fields if total_fields > 0 else 0.0

    def find_increments(self, new_item: Dict, existing_item: Dict, type_id: str) -> Dict:
        """
        识别新条目相对于已有条目的增量

        Returns:
            {
                "has_increment": bool,
                "new_elements": [...],  # 新增的条目
                "enhanced_fields": [...],  # 有补充的字段
            }
        """
        key_config = DEDUP_KEY_FIELDS.get(type_id, {"primary": [], "secondary": []})
        primary_paths = key_config.get("primary", [])

        new_elements = []
        enhanced_fields = []

        for path in primary_paths:
            new_vals = set(str(v).lower() for v in self.extract_nested_values(new_item, path) if v)
            existing_vals = set(
                str(v).lower() for v in self.extract_nested_values(existing_item, path) if v
            )

            # 找出新增的值
            added = new_vals - existing_vals
            if added:
                new_elements.append({"path": path, "added_values": list(added)})

        # 检查次要字段是否有补充
        secondary_paths = key_config.get("secondary", [])
        for path in secondary_paths:
            new_val = self.extract_nested_values(new_item, path)
            existing_val = self.extract_nested_values(existing_item, path)

            # 如果新内容更长，可能是补充
            new_len = sum(len(str(v)) for v in new_val)
            existing_len = sum(len(str(v)) for v in existing_val)

            if new_len > existing_len * 1.2:  # 新内容长度超过已有内容20%
                enhanced_fields.append(
                    {"path": path, "increase_ratio": new_len / max(existing_len, 1)}
                )

        return {
            "has_increment": bool(new_elements or enhanced_fields),
            "new_elements": new_elements,
            "enhanced_fields": enhanced_fields,
        }

    def check_duplicate(
        self, new_item: Dict, existing_items: List[Dict], type_id: str
    ) -> DeduplicationResult:
        """
        检查新条目是否与已有条目重复

        Args:
            new_item: 新的知识条目
            existing_items: 已有的知识条目列表
            type_id: 知识类型 ID

        Returns:
            DeduplicationResult
        """
        if not existing_items:
            return DeduplicationResult(is_duplicate=False)

        best_match = None
        best_score = 0.0

        for existing in existing_items:
            score = self.calculate_field_overlap(new_item, existing, type_id)
            if score > best_score:
                best_score = score
                best_match = existing

        is_duplicate = best_score >= self.similarity_threshold

        if is_duplicate and best_match:
            increment_info = self.find_increments(new_item, best_match, type_id)
            return DeduplicationResult(
                is_duplicate=True,
                similar_item=best_match,
                similarity_score=best_score,
                has_increment=increment_info["has_increment"],
                new_fields=increment_info.get("new_elements", []),
            )

        return DeduplicationResult(is_duplicate=False, similarity_score=best_score)


def test_deduplicator():
    """简单测试"""
    dedup = StructuralDeduplicator()

    item1 = {
        "content_slug": "elements_basics",
        "elements": [
            {"id": "external_entity", "name": "外部实体", "definition": "..."},
            {"id": "process", "name": "处理过程", "definition": "..."},
        ],
    }

    item2 = {
        "content_slug": "elements_full",
        "elements": [
            {"id": "external_entity", "name": "外部实体", "definition": "更详细的定义..."},
            {"id": "process", "name": "处理过程", "definition": "..."},
            {"id": "data_flow", "name": "数据流", "definition": "..."},  # 新增
        ],
    }

    result = dedup.check_duplicate(item2, [item1], "diagrams.dfd.concepts")
    print(f"Is duplicate: {result.is_duplicate}")
    print(f"Similarity: {result.similarity_score:.2f}")
    print(f"Has increment: {result.has_increment}")
    print(f"New fields: {result.new_fields}")


if __name__ == "__main__":
    test_deduplicator()
