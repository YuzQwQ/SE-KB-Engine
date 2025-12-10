"""
Registry - 知识类型注册表
支持 Legacy 和 Enhanced 两种 adapter 模式
"""

import os
from pathlib import Path


def _load_env_file():
    """加载 .env 文件到环境变量"""
    env_path = Path('.env')
    if env_path.exists():
        try:
            for line in env_path.read_text(encoding='utf-8').splitlines():
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                if '=' in line:
                    k, v = line.split('=', 1)
                    k, v = k.strip(), v.strip()
                    if k and v and os.getenv(k) is None:
                        os.environ[k] = v
        except Exception:
            pass


# 在导入前加载环境变量
_load_env_file()

# Legacy adapters (基于关键词规则)
from adapters.dfd_adapter import DFDAdapter
from adapters.concepts_adapter import ConceptsAdapter
from adapters.rules_adapter import RulesAdapter

# Enhanced adapters (基于 LLM Preselector)
from adapters.enhanced_adapters import (
    EnhancedDFDAdapter,
    EnhancedConceptsAdapter,
    EnhancedRulesAdapter,
)

from llm_extractor import extract_dfd_structure, extract_concepts, extract_rules
from validators.jsonschema_validator import make_validator


def _namer_default(name: str) -> str:
    """默认命名规范化"""
    import re
    n = (name or "").strip()
    n = re.sub(r"\s+", " ", n)
    return n[:64] if len(n) > 64 else n


def _normalize_default(artifact: dict, namer) -> dict:
    """默认规范化处理"""
    if isinstance(artifact, dict):
        for k, v in list(artifact.items()):
            if isinstance(v, str):
                artifact[k] = namer(v)
            elif isinstance(v, dict):
                artifact[k] = _normalize_default(v, namer)
            elif isinstance(v, list):
                artifact[k] = [
                    _normalize_default(i, namer) if isinstance(i, dict) 
                    else (namer(i) if isinstance(i, str) else i) 
                    for i in v
                ]
    return artifact


def _use_enhanced_adapters() -> bool:
    """
    检查是否使用增强版 adapter
    通过环境变量 USE_ENHANCED_ADAPTERS 控制
    默认：如果配置了 FILTER_BASE_URL 则启用
    """
    # 显式设置
    explicit = os.getenv('USE_ENHANCED_ADAPTERS', '').lower()
    if explicit in ('true', '1', 'yes', 'on'):
        return True
    if explicit in ('false', '0', 'no', 'off'):
        return False
    
    # 默认：检查是否配置了 preselector 所需的环境变量
    filter_url = os.getenv('FILTER_BASE_URL', '')
    filter_key = os.getenv('FILTER_API_KEY', '')
    
    # 调试输出
    if os.getenv('DEBUG_REGISTRY'):
        print(f"[Registry Debug] FILTER_BASE_URL: {'configured' if filter_url else 'NOT SET'}")
        print(f"[Registry Debug] FILTER_API_KEY: {'configured' if filter_key else 'NOT SET'}")
    
    return bool(filter_url and filter_key)


def get_registry() -> dict:
    """
    获取知识类型注册表
    
    根据配置自动选择使用 Legacy 或 Enhanced adapters
    """
    use_enhanced = _use_enhanced_adapters()
    base = Path("se_kb/schema")
    
    if use_enhanced:
        # 使用增强版 adapter（基于 LLM Preselector）
        return {
            "dfd": {
                "schema_path": str(base / "dfd_schema.json"),
                "builder": EnhancedDFDAdapter,
                "validator": make_validator(),
                "namer": _namer_default,
                "normalizer": _normalize_default,
                "llm_extractor": extract_dfd_structure,
                "mode": "enhanced",
            },
            "concepts": {
                "schema_path": str(Path("config/universal_knowledge_template.json")),
                "builder": EnhancedConceptsAdapter,
                "validator": make_validator(),
                "namer": _namer_default,
                "normalizer": _normalize_default,
                "llm_extractor": extract_concepts,
                "mode": "enhanced",
            },
            "rules": {
                "schema_path": str(Path("config/universal_knowledge_template.json")),
                "builder": EnhancedRulesAdapter,
                "validator": make_validator(),
                "namer": _namer_default,
                "normalizer": _normalize_default,
                "llm_extractor": extract_rules,
                "mode": "enhanced",
            },
        }
    else:
        # 使用 Legacy adapter（基于关键词规则）
        return {
            "dfd": {
                "schema_path": str(base / "dfd_schema.json"),
                "builder": DFDAdapter,
                "validator": make_validator(),
                "namer": _namer_default,
                "normalizer": _normalize_default,
                "llm_extractor": extract_dfd_structure,
                "mode": "legacy",
            },
            "concepts": {
                "schema_path": str(Path("config/universal_knowledge_template.json")),
                "builder": ConceptsAdapter,
                "validator": make_validator(),
                "namer": _namer_default,
                "normalizer": _normalize_default,
                "llm_extractor": extract_concepts,
                "mode": "legacy",
            },
            "rules": {
                "schema_path": str(Path("config/universal_knowledge_template.json")),
                "builder": RulesAdapter,
                "validator": make_validator(),
                "namer": _namer_default,
                "normalizer": _normalize_default,
                "llm_extractor": extract_rules,
                "mode": "legacy",
            },
        }


def get_registry_mode() -> str:
    """获取当前使用的 adapter 模式"""
    return "enhanced" if _use_enhanced_adapters() else "legacy"
