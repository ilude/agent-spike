"""Tag normalization service for semantic vocabulary consistency.

Two-phase approach:
1. Extract raw structured metadata (independent)
2. Normalize using semantic context and vocabulary

Example:
    >>> from compose.services.tagger import create_normalizer, create_retriever
    >>> from compose.services.tagger import VocabularyManager
    >>>
    >>> # Create components
    >>> vocab = VocabularyManager(Path("data/seed_vocabulary_v1.json"))
    >>> retriever = create_retriever()
    >>> normalizer = create_normalizer(vocabulary=vocab, retriever=retriever)
    >>>
    >>> # Normalize content
    >>> result = await normalizer.normalize_from_transcript(transcript)
    >>> print(result['normalized'].subject_matter)
"""

from .models import StructuredMetadata, NormalizedMetadata
from .config import TaggerConfig
from .vocabulary import VocabularyManager
from .retriever import SemanticTagRetriever, create_retriever
from .normalizer import TagNormalizer, create_normalizer

__all__ = [
    # Models
    "StructuredMetadata",
    "NormalizedMetadata",
    # Configuration
    "TaggerConfig",
    # Components
    "VocabularyManager",
    "SemanticTagRetriever",
    "TagNormalizer",
    # Factories
    "create_retriever",
    "create_normalizer",
]

__version__ = "0.1.0"
