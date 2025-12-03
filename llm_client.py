import os
import json
from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional

def _load_env_file():
    env_path = Path('.env')
    if env_path.exists():
        try:
            for line in env_path.read_text(encoding='utf-8').splitlines():
                if not line or line.strip().startswith('#'):
                    continue
                if '=' in line:
                    k, v = line.split('=', 1)
                    k = k.strip()
                    v = v.strip()
                    if k and v and os.getenv(k) is None:
                        os.environ[k] = v
        except Exception:
            pass

def _get_llm_env() -> Tuple[Optional[str], Optional[str], Optional[str]]:
    _load_env_file()
    base = os.getenv('KB_BASE_URL')
    key = os.getenv('KB_API_KEY')
    model = os.getenv('KB_MODEL_ID')
    return base, key, model

def _build_system_prompt(type_id: str, schema_text: str) -> str:
    return (
        "You are a strict JSON extractor for knowledge artifacts. "
        "Produce ONLY a single JSON object that strictly conforms to the target type schema. "
        "No explanations, no comments, no extra fields. additionalProperties=false must hold. "
        f"Target type: {type_id}. Schema (reference):\n" + schema_text
    )

def _build_user_prompt(type_id: str, candidates: List[Dict[str, Any]], ctx: Dict[str, Any]) -> str:
    j = {
        "context": {
            "title": ctx.get("title"),
            "url": ctx.get("url"),
        },
        "type": type_id,
        "candidates": candidates,
        "requirements": {
            "output_only_json": True,
            "strict_fields": True,
            "id_generation": True,
        },
    }
    return json.dumps(j, ensure_ascii=False)

def _read_schema(schema_path: str) -> str:
    try:
        p = Path(schema_path)
        return p.read_text(encoding='utf-8')
    except Exception:
        return "{}"

def extract_structured(type_id: str, candidates: List[Dict[str, Any]], ctx: Dict[str, Any], schema_path: str) -> Tuple[Optional[Dict[str, Any]], Dict[str, Any]]:
    base, key, model = _get_llm_env()
    if not base or not key or not model:
        return None, {"error": "missing_llm_env", "need": ["KB_BASE_URL","KB_API_KEY","KB_MODEL_ID"]}
    schema_text = _read_schema(schema_path)
    try:
        import httpx
        url = base.rstrip('/') + '/chat/completions'
        headers = {
            'Authorization': f'Bearer {key}',
            'Content-Type': 'application/json',
        }
        body = {
            'model': model,
            'messages': [
                {'role': 'system', 'content': _build_system_prompt(type_id, schema_text)},
                {'role': 'user', 'content': _build_user_prompt(type_id, candidates, ctx)},
            ],
            'temperature': 0,
            'response_format': {'type': 'json_object'},
        }
        with httpx.Client(timeout=30.0) as client:
            resp = client.post(url, headers=headers, json=body)
            resp.raise_for_status()
            data = resp.json()
            content = (
                ((data.get('choices') or [{}])[0].get('message') or {}).get('content')
            )
            if not content:
                return None, {"error": "empty_content", "status": resp.status_code}
            try:
                obj = json.loads(content)
            except Exception as e:
                return None, {"error": "invalid_json", "detail": str(e), "raw": content[:2000]}
            return obj, {"provider": "siliconflow", "model": model, "tokens": data.get('usage')}
    except Exception as e:
        return None, {"error": "llm_request_failed", "detail": str(e)}