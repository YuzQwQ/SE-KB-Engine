"""
知识检索器
支持语义检索、元数据过滤、结果重排序
"""

from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum

from .config import VectorConfig, TYPE_TO_COLLECTION
from .store import VectorStore


class QueryIntent(Enum):
    """查询意图"""
    CONCEPT = "concept"        # 查询概念定义
    EXAMPLE = "example"        # 查询案例
    RULE = "rule"              # 查询规则
    TEMPLATE = "template"      # 查询模板
    THEORY = "theory"          # 查询理论
    GENERAL = "general"        # 通用查询


@dataclass
class RetrievalResult:
    """检索结果"""
    id: str
    text: str
    score: float                    # 相似度分数 (0-1, 越高越好)
    collection: str
    metadata: Dict[str, Any]
    
    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "text": self.text,
            "score": self.score,
            "collection": self.collection,
            "metadata": self.metadata
        }


@dataclass
class RetrievalResponse:
    """检索响应"""
    query: str
    intent: QueryIntent
    results: List[RetrievalResult]
    total_found: int
    
    def to_dict(self) -> Dict:
        return {
            "query": self.query,
            "intent": self.intent.value,
            "total_found": self.total_found,
            "results": [r.to_dict() for r in self.results]
        }


class KnowledgeRetriever:
    """知识检索器"""
    
    # 意图关键词映射
    INTENT_KEYWORDS = {
        QueryIntent.CONCEPT: [
            "什么是", "定义", "概念", "含义", "是什么", "what is", "define",
            "外部实体", "处理", "数据流", "数据存储", "元素"
        ],
        QueryIntent.EXAMPLE: [
            "案例", "示例", "例子", "example", "如何", "怎么做", "实现",
            "系统", "平台", "项目", "应用"
        ],
        QueryIntent.RULE: [
            "规则", "规范", "约束", "校验", "检查", "必须", "不能", "rule",
            "平衡", "一致性", "命名"
        ],
        QueryIntent.TEMPLATE: [
            "模板", "模式", "结构", "template", "pattern", "框架",
            "分解", "流程"
        ],
        QueryIntent.THEORY: [
            "理论", "原理", "方法", "思想", "theory", "原则",
            "结构化", "软件工程"
        ]
    }
    
    # Collection 到意图的映射
    INTENT_TO_COLLECTIONS = {
        QueryIntent.CONCEPT: ["se_kb_dfd_concepts"],
        QueryIntent.EXAMPLE: ["se_kb_dfd_examples"],
        QueryIntent.RULE: ["se_kb_dfd_rules", "se_kb_dfd_levels"],
        QueryIntent.TEMPLATE: ["se_kb_dfd_templates"],
        QueryIntent.THEORY: ["se_kb_theory", "se_kb_domain"],
        QueryIntent.GENERAL: None  # 搜索所有
    }
    
    def __init__(self, config: VectorConfig = None):
        self.config = config or VectorConfig()
        self.store = VectorStore(self.config)
    
    def _detect_intent(self, query: str) -> QueryIntent:
        """检测查询意图"""
        query_lower = query.lower()
        
        intent_scores = {intent: 0 for intent in QueryIntent}
        
        for intent, keywords in self.INTENT_KEYWORDS.items():
            for keyword in keywords:
                if keyword.lower() in query_lower:
                    intent_scores[intent] += 1
        
        # 找最高分
        max_intent = max(intent_scores, key=intent_scores.get)
        
        if intent_scores[max_intent] > 0:
            return max_intent
        else:
            return QueryIntent.GENERAL
    
    def _distance_to_score(self, distance: float) -> float:
        """将距离转换为相似度分数 (0-1)"""
        # ChromaDB 使用 L2 距离，距离越小越相似
        # 转换为 0-1 分数，1 表示完全相似
        return max(0, 1 - distance / 2)
    
    def retrieve(self, 
                 query: str,
                 top_k: int = 5,
                 intent: QueryIntent = None,
                 collections: List[str] = None,
                 metadata_filter: Dict = None,
                 min_score: float = None) -> RetrievalResponse:
        """
        检索知识
        
        Args:
            query: 查询文本
            top_k: 返回结果数量
            intent: 指定意图（如不指定则自动检测）
            collections: 指定搜索的 Collections
            metadata_filter: 元数据过滤条件
            min_score: 最小相似度阈值
            
        Returns:
            RetrievalResponse
        """
        # 使用配置的默认阈值
        if min_score is None:
            min_score = self.config.similarity_threshold

        # 检测意图
        detected_intent = intent or self._detect_intent(query)
        
        # 确定搜索范围
        if collections:
            target_collections = collections
        else:
            target_collections = self.INTENT_TO_COLLECTIONS.get(detected_intent)
            if target_collections is None:
                target_collections = list(self.store.collections.keys())
        
        # 执行检索
        all_results = []
        
        print(f"[Retrieval] Query: {query}, Intent: {detected_intent}, Collections: {target_collections}")

        for collection_name in target_collections:
            if collection_name not in self.store.collections:
                continue
            
            try:
                results = self.store.query(
                    collection_name,
                    query,
                    n_results=top_k * 2,  # 多取一些用于过滤
                    where=metadata_filter
                )
                
                if results.get("documents") and results["documents"][0]:
                    for i, doc in enumerate(results["documents"][0]):
                        distance = results["distances"][0][i] if results.get("distances") else 0
                        score = self._distance_to_score(distance)
                        
                        print(f"[Retrieval] Collection: {collection_name}, Distance: {distance:.4f}, Score: {score:.4f}, Min: {min_score}")

                        if score >= min_score:
                            all_results.append(RetrievalResult(
                                id=results["ids"][0][i] if results.get("ids") else f"{collection_name}_{i}",
                                text=doc,
                                score=score,
                                collection=collection_name,
                                metadata=results["metadatas"][0][i] if results.get("metadatas") else {}
                            ))
            except Exception as e:
                print(f"[Retrieval] Error querying {collection_name}: {e}")
        
        # 按分数排序
        all_results.sort(key=lambda x: x.score, reverse=True)
        
        # 取 top_k
        top_results = all_results[:top_k]
        
        return RetrievalResponse(
            query=query,
            intent=detected_intent,
            results=top_results,
            total_found=len(all_results)
        )
    
    def retrieve_concepts(self, query: str, top_k: int = 5) -> RetrievalResponse:
        """检索概念定义"""
        return self.retrieve(query, top_k, intent=QueryIntent.CONCEPT)
    
    def retrieve_examples(self, query: str, top_k: int = 5, 
                         complexity: str = None) -> RetrievalResponse:
        """
        检索案例
        
        Args:
            complexity: 复杂度过滤 (low/medium/high)
        """
        metadata_filter = {"complexity": complexity} if complexity else None
        return self.retrieve(query, top_k, intent=QueryIntent.EXAMPLE, 
                            metadata_filter=metadata_filter)
    
    def retrieve_rules(self, query: str, top_k: int = 5,
                      severity: str = None) -> RetrievalResponse:
        """
        检索规则
        
        Args:
            severity: 严重级别过滤 (error/warning/info)
        """
        metadata_filter = {"severity": severity} if severity else None
        return self.retrieve(query, top_k, intent=QueryIntent.RULE,
                            metadata_filter=metadata_filter)
    
    def retrieve_templates(self, query: str, top_k: int = 5,
                          dfd_level: int = None) -> RetrievalResponse:
        """
        检索模板
        
        Args:
            dfd_level: DFD 层级过滤 (0/1/2/3)
        """
        metadata_filter = {"dfd_level": dfd_level} if dfd_level is not None else None
        return self.retrieve(query, top_k, intent=QueryIntent.TEMPLATE,
                            metadata_filter=metadata_filter)
    
    def retrieve_for_dfd_generation(self, requirements: str, 
                                    top_k: int = 3) -> Dict[str, List[RetrievalResult]]:
        """
        为 DFD 生成检索相关知识
        
        返回多类型知识的组合
        """
        results = {}
        
        # 1. 检索相关案例（参考）
        example_response = self.retrieve_examples(requirements, top_k)
        results["examples"] = example_response.results
        
        # 2. 检索相关概念（确保正确理解）
        concept_queries = ["外部实体识别", "处理过程命名", "数据流规范"]
        concept_results = []
        for q in concept_queries:
            resp = self.retrieve_concepts(q, 2)
            concept_results.extend(resp.results)
        results["concepts"] = concept_results[:top_k]
        
        # 3. 检索相关规则（确保正确性）
        rule_response = self.retrieve_rules("DFD 规则", top_k)
        results["rules"] = rule_response.results
        
        # 4. 检索相关模板
        template_response = self.retrieve_templates(requirements, 2)
        results["templates"] = template_response.results
        
        return results
    
    def format_context(self, results: List[RetrievalResult], 
                       max_length: int = 4000) -> str:
        """
        将检索结果格式化为上下文文本
        
        适合直接插入 LLM prompt
        """
        if not results:
            return ""
        
        context_parts = []
        total_length = 0
        
        for i, result in enumerate(results):
            chunk = f"[{i+1}] {result.text}"
            
            if total_length + len(chunk) > max_length:
                break
            
            context_parts.append(chunk)
            total_length += len(chunk)
        
        return "\n\n".join(context_parts)
    
    def get_stats(self) -> Dict:
        """获取检索器统计"""
        return self.store.get_stats()

