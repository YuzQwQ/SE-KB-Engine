import json
import logging
import os
import concurrent.futures
from typing import List, Dict, Any
from dataclasses import dataclass
from pathlib import Path

from openai import OpenAI
from .retriever import KnowledgeRetriever, RetrievalResult, QueryIntent

logger = logging.getLogger(__name__)

@dataclass
class SubQuery:
    """子查询对象"""
    query: str
    intent: str
    weight: int = 5

@dataclass
class PlannerResult:
    """规划器返回的最终结果"""
    original_query: str
    sub_queries: List[SubQuery]
    merged_results: List[Dict[str, Any]]
    
class QueryPlanner:
    """
    查询规划器
    Step 1: 语义拆解 (Decomposition)
    Step 2: 并行检索 (Parallel Retrieval)
    Step 3: 结果合并 (Fusion & Reranking)
    """
    
    def __init__(self, retriever: KnowledgeRetriever):
        self.retriever = retriever
        # 初始化 OpenAI 客户端 (复用环境变量)
        self.client = OpenAI(
            api_key=os.getenv("OPENAI_API_KEY"),
            base_url=os.getenv("BASE_URL") or "https://api.siliconflow.cn/v1"
        )
        self.model = os.getenv("MODEL") or "Qwen/Qwen2.5-7B-Instruct"  # 默认使用轻量模型
        self.system_prompt = self._load_system_prompt()

    def _load_system_prompt(self) -> str:
        """加载拆解用的 Prompt"""
        try:
            # 尝试从 focused 配置加载
            config_path = Path("config/system_prompts_focused.json")
            if not config_path.exists():
                config_path = Path("config/system_prompts.json")
                
            if config_path.exists():
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    return config.get("prompts", {}).get("query_decomposition", {}).get("system_prompt", "")
        except Exception as e:
            logger.error(f"Failed to load system prompt: {e}")
        
        # Fallback prompt
        return """
        你是一个专业的搜索意图分析专家。你的任务是将用户输入的复杂需求描述，拆解为多个独立的、目标明确的“可检索问题”。
        请直接输出一个JSON对象，包含一个 `sub_queries` 数组，每个元素包含 `query` (字符串), `intent` (字符串), `weight` (整数1-10)。
        """

    def decompose(self, query: str) -> List[SubQuery]:
        """Step 1: 使用 LLM 拆解查询"""
        if not query or len(query.strip()) < 10:
            # 如果查询太短，直接返回原始查询
            return [SubQuery(query=query, intent="general", weight=10)]

        try:
            logger.info(f"Decomposing query: {query[:50]}...")
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": query}
                ],
                response_format={"type": "json_object"},
                temperature=0.3
            )
            
            content = response.choices[0].message.content
            if not content:
                raise ValueError("empty response")
            data = json.loads(content)
            
            sub_queries = []
            for item in data.get("sub_queries", []):
                sub_queries.append(SubQuery(
                    query=item.get("query"),
                    intent=item.get("intent", "general"),
                    weight=item.get("weight", 5)
                ))
            
            logger.info(f"Decomposed into {len(sub_queries)} sub-queries")
            return sub_queries
            
        except Exception as e:
            logger.error(f"Decomposition failed: {e}")
            # 降级策略：直接使用原始查询
            return [SubQuery(query=query, intent="general", weight=10)]

    def _execute_single_search(self, sub_query: SubQuery, top_k: int = 3) -> List[RetrievalResult]:
        """执行单个子查询"""
        # 将字符串 intent 转换为 Enum
        intent_enum = None
        try:
            # 简单的映射逻辑
            intent_map = {
                "concept": QueryIntent.CONCEPT,
                "rule": QueryIntent.RULE,
                "example": QueryIntent.EXAMPLE,
                "template": QueryIntent.TEMPLATE,
                "theory": QueryIntent.THEORY
            }
            # 模糊匹配
            for key, val in intent_map.items():
                if key in sub_query.intent.lower():
                    intent_enum = val
                    break
        except Exception:
            pass

        response = self.retriever.retrieve(sub_query.query, top_k, intent_enum)
        
        # 为结果添加来源信息
        for res in response.results:
            res.metadata["_origin_query"] = sub_query.query
            res.metadata["_origin_intent"] = sub_query.intent
            res.metadata["_origin_weight"] = sub_query.weight
            
        return response.results

    def search(self, query: str, top_k: int = 5) -> PlannerResult:
        """主入口：执行完整流程"""
        
        # 1. 拆解
        sub_queries = self.decompose(query)
        
        # 2. 并行检索
        all_results: List[RetrievalResult] = []
        
        # 如果只有一个子查询（未拆解或本身很简单），直接执行
        if len(sub_queries) == 1:
            all_results = self._execute_single_search(sub_queries[0], top_k)
        else:
            # 并行执行
            with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
                # 每个子查询只查 top_k=3，避免噪音太大
                futures = {executor.submit(self._execute_single_search, sq, 3): sq for sq in sub_queries}
                for future in concurrent.futures.as_completed(futures):
                    try:
                        results = future.result()
                        all_results.extend(results)
                    except Exception as e:
                        logger.error(f"Sub-query search failed: {e}")

        # 3. 结果合并与重排序 (RRF + Weight)
        merged = self._merge_and_rank(all_results, top_k)
        
        return PlannerResult(
            original_query=query,
            sub_queries=sub_queries,
            merged_results=merged
        )

    def _merge_and_rank(self, results: List[RetrievalResult], final_top_k: int) -> List[Dict[str, Any]]:
        """
        合并结果并使用加权 RRF 排序
        """
        # 简单的去重 + 分数累加
        # 这里的 id 是 chunk id
        
        seen = {}  # id -> {data, score, sources}
        
        for res in results:
            rid = res.id
            weight = res.metadata.get("_origin_weight", 5)
            origin_query = res.metadata.get("_origin_query", "")
            
            # 基础分数 (Cosine Similarity) * 权重因子
            # 注意：Cosine Score 0.7-0.9 之间，权重 1-10
            # 简单公式：final_score = base_score * (1 + weight/20)
            weighted_score = res.score * (1 + weight / 20.0)
            
            if rid not in seen:
                seen[rid] = {
                    "content": res.text,
                    "score": weighted_score,
                    "collection": res.collection,
                    "metadata": res.metadata,
                    "matched_queries": [origin_query],
                    "raw_score": res.score
                }
            else:
                # 如果已经存在，说明多个子查询都召回了它
                # 累加分数 (给予奖励)
                seen[rid]["score"] += weighted_score * 0.5  # 叠加奖励
                if origin_query not in seen[rid]["matched_queries"]:
                    seen[rid]["matched_queries"].append(origin_query)
                    
        # 转换为列表并排序
        final_list = []
        for rid, data in seen.items():
            final_list.append({
                "id": rid,
                "content": data["content"],
                "score": round(data["score"], 4),
                "source": data["metadata"].get("source"),
                "type": data["metadata"].get("type"),
                "collection": data["collection"],
                "matched_queries": data["matched_queries"], # 让前端知道是哪个子问题匹配到的
                "metadata": data["metadata"]
            })
            
        # 按分数降序
        final_list.sort(key=lambda x: x["score"], reverse=True)
        
        return final_list[:final_top_k]
