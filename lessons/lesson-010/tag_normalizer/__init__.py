"""Tag Normalization System - Re-exports from tools.services.tagger.

This module now imports from the productionized service in tools/.
Kept for backward compatibility with lesson-010 scripts.
"""

import sys
from pathlib import Path

# Bootstrap to import lesson_base
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from lessons.lesson_base import setup_lesson_environment
setup_lesson_environment()

# Re-export everything from the production service
from tools.services.tagger import (
    StructuredMetadata,
    NormalizedMetadata,
    TaggerConfig,
    VocabularyManager,
    SemanticTagRetriever,
    TagNormalizer,
    create_retriever,
    create_normalizer,
)

__all__ = [
    "StructuredMetadata",
    "NormalizedMetadata",
    "TaggerConfig",
    "VocabularyManager",
    "SemanticTagRetriever",
    "TagNormalizer",
    "create_retriever",
    "create_normalizer",
]

__version__ = "0.1.0"
