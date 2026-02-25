"""
LLM 知识融合模块
使用大语言模型智能合并重复但有增量的知识
"""

import json
import os
import re
from typing import Dict, Optional
from datetime import datetime


class LLMMerger:
    """LLM 知识融合器"""
    
    def __init__(self, model_id: str = None):
        """
        Args:
            model_id: 使用的模型 ID，默认从环境变量读取
        """
        # 优先使用 MERGE_MODEL_ID (专门用于合并的模型)，其次是 KB_MODEL_ID
        self.model_id = model_id or os.getenv("MERGE_MODEL_ID") or os.getenv("KB_MODEL_ID") or "Qwen/Qwen2.5-7B-Instruct"
        
        # API 基础 URL - 确保有默认值
        self.api_base = os.getenv("OPENAI_API_BASE") or os.getenv("OPENAI_BASE_URL") or "https://api.siliconflow.cn/v1"
        # 优先使用 KB_API_KEY，其次 OPENAI_API_KEY
        self.api_key = os.getenv("KB_API_KEY") or os.getenv("OPENAI_API_KEY", "")
        
        if not self.api_key:
            print("[LLMMerger] 警告: KB_API_KEY 或 OPENAI_API_KEY 未设置")
        
        # 打印配置信息（调试用）
        print(f"[LLMMerger] 初始化: model={self.model_id}, api_base={self.api_base[:30]}...")
    
    def _build_merge_prompt(self, existing: Dict, new: Dict, type_id: str) -> str:
        """构建融合提示词"""
        return f'''你是一个知识融合专家。请将以下两份关于同一主题的知识进行智能融合，生成一份更完整、准确的版本。

【知识类型】
{type_id}

【已有知识】
```json
{json.dumps(existing, ensure_ascii=False, indent=2)}
```

【新知识】
```json
{json.dumps(new, ensure_ascii=False, indent=2)}
```

【融合原则】
1. 定义/描述：选择更准确、更完整的表述；如果各有侧重，整合两者要点
2. 列表类字段（elements、rules、examples等）：合并所有不重复的条目
3. 属性字段：取并集；冲突时保留更详细的版本
4. ID字段：保持原有ID不变，新增条目使用新ID
5. content_slug：保留已有的，或选择更具描述性的

【输出要求】
1. 输出格式必须与输入JSON结构完全一致
2. 只输出JSON，不要任何解释
3. 确保JSON格式正确，可以被直接解析

请输出融合后的JSON：'''

    def _call_llm(self, prompt: str, max_retries: int = 5) -> str:
        """调用 LLM（带重试）"""
        import httpx
        import time
        import random
        
        # 强制每次调用前等待，避免高频触发限流 (Rate Limiting)
        # 引入随机抖动避免并发冲突
        initial_wait = 2.0 + random.uniform(0, 1)
        print(f"[LLMMerger] 准备调用 API，主动等待 {initial_wait:.2f}s 以避免限流...")
        time.sleep(initial_wait)
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self.model_id,
            "messages": [
                {"role": "system", "content": "你是一个专业的知识融合助手，擅长将多个来源的知识整合为完整、准确的版本。"},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.3,
            "max_tokens": 8000
        }
        
        last_error: Exception | None = None
        for attempt in range(max_retries):
            try:
                # 增加 http2=False 以提高稳定性，timeout 增加到 180s
                with httpx.Client(timeout=180, http2=False) as client:
                    response = client.post(
                        f"{self.api_base}/chat/completions",
                        headers=headers,
                        json=payload
                    )
                    response.raise_for_status()
                    result = response.json()
                    return result["choices"][0]["message"]["content"]
            except httpx.HTTPStatusError as e:
                last_error = e
                print(f"[LLMMerger] API 状态错误 (尝试 {attempt + 1}/{max_retries}): {e.response.status_code} - {e}")
                
                # 429 Too Many Requests - 需要长等待
                if e.response.status_code == 429:
                    wait_time = 15 * (attempt + 1)  # 15s, 30s, 45s...
                    print(f"[LLMMerger] 触发限流 (429)，等待 {wait_time} 秒后重试...")
                    time.sleep(wait_time)
                    continue
                    
                if attempt < max_retries - 1:
                    wait_time = (2 ** attempt) * 2
                    print(f"[LLMMerger] 等待 {wait_time} 秒后重试...")
                    time.sleep(wait_time)
                    
            except Exception as e:
                last_error = e
                print(f"[LLMMerger] API 调用失败 (尝试 {attempt + 1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    # 对于连接错误，增加基础等待时间
                    wait_time = (2 ** attempt) * 3  # 3s, 6s, 12s...
                    print(f"[LLMMerger] 等待 {wait_time} 秒后重试...")
                    time.sleep(wait_time)
        
        print(f"[LLMMerger] API 最终失败: {last_error}")
        return ""
    
    def _extract_json(self, text: str) -> Optional[Dict]:
        """从 LLM 输出中提取 JSON"""
        # 尝试直接解析
        try:
            return json.loads(text)
        except Exception:
            pass
        
        # 尝试提取 ```json ... ``` 块
        match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', text)
        if match:
            try:
                return json.loads(match.group(1))
            except Exception:
                pass
        
        # 尝试找到 { ... } 块
        match = re.search(r'\{[\s\S]*\}', text)
        if match:
            try:
                return json.loads(match.group(0))
            except Exception:
                pass
        
        return None
    
    def merge(self, existing: Dict, new: Dict, type_id: str, 
              existing_source: str = None, new_source: str = None) -> Dict:
        """
        融合两份知识
        
        Args:
            existing: 已有知识
            new: 新知识
            type_id: 知识类型 ID
            existing_source: 已有知识的来源 URL
            new_source: 新知识的来源 URL
            
        Returns:
            融合后的知识，包含来源追溯
        """
        prompt = self._build_merge_prompt(existing, new, type_id)
        response = self._call_llm(prompt)
        
        if not response:
            # 如果 LLM 调用失败，返回简单合并结果
            print("[LLMMerger] LLM 调用失败，使用简单合并")
            return self._simple_merge(existing, new, type_id)
        
        merged = self._extract_json(response)
        
        if not merged:
            print("[LLMMerger] 无法解析 LLM 输出，使用简单合并")
            return self._simple_merge(existing, new, type_id)
        
        # 添加来源追溯信息
        merged = self._add_provenance(merged, existing_source, new_source)
        
        return merged
    
    def _simple_merge(self, existing: Dict, new: Dict, type_id: str) -> Dict:
        """
        简单合并：当 LLM 不可用时的后备方案
        基本策略：保留已有，补充新增
        """
        result = json.loads(json.dumps(existing))  # 深拷贝
        
        # 合并顶层列表字段
        list_fields = ["elements", "rules", "scenarios", "categories", 
                       "validation_rules", "concepts", "principles",
                       "leveling_principles", "decomposition_rules"]
        
        for field in list_fields:
            if field in new and field in result:
                existing_items = result[field]
                new_items = new[field]
                
                # 获取已有的 ID 集合
                existing_ids = set()
                for item in existing_items:
                    if isinstance(item, dict):
                        item_id = item.get("id") or item.get("name")
                        if item_id:
                            existing_ids.add(str(item_id).lower())
                
                # 添加新条目
                for item in new_items:
                    if isinstance(item, dict):
                        item_id = item.get("id") or item.get("name")
                        if item_id and str(item_id).lower() not in existing_ids:
                            existing_items.append(item)
        
        return result
    
    def _add_provenance(self, merged: Dict, existing_source: str = None, 
                        new_source: str = None) -> Dict:
        """添加来源追溯信息"""
        sources = merged.get("_sources", [])
        
        now = datetime.now().isoformat()
        
        if existing_source and existing_source not in [s.get("url") for s in sources]:
            sources.append({
                "url": existing_source,
                "merged_at": now,
                "role": "existing"
            })
        
        if new_source and new_source not in [s.get("url") for s in sources]:
            sources.append({
                "url": new_source,
                "merged_at": now,
                "role": "new"
            })
        
        if sources:
            merged["_sources"] = sources
            merged["_last_refined"] = now
        
        return merged


def test_merger():
    """测试融合器"""
    merger = LLMMerger()
    
    existing = {
        "content_slug": "elements_basics",
        "description": "DFD核心元素",
        "elements": [
            {"id": "external_entity", "name": "外部实体", "definition": "系统外部的参与者"}
        ]
    }
    
    new = {
        "content_slug": "elements_full",
        "description": "数据流图的四大核心元素定义",
        "elements": [
            {"id": "external_entity", "name": "外部实体", "definition": "位于系统边界之外，与系统进行数据交互的实体"},
            {"id": "process", "name": "处理过程", "definition": "对数据进行处理的功能单元"}
        ]
    }
    
    merged = merger.merge(existing, new, "diagrams.dfd.concepts")
    print(json.dumps(merged, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    test_merger()

