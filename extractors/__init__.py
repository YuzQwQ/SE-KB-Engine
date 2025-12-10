# Two-Stage Extraction Architecture
# Stage 1: Type Router (轻量模型判断类型)
# Stage 2: Specialized Extractors (专用模型结构化抽取)

from .type_router import TypeRouter, route_types
from .specialized_extractors import (
    get_extractor,
    DFDExtractor,
    ConceptsExtractor,
    RulesExtractor,
    PatternsExtractor,
    TransformationsExtractor,
)
from .type_registry import (
    TypeRegistry,
    get_type_registry,
    KnowledgeType,
)
from .pipeline import (
    ExtractionPipeline,
    PipelineResult,
    run_pipeline,
    run_pipeline_from_file,
)

# SE-KB 类型和抽取器 - 严格对应 se_kb/ 目录结构
from .se_kb_types import (
    SE_KB_TYPES,
    get_se_kb_types,
    get_se_kb_type_ids,
)
from .se_kb_extractors import (
    SE_KB_EXTRACTORS,
    get_se_kb_extractor,
    # diagrams/dfd/
    DFDConceptsExtractor,
    DFDExamplesExtractor,
    DFDRulesExtractor,
    DFDTemplatesExtractor,
    DFDValidationExtractor,
    DFDLevelsExtractor,
    # theory/
    TheoryExtractor,
    # mappings/
    MappingsExtractor,
    # schema/
    SchemaExtractor,
    # domain/, examples/, rules/
    DomainExtractor,
    ExamplesExtractor,
    RulesExtractor as SEKBRulesExtractor,
)

__all__ = [
    # Type Router
    'TypeRouter',
    'route_types',
    # Specialized Extractors (legacy)
    'get_extractor',
    'DFDExtractor',
    'ConceptsExtractor',
    'RulesExtractor',
    'PatternsExtractor',
    'TransformationsExtractor',
    # Type Registry
    'TypeRegistry',
    'get_type_registry',
    'KnowledgeType',
    # Pipeline
    'ExtractionPipeline',
    'PipelineResult',
    'run_pipeline',
    'run_pipeline_from_file',
    # SE-KB Types
    'SE_KB_TYPES',
    'get_se_kb_types',
    'get_se_kb_type_ids',
    # SE-KB Extractors
    'SE_KB_EXTRACTORS',
    'get_se_kb_extractor',
    'DFDConceptsExtractor',
    'DFDExamplesExtractor',
    'DFDRulesExtractor',
    'DFDTemplatesExtractor',
    'DFDValidationExtractor',
    'DFDLevelsExtractor',
    'TheoryExtractor',
    'MappingsExtractor',
    'SchemaExtractor',
    'DomainExtractor',
    'ExamplesExtractor',
    'SEKBRulesExtractor',
]

