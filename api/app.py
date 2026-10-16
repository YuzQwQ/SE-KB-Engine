import logging
import os
import sys
from pathlib import Path
from typing import TYPE_CHECKING

from flask import Flask
from flasgger import Swagger

# 添加项目根目录到路径
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))


from utils.env_loader import load_env_file


load_env_file(ROOT_DIR / ".env", override=True)

from vectorizer import VectorConfig, KnowledgeRetriever, QueryPlanner
from service_boundary.flask_support import install_flask_boundary
from service_boundary.audit import install_secret_redaction
from se_kb_app.observability import configure_logging

if TYPE_CHECKING:
    from se_kb_app.composition import Application

logger = logging.getLogger("se-kb-api")


def create_app(*, application: "Application | None" = None, initialize_services: bool = True):
    configure_logging()
    install_secret_redaction()
    app = Flask(__name__)
    install_flask_boundary(app)

    # Swagger 配置
    app.config["SWAGGER"] = {
        "title": "SE-KB Knowledge Service API",
        "uiversion": 3,
        "version": "1.0.0",
        "description": "Software Engineering Knowledge Builder RAG Service",
        "securityDefinitions": {
            "Bearer": {
                "type": "apiKey",
                "name": "Authorization",
                "in": "header",
                "description": "Enter your Bearer token in the format: Bearer &lt;token&gt;",
            }
        },
        "security": [{"Bearer": []}],
    }
    Swagger(app)

    app.config["APPLICATION"] = application

    # Prefer explicitly composed services; retain lazy legacy construction for compatibility.
    if application is not None:
        try:
            app.config["RETRIEVER"] = application.resource("retriever")
        except KeyError:
            app.config["RETRIEVER"] = None
        try:
            app.config["PLANNER"] = application.resource("planner")
        except KeyError:
            app.config["PLANNER"] = None
        try:
            app.config["RETRIEVAL_SERVICE"] = application.resource("retrieval")
        except KeyError:
            app.config["RETRIEVAL_SERVICE"] = None
    elif initialize_services:
        try:
            logger.info("Initializing KnowledgeRetriever and QueryPlanner...")
            vector_config = VectorConfig()
            retriever = KnowledgeRetriever(vector_config)
            app.config["RETRIEVER"] = retriever
            app.config["PLANNER"] = QueryPlanner(retriever)
            from se_kb_app.infrastructure.vector import VectorRetrieverAdapter
            from se_kb_app.services.retrieval import RetrievalService

            app.config["RETRIEVAL_SERVICE"] = RetrievalService(VectorRetrieverAdapter(retriever))
            logger.info("Knowledge services initialized successfully")
        except Exception as error:
            logger.error("Knowledge services unavailable: %s", type(error).__name__)
            app.config["RETRIEVER"] = None
            app.config["PLANNER"] = None
            app.config["RETRIEVAL_SERVICE"] = None
    else:
        app.config["RETRIEVER"] = None
        app.config["PLANNER"] = None
        app.config["RETRIEVAL_SERVICE"] = None

    # 注册蓝图
    from api.v1.search import search_bp
    from api.v1.admin import admin_bp

    app.register_blueprint(search_bp, url_prefix="/api/v1")
    app.register_blueprint(admin_bp, url_prefix="/api/v1")

    return app


# Gunicorn 入口
app = create_app(
    initialize_services=os.getenv("SKIP_SERVICE_INITIALIZATION", "").lower()
    not in {"1", "true", "yes"}
)

if __name__ == "__main__":
    debug = os.getenv("API_DEBUG", "").lower() in {"1", "true", "yes"}
    app.run(host="0.0.0.0", port=8000, debug=debug)
