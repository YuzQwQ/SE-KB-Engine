from __future__ import annotations

from dataclasses import dataclass, field

from .experiments import PromotionBudgets
from .planning import QueryBounds


@dataclass(frozen=True)
class RetrievalOptimizationConfig:
    default_candidate: str = "hybrid"
    no_answer_threshold: float = 0.01
    lexical_weight: float = 0.55
    query_bounds: QueryBounds = field(default_factory=QueryBounds)
    promotion_budgets: PromotionBudgets = field(
        default_factory=lambda: PromotionBudgets(max_ndcg_regression=0.01)
    )


DEFAULT_RETRIEVAL_CONFIG = RetrievalOptimizationConfig()
