"""
向量存储管理
基于 ChromaDB 实现
"""

import json
import hashlib
from pathlib import Path
from typing import Dict, List, Optional, Any, cast

import chromadb
from chromadb.config import Settings
from chromadb.api.types import Documents, EmbeddingFunction, Embeddings

from .config import VectorConfig, TYPE_TO_COLLECTION


class CustomEmbeddingFunction(EmbeddingFunction):
    """自定义嵌入函数，使用配置的嵌入模型 API"""

    def __init__(self, config: VectorConfig):
        self.config = config
        self._cache: Dict[str, List[float]] = {}

    def _get_cache_path(self, text_hash: str) -> Path:
        """获取缓存文件路径"""
        return self.config.embedding_cache_path / f"{text_hash}.json"

    def _load_from_cache(self, text: str) -> Optional[List[float]]:
        """从缓存加载"""
        text_hash = hashlib.md5(text.encode("utf-8")).hexdigest()

        if text_hash in self._cache:
            return self._cache[text_hash]

        cache_path = self._get_cache_path(text_hash)
        if cache_path.exists():
            try:
                data = json.loads(cache_path.read_text(encoding="utf-8"))
                self._cache[text_hash] = data["embedding"]
                return data["embedding"]
            except Exception:
                pass
        return None

    def _save_to_cache(self, text: str, embedding: List[float]):
        """保存到缓存"""
        text_hash = hashlib.md5(text.encode("utf-8")).hexdigest()
        self._cache[text_hash] = embedding

        cache_path = self._get_cache_path(text_hash)
        try:
            cache_path.write_text(json.dumps({"embedding": embedding}), encoding="utf-8")
        except Exception:
            pass

    def __call__(self, input: Documents) -> Embeddings:
        """生成嵌入向量"""
        import httpx

        results: List[Optional[List[float]]] = []
        uncached_texts = []
        uncached_indices = []

        # 检查缓存
        for i, text in enumerate(input):
            cached = self._load_from_cache(text[:8000])
            if cached:
                results.append(cached)
            else:
                results.append(None)
                uncached_texts.append(text[:8000])
                uncached_indices.append(i)

        # 调用 API 获取未缓存的
        if uncached_texts:
            try:
                headers = {
                    "Authorization": f"Bearer {self.config.embedding_api_key}",
                    "Content-Type": "application/json",
                }

                payload = {
                    "model": self.config.embedding_model_id,
                    "input": uncached_texts,
                    "encoding_format": "float",
                }

                with httpx.Client(timeout=60) as client:
                    response = client.post(
                        self.config.embedding_api_base, headers=headers, json=payload
                    )
                    response.raise_for_status()
                    data = response.json()

                for j, item in enumerate(data["data"]):
                    idx = uncached_indices[j]
                    embedding = item["embedding"]
                    results[idx] = embedding
                    self._save_to_cache(uncached_texts[j], embedding)

            except Exception as e:
                print(f"[EmbeddingFunction] 获取嵌入失败: {e}")
                # 填充零向量作为后备
                for idx in uncached_indices:
                    if results[idx] is None:
                        results[idx] = [0.0] * self.config.embedding_dimension

        # 确保没有 None
        return cast(
            Embeddings, [r if r else [0.0] * self.config.embedding_dimension for r in results]
        )


class VectorStore:
    """向量存储管理器"""

    def __init__(self, config: VectorConfig = None):
        self.config = config or VectorConfig()

        # 初始化 ChromaDB
        self.client = chromadb.PersistentClient(
            path=str(self.config.vector_store_path),
            settings=Settings(anonymized_telemetry=False, allow_reset=True),
        )

        # 初始化嵌入函数
        self.embedding_fn = CustomEmbeddingFunction(self.config)

        # 初始化 Collections
        self.collections: Dict[str, chromadb.Collection] = {}
        self._init_collections()

    def _init_collections(self):
        """初始化所有 Collection"""
        for name, info in self.config.collections.items():
            self.collections[name] = self.client.get_or_create_collection(
                name=name,
                metadata={"description": info["description"]},
                embedding_function=self.embedding_fn,
            )
            print(f"[VectorStore] Collection '{name}' 已就绪")

    def get_collection(self, name: str) -> Optional[chromadb.Collection]:
        """获取 Collection"""
        return self.collections.get(name)

    def get_collection_for_type(self, type_id: str) -> Optional[chromadb.Collection]:
        """根据知识类型获取对应的 Collection"""
        collection_name = TYPE_TO_COLLECTION.get(type_id)
        if collection_name:
            return self.collections.get(collection_name)
        return None

    def add_documents(
        self,
        collection_name: str,
        documents: List[str],
        metadatas: List[Dict[str, Any]],
        ids: List[str],
    ) -> bool:
        """添加文档到 Collection"""
        collection = self.collections.get(collection_name)
        if not collection:
            print(f"[VectorStore] Collection '{collection_name}' 不存在")
            return False

        try:
            collection.add(documents=documents, metadatas=cast(Any, metadatas), ids=ids)
            print(f"[VectorStore] 添加 {len(documents)} 个文档到 '{collection_name}'")
            return True
        except Exception as e:
            print(f"[VectorStore] 添加文档失败: {e}")
            return False

    def query(
        self,
        collection_name: str,
        query_text: str,
        n_results: int = 5,
        where: Dict = None,
        where_document: Dict = None,
    ) -> Dict[str, Any]:
        """查询相似文档"""
        collection = self.collections.get(collection_name)
        if not collection:
            return {"documents": [], "metadatas": [], "distances": []}

        try:
            results = collection.query(
                query_texts=[query_text],
                n_results=n_results,
                where=where,
                where_document=where_document,
            )
            return cast(Dict[str, Any], results)
        except Exception as e:
            print(f"[VectorStore] 查询失败: {e}")
            return {"documents": [], "metadatas": [], "distances": []}

    def search_all(
        self, query_text: str, n_results: int = 5, collection_filter: List[str] = None
    ) -> List[Dict]:
        """在所有 Collection 中搜索"""
        all_results = []

        collections_to_search = collection_filter or list(self.collections.keys())

        for name in collections_to_search:
            if name not in self.collections:
                continue

            results = self.query(name, query_text, n_results)

            if results.get("documents") and results["documents"][0]:
                for i, doc in enumerate(results["documents"][0]):
                    all_results.append(
                        {
                            "collection": name,
                            "document": doc,
                            "metadata": results["metadatas"][0][i]
                            if results.get("metadatas")
                            else {},
                            "distance": results["distances"][0][i]
                            if results.get("distances")
                            else 0,
                            "id": results["ids"][0][i] if results.get("ids") else "",
                        }
                    )

        # 按距离排序（距离越小越相似）
        all_results.sort(key=lambda x: x["distance"])

        return all_results[:n_results]

    def get_stats(self) -> Dict:
        """获取统计信息"""
        stats: Dict[str, Any] = {"total_documents": 0, "collections": {}}

        for name, collection in self.collections.items():
            count = collection.count()
            stats["collections"][name] = count
            stats["total_documents"] += count

        return stats

    def clear_collection(self, collection_name: str) -> bool:
        """清空 Collection"""
        collection = self.collections.get(collection_name)
        if not collection:
            return False

        try:
            # 删除并重建
            self.client.delete_collection(collection_name)
            info = self.config.collections.get(collection_name, {})
            self.collections[collection_name] = self.client.create_collection(
                name=collection_name,
                metadata={"description": info.get("description", "")},
                embedding_function=self.embedding_fn,
            )
            print(f"[VectorStore] Collection '{collection_name}' 已清空")
            return True
        except Exception as e:
            print(f"[VectorStore] 清空失败: {e}")
            return False

    def reset_all(self) -> bool:
        """重置所有数据"""
        try:
            self.client.reset()
            self._init_collections()
            print("[VectorStore] 所有数据已重置")
            return True
        except Exception as e:
            print(f"[VectorStore] 重置失败: {e}")
            return False
