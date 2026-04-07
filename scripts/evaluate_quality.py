import argparse
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from extractors.type_registry import get_type_registry
from validators.jsonschema_validator import make_validator


EXCLUDE_FILENAMES = {
    "metadata.json",
    "metrics.json",
    "errors.json",
    "parsed.json",
    "trace.json",
}

PLACEHOLDERS = {"暂无", "未知", "未提供", "无", "空", "n/a", "none", "null"}


TYPE_PREFIXES = [
    ("dfd_concepts", "diagrams.dfd.concepts"),
    ("dfd_rules", "diagrams.dfd.rules"),
    ("dfd_examples", "diagrams.dfd.examples"),
    ("dfd_levels", "diagrams.dfd.levels"),
    ("dfd_templates", "diagrams.dfd.templates"),
    ("dfd_validation", "diagrams.dfd.validation"),
    ("theory_", "theory"),
    ("domain_", "domain"),
    ("mappings_", "mappings"),
    ("schema_", "schema"),
]


def normalize_text(text):
    text = text.lower()
    text = re.sub(r"\s+", "", text)
    text = re.sub(r"[^\w\u4e00-\u9fff]", "", text)
    return text


def extract_text(value):
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, list):
        parts = []
        for item in value:
            if isinstance(item, str):
                parts.append(item)
        return " ".join(parts).strip()
    return ""


def is_low_info(text, min_len):
    if not text:
        return True
    if len(text) < min_len:
        return True
    lowered = text.strip().lower()
    for token in PLACEHOLDERS:
        if token in lowered:
            return True
    return False


def detect_type(file_path):
    name = file_path.name
    for prefix, type_id in TYPE_PREFIXES:
        if name.startswith(prefix):
            return type_id
    return None


def safe_list(value):
    return value if isinstance(value, list) else []


def find_first_list(data, keys):
    for key in keys:
        if "." in key:
            node = data
            ok = True
            for part in key.split("."):
                if isinstance(node, dict) and part in node:
                    node = node[part]
                else:
                    ok = False
                    break
            if ok and isinstance(node, list):
                return node
        else:
            if key in data and isinstance(data[key], list):
                return data[key]
    return []


def add_item_metrics(
    item, required_fields, text_fields, dup_field, metrics, min_info_len, min_index_len
):
    for field in required_fields:
        value = item.get(field)
        if value is None or value == "" or value == []:
            metrics["missing_fields"] += 1
    metrics["required_fields_total"] += len(required_fields)
    total_text_len = 0
    for field in text_fields:
        text = extract_text(item.get(field))
        total_text_len += len(text)
        if is_low_info(text, min_info_len):
            metrics["low_info_fields"] += 1
        metrics["text_fields_total"] += 1
    if total_text_len < min_index_len:
        metrics["indexable_failures"] += 1
    if dup_field:
        dup_text = extract_text(item.get(dup_field))
        if dup_text:
            metrics["dup_texts"].append(dup_text)


def evaluate_concepts(data, metrics, min_info_len, min_index_len):
    items = find_first_list(data, ["elements", "concepts", "generation_knowledge.concepts"])
    for item in items:
        if isinstance(item, dict):
            add_item_metrics(
                item,
                ["id", "name", "definition"],
                ["name", "definition"],
                "definition",
                metrics,
                min_info_len,
                min_index_len,
            )
    metrics["items"] += len(items)


def evaluate_rules(data, metrics, min_info_len, min_index_len):
    items = safe_list(data.get("rules"))
    for item in items:
        if isinstance(item, dict):
            add_item_metrics(
                item,
                ["id", "name", "detail", "level"],
                ["name", "detail"],
                "detail",
                metrics,
                min_info_len,
                min_index_len,
            )
    metrics["items"] += len(items)


def evaluate_examples(data, metrics, min_info_len, min_index_len):
    root_required = ["case_name", "description", "requirements_text", "dfd_elements"]
    root = {key: data.get(key) for key in root_required}
    add_item_metrics(
        root,
        root_required,
        ["description", "requirements_text"],
        "description",
        metrics,
        min_info_len,
        min_index_len,
    )
    metrics["items"] += 1
    elements = data.get("dfd_elements", {})
    for key, required in [
        ("external_entities", ["id", "name"]),
        ("processes", ["id", "name"]),
        ("data_stores", ["id", "name"]),
        ("data_flows", ["from", "to", "data"]),
    ]:
        items = safe_list(elements.get(key))
        for item in items:
            if isinstance(item, dict):
                add_item_metrics(
                    item,
                    required,
                    ["name", "data", "from", "to"],
                    "name",
                    metrics,
                    min_info_len,
                    min_index_len,
                )
        metrics["items"] += len(items)


def evaluate_levels(data, metrics, min_info_len, min_index_len):
    for items, required, text_fields, dup_field in [
        (
            safe_list(data.get("leveling_principles")),
            ["id", "description"],
            ["description"],
            "description",
        ),
        (
            safe_list(data.get("decomposition_rules")),
            ["id", "description"],
            ["description"],
            "description",
        ),
        (
            safe_list(data.get("level_definitions")),
            ["level", "name", "purpose"],
            ["name", "purpose"],
            "purpose",
        ),
    ]:
        for item in items:
            if isinstance(item, dict):
                add_item_metrics(
                    item, required, text_fields, dup_field, metrics, min_info_len, min_index_len
                )
        metrics["items"] += len(items)


def evaluate_templates(data, metrics, min_info_len, min_index_len):
    categories = safe_list(data.get("categories"))
    for category in categories:
        if not isinstance(category, dict):
            continue
        add_item_metrics(
            category,
            ["id", "name", "templates"],
            ["name"],
            "name",
            metrics,
            min_info_len,
            min_index_len,
        )
        metrics["items"] += 1
        templates = safe_list(category.get("templates"))
        for item in templates:
            if isinstance(item, dict):
                add_item_metrics(
                    item,
                    ["id", "name", "dfd_level", "pattern_type", "structure"],
                    ["name", "pattern_type"],
                    "name",
                    metrics,
                    min_info_len,
                    min_index_len,
                )
        metrics["items"] += len(templates)


def evaluate_validation(data, metrics, min_info_len, min_index_len):
    items = safe_list(data.get("validation_rules"))
    for item in items:
        if isinstance(item, dict):
            add_item_metrics(
                item,
                ["id", "name", "definition", "severity"],
                ["name", "definition", "error_message"],
                "definition",
                metrics,
                min_info_len,
                min_index_len,
            )
    metrics["items"] += len(items)


def evaluate_theory(data, metrics, min_info_len, min_index_len):
    concepts = safe_list(data.get("concepts"))
    for item in concepts:
        if isinstance(item, dict):
            add_item_metrics(
                item,
                ["id", "name", "definition"],
                ["name", "definition"],
                "definition",
                metrics,
                min_info_len,
                min_index_len,
            )
    metrics["items"] += len(concepts)
    principles = safe_list(data.get("principles"))
    for item in principles:
        if isinstance(item, dict):
            add_item_metrics(
                item,
                ["id", "detail"],
                ["detail"],
                "detail",
                metrics,
                min_info_len,
                min_index_len,
            )
    metrics["items"] += len(principles)


def evaluate_domain(data, metrics, min_info_len, min_index_len):
    root_required = ["domain_id", "name", "description"]
    root = {key: data.get(key) for key in root_required}
    add_item_metrics(
        root,
        root_required,
        ["name", "description"],
        "description",
        metrics,
        min_info_len,
        min_index_len,
    )
    metrics["items"] += 1
    terms = safe_list(data.get("terms"))
    for item in terms:
        if isinstance(item, dict):
            add_item_metrics(
                item,
                ["term", "definition"],
                ["term", "definition"],
                "definition",
                metrics,
                min_info_len,
                min_index_len,
            )
    metrics["items"] += len(terms)
    rules = safe_list(data.get("rules"))
    for item in rules:
        if isinstance(item, dict):
            add_item_metrics(
                item,
                ["rule_id", "description"],
                ["description"],
                "description",
                metrics,
                min_info_len,
                min_index_len,
            )
    metrics["items"] += len(rules)
    models = safe_list(data.get("models"))
    for item in models:
        if isinstance(item, dict):
            add_item_metrics(
                item,
                ["entity", "attributes", "relationships"],
                ["entity"],
                "entity",
                metrics,
                min_info_len,
                min_index_len,
            )
    metrics["items"] += len(models)


def evaluate_mappings(data, metrics, min_info_len, min_index_len):
    for key in ["semantic_cues", "linguistic_patterns", "extraction_guidelines"]:
        items = safe_list(data.get(key))
        for item in items:
            if isinstance(item, dict):
                add_item_metrics(
                    item,
                    ["id", "name", "description"],
                    ["name", "description"],
                    "description",
                    metrics,
                    min_info_len,
                    min_index_len,
                )
        metrics["items"] += len(items)


def evaluate_schema_file(data, metrics, min_info_len, min_index_len):
    title = data.get("title")
    add_item_metrics(
        {"title": title},
        ["title"],
        ["title"],
        "title",
        metrics,
        min_info_len,
        min_index_len,
    )
    metrics["items"] += 1


EVALUATORS = {
    "diagrams.dfd.concepts": evaluate_concepts,
    "diagrams.dfd.rules": evaluate_rules,
    "diagrams.dfd.examples": evaluate_examples,
    "diagrams.dfd.levels": evaluate_levels,
    "diagrams.dfd.templates": evaluate_templates,
    "diagrams.dfd.validation": evaluate_validation,
    "theory": evaluate_theory,
    "domain": evaluate_domain,
    "mappings": evaluate_mappings,
    "schema": evaluate_schema_file,
}


def compute_rates(metrics):
    missing_rate = 0
    if metrics["required_fields_total"] > 0:
        missing_rate = metrics["missing_fields"] / metrics["required_fields_total"]
    low_info_rate = 0
    if metrics["text_fields_total"] > 0:
        low_info_rate = metrics["low_info_fields"] / metrics["text_fields_total"]
    indexable_rate = 0
    if metrics["items"] > 0:
        indexable_rate = metrics["indexable_failures"] / metrics["items"]
    duplicate_rate = 0
    if metrics["dup_texts"]:
        normalized = [normalize_text(t) for t in metrics["dup_texts"] if t]
        counter = Counter(normalized)
        dup = sum(count - 1 for count in counter.values() if count > 1)
        duplicate_rate = dup / len(normalized) if normalized else 0
    return {
        "missing_rate": round(missing_rate, 4),
        "low_info_rate": round(low_info_rate, 4),
        "indexable_fail_rate": round(indexable_rate, 4),
        "duplicate_rate": round(duplicate_rate, 4),
    }


def load_schema(schema_path):
    try:
        data = json.loads(schema_path.read_text(encoding="utf-8"))
        if isinstance(data, dict) and "$schema" in data and "properties" in data:
            return data
    except Exception:
        return None
    return None


def new_metrics():
    return {
        "files": 0,
        "items": 0,
        "required_fields_total": 0,
        "missing_fields": 0,
        "text_fields_total": 0,
        "low_info_fields": 0,
        "indexable_failures": 0,
        "dup_texts": [],
    }


def load_baseline(path: Path):
    try:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None
    return None


def build_default_queries():
    return [
        {
            "query": "外部实体是什么",
            "expected_collections": ["se_kb_dfd_concepts"],
            "group": "concept",
        },
        {
            "query": "处理过程的定义",
            "expected_collections": ["se_kb_dfd_concepts"],
            "group": "concept",
        },
        {"query": "数据流含义", "expected_collections": ["se_kb_dfd_concepts"], "group": "concept"},
        {
            "query": "图书馆管理系统数据流图案例",
            "expected_collections": ["se_kb_dfd_examples"],
            "group": "example",
        },
        {
            "query": "ATM 余额查询 DFD 示例",
            "expected_collections": ["se_kb_dfd_examples"],
            "group": "example",
        },
        {
            "query": "电商下单流程数据流图案例",
            "expected_collections": ["se_kb_dfd_examples"],
            "group": "example",
        },
        {"query": "数据平衡规则", "expected_collections": ["se_kb_dfd_rules"], "group": "rule"},
        {"query": "父子图平衡规则", "expected_collections": ["se_kb_dfd_rules"], "group": "rule"},
        {"query": "命名规则约束", "expected_collections": ["se_kb_dfd_rules"], "group": "rule"},
        {
            "query": "顶层图模板",
            "expected_collections": ["se_kb_dfd_templates"],
            "group": "template",
        },
        {"query": "分解模板", "expected_collections": ["se_kb_dfd_templates"], "group": "template"},
        {
            "query": "数据存储交互模板",
            "expected_collections": ["se_kb_dfd_templates"],
            "group": "template",
        },
        {"query": "分层原则", "expected_collections": ["se_kb_dfd_levels"], "group": "level"},
        {"query": "分解规则", "expected_collections": ["se_kb_dfd_levels"], "group": "level"},
        {"query": "层次分解深度", "expected_collections": ["se_kb_dfd_levels"], "group": "level"},
        {"query": "结构化分析是什么", "expected_collections": ["se_kb_theory"], "group": "theory"},
        {"query": "内聚和耦合的定义", "expected_collections": ["se_kb_theory"], "group": "theory"},
        {"query": "软件工程理论原则", "expected_collections": ["se_kb_theory"], "group": "theory"},
    ]


def load_queries(path: Path):
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, list):
            queries = []
            for item in data:
                if not isinstance(item, dict):
                    continue
                query = item.get("query")
                expected = item.get("expected_collections") or []
                group = item.get("group") or "general"
                if query:
                    queries.append(
                        {
                            "query": query,
                            "expected_collections": expected,
                            "group": group,
                        }
                    )
            return queries
    except Exception:
        return None
    return None


def evaluate_recall(queries, top_k):
    from vectorizer.retriever import KnowledgeRetriever

    retriever = KnowledgeRetriever()
    k_values = [1, 3, 5]
    k_values = [k for k in k_values if k <= top_k]
    totals = {k: 0 for k in k_values}
    groups = {}
    details = []
    for item in queries:
        query = item["query"]
        expected = set(item.get("expected_collections") or [])
        group = item.get("group") or "general"
        response = retriever.retrieve(query, top_k=top_k)
        collections = [r.collection for r in response.results]
        hit_at = {}
        for k in k_values:
            hit = any(r.collection in expected for r in response.results[:k])
            hit_at[k] = hit
            if hit:
                totals[k] += 1
        group_stats = groups.setdefault(group, {"total": 0, **{f"hit@{k}": 0 for k in k_values}})
        group_stats["total"] += 1
        for k in k_values:
            if hit_at[k]:
                group_stats[f"hit@{k}"] += 1
        details.append(
            {
                "query": query,
                "group": group,
                "expected_collections": list(expected),
                "intent": response.intent.value if response.intent else None,
                "hit_at": {f"hit@{k}": hit_at[k] for k in k_values},
                "top_collections": collections,
            }
        )
    total_queries = len(queries)
    recall = {
        "top_k": top_k,
        "total_queries": total_queries,
        "hit_rates": {},
        "groups": {},
        "details": details,
    }
    for k in k_values:
        rate = round(totals[k] / total_queries, 4) if total_queries else 0.0
        recall["hit_rates"][f"hit@{k}"] = rate
    for group, stats in groups.items():
        total = stats["total"]
        group_rates = {
            f"hit@{k}": round(stats[f"hit@{k}"] / total, 4) if total else 0.0 for k in k_values
        }
        recall["groups"][group] = {
            "total": total,
            "hit_rates": group_rates,
        }
    return recall


def compute_trend(current, baseline):
    trend = {}
    if "schema_validation" in current and "schema_validation" in baseline:
        curr = current["schema_validation"]
        base = baseline["schema_validation"]
        trend["schema_validation"] = {
            "available_delta": curr.get("available", 0) - base.get("available", 0),
            "passed_delta": curr.get("passed", 0) - base.get("passed", 0),
            "failed_delta": curr.get("failed", 0) - base.get("failed", 0),
            "skipped_delta": curr.get("skipped", 0) - base.get("skipped", 0),
        }
    if "types" in current and "types" in baseline:
        type_trend = {}
        for type_id, metrics in current["types"].items():
            if type_id not in baseline["types"]:
                continue
            base_metrics = baseline["types"][type_id]
            type_trend[type_id] = {
                "missing_rate_delta": round(
                    metrics.get("missing_rate", 0) - base_metrics.get("missing_rate", 0), 4
                ),
                "low_info_rate_delta": round(
                    metrics.get("low_info_rate", 0) - base_metrics.get("low_info_rate", 0), 4
                ),
                "indexable_fail_rate_delta": round(
                    metrics.get("indexable_fail_rate", 0)
                    - base_metrics.get("indexable_fail_rate", 0),
                    4,
                ),
                "duplicate_rate_delta": round(
                    metrics.get("duplicate_rate", 0) - base_metrics.get("duplicate_rate", 0), 4
                ),
            }
        if type_trend:
            trend["types"] = type_trend
    if "retrieval_recall" in current and "retrieval_recall" in baseline:
        curr_rates = current["retrieval_recall"].get("hit_rates", {})
        base_rates = baseline["retrieval_recall"].get("hit_rates", {})
        recall_delta = {}
        for key, value in curr_rates.items():
            recall_delta[f"{key}_delta"] = round(value - base_rates.get(key, 0), 4)
        trend["retrieval_recall"] = recall_delta
    return trend


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--path", default="se_kb/artifacts")
    parser.add_argument("--min-info-len", type=int, default=12)
    parser.add_argument("--min-index-len", type=int, default=30)
    parser.add_argument("--output")
    parser.add_argument("--include-files", action="store_true")
    parser.add_argument("--include-recall", action="store_true")
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--recall-queries")
    parser.add_argument("--baseline")
    args = parser.parse_args()

    root = Path(__file__).resolve().parent.parent
    target = (root / args.path).resolve()
    registry = get_type_registry()
    validator = make_validator()
    schema_cache = {}
    baseline_report = None
    if args.baseline:
        baseline_report = load_baseline((root / args.baseline).resolve())

    per_type = defaultdict(new_metrics)

    schema_stats = {
        "available": 0,
        "passed": 0,
        "failed": 0,
        "skipped": 0,
    }
    schema_failures = []

    files = []
    for file_path in target.rglob("*.json"):
        if file_path.name in EXCLUDE_FILENAMES:
            continue
        files.append(file_path)

    file_reports = []
    for file_path in files:
        type_id = detect_type(file_path)
        if not type_id:
            continue
        try:
            data = json.loads(file_path.read_text(encoding="utf-8"))
        except Exception:
            continue
        metrics = per_type[type_id]
        metrics["files"] += 1
        evaluator = EVALUATORS.get(type_id)
        if evaluator:
            evaluator(data, metrics, args.min_info_len, args.min_index_len)
            if args.include_files:
                file_metrics = new_metrics()
                evaluator(data, file_metrics, args.min_info_len, args.min_index_len)
                rates = compute_rates(file_metrics)
                file_reports.append(
                    {
                        "file": str(file_path),
                        "type_id": type_id,
                        "items": file_metrics["items"],
                        "missing_fields": file_metrics["missing_fields"],
                        "required_fields_total": file_metrics["required_fields_total"],
                        "low_info_fields": file_metrics["low_info_fields"],
                        "text_fields_total": file_metrics["text_fields_total"],
                        "indexable_failures": file_metrics["indexable_failures"],
                        "missing_rate": rates["missing_rate"],
                        "low_info_rate": rates["low_info_rate"],
                        "indexable_fail_rate": rates["indexable_fail_rate"],
                        "duplicate_rate": rates["duplicate_rate"],
                    }
                )
        schema_validated = False
        schema_kt = registry.get(type_id)
        if schema_kt and schema_kt.schema_path:
            schema_path = root / schema_kt.schema_path
            if schema_path.exists():
                if schema_path not in schema_cache:
                    schema_cache[schema_path] = load_schema(schema_path)
                schema_data = schema_cache.get(schema_path)
                if schema_data:
                    schema_stats["available"] += 1
                    ok, errors = validator(data, str(schema_path))
                    schema_validated = True
                    if ok:
                        schema_stats["passed"] += 1
                    else:
                        schema_stats["failed"] += 1
                        schema_failures.append(
                            {
                                "file": str(file_path),
                                "type_id": type_id,
                                "schema": str(schema_path),
                                "errors": errors,
                            }
                        )
        if not schema_validated:
            schema_stats["skipped"] += 1

    report = {"summary": {}, "types": {}, "schema_validation": schema_stats}
    if schema_failures:
        report["schema_validation"]["failures"] = schema_failures
    if args.include_files:
        report["files"] = file_reports
    if args.include_recall:
        queries = None
        if args.recall_queries:
            queries = load_queries((root / args.recall_queries).resolve())
        if not queries:
            queries = build_default_queries()
        report["retrieval_recall"] = evaluate_recall(queries, args.top_k)
    total_files = sum(m["files"] for m in per_type.values())
    total_items = sum(m["items"] for m in per_type.values())
    report["summary"] = {
        "total_files": total_files,
        "total_items": total_items,
        "types": len(per_type),
    }
    for type_id, metrics in per_type.items():
        rates = compute_rates(metrics)
        report["types"][type_id] = {
            "files": metrics["files"],
            "items": metrics["items"],
            "missing_fields": metrics["missing_fields"],
            "required_fields_total": metrics["required_fields_total"],
            "low_info_fields": metrics["low_info_fields"],
            "text_fields_total": metrics["text_fields_total"],
            "indexable_failures": metrics["indexable_failures"],
            "missing_rate": rates["missing_rate"],
            "low_info_rate": rates["low_info_rate"],
            "indexable_fail_rate": rates["indexable_fail_rate"],
            "duplicate_rate": rates["duplicate_rate"],
        }
    if baseline_report:
        trend = compute_trend(report, baseline_report)
        if trend:
            report["trend"] = trend

    output = json.dumps(report, ensure_ascii=False, indent=2)
    if args.output:
        output_path = (root / args.output).resolve()
        output_path.write_text(output, encoding="utf-8")
    else:
        print(output)


if __name__ == "__main__":
    main()
