"""
知识库构建系统 - Web 界面
简洁的前端，用于搜索、爬取、抽取知识
"""

import sys
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
from utils.env_loader import load_env_file

load_env_file(ROOT_DIR / ".env")

import logging
import services

# 初始化日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__, template_folder='templates', static_folder='static')
CORS(app)

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
    
    if services.task_manager.status == "running":
        return jsonify({"error": "已有任务正在运行"}), 400
    
    # 在后台线程运行
    thread = threading.Thread(
        target=services.run_pipeline_task,
        args=(query, limit, force_types if force_types else None)
    )
    thread.daemon = True
    thread.start()
    
    return jsonify({"message": "任务已启动"})


@app.route('/api/crawl-url', methods=['POST'])
def start_manual_crawl():
    data = request.json or {}
    url = data.get('url', '').strip()
    extract = bool(data.get('extract', True))
    force_types = data.get('types', [])
    
    if not url:
        return jsonify({"error": "请输入 URL"}), 400
    
    if services.task_manager.status == "running":
        return jsonify({"error": "已有任务正在运行"}), 400
    
    thread = threading.Thread(
        target=services.run_manual_crawl_task,
        args=(url, force_types if force_types else None, extract)
    )
    thread.daemon = True
    thread.start()
    
    return jsonify({"message": "手动爬取任务已启动"})


@app.route('/api/status')
def get_status():
    """获取任务状态"""
    return jsonify(services.task_manager.get_state())


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
    stats = services.url_index.get_stats()
    stats["recent_urls"] = list(services.url_index.urls.values())[-10:]
    return jsonify(stats)


@app.route('/api/url-index/clear', methods=['POST'])
def clear_url_index():
    """清空 URL 索引（允许重新爬取）"""
    services.url_index.clear()
    return jsonify({"message": "URL 索引已清空", "total_urls": 0})


@app.route('/api/refine/start', methods=['POST'])
def start_refine():
    """启动精炼任务"""
    data = request.json or {}
    date_filter = data.get('date')
    time_filter = data.get('time')
    dry_run = data.get('dry_run', False)
    
    if services.refine_manager.status == "running":
        return jsonify({"error": "精炼任务正在运行"}), 400
    
    thread = threading.Thread(
        target=services.run_refine_task,
        args=(date_filter, time_filter, dry_run)
    )
    thread.daemon = True
    thread.start()
    
    return jsonify({"message": "精炼任务已启动"})


@app.route('/api/refine/status')
def get_refine_status():
    """获取精炼任务状态"""
    return jsonify(services.refine_manager.get_state())


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
    artifacts_dir = services.ROOT_DIR / "se_kb" / "artifacts"
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
        day_dir = services.ROOT_DIR / "se_kb" / "artifacts" / year / month / day
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
    if not services.knowledge_retriever:
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
        
        response = services.knowledge_retriever.retrieve(query, top_k, query_intent)
        
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
    try:
        from vectorizer import VectorConfig, KnowledgeRetriever
        vector_config = VectorConfig()
        services.knowledge_retriever = KnowledgeRetriever(vector_config)
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
