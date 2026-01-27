"""
知识库构建系统 - Web 界面
简洁的前端，用于搜索、爬取、抽取知识
"""

import os
import sys
import json
import asyncio
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any
from dataclasses import dataclass, asdict

# 添加项目根目录到路径
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from flask import Flask, render_template, request, jsonify, Response
from flask_cors import CORS
import queue
import threading

# 加载环境变量
def load_env():
    env_path = ROOT_DIR / '.env'
    if env_path.exists():
        for line in env_path.read_text(encoding='utf-8').splitlines():
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            if '=' in line:
                k, v = line.split('=', 1)
                k, v = k.strip(), v.strip()
                if k and v and os.getenv(k) is None:
                    os.environ[k] = v

load_env()

# 导入项目模块
from utils.webpage_crawler import WebpageCrawler
from extractors.pipeline import run_pipeline
from writers.artifacts_writer import ArtifactsWriter
import hashlib
import logging

# 初始化日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__, template_folder='templates', static_folder='static')
CORS(app)

# ============================================================
# 初始化知识检索器 (Semantic Search)
# ============================================================
knowledge_retriever = None
try:
    # 导入 vectorizer 模块 (确保 server.py 中使用的模块这里也能用)
    from vectorizer import VectorConfig, KnowledgeRetriever, QueryIntent
    
    vector_config = VectorConfig()
    knowledge_retriever = KnowledgeRetriever(vector_config)
    logger.info("KnowledgeRetriever initialized successfully for Web App")
except Exception as e:
    logger.error(f"Failed to initialize KnowledgeRetriever: {e}")
    # 不阻断应用启动，但在使用相关功能时需处理 None

# ============================================================
# URL 去重索引
# ============================================================

class UrlIndex:
    """URL 去重索引管理器"""
    
    def __init__(self):
        self.index_file = ROOT_DIR / "data" / "url_index.json"
        self.urls = {}  # url_hash -> {url, crawled_at, title}
        self._load()
    
    def _load(self):
        """从文件加载索引"""
        if self.index_file.exists():
            try:
                self.urls = json.loads(self.index_file.read_text(encoding='utf-8'))
            except Exception:
                self.urls = {}
    
    def _save(self):
        """保存索引到文件"""
        self.index_file.parent.mkdir(parents=True, exist_ok=True)
        self.index_file.write_text(
            json.dumps(self.urls, ensure_ascii=False, indent=2),
            encoding='utf-8'
        )
    
    def _hash(self, url: str) -> str:
        """生成 URL 的 hash"""
        # 规范化 URL（去掉尾部斜杠、排序参数等）
        normalized = url.rstrip('/').lower()
        return hashlib.md5(normalized.encode('utf-8')).hexdigest()[:12]
    
    def exists(self, url: str) -> bool:
        """检查 URL 是否已存在"""
        return self._hash(url) in self.urls
    
    def add(self, url: str, title: str = ""):
        """添加 URL 到索引"""
        url_hash = self._hash(url)
        self.urls[url_hash] = {
            "url": url,
            "title": title,
            "crawled_at": datetime.now().isoformat()
        }
        self._save()
    
    def get_stats(self) -> Dict[str, Any]:
        """获取索引统计"""
        return {
            "total_urls": len(self.urls),
            "index_file": str(self.index_file)
        }
    
    def clear(self):
        """清空索引（谨慎使用）"""
        self.urls = {}
        self._save()


# 全局 URL 索引实例
url_index = UrlIndex()


# 全局状态
class TaskManager:
    def __init__(self):
        self.current_task = None
        self.logs = []
        self.status = "idle"  # idle, running, completed, error
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
                "logs": self.logs[-50:],  # 最近50条
                "results": self.results
            }

task_manager = TaskManager()


def search_urls(query: str, limit: int = 10) -> List[str]:
    """使用 SerpAPI Google 搜索获取 URL"""
    task_manager.log(f"🔍 搜索: {query}")
    
    api_key = os.getenv("SERPAPI_API_KEY")
    if not api_key:
        task_manager.log("❌ 未配置 SERPAPI_API_KEY", "error")
        return []
    
    try:
        import httpx
        
        params = {
            "engine": "google",
            "q": query,
            "api_key": api_key,
            "num": limit,
            "hl": "zh-cn",
            "gl": "cn"
        }
        
        task_manager.log(f"🌐 调用 SerpAPI Google 搜索...")
        
        # 简单重试，规避偶发连接重置/超时
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
            raise last_err
        
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


def crawl_url(url: str, crawler: WebpageCrawler) -> Dict[str, Any]:
    """爬取单个 URL"""
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
    """从 parsed.json 抽取知识"""
    task_manager.log(f"🧠 抽取知识...")
    
    try:
        parsed_data = json.loads(Path(parsed_path).read_text(encoding='utf-8'))
        title = parsed_data.get('title', '未知')
        url = parsed_data.get('source_url') or parsed_data.get('url', '')
        
        # 运行流水线
        result = run_pipeline(parsed_data, force_types)
        
        if result.artifacts:
            types = list(result.artifacts.keys())
            task_manager.log(f"✅ 抽取成功: {types}")
            
            # 写入 artifacts
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
            task_manager.log(f"⚠️ 未抽取到知识", "warning")
            return {"success": False, "title": title, "error": "无知识抽取"}
    
    except Exception as e:
        task_manager.log(f"❌ 抽取错误: {str(e)[:50]}", "error")
        return {"success": False, "error": str(e)}


def run_pipeline_task(query: str, limit: int, force_types: List[str]):
    """完整流水线任务"""
    task_manager.clear()
    task_manager.set_status("running", 0)
    
    try:
        # Step 1: 搜索
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
        
        # URL 去重
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
        
        # Step 2: 爬取
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
                # 爬取成功后添加到索引
                title = result.get('parsed_data', {}).get('title', '')
                url_index.add(url, title)
        
        task_manager.log(f"✅ 成功采取 {len(parsed_files)}/{len(new_urls)} 个网页")
        
        if not parsed_files:
            task_manager.log("❌ 无可用的采取结果", "error")
            task_manager.set_status("error", 100)
            return
        
        # Step 3: 抽取
        task_manager.log("-" * 40)
        task_manager.log(f"🧠 开始知识抽取")
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
        
        # 完成
        task_manager.log("=" * 40)
        task_manager.log(f"🎉 任务完成！成功抽取 {success_count}/{len(parsed_files)} 个")
        task_manager.log("=" * 40)
        task_manager.set_status("completed", 100)
    
    except Exception as e:
        task_manager.log(f"❌ 任务失败: {str(e)}", "error")
        task_manager.set_status("error", 100)


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/api/start', methods=['POST'])
def start_task():
    """启动任务"""
    data = request.json
    query = data.get('query', '').strip()
    limit = int(data.get('limit', 5))
    force_types = data.get('types', [])
    
    if not query:
        return jsonify({"error": "请输入搜索内容"}), 400
    
    if task_manager.status == "running":
        return jsonify({"error": "已有任务正在运行"}), 400
    
    # 在后台线程运行
    thread = threading.Thread(
        target=run_pipeline_task,
        args=(query, limit, force_types if force_types else None)
    )
    thread.daemon = True
    thread.start()
    
    return jsonify({"message": "任务已启动"})


@app.route('/api/status')
def get_status():
    """获取任务状态"""
    return jsonify(task_manager.get_state())


@app.route('/api/types')
def get_types():
    """获取支持的知识类型"""
    from extractors.type_registry import get_type_registry
    registry = get_type_registry()
    types = [
        {"id": kt.type_id, "name": kt.name, "brief": kt.brief}
        for kt in registry.get_enabled()
    ]
    return jsonify(types)


@app.route('/api/url-index')
def get_url_index():
    """获取 URL 索引统计"""
    stats = url_index.get_stats()
    stats["recent_urls"] = list(url_index.urls.values())[-10:]  # 最近 10 个
    return jsonify(stats)


@app.route('/api/url-index/clear', methods=['POST'])
def clear_url_index():
    """清空 URL 索引（允许重新爬取）"""
    url_index.clear()
    return jsonify({"message": "URL 索引已清空", "total_urls": 0})


# ============================================================
# 知识精炼 API
# ============================================================

# 精炼任务管理器
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
    """执行精炼任务"""
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


@app.route('/api/refine/start', methods=['POST'])
def start_refine():
    """启动精炼任务"""
    data = request.json or {}
    date_filter = data.get('date')
    time_filter = data.get('time')
    dry_run = data.get('dry_run', False)
    
    if refine_manager.status == "running":
        return jsonify({"error": "精炼任务正在运行"}), 400
    
    thread = threading.Thread(
        target=run_refine_task,
        args=(date_filter, time_filter, dry_run)
    )
    thread.daemon = True
    thread.start()
    
    return jsonify({"message": "精炼任务已启动"})


@app.route('/api/refine/status')
def get_refine_status():
    """获取精炼任务状态"""
    return jsonify(refine_manager.get_state())


@app.route('/api/refine/preview', methods=['POST'])
def preview_refine():
    """预览精炼（不实际执行）"""
    data = request.json or {}
    date_filter = data.get('date')
    time_filter = data.get('time')
    
    try:
        from refiner import KnowledgeRefiner
        
        refiner = KnowledgeRefiner()
        preview = refiner.preview(date_filter, time_filter)
        
        return jsonify(preview)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/artifacts/dates')
def list_artifact_dates():
    """获取 artifacts 日期列表"""
    artifacts_dir = ROOT_DIR / "se_kb" / "artifacts"
    dates = []
    
    if artifacts_dir.exists():
        for year_dir in sorted(artifacts_dir.iterdir(), reverse=True):
            if not year_dir.is_dir() or not year_dir.name.isdigit(): continue
            for month_dir in sorted(year_dir.iterdir(), reverse=True):
                if not month_dir.is_dir() or not month_dir.name.isdigit(): continue
                for day_dir in sorted(month_dir.iterdir(), reverse=True):
                    if not day_dir.is_dir() or not day_dir.name.isdigit(): continue
                    dates.append(f"{year_dir.name}/{month_dir.name}/{day_dir.name}")
                    
    return jsonify(dates)


@app.route('/api/artifacts/times')
def list_artifact_times():
    """获取指定日期的 artifacts 时间列表"""
    date_str = request.args.get('date')
    if not date_str:
        return jsonify([])
        
    try:
        year, month, day = date_str.split('/')
        day_dir = ROOT_DIR / "se_kb" / "artifacts" / year / month / day
        times = []
        
        if day_dir.exists():
            for time_dir in sorted(day_dir.iterdir(), reverse=True):
                if time_dir.is_dir() and "_" in time_dir.name:
                    # 统计文件数
                    file_count = sum(1 for _ in time_dir.rglob("*.json") 
                                   if _.name not in ["metadata.json", "parsed.json", 
                                                    "trace.json", "metrics.json", "errors.json"])
                    times.append({
                        "time": time_dir.name,
                        "count": file_count
                    })
        
        return jsonify(times)
    except Exception:
        return jsonify([])


@app.route('/api/semantic-search', methods=['POST'])
def semantic_search_endpoint():
    """语义搜索接口"""
    if not knowledge_retriever:
        return jsonify({"error": "KnowledgeRetriever not initialized"}), 500
        
    try:
        data = request.json or {}
        query = data.get("query")
        intent_str = data.get("intent")
        top_k = int(data.get("top_k", 5))
        
        if not query:
            return jsonify({"error": "缺少查询内容 (query)"}), 400

        from vectorizer import QueryIntent
        query_intent = QueryIntent(intent_str.lower()) if intent_str else None
        
        response = knowledge_retriever.retrieve(query, top_k, query_intent)
        
        results = []
        for r in response.results:
            results.append({
                "content": r.text,
                "score": round(r.score, 4),
                "source": r.metadata.get("source"),
                "type": r.metadata.get("type"),
                "collection": r.collection
            })
            
        return jsonify({
            "query": response.query,
            "intent": response.intent.value,
            "total_found": response.total_found,
            "results": results
        })
    except Exception as e:
        logger.error(f"Semantic search failed: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/system/reload-kb', methods=['POST'])
def reload_kb():
    """重载知识库连接"""
    global knowledge_retriever
    try:
        from vectorizer import VectorConfig, KnowledgeRetriever
        vector_config = VectorConfig()
        knowledge_retriever = KnowledgeRetriever(vector_config)
        logger.info("KnowledgeRetriever reloaded successfully")
        return jsonify({"message": "知识库连接已重置"})
    except Exception as e:
        logger.error(f"Failed to reload KnowledgeRetriever: {e}")
        return jsonify({"error": str(e)}), 500



if __name__ == '__main__':
    print("=" * 50)
    print("🚀 知识库构建系统 Web 界面")
    print("=" * 50)
    print("访问: http://localhost:5000")
    print("=" * 50)
    # 关闭自动重载，避免 Playwright/依赖文件改动导致任务中途重启
    # 端口 5000 被占用且无法释放，改用 8000
    try:
        app.run(host='0.0.0.0', port=8000, debug=False, use_reloader=False)
    except OSError:
        print("端口 8000 被占用，尝试使用 8001...")
        app.run(host='0.0.0.0', port=8001, debug=False, use_reloader=False)

