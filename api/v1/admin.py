import logging
from flask import Blueprint, jsonify, current_app
from vectorizer import VectorConfig, KnowledgeRetriever

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


@admin_bp.route("/admin/reload", methods=["POST"])
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
    from api.auth import require_api_key

    @require_api_key(admin_only=True)
    def _handler():
        try:
            logger.info("Reloading KnowledgeRetriever...")
            config = VectorConfig()
            # 重新初始化
            new_retriever = KnowledgeRetriever(config)
            # 更新全局配置
            current_app.config["RETRIEVER"] = new_retriever

            # 获取统计信息
            stats = new_retriever.get_stats()

            logger.info("KnowledgeRetriever reloaded successfully")
            return jsonify(
                {"code": 200, "message": "Index reloaded successfully", "data": {"stats": stats}}
            )
        except Exception as e:
            logger.error(f"Failed to reload index: {e}", exc_info=True)
            return jsonify({"code": 500, "message": str(e)}), 500

    return _handler()


@admin_bp.route("/admin/stats", methods=["GET"])
def get_stats():
    """
    获取索引统计 (Admin Only)
    ---
    tags:
      - Admin
    security:
      - Bearer: []
    """
    from api.auth import require_api_key

    @require_api_key(admin_only=True)
    def _handler():
        retriever = current_app.config.get("RETRIEVER")
        if not retriever:
            return jsonify({"code": 503, "message": "Service not initialized"}), 503

        stats = retriever.get_stats()
        return jsonify({"code": 200, "data": stats})

    return _handler()
