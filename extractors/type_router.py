"""
Type Router - 类型路由模块 (Stage 1)
使用轻量模型判断网页内容包含哪些知识类型
"""

import os
import json
import re
from typing import List, Dict, Any, Tuple, Optional
from dataclasses import dataclass

from .type_registry import get_type_registry
from utils.env_loader import load_env_file


@dataclass
class RoutingResult:
    """路由结果"""

    types: List[str]  # 识别出的类型列表
    confidences: Dict[str, float]  # 每个类型的置信度
    reasoning: str  # 推理说明
    tokens_used: int  # 消耗的 tokens


# Routing System Prompt - 精简版，只做类型判断
ROUTING_SYSTEM_PROMPT = """你是一个知识类型分类器。你的任务是判断给定的网页内容可能包含哪些类型的知识。

## 可识别的知识类型

{type_descriptions}

## 任务要求

1. 仔细阅读网页内容
2. 判断内容中**可能包含**哪些类型的知识（高召回率优先）
3. 为每种识别出的类型给出置信度（0.0-1.0）
4. 只输出 JSON，不要任何其他内容

## 输出格式

```json
{{
  "types": ["type_id1", "type_id2"],
  "confidences": {{"type_id1": 0.85, "type_id2": 0.72}},
  "reasoning": "简短说明为什么识别出这些类型（50字以内）"
}}
```

## 判断原则

- 宁可多选，不要漏选（高召回率）
- 如果不确定，也可以选入，但给较低置信度
- 如果完全不相关，可以返回空数组
- 只选择上面列出的类型，不要发明新类型
"""

ROUTING_USER_PROMPT = """请分析以下网页内容，判断它包含哪些类型的知识。

## 网页信息
- 标题: {title}
- URL: {url}

## 网页内容摘要
{content_summary}

---

请输出 JSON 格式的分类结果。"""


class TypeRouter:
    """类型路由器 - 判断内容包含哪些知识类型"""

    def __init__(self):
        load_env_file()
        self.base_url = os.getenv("FILTER_BASE_URL", "").rstrip("/")
        self.api_key = os.getenv("FILTER_API_KEY", "")
        self.model_id = os.getenv("FILTER_MODEL_ID", "Qwen/Qwen2.5-7B-Instruct")
        self.max_content_chars = 8000  # 内容摘要最大长度
        self.timeout = 45.0
        self.registry = get_type_registry()

    def _prepare_content_summary(self, parsed_data: Dict[str, Any]) -> str:
        """准备内容摘要（截取关键部分）"""
        # 优先使用 sections 的标题和摘要
        sections = parsed_data.get("sections") or parsed_data.get("structured_json") or []

        if sections:
            parts = []
            total_len = 0
            for sec in sections:
                heading = sec.get("heading", "")
                text = sec.get("text", "")[:500]  # 每个 section 最多 500 字符
                lists = sec.get("lists", [])[:5]  # 最多 5 个列表项

                if heading:
                    parts.append(f"## {heading}")
                if text:
                    parts.append(text[:300])
                if lists:
                    parts.append("- " + "\n- ".join(str(item)[:100] for item in lists[:3]))

                total_len += len(parts[-1]) if parts else 0
                if total_len > self.max_content_chars:
                    break

            content = "\n\n".join(parts)
        else:
            # 使用 clean_text
            content = parsed_data.get("clean_text") or parsed_data.get("markdown") or ""

        # 截断
        if len(content) > self.max_content_chars:
            content = content[: self.max_content_chars] + "\n\n[...内容已截断...]"

        return content

    def _build_system_prompt(self) -> str:
        """构建系统提示词"""
        type_descriptions = self.registry.get_routing_prompt_section()
        return ROUTING_SYSTEM_PROMPT.format(type_descriptions=type_descriptions)

    def _call_llm(self, system_prompt: str, user_prompt: str) -> Tuple[Optional[str], Dict]:
        """调用 LLM"""
        if not self.base_url or not self.api_key:
            return None, {"error": "missing_env", "need": ["FILTER_BASE_URL", "FILTER_API_KEY"]}

        try:
            import httpx

            url = f"{self.base_url}/chat/completions"
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            }
            body = {
                "model": self.model_id,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                "temperature": 0.1,
                "max_tokens": 512,  # 输出很短，只需要 JSON
            }

            with httpx.Client(timeout=self.timeout) as client:
                resp = client.post(url, headers=headers, json=body)
                resp.raise_for_status()
                data = resp.json()
                content = ((data.get("choices") or [{}])[0].get("message") or {}).get("content", "")
                tokens = data.get("usage", {}).get("total_tokens", 0)
                return content, {"tokens": tokens, "model": self.model_id}

        except Exception as e:
            return None, {"error": str(e)}

    def _parse_response(self, response: str) -> Dict[str, Any]:
        """解析 LLM 响应"""
        if not response:
            return {"types": [], "confidences": {}, "reasoning": ""}

        # 尝试直接解析
        try:
            result = json.loads(response)
            if isinstance(result, dict) and "types" in result:
                return result
        except json.JSONDecodeError:
            pass

        # 尝试提取 JSON 块
        patterns = [
            r"```json\s*([\s\S]*?)\s*```",
            r"```\s*([\s\S]*?)\s*```",
            r'\{[\s\S]*"types"[\s\S]*\}',
        ]

        for pattern in patterns:
            match = re.search(pattern, response)
            if match:
                try:
                    json_str = match.group(1) if "```" in pattern else match.group(0)
                    result = json.loads(json_str)
                    if isinstance(result, dict) and "types" in result:
                        return result
                except (json.JSONDecodeError, IndexError):
                    continue

        return {"types": [], "confidences": {}, "reasoning": "解析失败"}

    def route(self, parsed_data: Dict[str, Any]) -> Tuple[RoutingResult, Dict[str, Any]]:
        """
        路由：判断内容包含哪些知识类型

        Args:
            parsed_data: 包含 title, url, clean_text/sections 等的 parsed.json 数据

        Returns:
            (RoutingResult, trace): 路由结果和追踪信息
        """
        title = parsed_data.get("title", "未命名")
        url = parsed_data.get("source_url") or parsed_data.get("url", "")

        # 准备内容摘要
        content_summary = self._prepare_content_summary(parsed_data)

        if not content_summary.strip():
            return RoutingResult([], {}, "内容为空", 0), {"error": "empty_content"}

        # 构建提示词
        system_prompt = self._build_system_prompt()
        user_prompt = ROUTING_USER_PROMPT.format(
            title=title, url=url, content_summary=content_summary
        )

        # 调用 LLM
        response, trace = self._call_llm(system_prompt, user_prompt)

        if not response:
            return RoutingResult([], {}, "LLM 调用失败", 0), trace

        # 解析响应
        parsed = self._parse_response(response)

        # 过滤：只保留注册表中存在且启用的类型
        valid_types = []
        valid_confidences = {}
        for t in parsed.get("types", []):
            kt = self.registry.get(t)
            if kt and kt.enabled:
                conf = parsed.get("confidences", {}).get(t, 0.5)
                if conf >= kt.min_confidence:
                    valid_types.append(t)
                    valid_confidences[t] = conf

        result = RoutingResult(
            types=valid_types,
            confidences=valid_confidences,
            reasoning=parsed.get("reasoning", ""),
            tokens_used=trace.get("tokens", 0),
        )

        trace["raw_types"] = parsed.get("types", [])
        trace["valid_types"] = valid_types
        trace["reasoning"] = parsed.get("reasoning", "")

        return result, trace


# 便捷函数
_router_instance: Optional[TypeRouter] = None


def get_router() -> TypeRouter:
    """获取路由器单例"""
    global _router_instance
    if _router_instance is None:
        _router_instance = TypeRouter()
    return _router_instance


def route_types(parsed_data: Dict[str, Any]) -> Tuple[List[str], Dict[str, Any]]:
    """
    便捷函数：路由类型

    Returns:
        (types, trace): 类型列表和追踪信息
    """
    router = get_router()
    result, trace = router.route(parsed_data)
    return result.types, trace
