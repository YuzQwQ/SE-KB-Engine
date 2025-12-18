import logging
from flask import Blueprint, request, jsonify, current_app
from vectorizer import QueryIntent

# 创建蓝图
search_bp = Blueprint('search', __name__)

logger = logging.getLogger(__name__)

@search_bp.route('/search', methods=['POST'])
def search():
    """
    语义检索接口 (RAG)
    ---
    tags:
      - Search
    security:
      - Bearer: []
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          required:
            - query
          properties:
            query:
              type: string
              description: 检索关键词
              example: "DFD中的外部实体是什么"
            intent:
              type: string
              description: 检索意图 (concept, rule, example, template, theory)
              enum: [concept, rule, example, template, theory]
            top_k:
              type: integer
              description: 返回结果数量
              default: 5
              example: 5
    responses:
      200:
        description: 检索成功
    """
    # 延迟导入鉴权，避免循环引用
    from api.auth import require_api_key
    
    @require_api_key(admin_only=False)
    def _handler():
        retriever = current_app.config.get('RETRIEVER')
        if not retriever:
            return jsonify({"code": 503, "message": "Knowledge Retriever not initialized"}), 503
        
        try:
            data = request.json or {}
            query = data.get("query")
            intent_str = data.get("intent")
            top_k = int(data.get("top_k", 5))
            
            if not query:
                return jsonify({"code": 400, "message": "Missing 'query' parameter"}), 400

            # 解析意图
            query_intent = QueryIntent(intent_str.lower()) if intent_str else None
            
            # 执行检索
            response = retriever.retrieve(query, top_k, query_intent)
            
            results = []
            for r in response.results:
                results.append({
                    "content": r.text,
                    "score": round(r.score, 4),
                    "source": r.metadata.get("source"),
                    "type": r.metadata.get("type"),
                    "collection": r.collection,
                    "metadata": r.metadata  # 包含更详细的元数据
                })
                
            return jsonify({
                "code": 200,
                "message": "success",
                "data": {
                    "query": response.query,
                    "intent": response.intent.value,
                    "total_found": response.total_found,
                    "results": results
                }
            })
            
        except Exception as e:
            logger.error(f"Search failed: {e}", exc_info=True)
            return jsonify({"code": 500, "message": str(e)}), 500

    return _handler()
