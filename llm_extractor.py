from typing import List, Dict, Any, Tuple
from llm_client import extract_structured
from pathlib import Path

def _schema_path_for(type_id: str) -> str:
    if type_id == 'dfd':
        return str(Path('se_kb/schema/dfd_schema.json'))
    return str(Path('config/universal_knowledge_template.json'))

def extract_concepts(candidates: List[Dict[str, Any]], ctx: Dict[str, Any]) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    art, trace = extract_structured('concepts', candidates, ctx, _schema_path_for('concepts'))
    return (art or {}), trace

def extract_rules(candidates: List[Dict[str, Any]], ctx: Dict[str, Any]) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    art, trace = extract_structured('rules', candidates, ctx, _schema_path_for('rules'))
    return (art or {}), trace

def extract_dfd_structure(candidates: List[Dict[str, Any]], ctx: Dict[str, Any]) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    art, trace = extract_structured('dfd', candidates, ctx, _schema_path_for('dfd'))
    return (art or {}), trace