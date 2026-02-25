"""
Two-Stage Extraction Pipeline - 两阶段抽取主流程
Stage 1: Type Router (轻量模型判断类型)
Stage 2: Specialized Extractors (专用模型结构化抽取)
"""

import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List
from dataclasses import dataclass

from .type_router import TypeRouter
from .specialized_extractors import get_extractor
from .type_registry import get_type_registry
from validators.semantic_stage3 import Stage3Validator


@dataclass
class PipelineResult:
    """流水线执行结果"""
    source_url: str
    title: str
    routed_types: List[str]              # Stage 1 识别的类型
    extraction_results: Dict[str, Any]   # Stage 2 各类型抽取结果
    artifacts: Dict[str, Dict]           # 成功的 artifact
    errors: Dict[str, str]               # 失败的错误信息
    stage3_results: Dict[str, Any]       # Stage 3 校验结果
    trace: Dict[str, Any]                # 完整追踪信息
    total_tokens: int                    # 总 token 消耗
    
    def summary(self) -> str:
        """生成摘要"""
        success = list(self.artifacts.keys())
        failed = list(self.errors.keys())
        return (
            f"Types: {self.routed_types} | "
            f"Success: {success} | "
            f"Failed: {failed} | "
            f"Tokens: {self.total_tokens}"
        )


class ExtractionPipeline:
    """两阶段抽取流水线"""
    
    def __init__(self, skip_routing: bool = False, force_types: List[str] = None):
        """
        Args:
            skip_routing: 是否跳过路由阶段（直接使用 force_types）
            force_types: 强制指定的类型列表
        """
        self.router = TypeRouter()
        self.registry = get_type_registry()
        self.stage3 = Stage3Validator()
        self.skip_routing = skip_routing
        self.force_types = force_types or []
    
    def _prepare_content(self, parsed_data: Dict[str, Any]) -> str:
        """准备用于抽取的内容"""
        # 优先使用结构化内容
        sections = parsed_data.get('sections') or parsed_data.get('structured_json') or []
        
        if sections:
            parts = []
            for sec in sections:
                heading = sec.get('heading', '')
                text = sec.get('text', '')
                lists = sec.get('lists', [])
                
                if heading:
                    parts.append(f"## {heading}\n")
                if text:
                    parts.append(text)
                if lists:
                    parts.append("\n".join(f"- {item}" for item in lists))
                parts.append("")
            
            return "\n".join(parts)
        
        # 回退到 clean_text
        return parsed_data.get('clean_text') or parsed_data.get('markdown') or ''
    
    def run(self, parsed_data: Dict[str, Any]) -> PipelineResult:
        """
        执行两阶段抽取流水线
        
        Args:
            parsed_data: parsed.json 数据
        
        Returns:
            PipelineResult
        """
        title = parsed_data.get('title', '未命名')
        url = parsed_data.get('source_url') or parsed_data.get('url', '')
        
        trace = {
            "pipeline_start": datetime.now().isoformat(),
            "title": title,
            "url": url,
        }
        total_tokens = 0
        
        # ========== Stage 1: Type Routing ==========
        if self.skip_routing and self.force_types:
            routed_types = self.force_types
            trace["stage1"] = {
                "skipped": True,
                "force_types": self.force_types,
            }
        else:
            routing_result, routing_trace = self.router.route(parsed_data)
            routed_types = routing_result.types
            total_tokens += routing_result.tokens_used
            
            trace["stage1"] = {
                "types": routed_types,
                "confidences": routing_result.confidences,
                "reasoning": routing_result.reasoning,
                "tokens": routing_result.tokens_used,
                **routing_trace,
            }
        
        if not routed_types:
            return PipelineResult(
                source_url=url,
                title=title,
                routed_types=[],
                extraction_results={},
                artifacts={},
                errors={"routing": "未识别到任何知识类型"},
                stage3_results={},
                trace=trace,
                total_tokens=total_tokens,
            )
        
        # ========== Stage 2: Specialized Extraction ==========
        content = self._prepare_content(parsed_data)
        ctx = {"title": title, "url": url}
        
        extraction_results = {}
        artifacts = {}
        errors = {}
        stage2_trace = {}
        stage3_results = {}
        
        for type_id in routed_types:
            extractor = get_extractor(type_id)
            if not extractor:
                errors[type_id] = f"无可用的抽取器: {type_id}"
                continue
            
            result, ext_trace = extractor.extract(content, ctx)
            total_tokens += result.tokens_used
            
            extraction_results[type_id] = {
                "success": result.success,
                "tokens": result.tokens_used,
                "error": result.error,
            }
            stage2_trace[type_id] = ext_trace
            
            if result.success and result.artifact:
                artifacts[type_id] = result.artifact
            elif result.error:
                errors[type_id] = result.error
        
        trace["stage2"] = stage2_trace
        for type_id in list(artifacts.keys()):
            artifact = artifacts[type_id]
            validation = self.stage3.validate(artifact, content, type_id, title, url)
            stage3_results[type_id] = validation
            extraction_results[type_id]["stage3_passed"] = validation["passed"]
            if not validation["passed"]:
                errors[type_id] = validation.get("error", "stage3_failed")
                artifacts.pop(type_id, None)
        
        trace["stage3"] = stage3_results
        trace["pipeline_end"] = datetime.now().isoformat()
        trace["total_tokens"] = total_tokens
        
        return PipelineResult(
            source_url=url,
            title=title,
            routed_types=routed_types,
            extraction_results=extraction_results,
            artifacts=artifacts,
            errors=errors,
            stage3_results=stage3_results,
            trace=trace,
            total_tokens=total_tokens,
        )


def run_pipeline(parsed_data: Dict[str, Any], 
                 force_types: List[str] = None) -> PipelineResult:
    """
    便捷函数：运行两阶段抽取流水线
    
    Args:
        parsed_data: parsed.json 数据
        force_types: 可选，强制指定类型（跳过路由）
    
    Returns:
        PipelineResult
    """
    pipeline = ExtractionPipeline(
        skip_routing=bool(force_types),
        force_types=force_types
    )
    return pipeline.run(parsed_data)


def run_pipeline_from_file(file_path: str, 
                           force_types: List[str] = None) -> PipelineResult:
    """
    便捷函数：从文件运行流水线
    
    Args:
        file_path: parsed.json 文件路径
        force_types: 可选，强制指定类型
    
    Returns:
        PipelineResult
    """
    parsed_data = json.loads(Path(file_path).read_text(encoding='utf-8'))
    return run_pipeline(parsed_data, force_types)

