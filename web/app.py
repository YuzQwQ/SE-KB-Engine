"""
知识库构建系统 - Web 界面
简洁的前端，用于搜索、爬取、抽取知识
"""

import sys
import asyncio
from pathlib import Path
from datetime import date, datetime
from typing import List, Dict, Any, cast
from dataclasses import dataclass, asdict

# 添加项目根目录到路径
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from flask import Flask, jsonify, make_response, render_template, request
import queue
import threading
from typing import TYPE_CHECKING
from utils.env_loader import load_env_file
from service_boundary.auth import Role
from service_boundary.errors import public_error
from service_boundary.flask_support import (
    install_flask_boundary,
    issue_csrf_cookie,
    require_browser_mutation,
    require_role,
)
from service_boundary.inputs import (
    InputLimits,
    boolean_field,
    date_field,
    enum_field,
    integer_field,
    object_body,
    path_component,
    string_field,
    string_list_field,
)
from service_boundary.url_policy import validate_url
from service_boundary.audit import install_secret_redaction
from se_kb_app.domain import RetrievalRequest
from se_kb_app.presenters import retrieval_payload
from se_kb_app.observability import configure_logging
from se_kb_app.errors import ApplicationError
from se_kb_app.obsidian.jobs import ObsidianJobManager
from se_kb_app.obsidian.service import ObsidianVaultService
from se_kb_app.obsidian.models import RelationshipKind
from se_kb_app.obsidian.presenters import (
    location_payload as obsidian_location_payload,
    plan_payload as obsidian_plan_payload,
    relationship_payload as obsidian_relationship_payload,
    status_payload as obsidian_status_payload,
)
from se_kb_app.obsidian.source import KnowledgeSelection

if TYPE_CHECKING:
    from se_kb_app.composition import Application

load_env_file(ROOT_DIR / ".env")

import logging
from web import services

configure_logging()
logger = logging.getLogger(__name__)

app = Flask(__name__, template_folder='templates', static_folder='static')
install_secret_redaction()
install_flask_boundary(app)


def bind_application(application: "Application") -> Flask:
    """Bind composed services without changing the legacy Flask import contract."""
    app.config["APPLICATION"] = application
    for name, legacy_name in (
        ("retriever", "knowledge_retriever"),
        ("crawl", "crawl_service"),
        ("task_manager", "task_manager"),
        ("url_index", "url_index"),
        ("refine_manager", "refine_manager"),
    ):
        try:
            setattr(services, legacy_name, application.resource(name))
        except KeyError:
            continue
    try:
        app.config["RETRIEVAL_SERVICE"] = application.resource("retrieval")
    except KeyError:
        app.config["RETRIEVAL_SERVICE"] = None
    try:
        obsidian_service = cast(ObsidianVaultService, application.resource("obsidian"))
        app.config["OBSIDIAN_RUNTIME"] = ObsidianJobManager(obsidian_service)
    except KeyError:
        app.config["OBSIDIAN_RUNTIME"] = None
    return app


def _obsidian_runtime() -> ObsidianJobManager:
    runtime = app.config.get("OBSIDIAN_RUNTIME")
    if runtime is None:
        runtime = services.get_obsidian_runtime()
        app.config["OBSIDIAN_RUNTIME"] = runtime
    return runtime


def _obsidian_selection(data) -> KnowledgeSelection:
    limits = InputLimits.from_environment()
    sources = tuple(string_list_field(data, "sources", maximum=limits.list_items_max))
    kinds = tuple(string_list_field(data, "kinds", maximum=limits.list_items_max))
    entity_kinds = tuple(string_list_field(data, "entity_kinds", maximum=limits.list_items_max))
    quality = data.get("minimum_quality", 0.0)
    if isinstance(quality, bool) or not isinstance(quality, (int, float)) or not 0 <= quality <= 1:
        raise public_error("invalid_field", field="minimum_quality")
    return KnowledgeSelection(
        sources=sources,
        kinds=kinds,
        entity_kinds=entity_kinds,
        minimum_quality=float(quality),
        date_from=_iso_date(data.get("date_from"), "date_from"),
        date_to=_iso_date(data.get("date_to"), "date_to"),
    )


def _iso_date(value, field):
    if value in (None, ""):
        return None
    if not isinstance(value, str):
        raise public_error("invalid_field", field=field)
    try:
        return date.fromisoformat(value)
    except ValueError as error:
        raise public_error("invalid_field", field=field) from error


def _query_integer(name: str, default: int, minimum: int, maximum: int) -> int:
    raw = request.args.get(name)
    try:
        value = default if raw is None else int(raw)
    except ValueError as error:
        raise public_error("invalid_field", field=name) from error
    if not minimum <= value <= maximum:
        raise public_error("invalid_field", field=name)
    return value


def _query_float(name: str, default: float, minimum: float, maximum: float) -> float:
    raw = request.args.get(name)
    try:
        value = default if raw is None else float(raw)
    except ValueError as error:
        raise public_error("invalid_field", field=name) from error
    if not minimum <= value <= maximum:
        raise public_error("invalid_field", field=name)
    return value


def _raise_obsidian_public(error: ApplicationError):
    if error.public_code == "obsidian_note_not_found":
        raise public_error("not_found") from error
    if error.public_code == "obsidian_export_busy":
        raise public_error("conflict") from error
    if error.public_code.startswith("obsidian_"):
        raise public_error("unavailable") from error
    raise error

@app.route('/')
def index():
    return issue_csrf_cookie(make_response(render_template('index.html')))


def _submit_task(manager, operation, parameters, function, *args):
    try:
        return manager.submit(operation, parameters, function, *args)
    except ApplicationError as error:
        raise public_error("conflict" if error.public_code == "job_conflict" else "rate_limited") from error


@app.route('/api/start', methods=['POST'])
@require_browser_mutation
def start_task():
    """启动任务"""
    limits = InputLimits.from_environment()
    data = object_body(request.get_json(silent=True))
    query = string_field(data, 'query', required=True, max_length=limits.query_chars)
    limit = integer_field(data, 'limit', default=5, minimum=1, maximum=limits.task_limit_max)
    force_types = string_list_field(data, 'types', maximum=limits.list_items_max)
    
    job_id = _submit_task(services.task_manager, "search-crawl",
        {"query": query, "limit": limit, "types": tuple(force_types)},
        services.run_pipeline_task, query, limit, force_types if force_types else None)

    response = jsonify({"message": "任务已启动"})
    response.headers["X-Job-ID"] = job_id
    response.headers["Location"] = f"/api/jobs/{job_id}"
    return response


@app.route('/api/crawl-url', methods=['POST'])
@require_browser_mutation
def start_manual_crawl():
    limits = InputLimits.from_environment()
    data = object_body(request.get_json(silent=True))
    raw_url = string_field(data, 'url', required=True, max_length=limits.url_chars)
    url = validate_url(raw_url or '').url
    extract = boolean_field(data, 'extract', default=True)
    force_types = string_list_field(data, 'types', maximum=limits.list_items_max)
    
    job_id = _submit_task(services.task_manager, "manual-crawl",
        {"url": url, "extract": extract, "types": tuple(force_types)},
        services.run_manual_crawl_task, url, force_types if force_types else None, extract)

    response = jsonify({"message": "手动爬取任务已启动"})
    response.headers["X-Job-ID"] = job_id
    response.headers["Location"] = f"/api/jobs/{job_id}"
    return response


@app.route('/api/status')
@require_role(Role.READ)
def get_status():
    """获取任务状态"""
    return jsonify(services.task_manager.get_state(request.args.get("job_id")))


@app.route('/api/jobs/<job_id>')
@require_role(Role.READ)
def get_job(job_id):
    for manager in (_obsidian_runtime(), services.task_manager, services.refine_manager):
        try:
            return jsonify(manager.get_state(job_id))
        except Exception:
            continue
    raise public_error("not_found")


@app.route('/api/jobs/<job_id>/cancel', methods=['POST'])
@require_browser_mutation
def cancel_job(job_id):
    for manager in (_obsidian_runtime(), services.task_manager, services.refine_manager):
        try:
            return jsonify(manager.cancel(job_id))
        except Exception:
            continue
    raise public_error("not_found")


@app.route('/api/types')
@require_role(Role.READ)
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
@require_role(Role.ADMIN)
def get_url_index():
    """获取 URL 索引统计"""
    stats = services.url_index.get_stats()
    stats["recent_urls"] = list(services.url_index.urls.values())[-10:]
    return jsonify(stats)


@app.route('/api/url-index/clear', methods=['POST'])
@require_browser_mutation
def clear_url_index():
    """清空 URL 索引（允许重新爬取）"""
    services.url_index.clear()
    return jsonify({"message": "URL 索引已清空", "total_urls": 0})


@app.route('/api/refine/start', methods=['POST'])
@require_browser_mutation
def start_refine():
    """启动精炼任务"""
    data = object_body(request.get_json(silent=True))
    date_filter = date_field(data.get('date'))
    time_filter = path_component(data.get('time'), 'time')
    dry_run = boolean_field(data, 'dry_run', default=False)
    
    job_id = _submit_task(services.refine_manager, "refine",
        {"date": date_filter, "time": time_filter, "dry_run": dry_run},
        services.run_refine_task, date_filter, time_filter, dry_run)

    response = jsonify({"message": "精炼任务已启动"})
    response.headers["X-Job-ID"] = job_id
    response.headers["Location"] = f"/api/jobs/{job_id}"
    return response


@app.route('/api/refine/status')
@require_role(Role.READ)
def get_refine_status():
    """获取精炼任务状态"""
    return jsonify(services.refine_manager.get_state(request.args.get("job_id")))


@app.route('/api/refine/preview', methods=['POST'])
@require_browser_mutation
def preview_refine():
    """预览精炼（不实际执行）"""
    data = object_body(request.get_json(silent=True))
    date_filter = date_field(data.get('date'))
    time_filter = path_component(data.get('time'), 'time')
    from refiner import KnowledgeRefiner

    refiner = KnowledgeRefiner()
    return jsonify(refiner.preview(date_filter, time_filter))


@app.route('/api/artifacts/dates')
@require_role(Role.READ)
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
@require_role(Role.READ)
def list_artifact_times():
    """获取指定日期的 artifacts 时间列表"""
    date_str = date_field(request.args.get('date'))
    if not date_str:
        return jsonify([])
        
    year, month, day = date_str.split('/')
    day_dir = services.ROOT_DIR / "se_kb" / "artifacts" / year / month / day
    times = []
    if day_dir.exists():
        for time_dir in sorted(day_dir.iterdir(), reverse=True):
            if time_dir.is_dir() and "_" in time_dir.name:
                file_count = sum(1 for item in time_dir.rglob("*.json")
                                 if item.name not in ["metadata.json", "parsed.json",
                                                      "trace.json", "metrics.json", "errors.json"])
                times.append({"time": time_dir.name, "count": file_count})
    return jsonify(times)


@app.route('/api/semantic-search', methods=['POST'])
@require_role(Role.READ)
def semantic_search_endpoint():
    """语义搜索接口"""
    retrieval_service = app.config.get("RETRIEVAL_SERVICE")
    retriever = services.knowledge_retriever
    if retriever is None and retrieval_service is None:
        retriever = services.get_knowledge_retriever()
    if retriever is None and retrieval_service is None:
        raise public_error("unavailable")
    from vectorizer import QueryIntent

    limits = InputLimits.from_environment()
    data = object_body(request.get_json(silent=True))
    query = string_field(data, 'query', required=True, max_length=limits.query_chars)
    intent_str = enum_field(data, 'intent', [intent.value for intent in QueryIntent])
    top_k = integer_field(data, 'top_k', default=5, minimum=1, maximum=limits.top_k_max)
    query_intent = QueryIntent(intent_str) if intent_str else None
    if retrieval_service is not None:
        return jsonify(
            retrieval_payload(
                retrieval_service.retrieve(RetrievalRequest(query or "", top_k, intent_str))
            )
        )
    response = retriever.retrieve(query, top_k, query_intent)
    results = [{
        "content": result.text,
        "score": round(result.score, 4),
        "source": result.metadata.get("source"),
        "type": result.metadata.get("type"),
        "collection": result.collection
    } for result in response.results]
    return jsonify({"query": response.query, "intent": response.intent.value,
                    "total_found": response.total_found, "results": results})


@app.route('/api/obsidian/status')
@require_role(Role.READ)
def obsidian_status_endpoint():
    return jsonify(obsidian_status_payload(_obsidian_runtime().service.status()))


@app.route('/api/obsidian/preview', methods=['POST'])
@require_role(Role.READ)
def obsidian_preview_endpoint():
    data = object_body(request.get_json(silent=True))
    offset = integer_field(data, 'offset', default=0, minimum=0, maximum=1_000_000)
    limit = integer_field(data, 'limit', default=100, minimum=1, maximum=1000)
    try:
        plan = _obsidian_runtime().service.preview(
            _obsidian_selection(data),
            offset=offset,
            limit=limit,
        )
    except ApplicationError as error:
        _raise_obsidian_public(error)
    return jsonify(obsidian_plan_payload(plan))


@app.route('/api/obsidian/export', methods=['POST'])
@require_browser_mutation
def obsidian_export_endpoint():
    data = object_body(request.get_json(silent=True))
    runtime = _obsidian_runtime()
    try:
        identifier = runtime.submit(_obsidian_selection(data))
    except ApplicationError as error:
        _raise_obsidian_public(error)
    response = jsonify({"message": "Obsidian Vault 导出任务已启动", "job_id": identifier})
    response.status_code = 202
    response.headers["X-Job-ID"] = identifier
    response.headers["Location"] = f"/api/jobs/{identifier}"
    return response


@app.route('/api/obsidian/relationships')
@require_role(Role.READ)
def obsidian_relationships_endpoint():
    kind_value = request.args.get('kind')
    if kind_value not in {None, '', RelationshipKind.EXPLICIT.value, RelationshipKind.SEMANTIC.value}:
        raise public_error("invalid_field", field="kind")
    kind = RelationshipKind(kind_value) if kind_value else None
    node = request.args.get('node') or None
    source = request.args.get('source') or None
    if node is not None and (len(node) > 512 or any(ord(char) < 32 for char in node)):
        raise public_error("invalid_field", field="node")
    if source is not None and len(source) > 2048:
        raise public_error("invalid_field", field="source")
    offset = _query_integer('offset', 0, 0, 1_000_000)
    limit = _query_integer('limit', 100, 1, 1000)
    minimum_score = _query_float('minimum_score', 0.0, 0.0, 1.0)
    try:
        page = _obsidian_runtime().service.relationships(
            KnowledgeSelection(),
            node=node,
            kind=kind,
            source=source,
            minimum_score=minimum_score,
            offset=offset,
            limit=limit,
        )
    except (ApplicationError, ValueError) as error:
        if isinstance(error, ApplicationError):
            _raise_obsidian_public(error)
        raise public_error("invalid_field") from error
    return jsonify(obsidian_relationship_payload(page))


@app.route('/api/obsidian/notes/<identifier>/location')
@require_role(Role.READ)
def obsidian_note_location_endpoint(identifier):
    if not identifier or len(identifier) > 512 or any(ord(char) < 32 for char in identifier):
        raise public_error("invalid_field", field="identifier")
    try:
        location = _obsidian_runtime().service.note_location(identifier)
    except ApplicationError as error:
        _raise_obsidian_public(error)
    return jsonify(obsidian_location_payload(location))


@app.route('/api/system/reload-kb', methods=['POST'])
@require_browser_mutation
def reload_kb():
    """重载知识库连接"""
    from vectorizer import VectorConfig, KnowledgeRetriever
    vector_config = VectorConfig()
    services.knowledge_retriever = KnowledgeRetriever(vector_config)
    logger.info("KnowledgeRetriever reloaded successfully")
    return jsonify({"message": "知识库连接已重置"})



if __name__ == '__main__':
    print("=" * 50)
    print("[SE-KB] 知识库构建系统 Web 界面")
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
