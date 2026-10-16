import logging
from flask import Blueprint, request, jsonify, current_app
from vectorizer import QueryIntent
from service_boundary.auth import Role
from service_boundary.errors import public_error
from service_boundary.flask_support import require_role
from service_boundary.inputs import InputLimits, boolean_field, enum_field, integer_field, object_body, string_field
from se_kb_app.domain import RetrievalRequest
from se_kb_app.presenters import retrieval_payload

# 创建蓝图
search_bp = Blueprint("search", __name__)

logger = logging.getLogger(__name__)


@search_bp.route("/search", methods=["POST"])
@require_role(Role.READ)
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
    retriever = current_app.config.get("RETRIEVER")
    retrieval_service = current_app.config.get("RETRIEVAL_SERVICE")
    if not retriever and retrieval_service is None:
        raise public_error("unavailable")

    limits = InputLimits.from_environment()
    data = object_body(request.get_json(silent=True))
    query = string_field(data, "query", required=True, max_length=limits.query_chars)
    intent_str = enum_field(data, "intent", [intent.value for intent in QueryIntent])
    top_k = integer_field(data, "top_k", default=5, minimum=1, maximum=limits.top_k_max)
    use_smart_search = boolean_field(data, "smart_search", default=False)
    query_intent = QueryIntent(intent_str) if intent_str else None
    planner = current_app.config.get("PLANNER")

    if use_smart_search and planner:
        logger.info("Using QueryPlanner for query length=%s", len(query or ""))
        plan_result = planner.search(query, top_k)
        results = [
            {
                "content": result["content"],
                "score": result["score"],
                "source": result["source"],
                "type": result["type"],
                "collection": result["collection"],
                "metadata": result["metadata"],
                "matched_queries": result["matched_queries"],
            }
            for result in plan_result.merged_results
        ]
        return jsonify(
            {
                "code": 200,
                "message": "success",
                "data": {
                    "query": plan_result.original_query,
                    "intent": "decomposed_search",
                    "total_found": len(results),
                    "results": results,
                    "sub_queries": [
                        {"query": item.query, "intent": item.intent, "weight": item.weight}
                        for item in plan_result.sub_queries
                    ],
                },
            }
        )

    if retrieval_service is not None:
        payload = retrieval_payload(
            retrieval_service.retrieve(RetrievalRequest(query or "", top_k, intent_str))
        )
        return jsonify({"code": 200, "message": "success", "data": payload})

    response = retriever.retrieve(query, top_k, query_intent)
    results = [
        {
            "content": result.text,
            "score": round(result.score, 4),
            "source": result.metadata.get("source"),
            "type": result.metadata.get("type"),
            "collection": result.collection,
            "metadata": result.metadata,
        }
        for result in response.results
    ]
    return jsonify(
        {
            "code": 200,
            "message": "success",
            "data": {
                "query": response.query,
                "intent": response.intent.value,
                "total_found": response.total_found,
                "results": results,
            },
        }
    )
