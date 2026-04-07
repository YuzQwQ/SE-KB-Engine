#!/usr/bin/env python3
"""
Text-centric image analyzer using a unified vision model.

Configuration:
- Edit `config/vision_model.json` to set provider, endpoint, api key, timeout.
- Or pass `image_analysis_options` into `crawl_and_parse(..., image_analysis_options=...)`.

Expected model output per image:
{
  "ocr": ["...", "..."],
  "description": "...",
  "dfd": {
    "entities": [{"id":"E1","name":"..."}],
    "processes": [{"id":"P1","name":"..."}],
    "data_stores": [{"id":"D1","name":"..."}],
    "flows": [{"from":"E1","to":"P1","label":"..."}]
  } | null
}
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx


DEFAULT_RESULT: Dict[str, Any] = {
    "ocr": [],
    "description": "",
    "dfd": None,
}


class VisionModel:
    """Base vision model interface. Implement `infer` in concrete classes."""

    def infer(self, image_input: str) -> Dict[str, Any]:
        return DEFAULT_RESULT.copy()


class VisionModelHTTP(VisionModel):
    """HTTP adapter for a remote unified vision model API.

    Options schema (from config or runtime):
    - endpoint: string, POST URL of your API
    - api_key: optional, if set use Bearer token
    - timeout: seconds (int)
    - request_schema: {url_field, base64_field, tasks_field}
    - response_schema: {ocr_field, description_field, dfd_field}
    - default_tasks: ["ocr", "description", "dfd"]
    """

    def __init__(self, options: Dict[str, Any]):
        self.endpoint: str = options.get("endpoint", "")
        self.api_key: str = options.get("api_key", "")
        self.timeout: int = int(options.get("timeout", 30))
        self.req: Dict[str, str] = options.get("request_schema", {})
        self.resp: Dict[str, str] = options.get("response_schema", {})
        default_tasks = options.get("default_tasks", ["ocr", "description", "dfd"])
        self.default_tasks = (
            list(default_tasks)
            if isinstance(default_tasks, list)
            else ["ocr", "description", "dfd"]
        )

    def infer(self, image_input: str) -> Dict[str, Any]:
        if not self.endpoint:
            return DEFAULT_RESULT.copy()

        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        payload: Dict[str, Any] = {}
        url_field = self.req.get("url_field", "image_url")
        b64_field = self.req.get("base64_field", "image_base64")
        tasks_field = self.req.get("tasks_field", "tasks")

        # Decide whether input is URL or base64 (data URI counts as base64)
        if image_input.startswith("http://") or image_input.startswith("https://"):
            payload[url_field] = image_input
            payload[b64_field] = None
        else:
            # Pass through base64/data URI without local file fetching
            payload[url_field] = None
            payload[b64_field] = image_input

        payload[tasks_field] = self.default_tasks

        try:
            with httpx.Client(timeout=self.timeout) as client:
                r = client.post(self.endpoint, headers=headers, json=payload)
                r.raise_for_status()
                data = r.json()
        except Exception:
            return DEFAULT_RESULT.copy()

        ocr_field = self.resp.get("ocr_field", "ocr")
        description_field = self.resp.get("description_field", "description")
        dfd_field = self.resp.get("dfd_field", "dfd")

        # Normalize output with safe fallbacks
        ocr = data.get(ocr_field) or []
        if isinstance(ocr, str):
            ocr = [ocr]
        if not isinstance(ocr, list):
            ocr = []

        description = data.get(description_field) or ""
        if not isinstance(description, str):
            description = ""

        dfd = data.get(dfd_field)
        if not isinstance(dfd, dict):
            dfd = None

        return {
            "ocr": ocr,
            "description": description,
            "dfd": dfd,
        }


class VisionModelSiliconFlow(VisionModel):
    """SiliconFlow OpenAI-compatible chat completions for unified vision analysis.

    Reads env or options:
    - base_url: e.g., https://api.siliconflow.cn/v1
    - api_key: VISUAL_MODEL_API_KEY
    - model: VISUAL_MODEL
    - timeout: seconds
    """

    def __init__(self, options: Dict[str, Any]):
        self.base_url: str = options.get("base_url", "")
        self.api_key: str = options.get("api_key", "")
        self.model: str = options.get("model", "")
        self.timeout: int = int(options.get("timeout", 60))

    def _chat_url(self) -> str:
        base = self.base_url.rstrip("/")
        return f"{base}/chat/completions"

    def infer(self, image_input: str) -> Dict[str, Any]:
        if not (self.base_url and self.api_key and self.model and image_input):
            return DEFAULT_RESULT.copy()

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }

        system_prompt = (
            "You are a unified vision analyzer. Extract OCR text, a concise semantic "
            "description, and recognize Data Flow Diagrams (DFD). Return ONLY a JSON object "
            "with keys: ocr (array of strings), description (string), dfd (object or null). "
            "If the image is not a DFD, set dfd to null."
        )

        user_instruction = (
            "Analyze this image and respond with JSON only. Keys: ocr[], description, dfd|null. "
            "For dfd include entities/processes/data_stores/flows; flows have from/to/label."
        )

        # Try multiple payload variants to maximize compatibility
        payload_variants = []
        # Variant A: OpenAI-style image_url
        payload_variants.append(
            {
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": user_instruction},
                            {"type": "image_url", "image_url": {"url": image_input}},
                        ],
                    },
                ]
            }
        )
        # Variant B: Qwen-style input_image
        payload_variants.append(
            {
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {
                        "role": "user",
                        "content": [
                            {"type": "input_text", "text": user_instruction},
                            {"type": "input_image", "image_url": image_input},
                        ],
                    },
                ]
            }
        )

        text: str = ""
        data: Dict[str, Any] = {}
        for variant in payload_variants:
            payload = {
                "model": self.model,
                "temperature": 0.2,
                "top_p": 1,
                "max_tokens": 2048,
                "stream": False,
            }
            payload.update(variant)
            try:
                with httpx.Client(timeout=self.timeout) as client:
                    r = client.post(self._chat_url(), headers=headers, json=payload)
                    r.raise_for_status()
                    data = r.json()
                # Parse text
                choices = data.get("choices") or []
                if choices:
                    msg = choices[0].get("message") or {}
                    content_val = msg.get("content")
                    if isinstance(content_val, str):
                        text = content_val
                    elif isinstance(content_val, list):
                        for seg in content_val:
                            if isinstance(seg, dict):
                                if seg.get("type") in ("text", "output_text") and isinstance(
                                    seg.get("text"), str
                                ):
                                    text = seg["text"]
                                    break
                                content_text = seg.get("content")
                                if isinstance(content_text, str):
                                    text = content_text
                                    break
                if text:
                    break
            except Exception:
                # try next variant
                text = ""

        # Try to extract JSON from text
        result = DEFAULT_RESULT.copy()
        if text:
            # strip fences
            cleaned = re.sub(r"^```json\n|\n```$", "", text.strip(), flags=re.MULTILINE)
            # find first JSON object braces if necessary
            if not cleaned.strip().startswith("{"):
                m = re.search(r"\{[\s\S]*\}", cleaned)
                cleaned = m.group(0) if m else cleaned
            try:
                parsed = json.loads(cleaned)
                ocr = parsed.get("ocr") or []
                if isinstance(ocr, str):
                    ocr = [ocr]
                if not isinstance(ocr, list):
                    ocr = []
                description = parsed.get("description") or ""
                if not isinstance(description, str):
                    description = ""
                dfd = parsed.get("dfd")
                if not isinstance(dfd, dict):
                    dfd = None
                result = {"ocr": ocr, "description": description, "dfd": dfd}
            except Exception:
                result = DEFAULT_RESULT.copy()

        return result


def load_vision_config() -> Optional[Dict[str, Any]]:
    cfg_path = Path("config/vision_model.json")
    if cfg_path.exists():
        try:
            return json.loads(cfg_path.read_text(encoding="utf-8"))
        except Exception:
            return None
    return None


def load_env_vision_config() -> Dict[str, Any]:
    """Load SiliconFlow vision config from environment variables if present."""
    # Try loading from local .env file if present (lightweight parser)
    dotenv_path = Path(".env")
    if dotenv_path.exists():
        try:
            for line in dotenv_path.read_text(encoding="utf-8").splitlines():
                s = line.strip()
                if not s or s.startswith("#"):
                    continue
                if "=" in s:
                    k, v = s.split("=", 1)
                    k = k.strip()
                    v = v.strip().strip('"').strip("'")
                    # Don't override existing env
                    if k and (k not in os.environ):
                        os.environ[k] = v
        except Exception:
            pass
    base_url = os.getenv("BASE_URL", "")
    # Fallbacks: allow OPENAI_API_KEY or SILICONFLOW_API_KEY if VISUAL_MODEL_API_KEY absent
    api_key = (
        os.getenv("VISUAL_MODEL_API_KEY")
        or os.getenv("OPENAI_API_KEY")
        or os.getenv("SILICONFLOW_API_KEY")
        or ""
    )
    model = os.getenv("VISUAL_MODEL", "")
    cfg: Dict[str, Any] = {}
    if base_url and api_key and model:
        cfg = {
            "provider": "siliconflow",
            "base_url": base_url,
            "api_key": api_key,
            "model": model,
        }
    return cfg


def build_vision_model(options: Optional[Dict[str, Any]]) -> VisionModel:
    # Merge config precedence: file < env < runtime options
    file_cfg = load_vision_config() or {}
    env_cfg = load_env_vision_config() or {}
    merged: Dict[str, Any] = {**file_cfg, **env_cfg, **(options or {})}

    provider = (merged.get("provider") or "").lower()
    if provider == "siliconflow":
        return VisionModelSiliconFlow(merged)
    if provider == "http":
        return VisionModelHTTP(merged)
    # Default stub if provider unknown
    return VisionModel()


def analyze_images(
    images: List[Dict[str, Any]], base_url: Optional[str], options: Optional[Dict[str, Any]] = None
) -> List[Dict[str, Any]]:
    """Analyze images with a unified vision model, returning text-only info.

    - Input image dicts may contain: src, abs_url, base64, alt, title
    - Output keeps only: alt, title, ocr, description, dfd
    """
    model = build_vision_model(options)

    results: List[Dict[str, Any]] = []
    for img in images or []:
        alt = img.get("alt") or ""
        title = img.get("title") or ""
        image_input = img.get("abs_url") or img.get("src") or img.get("base64") or ""

        if not image_input:
            vision = DEFAULT_RESULT.copy()
        else:
            vision = model.infer(image_input)

        results.append(
            {
                "alt": alt,
                "title": title,
                "ocr": vision.get("ocr", []),
                "description": vision.get("description", ""),
                "dfd": vision.get("dfd"),
            }
        )

    return results
