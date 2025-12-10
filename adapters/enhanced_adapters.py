"""
Enhanced Adapters - 使用 LLM Preselector 的增强版候选过滤器
替代原有的 dfd_adapter, concepts_adapter, rules_adapter
"""

from typing import Tuple, Dict, Any, List
from pathlib import Path
import json

from .llm_preselector import get_preselector, preselect_candidates


class EnhancedDFDAdapter:
    """
    增强版 DFD Adapter
    使用 LLM Preselector 提取完整的 DFD 相关段落，而不是只取标题
    """
    
    def __init__(self):
        self.preselector = get_preselector()
        self._load_semantic_cues()
    
    def _load_semantic_cues(self):
        """加载语义线索用于补充评分"""
        try:
            cues_path = Path("se_kb/mappings/semantic_cues.json")
            self.cues = json.loads(cues_path.read_text(encoding="utf-8"))
        except Exception:
            self.cues = {
                "process": ["处理", "校验", "计算", "生成", "更新", "解析"],
                "data_flow": ["请求", "响应", "消息", "数据", "参数", "结果"],
                "data_store": ["记录", "表", "档案", "数据库", "清单", "库存"],
                "external_entity": ["用户", "管理员", "第三方系统", "客户端", "供应商"]
            }
    
    def _calculate_dfd_signal_score(self, text: str) -> Dict[str, Any]:
        """计算 DFD 信号得分（补充 LLM 评估）"""
        signals = {
            "process": sum(text.count(k) for k in self.cues.get("process", [])),
            "data_flow": sum(text.count(k) for k in self.cues.get("data_flow", [])),
            "data_store": sum(text.count(k) for k in self.cues.get("data_store", [])),
            "external_entity": sum(text.count(k) for k in self.cues.get("external_entity", [])),
        }
        # DFD 特有关键词加权
        dfd_keywords = ["数据流图", "DFD", "Data Flow", "顶层图", "0层", "1层", 
                        "外部实体", "数据存储", "加工", "处理过程"]
        signals["dfd_keywords"] = sum(text.count(k) for k in dfd_keywords)
        
        return signals
    
    def build_candidates(self, text: str, ctx: Dict[str, Any]) -> Tuple[List[Dict[str, Any]], Dict[str, Any], Dict[str, Any], float]:
        """
        构建候选片段
        
        Args:
            text: 原始文本（为兼容性保留，实际使用 ctx 中的完整数据）
            ctx: 上下文，应包含完整的 parsed_data
        
        Returns:
            (candidates, trace, metrics, score)
        """
        # 构建完整的 parsed_data
        parsed_data = ctx.get('_parsed_data', {})
        if not parsed_data:
            # 兼容旧调用方式
            parsed_data = {
                'clean_text': text,
                'title': ctx.get('title', ''),
                'source_url': ctx.get('url', ''),
            }
        
        # 使用 LLM Preselector
        candidates, trace, base_score = preselect_candidates(parsed_data, 'dfd')
        
        # 补充信号评分
        all_text = " ".join(c.get('text', '') for c in candidates)
        signals = self._calculate_dfd_signal_score(all_text)
        
        # 综合评分
        signal_score = min(1.0, (
            signals["process"] * 0.3 +
            signals["data_flow"] * 0.25 +
            signals["data_store"] * 0.2 +
            signals["external_entity"] * 0.1 +
            signals["dfd_keywords"] * 0.5
        ) / 10.0)
        
        final_score = max(base_score, signal_score)
        
        # 如果有 DFD 强信号，提升得分
        if signals["dfd_keywords"] >= 3:
            final_score = max(final_score, 0.7)
        
        trace["signals"] = signals
        trace["base_score"] = base_score
        trace["signal_score"] = signal_score
        
        metrics = {
            "dfd_candidates": len([c for c in candidates if c.get('type') == 'dfd']),
            "unknown_candidates": len([c for c in candidates if c.get('type') == 'unknown']),
            "total_candidates": len(candidates),
            "signal_sum": sum(signals.values()),
        }
        
        return candidates, trace, metrics, final_score


class EnhancedConceptsAdapter:
    """
    增强版 Concepts Adapter
    使用 LLM Preselector 提取概念定义相关段落
    """
    
    def build_candidates(self, text: str, ctx: Dict[str, Any]) -> Tuple[List[Dict[str, Any]], Dict[str, Any], Dict[str, Any], float]:
        """构建概念候选片段"""
        parsed_data = ctx.get('_parsed_data', {})
        if not parsed_data:
            parsed_data = {
                'clean_text': text,
                'title': ctx.get('title', ''),
                'source_url': ctx.get('url', ''),
            }
        
        candidates, trace, base_score = preselect_candidates(parsed_data, 'concepts')
        
        # 计算概念相关度
        concept_keywords = ["概念", "定义", "是指", "表示", "即", "所谓", "术语", "含义"]
        all_text = " ".join(c.get('text', '') for c in candidates)
        keyword_hits = sum(all_text.count(k) for k in concept_keywords)
        
        # 调整得分
        keyword_score = min(1.0, keyword_hits / 8.0)
        final_score = max(base_score, keyword_score * 0.8)
        
        trace["keyword_hits"] = keyword_hits
        
        metrics = {
            "concept_candidates": len([c for c in candidates if c.get('type') == 'concept']),
            "total_candidates": len(candidates),
        }
        
        return candidates, trace, metrics, final_score


class EnhancedRulesAdapter:
    """
    增强版 Rules Adapter
    使用 LLM Preselector 提取规则约束相关段落
    """
    
    def build_candidates(self, text: str, ctx: Dict[str, Any]) -> Tuple[List[Dict[str, Any]], Dict[str, Any], Dict[str, Any], float]:
        """构建规则候选片段"""
        parsed_data = ctx.get('_parsed_data', {})
        if not parsed_data:
            parsed_data = {
                'clean_text': text,
                'title': ctx.get('title', ''),
                'source_url': ctx.get('url', ''),
            }
        
        candidates, trace, base_score = preselect_candidates(parsed_data, 'rules')
        
        # 计算规则相关度
        rule_keywords = ["规则", "必须", "应当", "不得", "如果", "则", "要求", 
                         "约束", "限制", "规范", "注意", "警告"]
        all_text = " ".join(c.get('text', '') for c in candidates)
        keyword_hits = sum(all_text.count(k) for k in rule_keywords)
        
        # 调整得分
        keyword_score = min(1.0, keyword_hits / 10.0)
        final_score = max(base_score, keyword_score * 0.8)
        
        trace["keyword_hits"] = keyword_hits
        
        metrics = {
            "rule_candidates": len([c for c in candidates if c.get('type') == 'rule']),
            "total_candidates": len(candidates),
        }
        
        return candidates, trace, metrics, final_score


# 工厂函数
def get_enhanced_adapter(adapter_type: str):
    """
    获取增强版 adapter 实例
    
    Args:
        adapter_type: 'dfd', 'concepts', 或 'rules'
    
    Returns:
        对应的 adapter 实例
    """
    adapters = {
        'dfd': EnhancedDFDAdapter,
        'concepts': EnhancedConceptsAdapter,
        'rules': EnhancedRulesAdapter,
    }
    
    adapter_class = adapters.get(adapter_type)
    if adapter_class:
        return adapter_class()
    raise ValueError(f"Unknown adapter type: {adapter_type}")

