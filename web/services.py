import os
import json
import hashlib
import logging
import threading
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional

from utils.webpage_crawler import WebpageCrawler
from extractors.pipeline import run_pipeline
from writers.artifacts_writer import ArtifactsWriter

ROOT_DIR = Path(__file__).resolve().parent.parent

logger = logging.getLogger(__name__)

knowledge_retriever = None
try:
    from vectorizer import VectorConfig, KnowledgeRetriever
    vector_config = VectorConfig()
    knowledge_retriever = KnowledgeRetriever(vector_config)
    logger.info("KnowledgeRetriever initialized successfully for Web App")
except Exception as e:
    logger.error(f"Failed to initialize KnowledgeRetriever: {e}")


class UrlIndex:
    def __init__(self):
        self.index_file = ROOT_DIR / "data" / "url_index.json"
        self.urls = {}
        self._load()
    
    def _load(self):
        if self.index_file.exists():
            try:
                self.urls = json.loads(self.index_file.read_text(encoding='utf-8'))
            except Exception:
                self.urls = {}
    
    def _save(self):
        self.index_file.parent.mkdir(parents=True, exist_ok=True)
        self.index_file.write_text(
            json.dumps(self.urls, ensure_ascii=False, indent=2),
            encoding='utf-8'
        )
    
    def _hash(self, url: str) -> str:
        normalized = url.rstrip('/').lower()
        return hashlib.md5(normalized.encode('utf-8')).hexdigest()[:12]
    
    def exists(self, url: str) -> bool:
        return self._hash(url) in self.urls
    
    def add(self, url: str, title: str = ""):
        url_hash = self._hash(url)
        self.urls[url_hash] = {
            "url": url,
            "title": title,
            "crawled_at": datetime.now().isoformat()
        }
        self._save()
    
    def get_stats(self) -> Dict[str, Any]:
        return {
            "total_urls": len(self.urls),
            "index_file": str(self.index_file)
        }
    
    def clear(self):
        self.urls = {}
        self._save()


url_index = UrlIndex()


class TaskManager:
    def __init__(self):
        self.current_task = None
        self.logs = []
        self.status = "idle"
        self.progress = 0
        self.results = []
        self.lock = threading.Lock()
    
    def log(self, message: str, level: str = "info"):
        with self.lock:
            entry = {
                "time": datetime.now().strftime("%H:%M:%S"),
                "level": level,
                "message": message
            }
            self.logs.append(entry)
            print(f"[{entry['time']}] [{level.upper()}] {message}")
    
    def set_status(self, status: str, progress: int = None):
        with self.lock:
            self.status = status
            if progress is not None:
                self.progress = progress
    
    def clear(self):
        with self.lock:
            self.logs = []
            self.results = []
            self.progress = 0
            self.status = "idle"
    
    def get_state(self):
        with self.lock:
            return {
                "status": self.status,
                "progress": self.progress,
                "logs": self.logs[-50:],
                "results": self.results
            }


task_manager = TaskManager()


def search_urls(query: str, limit: int = 10) -> List[str]:
    task_manager.log(f"🔍 搜索: {query}")
    
    api_key = os.getenv("SERPAPI_API_KEY")
    if not api_key:
        task_manager.log("❌ 未配置 SERPAPI_API_KEY", "error")
        return []
    
    try:
        import httpx
        
        params: Dict[str, str | int] = {
            "engine": "google",
            "q": query,
            "api_key": api_key,
            "num": limit,
            "hl": "zh-cn",
            "gl": "cn"
        }
        
        task_manager.log("🌐 调用 SerpAPI Google 搜索...")
        
        last_err = None
        data = None
        for _ in range(3):
            try:
                with httpx.Client(timeout=30.0) as client:
                    resp = client.get("https://serpapi.com/search.json", params=params)
                    resp.raise_for_status()
                    data = resp.json()
                break
            except Exception as e:
                last_err = e
                continue
        if data is None:
            if last_err is not None:
                raise last_err
            raise RuntimeError("SerpAPI request failed without exception")
        
        urls = []
        for item in data.get("organic_results", [])[:limit]:
            link = item.get("link")
            if link:
                urls.append(link)
                task_manager.log(f"  📎 {item.get('title', '')[:40]}")
        
        task_manager.log(f"✅ 找到 {len(urls)} 个结果")
        return urls
        
    except Exception as e:
        task_manager.log(f"❌ 搜索失败: {e}", "error")
        return []


def crawl_url(url: str, crawler: WebpageCrawler) -> Optional[Dict[str, Any]]:
    task_manager.log(f"🌐 采取: {url[:60]}...")
    
    try:
        result = crawler.crawl_and_parse(url, save_data=True)
        if result.get('success'):
            title = result.get('parsed_data', {}).get('title', '未知')
            task_manager.log(f"✅ 成功: {title[:40]}")
            return result
        else:
            task_manager.log(f"⚠️ 采取失败: {url[:40]}", "warning")
            return None
    except Exception as e:
        task_manager.log(f"❌ 采取错误: {str(e)[:50]}", "error")
        return None


def extract_knowledge(parsed_path: str, force_types: List[str] = None) -> Dict[str, Any]:
    task_manager.log("🧠 抽取知识...")
    
    try:
        parsed_data = json.loads(Path(parsed_path).read_text(encoding='utf-8'))
        title = parsed_data.get('title', '未知')
        url = parsed_data.get('source_url') or parsed_data.get('url', '')
        
        result = run_pipeline(parsed_data, force_types)
        
        if result.artifacts:
            types = list(result.artifacts.keys())
            task_manager.log(f"✅ 抽取成功: {types}")
            
            writer = ArtifactsWriter()
            from urllib.parse import urlparse
            domain = urlparse(url).netloc or "unknown"
            
            for type_id, artifact in result.artifacts.items():
                writer.write(
                    domain, title, parsed_data,
                    parsed_data.get('clean_text', ''),
                    type_id, artifact, result.trace,
                    {"source_url": url, "title": title, "type": type_id},
                    {"tokens": result.total_tokens}, []
                )
            
            return {
                "success": True,
                "title": title,
                "types": types,
                "tokens": result.total_tokens
            }
        else:
            task_manager.log("⚠️ 未抽取到知识", "warning")
            return {"success": False, "title": title, "error": "无知识抽取"}
    
    except Exception as e:
        task_manager.log(f"❌ 抽取错误: {str(e)[:50]}", "error")
        return {"success": False, "error": str(e)}


def run_manual_crawl_task(url: str, force_types: Optional[List[str]] = None, extract: bool = True):
    task_manager.clear()
    task_manager.set_status("running", 0)
    
    try:
        task_manager.log("=" * 40)
        task_manager.log(f"📋 手动采取: {url}")
        task_manager.log(f"📊 URL 索引: 已有 {len(url_index.urls)} 个 URL")
        task_manager.log("=" * 40)
        task_manager.set_status("running", 15)
        
        if url_index.exists(url):
            task_manager.log("⚠️ 该 URL 已采取过，仍将重新爬取", "warning")
        
        crawler = WebpageCrawler()
        result = crawl_url(url, crawler)
        
        if not result or not result.get('file_paths', {}).get('parsed_file'):
            task_manager.log("❌ 无可用的采取结果", "error")
            task_manager.set_status("error", 100)
            return
        
        parsed_path = result['file_paths']['parsed_file']
        title = result.get('parsed_data', {}).get('title', '')
        url_index.add(url, title)
        
        if not extract:
            task_manager.log("✅ 采取完成，已跳过抽取")
            task_manager.set_status("completed", 100)
            return
        
        task_manager.log("🧠 开始知识抽取")
        task_manager.set_status("running", 70)
        
        extract_result = extract_knowledge(parsed_path, force_types)
        if extract_result.get('success'):
            task_manager.results.append(extract_result)
            task_manager.log("🎉 任务完成！")
            task_manager.set_status("completed", 100)
        else:
            task_manager.log("⚠️ 抽取未产生结果", "warning")
            task_manager.set_status("completed", 100)
    
    except Exception as e:
        task_manager.log(f"❌ 任务失败: {str(e)}", "error")
        task_manager.set_status("error", 100)


def run_pipeline_task(query: str, limit: int, force_types: List[str]):
    task_manager.clear()
    task_manager.set_status("running", 0)
    
    try:
        task_manager.log("=" * 40)
        task_manager.log(f"📋 开始任务: {query}")
        task_manager.log(f"📊 URL 索引: 已有 {len(url_index.urls)} 个 URL")
        task_manager.log("=" * 40)
        task_manager.set_status("running", 10)
        
        urls = search_urls(query, limit)
        if not urls:
            task_manager.log("❌ 未找到任何结果", "error")
            task_manager.set_status("error", 100)
            return
        
        new_urls = []
        skipped_urls = []
        for url in urls:
            if url_index.exists(url):
                skipped_urls.append(url)
            else:
                new_urls.append(url)
        
        if skipped_urls:
            task_manager.log(f"⏭️ 跳过 {len(skipped_urls)} 个已采取的 URL")
        
        if not new_urls:
            task_manager.log("✅ 所有 URL 已采取过，无需重复处理")
            task_manager.set_status("completed", 100)
            return
        
        task_manager.set_status("running", 20)
        
        task_manager.log("-" * 40)
        task_manager.log(f"🌐 开始采取 {len(new_urls)} 个新网页")
        task_manager.log("-" * 40)
        
        crawler = WebpageCrawler()
        parsed_files = []
        
        for i, url in enumerate(new_urls):
            progress = 20 + int(50 * (i + 1) / len(new_urls))
            task_manager.set_status("running", progress)
            
            result = crawl_url(url, crawler)
            if result and result.get('file_paths', {}).get('parsed_file'):
                parsed_files.append(result['file_paths']['parsed_file'])
                title = result.get('parsed_data', {}).get('title', '')
                url_index.add(url, title)
        
        task_manager.log(f"✅ 成功采取 {len(parsed_files)}/{len(new_urls)} 个网页")
        
        if not parsed_files:
            task_manager.log("❌ 无可用的采取结果", "error")
            task_manager.set_status("error", 100)
            return
        
        task_manager.log("-" * 40)
        task_manager.log("🧠 开始知识抽取")
        task_manager.log("-" * 40)
        task_manager.set_status("running", 75)
        
        success_count = 0
        for i, parsed_path in enumerate(parsed_files):
            progress = 75 + int(20 * (i + 1) / len(parsed_files))
            task_manager.set_status("running", progress)
            
            result = extract_knowledge(parsed_path, force_types)
            if result.get('success'):
                success_count += 1
                task_manager.results.append(result)
        
        task_manager.log("=" * 40)
        task_manager.log(f"🎉 任务完成！成功抽取 {success_count}/{len(parsed_files)} 个")
        task_manager.log("=" * 40)
        task_manager.set_status("completed", 100)
    
    except Exception as e:
        task_manager.log(f"❌ 任务失败: {str(e)}", "error")
        task_manager.set_status("error", 100)


class RefineTaskManager:
    def __init__(self):
        self.logs = []
        self.status = "idle"
        self.progress = 0
        self.stats = {}
        self.lock = threading.Lock()
    
    def log(self, message: str):
        with self.lock:
            entry = {
                "time": datetime.now().strftime("%H:%M:%S"),
                "message": message
            }
            self.logs.append(entry)
            print(f"[REFINE] [{entry['time']}] {message}")
    
    def set_status(self, status: str, progress: int = None):
        with self.lock:
            self.status = status
            if progress is not None:
                self.progress = progress
    
    def clear(self):
        with self.lock:
            self.logs = []
            self.stats = {}
            self.progress = 0
            self.status = "idle"
    
    def get_state(self):
        with self.lock:
            return {
                "status": self.status,
                "progress": self.progress,
                "logs": self.logs[-100:],
                "stats": self.stats
            }


refine_manager = RefineTaskManager()


def run_refine_task(date_filter: str = None, time_filter: str = None, dry_run: bool = False):
    refine_manager.clear()
    refine_manager.set_status("running", 0)
    
    try:
        from refiner import KnowledgeRefiner
        
        refiner = KnowledgeRefiner(log_callback=refine_manager.log)
        stats = refiner.run(date_filter, time_filter, dry_run)
        
        refine_manager.stats = stats.to_dict()
        refine_manager.set_status("completed", 100)
        
    except Exception as e:
        refine_manager.log(f"❌ 精炼失败: {str(e)}")
        refine_manager.set_status("error", 100)
