import os
import json
import re
from pathlib import Path
from typing import Dict, Any, Optional
import httpx

from refiner.embedder import SemanticEmbedder


class SemanticJudge:
    def __init__(self):
        self._load_env()
        self.base_url = os.getenv("JUDGE_BASE_URL", "").rstrip("/")
        self.api_key = os.getenv("JUDGE_API_KEY", "")
        self.model_id = os.getenv("JUDGE_MODEL_ID", "")
        self.timeout = float(os.getenv("JUDGE_TIMEOUT", "60"))

    def _load_env(self):
        env_path = Path(".env")
        if env_path.exists():
            try:
                for line in env_path.read_text(encoding="utf-8").splitlines():
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    if "=" in line:
                        k, v = line.split("=", 1)
                        k, v = k.strip(), v.strip()
                        if k and v and os.getenv(k) is None:
                            os.environ[k] = v
            except Exception:
                pass

    def is_available(self) -> bool:
        return bool(self.base_url and self.api_key and self.model_id)

    def _extract_json(self, text: str) -> Optional[Dict[str, Any]]:
        try:
            return json.loads(text)
        except Exception:
            pass
        match = re.search(r"\{[\s\S]*\}", text)
        if match:
            try:
                return json.loads(match.group(0))
            except Exception:
                return None
        return None

    def judge(self, source_text: str, artifact_text: str, type_id: str, title: str, url: str) -> Dict[str, Any]:
        if not self.is_available():
            return {"available": False, "passed": True, "score": None, "reason": "judge_unavailable"}

        source_snippet = source_text[:2000]
        artifact_snippet = artifact_text[:2000]

        system_prompt = (
            "You are a strict semantic judge. Determine whether the extracted knowledge is consistent "
            "with the source content. Return JSON only with fields: passed (bool), score (0-1), reason (string)."
        )
        user_prompt = (
            f"Title: {title}\nURL: {url}\nType: {type_id}\n\n"
            f"[Source]\n{source_snippet}\n\n"
            f"[Extracted]\n{artifact_snippet}\n\n"
            "Judge consistency and return JSON."
        )

        payload = {
            "model": self.model_id,
            "temperature": 0,
            "max_tokens": 256,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        }

        headers = {"Content-Type": "application/json", "Authorization": f"Bearer {self.api_key}"}

        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.post(f"{self.base_url}/chat/completions", headers=headers, json=payload)
                response.raise_for_status()
                data = response.json()
            content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
            parsed = self._extract_json(content) or {}
            passed = bool(parsed.get("passed", False))
            score = parsed.get("score")
            reason = parsed.get("reason", "") if isinstance(parsed.get("reason", ""), str) else ""
            return {"available": True, "passed": passed, "score": score, "reason": reason}
        except Exception as e:
            return {"available": True, "passed": False, "score": None, "reason": f"judge_error: {e}"}


class Stage3Validator:
    def __init__(self):
        self.embedder = SemanticEmbedder()
        self.embedding_threshold = float(os.getenv("SOURCE_EMBEDDING_MIN_SCORE", "0.35"))
        self.judge = SemanticJudge()

    def _embedding_check(self, source_text: str, artifact_text: str) -> Dict[str, Any]:
        if not self.embedder.is_available():
            return {"available": False, "passed": True, "score": None, "error": "embedding_unavailable"}
        if not source_text or not artifact_text:
            return {"available": True, "passed": True, "score": None, "error": "embedding_skipped"}
        vec_source = self.embedder.get_embedding(source_text)
        vec_artifact = self.embedder.get_embedding(artifact_text)
        if vec_source is None or vec_artifact is None:
            return {"available": True, "passed": False, "score": None, "error": "embedding_failed"}
        score = self.embedder.cosine_similarity(vec_source, vec_artifact)
        return {
            "available": True,
            "passed": score >= self.embedding_threshold,
            "score": score,
            "error": "" if score >= self.embedding_threshold else "embedding_below_threshold",
        }

    def validate(self, artifact: Dict[str, Any], source_text: str, type_id: str, title: str, url: str) -> Dict[str, Any]:
        artifact_text = self.embedder.extract_text_for_embedding(artifact)
        embedding_result = self._embedding_check(source_text, artifact_text)
        judge_result = self.judge.judge(source_text, artifact_text, type_id, title, url)

        passed = True
        error = ""
        if embedding_result.get("available") and not embedding_result.get("passed"):
            passed = False
            error = embedding_result.get("error", "embedding_failed")
        if judge_result.get("available") and not judge_result.get("passed"):
            passed = False
            error = judge_result.get("reason", "judge_failed") or error

        return {
            "passed": passed,
            "embedding": embedding_result,
            "judge": judge_result,
            "error": error,
        }
