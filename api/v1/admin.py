import logging
from flask import Blueprint, jsonify, current_app
from vectorizer import VectorConfig, KnowledgeRetriever
from service_boundary.auth import Role
from service_boundary.errors import public_error
from service_boundary.flask_support import audit_operation, require_role
from service_boundary.health import readiness_status
from se_kb_app.observability import METRICS

admin_bp = Blueprint("admin", __name__)
logger = logging.getLogger(__name__)


@admin_bp.route("/health", methods=["GET"])
def health_check():
    """
    健康检查接口
    ---
    tags:
      - System
    responses:
      200:
        description: 服务正常
    """
    retriever = current_app.config.get("RETRIEVER")
    status = "healthy" if retriever else "degraded"

    return jsonify({"code": 200, "status": status, "service": "se-kb-api", "version": "1.0.0"})


@admin_bp.route("/live", methods=["GET"])
def liveness():
    return jsonify({"code": 200, "status": "alive", "service": "se-kb-api"})


@admin_bp.route("/ready", methods=["GET"])
def readiness():
    ready, capabilities = readiness_status(retriever=current_app.config.get("RETRIEVER"))
    payload = {
        "code": 200 if ready else 503,
        "status": "ready" if ready else "not_ready",
        "capabilities": capabilities,
    }
    return jsonify(payload), 200 if ready else 503


@admin_bp.route("/admin/reload", methods=["POST"])
@require_role(Role.ADMIN)
@audit_operation
def reload_index():
    """
    热重载向量索引 (Admin Only)
    ---
    tags:
      - Admin
    security:
      - Bearer: []
    responses:
      200:
        description: 重载成功
    """
    logger.info("Reloading KnowledgeRetriever...")
    config = VectorConfig()
    new_retriever = KnowledgeRetriever(config)
    current_app.config["RETRIEVER"] = new_retriever
    stats = new_retriever.get_stats()
    logger.info("KnowledgeRetriever reloaded successfully")
    return jsonify(
        {"code": 200, "message": "Index reloaded successfully", "data": {"stats": stats}}
    )


@admin_bp.route("/admin/stats", methods=["GET"])
@require_role(Role.ADMIN)
@audit_operation
def get_stats():
    """
    获取索引统计 (Admin Only)
    ---
    tags:
      - Admin
    security:
      - Bearer: []
    """
    retriever = current_app.config.get("RETRIEVER")
    if not retriever:
        raise public_error("unavailable")
    stats = retriever.get_stats()
    return jsonify({"code": 200, "data": stats})


@admin_bp.route("/admin/diagnostics", methods=["GET"])
@require_role(Role.ADMIN)
@audit_operation
def diagnostics():
    ready, capabilities = readiness_status(retriever=current_app.config.get("RETRIEVER"))
    return jsonify(
        {
            "code": 200,
            "data": {
                "live": True,
                "ready": ready,
                "capabilities": capabilities,
                "metrics": METRICS.snapshot(),
            },
        }
    )
