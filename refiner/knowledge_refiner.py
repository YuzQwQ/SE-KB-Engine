"""
知识精炼器
整合去重、融合、输出的完整流程

三层去重策略：
1. 语义相似度检测（嵌入向量）- 快速筛选语义相近的内容
2. 结构化字段匹配 - 精确判断是否描述同一对象
3. 增量知识检测 - 判断是否有新增价值
"""

import json
import os
import shutil
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Callable
from dataclasses import dataclass, field

from .deduplicator import StructuralDeduplicator, DeduplicationResult
from .embedder import SemanticEmbedder, SemanticDeduplicator
from .merger import LLMMerger


@dataclass
class RefineStats:
    """精炼统计信息"""
    total_artifacts: int = 0
    by_type: Dict[str, int] = field(default_factory=dict)
    duplicates_found: int = 0
    semantic_duplicates: int = 0  # 语义层发现的重复
    structural_duplicates: int = 0  # 结构层发现的重复
    merged_count: int = 0
    skipped_count: int = 0
    new_count: int = 0
    errors: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        return {
            "total_artifacts": self.total_artifacts,
            "by_type": self.by_type,
            "duplicates_found": self.duplicates_found,
            "semantic_duplicates": self.semantic_duplicates,
            "structural_duplicates": self.structural_duplicates,
            "merged_count": self.merged_count,
            "skipped_count": self.skipped_count,
            "new_count": self.new_count,
            "errors": self.errors
        }


@dataclass
class ArtifactInfo:
    """Artifact 信息"""
    path: Path
    type_id: str
    content: Dict
    source_url: str = ""
    created_at: str = ""


class KnowledgeRefiner:
    """知识精炼器"""
    
    def __init__(self, 
                 artifacts_dir: str = "se_kb/artifacts",
                 output_dir: str = "se_kb",
                 structural_threshold: float = 0.6,
                 semantic_threshold: float = 0.85,
                 log_callback: Callable[[str], None] = None):
        """
        Args:
            artifacts_dir: artifacts 目录路径
            output_dir: 输出目录路径（正式知识库）
            structural_threshold: 结构化去重相似度阈值
            semantic_threshold: 语义去重相似度阈值
            log_callback: 日志回调函数
        """
        self.artifacts_dir = Path(artifacts_dir)
        self.output_dir = Path(output_dir)
        self.structural_threshold = structural_threshold
        self.semantic_threshold = semantic_threshold
        self.log_callback = log_callback or print
        
        # 三层去重器
        self.semantic_dedup = SemanticDeduplicator(semantic_threshold)
        self.structural_dedup = StructuralDeduplicator(structural_threshold)
        self.merger = LLMMerger()
        
        # 检查语义去重是否可用
        self.semantic_available = self.semantic_dedup.is_available()
        if not self.semantic_available:
            self.log("⚠️ 语义去重不可用（嵌入模型未配置），将仅使用结构化匹配")
        
        # 类型到输出目录的映射
        self.type_output_mapping = {
            "diagrams.dfd.concepts": "diagrams/dfd/concepts",
            "diagrams.dfd.rules": "diagrams/dfd/rules",
            "diagrams.dfd.examples": "diagrams/dfd/examples",
            "diagrams.dfd.templates": "diagrams/dfd/templates",
            "diagrams.dfd.validation": "diagrams/dfd/validation",
            "diagrams.dfd.levels": "diagrams/dfd/levels",
            "theory": "theory",
            "mappings": "mappings",
            "schema": "schema",
            "domain": "domain",
            "examples": "examples",
            "rules": "rules",
        }
    
    def log(self, message: str):
        """输出日志"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_callback(f"[{timestamp}] {message}")
    
    def scan_artifacts(self, date_filter: str = None, 
                       time_filter: str = None) -> List[ArtifactInfo]:
        """
        扫描 artifacts 目录
        
        Args:
            date_filter: 日期过滤，格式 "YYYY/MM/DD" 或 "YYYY-MM-DD"
            time_filter: 时间过滤，格式 "HH_MM" 或 "HH:MM"
            
        Returns:
            ArtifactInfo 列表
        """
        artifacts = []
        
        if not self.artifacts_dir.exists():
            self.log(f"目录不存在: {self.artifacts_dir}")
            return artifacts
        
        # 构建搜索路径
        search_path = self.artifacts_dir
        
        if date_filter:
            # 标准化日期格式
            date_filter = date_filter.replace("-", "/")
            search_path = search_path / date_filter
            if not search_path.exists():
                self.log(f"日期目录不存在: {search_path}")
                return artifacts
        
        self.log(f"扫描目录: {search_path}")
        
        # 遍历查找所有 JSON 文件
        for json_file in search_path.rglob("*.json"):
            # 跳过元数据文件
            if json_file.name in ["metadata.json", "parsed.json", "trace.json", 
                                  "metrics.json", "errors.json"]:
                continue
            
            # 时间过滤
            if time_filter:
                time_filter_normalized = time_filter.replace(":", "_")
                # 检查路径中是否包含时间目录
                if time_filter_normalized not in str(json_file):
                    continue
            
            try:
                content = json.loads(json_file.read_text(encoding="utf-8"))
                
                # 从文件名推断类型
                type_id = self._infer_type_from_filename(json_file.name)
                
                if not type_id:
                    continue
                
                # 尝试获取来源 URL
                source_url = self._get_source_url(json_file)
                
                artifacts.append(ArtifactInfo(
                    path=json_file,
                    type_id=type_id,
                    content=content,
                    source_url=source_url,
                    created_at=datetime.fromtimestamp(json_file.stat().st_mtime).isoformat()
                ))
                
            except Exception as e:
                self.log(f"读取文件失败 {json_file}: {e}")
        
        self.log(f"共发现 {len(artifacts)} 个 artifact 文件")
        return artifacts
    
    def _infer_type_from_filename(self, filename: str) -> Optional[str]:
        """从文件名推断知识类型"""
        # 文件名格式: {type_short}_{domain}_{slug}_{hash}.json
        # 例如: dfd_concepts_csdn_elements_basics_abc123.json
        
        name = filename.replace(".json", "")
        
        # 类型前缀映射
        type_prefix_map = {
            "dfd_concepts": "diagrams.dfd.concepts",
            "dfd_rules": "diagrams.dfd.rules",
            "dfd_examples": "diagrams.dfd.examples",
            "dfd_templates": "diagrams.dfd.templates",
            "dfd_validation": "diagrams.dfd.validation",
            "dfd_levels": "diagrams.dfd.levels",
            "theory": "theory",
            "mappings": "mappings",
            "schema": "schema",
            "domain": "domain",
            "examples": "examples",
            "rules": "rules",
        }
        
        for prefix, type_id in type_prefix_map.items():
            if name.startswith(prefix):
                return type_id
        
        return None
    
    def _get_source_url(self, artifact_path: Path) -> str:
        """获取 artifact 的来源 URL"""
        # 尝试从同目录的 metadata.json 读取
        metadata_path = artifact_path.parent / "metadata.json"
        if metadata_path.exists():
            try:
                metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
                return metadata.get("url", "")
            except:
                pass
        
        # 尝试从 parsed.json 读取
        parsed_path = artifact_path.parent / "parsed.json"
        if parsed_path.exists():
            try:
                parsed = json.loads(parsed_path.read_text(encoding="utf-8"))
                return parsed.get("source_url", parsed.get("url", ""))
            except:
                pass
        
        return ""
    
    def group_by_type(self, artifacts: List[ArtifactInfo]) -> Dict[str, List[ArtifactInfo]]:
        """按知识类型分组"""
        groups = {}
        for artifact in artifacts:
            if artifact.type_id not in groups:
                groups[artifact.type_id] = []
            groups[artifact.type_id].append(artifact)
        return groups
    
    def load_existing_knowledge(self, type_id: str) -> List[Dict]:
        """加载正式知识库中该类型的现有知识"""
        output_subdir = self.type_output_mapping.get(type_id)
        if not output_subdir:
            return []
        
        output_path = self.output_dir / output_subdir
        if not output_path.exists():
            return []
        
        existing = []
        for json_file in output_path.glob("*.json"):
            try:
                content = json.loads(json_file.read_text(encoding="utf-8"))
                content["_file_path"] = str(json_file)
                existing.append(content)
            except Exception as e:
                self.log(f"读取现有知识失败 {json_file}: {e}")
        
        return existing
    
    def refine_type(self, type_id: str, artifacts: List[ArtifactInfo], 
                    stats: RefineStats) -> List[Dict]:
        """
        精炼单个类型的知识
        
        采用三层去重策略：
        1. 语义相似度检测（嵌入向量）- 快速筛选
        2. 结构化字段匹配 - 精确判断
        3. 增量知识检测 - 判断是否有新增价值
        
        Args:
            type_id: 知识类型 ID
            artifacts: 该类型的所有 artifact
            stats: 统计信息
            
        Returns:
            精炼后的知识列表
        """
        self.log(f"\n{'='*50}")
        self.log(f"处理类型: {type_id} ({len(artifacts)} 个文件)")
        self.log(f"{'='*50}")
        
        # 加载现有知识
        existing_knowledge = self.load_existing_knowledge(type_id)
        self.log(f"现有知识: {len(existing_knowledge)} 个")
        
        # 合并后的知识列表
        refined_knowledge = list(existing_knowledge)
        
        for i, artifact in enumerate(artifacts):
            self.log(f"\n[{i+1}/{len(artifacts)}] 处理: {artifact.path.name}")
            
            try:
                # ========== 第一层：语义相似度检测 ==========
                semantic_duplicate = False
                semantic_similar_idx = None
                semantic_score = 0.0
                
                if self.semantic_available and refined_knowledge:
                    is_sem_dup, sem_idx, sem_score = self.semantic_dedup.check_semantic_duplicate(
                        artifact.content,
                        refined_knowledge
                    )
                    semantic_duplicate = is_sem_dup
                    semantic_similar_idx = sem_idx
                    semantic_score = sem_score
                    
                    if semantic_duplicate:
                        self.log(f"  → [语义层] 发现相似内容 (相似度: {semantic_score:.2f})")
                    else:
                        self.log(f"  → [语义层] 无明显相似 (最高: {semantic_score:.2f})")
                
                # ========== 第二层：结构化字段匹配 ==========
                structural_result = self.structural_dedup.check_duplicate(
                    artifact.content, 
                    refined_knowledge, 
                    type_id
                )
                
                if structural_result.is_duplicate:
                    self.log(f"  → [结构层] 字段匹配重复 (匹配度: {structural_result.similarity_score:.2f})")
                
                # ========== 综合判断 ==========
                # 优先使用结构化匹配的结果（更精确）
                # 语义匹配作为补充（捕获跨结构的重复）
                
                is_duplicate = structural_result.is_duplicate
                similar_item = structural_result.similar_item
                has_increment = structural_result.has_increment
                
                # 如果结构化没发现重复，但语义发现了，使用语义结果
                if not is_duplicate and semantic_duplicate and semantic_similar_idx is not None:
                    is_duplicate = True
                    similar_item = refined_knowledge[semantic_similar_idx]
                    # 语义重复默认认为有增量（需要进一步检查）
                    has_increment = True
                    self.log(f"  → [综合] 语义重复，结构不同，可能需要融合")
                
                # ========== 第三层：增量检测与处理 ==========
                if is_duplicate:
                    stats.duplicates_found += 1
                    
                    if has_increment:
                        # 有增量，执行 LLM 融合
                        self.log(f"  → [融合] 检测到增量内容，调用 LLM 融合...")
                        
                        merged = self.merger.merge(
                            similar_item,
                            artifact.content,
                            type_id,
                            existing_source=similar_item.get("_file_path"),
                            new_source=artifact.source_url
                        )
                        
                        # 替换原有知识
                        for j, existing in enumerate(refined_knowledge):
                            if existing is similar_item:
                                refined_knowledge[j] = merged
                                break
                        
                        stats.merged_count += 1
                        self.log(f"  → ✅ 融合完成")
                    else:
                        # 纯重复，跳过
                        stats.skipped_count += 1
                        self.log(f"  → ⏭️ 纯重复，跳过")
                else:
                    # 全新内容，直接添加
                    artifact.content["_source_url"] = artifact.source_url
                    artifact.content["_added_at"] = datetime.now().isoformat()
                    refined_knowledge.append(artifact.content)
                    stats.new_count += 1
                    self.log(f"  → ➕ 全新内容，添加")
                    
            except Exception as e:
                error_msg = f"处理失败 {artifact.path}: {e}"
                self.log(f"  → ❌ 错误: {e}")
                stats.errors.append(error_msg)
        
        return refined_knowledge
    
    def save_refined_knowledge(self, type_id: str, knowledge_list: List[Dict]):
        """保存精炼后的知识到正式知识库"""
        output_subdir = self.type_output_mapping.get(type_id)
        if not output_subdir:
            self.log(f"未知类型，无法保存: {type_id}")
            return
        
        output_path = self.output_dir / output_subdir
        output_path.mkdir(parents=True, exist_ok=True)
        
        for knowledge in knowledge_list:
            # 生成文件名
            content_slug = knowledge.get("content_slug", "unknown")
            # 清理 slug
            content_slug = "".join(c if c.isalnum() or c == "_" else "_" for c in content_slug)
            
            filename = f"{type_id.split('.')[-1]}_{content_slug}.json"
            filepath = output_path / filename
            
            # 移除内部字段
            output_knowledge = {k: v for k, v in knowledge.items() 
                               if not k.startswith("_file_path")}
            
            filepath.write_text(
                json.dumps(output_knowledge, ensure_ascii=False, indent=2),
                encoding="utf-8"
            )
            self.log(f"  保存: {filepath}")
    
    def run(self, date_filter: str = None, time_filter: str = None,
            dry_run: bool = False) -> RefineStats:
        """
        执行完整的精炼流程
        
        Args:
            date_filter: 日期过滤
            time_filter: 时间过滤
            dry_run: 试运行，不实际保存
            
        Returns:
            精炼统计信息
        """
        stats = RefineStats()
        
        self.log("=" * 60)
        self.log("知识去重与精炼流程启动")
        self.log("=" * 60)
        
        # 1. 扫描 artifacts
        artifacts = self.scan_artifacts(date_filter, time_filter)
        stats.total_artifacts = len(artifacts)
        
        if not artifacts:
            self.log("未找到任何 artifact，流程结束")
            return stats
        
        # 2. 按类型分组
        groups = self.group_by_type(artifacts)
        stats.by_type = {k: len(v) for k, v in groups.items()}
        
        self.log(f"\n类型分布:")
        for type_id, count in stats.by_type.items():
            self.log(f"  {type_id}: {count}")
        
        # 3. 逐类型精炼
        for type_id, type_artifacts in groups.items():
            refined = self.refine_type(type_id, type_artifacts, stats)
            
            # 4. 保存结果
            if not dry_run and refined:
                self.log(f"\n保存 {type_id} 精炼结果...")
                self.save_refined_knowledge(type_id, refined)
        
        # 5. 输出统计
        self.log("\n" + "=" * 60)
        self.log("精炼完成！统计信息:")
        self.log("=" * 60)
        self.log(f"  总 artifact 数: {stats.total_artifacts}")
        self.log(f"  发现重复: {stats.duplicates_found}")
        self.log(f"  执行融合: {stats.merged_count}")
        self.log(f"  纯重复跳过: {stats.skipped_count}")
        self.log(f"  新增内容: {stats.new_count}")
        if stats.errors:
            self.log(f"  错误数: {len(stats.errors)}")
        
        return stats
    
    def preview(self, date_filter: str = None, time_filter: str = None) -> Dict:
        """
        预览模式：扫描并分析，但不执行实际操作
        
        Returns:
            预览信息
        """
        artifacts = self.scan_artifacts(date_filter, time_filter)
        groups = self.group_by_type(artifacts)
        
        preview_info = {
            "total_artifacts": len(artifacts),
            "by_type": {},
            "potential_duplicates": {}
        }
        
        for type_id, type_artifacts in groups.items():
            existing = self.load_existing_knowledge(type_id)
            all_items = existing + [a.content for a in type_artifacts]
            
            # 检测潜在重复
            duplicates = []
            for i, artifact in enumerate(type_artifacts):
                result = self.deduplicator.check_duplicate(
                    artifact.content,
                    existing + [a.content for a in type_artifacts[:i]],
                    type_id
                )
                if result.is_duplicate:
                    duplicates.append({
                        "file": artifact.path.name,
                        "similarity": result.similarity_score,
                        "has_increment": result.has_increment
                    })
            
            preview_info["by_type"][type_id] = {
                "artifact_count": len(type_artifacts),
                "existing_count": len(existing)
            }
            
            if duplicates:
                preview_info["potential_duplicates"][type_id] = duplicates
        
        return preview_info


def main():
    """命令行入口"""
    import argparse
    
    parser = argparse.ArgumentParser(description="知识去重与精炼工具")
    parser.add_argument("--date", help="日期过滤，格式: YYYY/MM/DD")
    parser.add_argument("--time", help="时间过滤，格式: HH_MM")
    parser.add_argument("--dry-run", action="store_true", help="试运行，不保存")
    parser.add_argument("--preview", action="store_true", help="仅预览")
    
    args = parser.parse_args()
    
    refiner = KnowledgeRefiner()
    
    if args.preview:
        preview = refiner.preview(args.date, args.time)
        print(json.dumps(preview, ensure_ascii=False, indent=2))
    else:
        stats = refiner.run(args.date, args.time, args.dry_run)
        print(json.dumps(stats.to_dict(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()


