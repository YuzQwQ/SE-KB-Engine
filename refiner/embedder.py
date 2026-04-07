"""
语义嵌入模块
使用嵌入模型计算文本的向量表示，用于语义相似度检测
"""

import os
import json
import hashlib
from typing import List, Dict, Optional, Tuple
from pathlib import Path
import numpy as np
from utils.env_loader import load_env_file


load_env_file()


class SemanticEmbedder:
    """语义嵌入器"""

    def __init__(self, cache_dir: str = None):
        """
        Args:
            cache_dir: 嵌入向量缓存目录，避免重复计算
        """
        self.api_base = os.getenv("EMBEDDING_BASE_URL", "")
        self.api_key = os.getenv("EMBEDDING_API_KEY", "")
        self.model_id = os.getenv("EMBEDDING_MODEL_ID", "")

        # 缓存目录
        if cache_dir:
            self.cache_dir = Path(cache_dir)
        else:
            self.cache_dir = Path("data/embedding_cache")
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        # 内存缓存
        self._cache: Dict[str, List[float]] = {}

        # 验证配置
        if not all([self.api_base, self.api_key, self.model_id]):
            print("[SemanticEmbedder] 警告: 嵌入模型配置不完整，请检查环境变量")
            print(f"  EMBEDDING_BASE_URL: {'已设置' if self.api_base else '未设置'}")
            print(f"  EMBEDDING_API_KEY: {'已设置' if self.api_key else '未设置'}")
            print(f"  EMBEDDING_MODEL_ID: {'已设置' if self.model_id else '未设置'}")

    def is_available(self) -> bool:
        """检查嵌入服务是否可用"""
        return all([self.api_base, self.api_key, self.model_id])

    def _text_hash(self, text: str) -> str:
        """计算文本的 hash，用于缓存"""
        return hashlib.md5(text.encode("utf-8")).hexdigest()

    def _load_from_cache(self, text_hash: str) -> Optional[List[float]]:
        """从缓存加载嵌入向量"""
        # 内存缓存
        if text_hash in self._cache:
            return self._cache[text_hash]

        # 文件缓存
        cache_file = self.cache_dir / f"{text_hash}.json"
        if cache_file.exists():
            try:
                data = json.loads(cache_file.read_text(encoding="utf-8"))
                self._cache[text_hash] = data["embedding"]
                return data["embedding"]
            except Exception:
                pass

        return None

    def _save_to_cache(self, text_hash: str, embedding: List[float]):
        """保存嵌入向量到缓存"""
        self._cache[text_hash] = embedding

        cache_file = self.cache_dir / f"{text_hash}.json"
        try:
            cache_file.write_text(
                json.dumps({"embedding": embedding}, ensure_ascii=False), encoding="utf-8"
            )
        except Exception:
            pass

    def get_embedding(self, text: str) -> Optional[List[float]]:
        """
        获取文本的嵌入向量

        Args:
            text: 输入文本

        Returns:
            嵌入向量，失败返回 None
        """
        if not self.is_available():
            return None

        if not text or not text.strip():
            return None

        # 截断过长文本
        text = text[:8000]

        # 检查缓存
        text_hash = self._text_hash(text)
        cached = self._load_from_cache(text_hash)
        if cached:
            return cached

        # 调用 API（带重试）
        import httpx
        import time

        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}

        payload = {"model": self.model_id, "input": text, "encoding_format": "float"}

        max_retries = 3
        for attempt in range(max_retries):
            try:
                with httpx.Client(timeout=30) as client:
                    response = client.post(self.api_base, headers=headers, json=payload)
                    response.raise_for_status()
                    result = response.json()

                embedding = result["data"][0]["embedding"]

                # 保存到缓存
                self._save_to_cache(text_hash, embedding)

                return embedding

            except Exception as e:
                if attempt < max_retries - 1:
                    time.sleep(1)
                    continue
                print(f"[SemanticEmbedder] 获取嵌入向量失败: {e}")
                return None
        return None

    def get_embeddings_batch(self, texts: List[str]) -> List[Optional[List[float]]]:
        """
        批量获取嵌入向量

        Args:
            texts: 文本列表

        Returns:
            嵌入向量列表
        """
        if not self.is_available():
            return [None] * len(texts)

        results: List[Optional[List[float]]] = []
        uncached_indices = []
        uncached_texts = []

        # 先检查缓存
        for i, text in enumerate(texts):
            if not text or not text.strip():
                results.append(None)
                continue

            text_hash = self._text_hash(text[:8000])
            cached = self._load_from_cache(text_hash)
            if cached:
                results.append(cached)
            else:
                results.append(None)  # 占位
                uncached_indices.append(i)
                uncached_texts.append(text[:8000])

        # 批量获取未缓存的
        if uncached_texts:
            try:
                import httpx

                headers = {
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                }

                payload = {
                    "model": self.model_id,
                    "input": uncached_texts,
                    "encoding_format": "float",
                }

                with httpx.Client(timeout=60) as client:
                    response = client.post(self.api_base, headers=headers, json=payload)
                    response.raise_for_status()
                    result = response.json()

                for j, item in enumerate(result["data"]):
                    idx = uncached_indices[j]
                    embedding = item["embedding"]
                    results[idx] = embedding

                    # 保存到缓存
                    text_hash = self._text_hash(uncached_texts[j])
                    self._save_to_cache(text_hash, embedding)

            except Exception as e:
                print(f"[SemanticEmbedder] 批量获取嵌入向量失败: {e}")

        return results

    def cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """
        计算两个向量的余弦相似度

        Args:
            vec1: 向量1
            vec2: 向量2

        Returns:
            相似度 [0, 1]
        """
        if not vec1 or not vec2:
            return 0.0

        a = np.array(vec1)
        b = np.array(vec2)

        dot_product = np.dot(a, b)
        norm_a = np.linalg.norm(a)
        norm_b = np.linalg.norm(b)

        if norm_a == 0 or norm_b == 0:
            return 0.0

        return float(dot_product / (norm_a * norm_b))

    def semantic_similarity(self, text1: str, text2: str) -> float:
        """
        计算两段文本的语义相似度

        Args:
            text1: 文本1
            text2: 文本2

        Returns:
            相似度 [0, 1]
        """
        vec1 = self.get_embedding(text1)
        vec2 = self.get_embedding(text2)

        if not vec1 or not vec2:
            return 0.0

        return self.cosine_similarity(vec1, vec2)

    def extract_text_for_embedding(self, knowledge: Dict) -> str:
        """
        从知识对象中提取用于嵌入的文本

        Args:
            knowledge: 知识对象（JSON 格式）

        Returns:
            合并后的文本
        """
        parts = []

        # 提取描述性字段
        for key in ["description", "definition", "content_slug", "name", "title"]:
            if key in knowledge and knowledge[key]:
                parts.append(str(knowledge[key]))

        # 提取列表中的关键内容
        for list_key in [
            "elements",
            "rules",
            "concepts",
            "principles",
            "scenarios",
            "validation_rules",
        ]:
            if list_key in knowledge and isinstance(knowledge[list_key], list):
                for item in knowledge[list_key][:10]:  # 限制数量
                    if isinstance(item, dict):
                        for field in ["name", "definition", "detail", "description"]:
                            if field in item and item[field]:
                                parts.append(str(item[field]))
                    elif isinstance(item, str):
                        parts.append(item)

        return " ".join(parts)[:8000]


class SemanticDeduplicator:
    """基于语义相似度的去重器"""

    def __init__(self, similarity_threshold: float = 0.85):
        """
        Args:
            similarity_threshold: 相似度阈值，超过则认为语义重复
        """
        self.embedder = SemanticEmbedder()
        self.similarity_threshold = similarity_threshold

    def is_available(self) -> bool:
        """检查是否可用"""
        return self.embedder.is_available()

    def find_semantic_duplicates(self, items: List[Dict]) -> List[Tuple[int, int, float]]:
        """
        在一组知识中找出语义重复的对

        Args:
            items: 知识对象列表

        Returns:
            重复对列表: [(index1, index2, similarity), ...]
        """
        if not self.is_available():
            return []

        # 提取文本
        texts = [self.embedder.extract_text_for_embedding(item) for item in items]

        # 批量获取嵌入
        embeddings = self.embedder.get_embeddings_batch(texts)

        # 计算两两相似度
        duplicates = []
        n = len(items)

        for i in range(n):
            for j in range(i + 1, n):
                emb_i = embeddings[i]
                emb_j = embeddings[j]
                if emb_i is not None and emb_j is not None:
                    sim = self.embedder.cosine_similarity(emb_i, emb_j)
                    if sim >= self.similarity_threshold:
                        duplicates.append((i, j, sim))

        # 按相似度降序排序
        duplicates.sort(key=lambda x: x[2], reverse=True)

        return duplicates

    def check_semantic_duplicate(
        self, new_item: Dict, existing_items: List[Dict]
    ) -> Tuple[bool, Optional[int], float]:
        """
        检查新知识是否与已有知识语义重复

        Args:
            new_item: 新知识
            existing_items: 已有知识列表

        Returns:
            (is_duplicate, most_similar_index, similarity)
        """
        if not self.is_available() or not existing_items:
            return False, None, 0.0

        new_text = self.embedder.extract_text_for_embedding(new_item)
        new_embedding = self.embedder.get_embedding(new_text)

        if not new_embedding:
            return False, None, 0.0

        # 获取已有知识的嵌入
        existing_texts = [self.embedder.extract_text_for_embedding(item) for item in existing_items]
        existing_embeddings = self.embedder.get_embeddings_batch(existing_texts)

        # 找最相似的
        best_sim = 0.0
        best_idx = None

        for i, emb in enumerate(existing_embeddings):
            if emb is not None:
                sim = self.embedder.cosine_similarity(new_embedding, emb)
                if sim > best_sim:
                    best_sim = sim
                    best_idx = i

        is_duplicate = best_sim >= self.similarity_threshold

        return is_duplicate, best_idx, best_sim


def test_embedder():
    """测试嵌入器"""
    embedder = SemanticEmbedder()

    if not embedder.is_available():
        print("嵌入服务不可用，请检查环境变量配置")
        return

    text1 = "数据流图中的外部实体是指位于系统边界之外，与系统进行数据交互的人员、组织或其他系统"
    text2 = "外部实体是DFD图中表示系统外部参与者的元素，用矩形表示"
    text3 = "Python是一种解释型编程语言"

    print("测试语义相似度:")
    print(f"  文本1 vs 文本2: {embedder.semantic_similarity(text1, text2):.4f}")
    print(f"  文本1 vs 文本3: {embedder.semantic_similarity(text1, text3):.4f}")
    print(f"  文本2 vs 文本3: {embedder.semantic_similarity(text2, text3):.4f}")


if __name__ == "__main__":
    test_embedder()
