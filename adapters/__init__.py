# Legacy adapters (基于关键词规则)
from .dfd_adapter import DFDAdapter
from .concepts_adapter import ConceptsAdapter
from .rules_adapter import RulesAdapter

# Enhanced adapters (基于 LLM Preselector)
from .enhanced_adapters import (
    EnhancedDFDAdapter,
    EnhancedConceptsAdapter,
    EnhancedRulesAdapter,
    get_enhanced_adapter,
)

# LLM Preselector
from .llm_preselector import (
    LLMPreselector,
    get_preselector,
    preselect_candidates,
    CandidateChunk,
)

__all__ = [
    # Legacy
    'DFDAdapter',
    'ConceptsAdapter', 
    'RulesAdapter',
    # Enhanced
    'EnhancedDFDAdapter',
    'EnhancedConceptsAdapter',
    'EnhancedRulesAdapter',
    'get_enhanced_adapter',
    # Preselector
    'LLMPreselector',
    'get_preselector',
    'preselect_candidates',
    'CandidateChunk',
]
