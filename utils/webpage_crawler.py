"""Compatibility facade over the application's shared crawl policy."""
from __future__ import annotations

from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlparse
from uuid import uuid4
import hashlib

from bs4 import BeautifulSoup

from se_kb_app.artifacts.storage import atomic_write_bytes, atomic_write_json, safe_component
from se_kb_app.domain import FetchRequest
from se_kb_app.errors import ApplicationError, ErrorKind
from se_kb_app.jobs.context import checkpoint, current_cancellation, publication
from utils.html_cleaner import clean_and_structure, clean_html_content


class WebpageCrawler:
    def __init__(self, data_dir: str = "data", *, service=None):
        self.data_dir = Path(data_dir)
        self.raw_data_dir = self.data_dir / "raw"
        self.parsed_data_dir = self.data_dir / "parsed"
        self.raw_data_dir.mkdir(parents=True, exist_ok=True)
        self.parsed_data_dir.mkdir(parents=True, exist_ok=True)
        self._service = service

    def _runtime(self):
        if self._service is not None:
            return self._service
        from se_kb_app.crawling.runtime import default_crawl_service
        return default_crawl_service()

    def _acquire(self, request):
        checkpoint()
        try:
            outcome = self._runtime().run(request)
        except ApplicationError as error:
            if error.kind is ErrorKind.CANCELLATION:
                raise
            return {"url": request.url, "requested_url": request.url, "success": False,
                    "error": error.public_code, "source": "policy", "content": "",
                    "status_code": None, "encoding": None, "headers": {},
                    "timestamp": datetime.now().isoformat()}, None, None
        document = outcome.document
        reason = outcome.transitions[-1].reason if outcome.transitions else "fetch_failed"
        raw = {"url": document.url if document else request.url,
               "requested_url": request.url, "status_code": document.status_code if document else None,
               "headers": {}, "content": document.content if document else "",
               "encoding": document.encoding if document else None,
               "timestamp": datetime.now().isoformat(), "success": document is not None,
               "error": None if document else reason,
               "source": "playwright" if document and document.metadata.get("rendered") else "httpx"}
        if outcome.kind.value == "cancelled":
            checkpoint()
            raise ApplicationError(ErrorKind.CANCELLATION,
                                   "job_cancelled", "The job was cancelled.")
        return raw, document, outcome

    def fetch_webpage(self, url: str, timeout: int = 20, retry_times: int = 3) -> dict[str, Any]:
        from time import monotonic
        if not 1 <= retry_times <= 3 or timeout <= 0:
            raise ValueError("timeout must be positive; attempts must be between 1 and 3")
        request = FetchRequest(url, deadline=monotonic() + min(timeout, 60),
                               cancellation=current_cancellation.get(), maximum_attempts=retry_times)
        return self._acquire(request)[0]

    def parse_csdn_article(self, html_content: str, url: str) -> dict[str, Any]:
        """解析CSDN文章内容

        Args:
            html_content: HTML内容
            url: 文章URL

        Returns:
            解析后的文章数据
        """
        soup = BeautifulSoup(html_content, "html.parser")

        # 提取文章标题
        title = ""
        title_selectors = ["h1.title-article", ".article-title-box h1", "h1", ".title"]

        for selector in title_selectors:
            title_elem = soup.select_one(selector)
            if title_elem:
                title = title_elem.get_text().strip()
                break

        # 提取文章内容
        content = ""
        content_selectors = [
            "#content_views",
            ".article_content",
            ".blog-content-box",
            "article",
            ".content",
        ]

        for selector in content_selectors:
            content_elem = soup.select_one(selector)
            if content_elem:
                # 移除不需要的元素
                for unwanted in content_elem.select("script, style, .hljs-button"):
                    unwanted.decompose()
                # 获取原始文本内容
                raw_content = content_elem.get_text().strip()
                # 使用HTML清理器清理内容
                content = clean_html_content(raw_content)
                break

        # 提取作者信息
        author = ""
        author_selectors = [".follow-nickName", ".username", ".author-name", ".user-info .name"]

        for selector in author_selectors:
            author_elem = soup.select_one(selector)
            if author_elem:
                author = author_elem.get_text().strip()
                break

        # 提取发布时间
        publish_time = ""
        time_selectors = [
            ".time",
            ".publish-time",
            ".article-bar-top .time",
            ".blog-content-box .time",
        ]

        for selector in time_selectors:
            time_elem = soup.select_one(selector)
            if time_elem:
                publish_time = time_elem.get_text().strip()
                break

        # 提取标签
        tags = []
        tag_selectors = [".tags-box .tag-link", ".article-tags a", ".tag"]

        for selector in tag_selectors:
            tag_elems = soup.select(selector)
            if tag_elems:
                tags = [tag.get_text().strip() for tag in tag_elems]
                break

        return {
            "title": title,
            "content": content,
            "author": author,
            "publish_time": publish_time,
            "tags": tags,
            "url": url,
            "word_count": len(content),
            "parsed_at": datetime.now().isoformat(),
        }

    def save_data(self, data: dict[str, Any], filename_prefix: str, *, payload: bytes | None = None) -> dict:
        with publication():
            return self._save_data(data, filename_prefix, payload=payload)

    def _save_data(self, data: dict[str, Any], filename_prefix: str, *, payload: bytes | None = None) -> dict:
        checkpoint()
        collection_id = uuid4().hex
        prefix = safe_component(filename_prefix, maximum=100)
        raw_path = self.raw_data_dir / f"{prefix}_{collection_id}.json"
        parsed_path = self.parsed_data_dir / f"{prefix}_{collection_id}_parsed.json"
        body_path = self.raw_data_dir / f"{prefix}_{collection_id}.body"
        atomic_write_json(raw_path, data)
        checkpoint()
        if "parsed_data" in data:
            atomic_write_json(parsed_path, data["parsed_data"])
        if payload is not None:
            atomic_write_bytes(body_path, payload)
        checkpoint()
        manifest = self.data_dir / "crawl_snapshots" / f"{collection_id}.json"
        atomic_write_json(manifest, {"collection_id": collection_id,
            "requested_url": data.get("raw_data", {}).get("requested_url", ""),
            "final_url": data.get("raw_data", {}).get("url", ""),
            "raw_file": str(raw_path), "parsed_file": str(parsed_path) if "parsed_data" in data else None,
            "body_file": str(body_path) if payload is not None else None,
            "payload_sha256": hashlib.sha256(payload).hexdigest() if payload is not None else None,
            "cleaner_version": data.get("parsed_data", {}).get("cleaner_version")})
        return {"raw_file": str(raw_path), "parsed_file": str(parsed_path) if "parsed_data" in data else None,
                "body_file": str(body_path) if payload is not None else None, "manifest_file": str(manifest)}

    def crawl_and_parse(self, url: str, save_data: bool = True, image_analysis_options=None,
                        *, headers=None, cookies=None, automatic: bool = False, cancellation=None) -> dict:
        request = FetchRequest(url, save=save_data, cancellation=cancellation or current_cancellation.get(),
                               headers=headers or {}, cookies=cookies or {}, automatic=automatic)
        raw, document, outcome = self._acquire(request)
        if document is None:
            return raw
        checkpoint()
        if request.cancellation:
            request.cancellation.checkpoint()
        parsed = clean_and_structure(document.content, document.url)
        parsed.update(url=document.url, requested_url=url, parsed_at=datetime.now().isoformat(),
                      word_count=len(parsed.get("clean_text", "")), content=parsed.get("clean_text", ""))
        if (urlparse(document.url).hostname or "") == "csdn.net" or (urlparse(document.url).hostname or "").endswith(".csdn.net"):
            site = self.parse_csdn_article(document.content, document.url)
            parsed.update({key: site[key] for key in ("author", "publish_time", "tags")})
        if image_analysis_options is not None and parsed.get("images"):
            from utils.image_analyzer import analyze_images
            checkpoint()
            if request.cancellation:
                request.cancellation.checkpoint()
            parsed["images"] = analyze_images(parsed["images"], document.url, image_analysis_options)
        checkpoint()
        if request.cancellation:
            request.cancellation.checkpoint()
        result = {"raw_data": raw, "parsed_data": parsed, "success": True,
                  "metrics": {"attempts": [asdict(item) for item in outcome.attempts],
                              "elapsed_seconds": outcome.elapsed_seconds,
                              "fallback_used": bool(document.metadata.get("rendered")), **document.metadata}}
        if save_data:
            with publication(request.cancellation):
                result["file_paths"] = self.save_data(result,
                    f"{urlparse(document.url).hostname}_{parsed.get('title', 'untitled')}", payload=document.payload)
        return result

    def close(self) -> None:
        # Injected/shared service is owned by Application (or the process fallback).
        return None

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()
