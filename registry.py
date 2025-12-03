from pathlib import Path
from adapters.dfd_adapter import DFDAdapter
from adapters.concepts_adapter import ConceptsAdapter
from adapters.rules_adapter import RulesAdapter
from llm_extractor import extract_dfd_structure, extract_concepts, extract_rules
from validators.jsonschema_validator import make_validator

def _namer_default(name: str) -> str:
    import re
    n = (name or "").strip()
    n = re.sub(r"\s+", " ", n)
    return n[:64] if len(n)>64 else n

def _normalize_default(artifact: dict, namer) -> dict:
    if isinstance(artifact, dict):
        for k,v in list(artifact.items()):
            if isinstance(v, str):
                artifact[k] = namer(v)
            elif isinstance(v, dict):
                artifact[k] = _normalize_default(v, namer)
            elif isinstance(v, list):
                artifact[k] = [_normalize_default(i, namer) if isinstance(i, dict) else (namer(i) if isinstance(i, str) else i) for i in v]
    return artifact

def get_registry() -> dict:
    base = Path("se_kb/schema")
    return {
        "dfd": {
            "schema_path": str(base / "dfd_schema.json"),
            "builder": DFDAdapter,
            "validator": make_validator(),
            "namer": _namer_default,
            "normalizer": _normalize_default,
            "llm_extractor": extract_dfd_structure,
        },
        "concepts": {
            "schema_path": str(Path("config/universal_knowledge_template.json")),
            "builder": ConceptsAdapter,
            "validator": make_validator(),
            "namer": _namer_default,
            "normalizer": _normalize_default,
            "llm_extractor": extract_concepts,
        },
        "rules": {
            "schema_path": str(Path("config/universal_knowledge_template.json")),
            "builder": RulesAdapter,
            "validator": make_validator(),
            "namer": _namer_default,
            "normalizer": _normalize_default,
            "llm_extractor": extract_rules,
        },
    }