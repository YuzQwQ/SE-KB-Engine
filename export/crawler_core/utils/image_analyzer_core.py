from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional

import httpx


DEFAULT_RESULT = {"ocr": [], "description": "", "dfd": None}


class VisionModel:
    def infer(self, image_input: str) -> Dict[str, Any]:
        return DEFAULT_RESULT.copy()


class VisionModelHTTP(VisionModel):
    def __init__(self, options: Dict[str, Any]):
        self.endpoint: str = options.get("endpoint", "")
        self.api_key: str = options.get("api_key", "")
        self.timeout: int = int(options.get("timeout", 30))
        self.req: Dict[str, str] = options.get("request_schema", {})
        self.resp: Dict[str, str] = options.get("response_schema", {})
        self.default_tasks: List[str] = options.get("default_tasks", ["ocr", "description", "dfd"])  # type: ignore

    def infer(self, image_input: str) -> Dict[str, Any]:
        if not (self.endpoint and image_input):
            return DEFAULT_RESULT.copy()
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        url_field = self.req.get("url_field", "image_url")
        b64_field = self.req.get("base64_field", "image_base64")
        tasks_field = self.req.get("tasks_field", "tasks")
        payload: Dict[str, Any] = {tasks_field: self.default_tasks}
        if image_input.startswith("http://") or image_input.startswith("https://"):
            payload[url_field] = image_input
            payload[b64_field] = None
        else:
            payload[url_field] = None
            payload[b64_field] = image_input
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
        return {"ocr": ocr, "description": description, "dfd": dfd}


class VisionModelSiliconFlow(VisionModel):
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
        headers = {"Content-Type": "application/json", "Authorization": f"Bearer {self.api_key}"}
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
        payload = {
            "model": self.model,
            "temperature": 0.2,
            "top_p": 1,
            "max_tokens": 1024,
            "stream": False,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": [
                    {"type": "text", "text": user_instruction},
                    {"type": "image_url", "image_url": {"url": image_input}},
                ]},
            ],
        }
        text: str = ""
        try:
            with httpx.Client(timeout=self.timeout) as client:
                r = client.post(self._chat_url(), headers=headers, json=payload)
                r.raise_for_status()
                data = r.json()
            choices = data.get("choices") or []
            if choices:
                msg = choices[0].get("message") or {}
                content_val = msg.get("content")
                if isinstance(content_val, str):
                    text = content_val
                elif isinstance(content_val, list):
                    for seg in content_val:
                        if isinstance(seg, dict) and seg.get("type") in ("text", "output_text") and isinstance(seg.get("text"), str):
                            text = seg["text"]
                            break
        except Exception:
            return DEFAULT_RESULT.copy()

        result = DEFAULT_RESULT.copy()
        if text:
            cleaned = re.sub(r"^```json\n|\n```$", "", text.strip(), flags=re.MULTILINE)
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


def build_vision_model(options: Optional[Dict[str, Any]]) -> VisionModel:
    opts = options or {}
    provider = (opts.get("provider") or "").lower()
    if provider == "http":
        return VisionModelHTTP(opts)
    if provider == "siliconflow":
        return VisionModelSiliconFlow(opts)
    return VisionModel()


def analyze_images(images: List[Dict[str, Any]], base_url: Optional[str], options: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    model = build_vision_model(options)
    results: List[Dict[str, Any]] = []
    for img in images or []:
        alt = img.get("alt") or ""
        title = img.get("title") or ""
        image_input = img.get("abs_url") or img.get("src") or img.get("base64") or ""
        vision = model.infer(image_input) if image_input else DEFAULT_RESULT.copy()
        results.append({
            "alt": alt,
            "title": title,
            "ocr": vision.get("ocr", []),
            "description": vision.get("description", ""),
            "dfd": vision.get("dfd"),
        })
    return results