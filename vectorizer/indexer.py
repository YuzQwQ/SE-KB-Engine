"""
批量索引器
将 JSON 知识库批量向量化并存入 ChromaDB
"""

from pathlib import Path
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime

from .config import VectorConfig, TYPE_TO_COLLECTION
from .store import VectorStore
from .chunker import KnowledgeChunker


@dataclass
class IndexStats:
    """索引统计"""
    total_files: int = 0
    total_chunks: int = 0
    by_collection: Dict[str, int] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)
    start_time: datetime = field(default_factory=datetime.now)
    end_time: Optional[datetime] = None
    
    def to_dict(self) -> Dict:
        return {
            "total_files": self.total_files,
            "total_chunks": self.total_chunks,
            "by_collection": self.by_collection,
            "errors": self.errors[:10],  # 最多10个错误
            "duration_seconds": (self.end_time - self.start_time).total_seconds() if self.end_time else 0
        }


class KnowledgeIndexer:
    """知识索引器"""
    
    def __init__(self, 
                 config: VectorConfig = None,
                 log_callback: Callable[[str], None] = None):
        self.config = config or VectorConfig()
        self.log = log_callback or print
        
        self.store = VectorStore(self.config)
        self.chunker = KnowledgeChunker()
    
    def _get_knowledge_type(self, file_path: Path) -> str:
        """从文件路径推断知识类型"""
        parts = file_path.parts
        
        # 查找关键目录
        if "concepts" in parts:
            return "diagrams.dfd.concepts"
        elif "examples" in parts:
            return "diagrams.dfd.examples"
        elif "rules" in parts:
            return "diagrams.dfd.rules"
        elif "templates" in parts:
            return "diagrams.dfd.templates"
        elif "validation" in parts:
            return "diagrams.dfd.validation"
        elif "levels" in parts:
            return "diagrams.dfd.levels"
        elif "theory" in parts:
            return "theory"
        elif "domain" in parts:
            return "domain"
        elif "mappings" in parts:
            return "mappings"
        elif "schema" in parts:
            return "schema"
        else:
            return "unknown"
    
    def _get_collection_name(self, knowledge_type: str) -> Optional[str]:
        """获取对应的 Collection 名称"""
        return TYPE_TO_COLLECTION.get(knowledge_type)
    
    def index_file(self, file_path: Path) -> int:
        """
        索引单个文件
        
        Returns:
            添加的 chunk 数量
        """
        knowledge_type = self._get_knowledge_type(file_path)
        collection_name = self._get_collection_name(knowledge_type)
        
        if not collection_name:
            self.log(f"  ⚠️ 未知类型，跳过: {file_path.name}")
            return 0
        
        # 分块
        chunks = self.chunker.chunk_file(file_path, knowledge_type)
        
        if not chunks:
            self.log(f"  ⚠️ 无法分块: {file_path.name}")
            return 0
        
        # 准备数据
        documents = [chunk.text for chunk in chunks]
        metadatas = [chunk.metadata for chunk in chunks]
        ids = [chunk.id for chunk in chunks]
        
        # 添加到向量库
        success = self.store.add_documents(
            collection_name,
            documents,
            metadatas,
            ids
        )
        
        if success:
            return len(chunks)
        else:
            return 0
    
    def index_directory(self, dir_path: Path, 
                        recursive: bool = True) -> IndexStats:
        """
        索引目录
        
        Args:
            dir_path: 目录路径
            recursive: 是否递归处理子目录
            
        Returns:
            索引统计
        """
        stats = IndexStats()
        
        if not dir_path.exists():
            self.log(f"❌ 目录不存在: {dir_path}")
            return stats
        
        # 收集所有 JSON 文件
        if recursive:
            json_files = list(dir_path.rglob("*.json"))
        else:
            json_files = list(dir_path.glob("*.json"))
        
        # 过滤掉不需要的文件
        exclude_names = {"metadata.json", "parsed.json", "trace.json", 
                        "metrics.json", "errors.json", "README.json"}
        exclude_dirs = {"artifacts", "vector_store"}
        
        json_files = [
            f for f in json_files 
            if f.name not in exclude_names
            and not any(d in f.parts for d in exclude_dirs)
        ]
        
        self.log(f"📁 发现 {len(json_files)} 个 JSON 文件")
        
        for i, file_path in enumerate(json_files):
            try:
                self.log(f"[{i+1}/{len(json_files)}] 索引: {file_path.name}")
                
                chunk_count = self.index_file(file_path)
                
                if chunk_count > 0:
                    stats.total_files += 1
                    stats.total_chunks += chunk_count
                    
                    # 统计每个 Collection
                    knowledge_type = self._get_knowledge_type(file_path)
                    collection_name = self._get_collection_name(knowledge_type) or "unknown"
                    stats.by_collection[collection_name] = stats.by_collection.get(collection_name, 0) + chunk_count
                    
                    self.log(f"  ✅ 添加 {chunk_count} 个块")
                    
            except Exception as e:
                error_msg = f"索引失败 {file_path.name}: {e}"
                self.log(f"  ❌ {e}")
                stats.errors.append(error_msg)
        
        stats.end_time = datetime.now()
        return stats
    
    def build_full_index(self, reset: bool = False) -> IndexStats:
        """
        构建完整索引
        
        Args:
            reset: 是否先重置所有数据
            
        Returns:
            索引统计
        """
        self.log("=" * 60)
        self.log("开始构建向量索引")
        self.log("=" * 60)
        
        if reset:
            self.log("\n🔄 重置现有索引...")
            self.store.reset_all()
        
        # 显示当前状态
        current_stats = self.store.get_stats()
        self.log(f"\n📊 当前索引状态: {current_stats['total_documents']} 个文档")
        
        # 索引各个目录
        all_stats = IndexStats()
        
        for collection_name, collection_info in self.config.collections.items():
            self.log(f"\n{'='*40}")
            self.log(f"📂 处理 Collection: {collection_name}")
            self.log(f"   描述: {collection_info['description']}")
            self.log(f"{'='*40}")
            
            for source_dir in collection_info["source_dirs"]:
                dir_path = self.config.kb_root / source_dir
                
                if not dir_path.exists():
                    self.log(f"  ⚠️ 目录不存在: {source_dir}")
                    continue
                
                self.log(f"\n  📁 扫描: {source_dir}")
                dir_stats = self.index_directory(dir_path, recursive=False)
                
                # 合并统计
                all_stats.total_files += dir_stats.total_files
                all_stats.total_chunks += dir_stats.total_chunks
                all_stats.errors.extend(dir_stats.errors)
                
                for col, count in dir_stats.by_collection.items():
                    all_stats.by_collection[col] = all_stats.by_collection.get(col, 0) + count
        
        all_stats.end_time = datetime.now()
        
        # 最终统计
        self.log("\n" + "=" * 60)
        self.log("✅ 索引构建完成!")
        self.log("=" * 60)
        self.log(f"  处理文件: {all_stats.total_files}")
        self.log(f"  生成块数: {all_stats.total_chunks}")
        self.log(f"  耗时: {all_stats.to_dict()['duration_seconds']:.1f} 秒")
        
        if all_stats.errors:
            self.log(f"  错误数: {len(all_stats.errors)}")
        
        self.log("\n📊 各 Collection 统计:")
        final_stats = self.store.get_stats()
        for name, count in final_stats['collections'].items():
            self.log(f"  - {name}: {count} 文档")
        
        return all_stats
    
    def get_index_stats(self) -> Dict:
        """获取当前索引统计"""
        return self.store.get_stats()
