import os
import sys
import logging
from pathlib import Path
from flask import Flask, jsonify
from flasgger import Swagger

# 添加项目根目录到路径
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

# 加载环境变量
def load_env():
    env_path = ROOT_DIR / '.env'
    if env_path.exists():
        for line in env_path.read_text(encoding='utf-8').splitlines():
            line = line.strip()
            if not line or line.startswith('#'): continue
            if '=' in line:
                k, v = line.split('=', 1)
                os.environ[k.strip()] = v.strip()

load_env()

from vectorizer import VectorConfig, KnowledgeRetriever

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)
logger = logging.getLogger("se-kb-api")

def create_app():
    app = Flask(__name__)
    
    # Swagger 配置
    app.config['SWAGGER'] = {
        'title': 'SE-KB Knowledge Service API',
        'uiversion': 3,
        'version': "1.0.0",
        'description': "Software Engineering Knowledge Builder RAG Service",
        'securityDefinitions': {
            'Bearer': {
                'type': 'apiKey',
                'name': 'Authorization',
                'in': 'header',
                'description': 'Enter your Bearer token in the format: Bearer &lt;token&gt;'
            }
        },
        'security': [{'Bearer': []}]
    }
    Swagger(app)
    
    # 初始化知识检索器
    try:
        logger.info("Initializing KnowledgeRetriever...")
        vector_config = VectorConfig()
        app.config['RETRIEVER'] = KnowledgeRetriever(vector_config)
        logger.info("KnowledgeRetriever initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize KnowledgeRetriever: {e}")
        # 不阻断启动，允许 /health 检查
        app.config['RETRIEVER'] = None

    # 注册蓝图
    from api.v1.search import search_bp
    from api.v1.admin import admin_bp
    
    app.register_blueprint(search_bp, url_prefix='/api/v1')
    app.register_blueprint(admin_bp, url_prefix='/api/v1')
    
    # 打印路由映射
    print("\nURL Map:")
    print(app.url_map)
    print("\n")
    
    # 全局错误处理
    @app.errorhandler(404)
    def not_found(e):
        return jsonify({"code": 404, "message": "Endpoint not found"}), 404
        
    @app.errorhandler(500)
    def internal_error(e):
        return jsonify({"code": 500, "message": "Internal server error"}), 500

    return app

# Gunicorn 入口
app = create_app()

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=8000, debug=True)
