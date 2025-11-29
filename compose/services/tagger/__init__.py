"""Tag normalization service for semantic vocabulary consistency.

Two-phase approach:
1. Extract raw structured metadata (independent)
2. Normalize using semantic context and vocabulary

Uses SurrealDB for semantic similarity search and archive files for metadata.

Example:
    >>> from compose.services.tagger import VocabularyManager, SemanticTagRetriever
    >>> vocab = VocabularyManager(Path("data/seed_vocabulary_v1.json"))
    >>> retriever = SemanticTagRetriever()
    >>> context = retriever.get_context_tags("AI agent development")

Full pipeline example:
    >>> from compose.services.tagger import create_normalizer, create_retriever
    >>> retriever = create_retriever()
    >>> normalizer = create_normalizer(retriever=retriever, vocabulary=vocab)
    >>> result = await normalizer.normalize_from_transcript(transcript)
"""

from .models import StructuredMetadata, NormalizedMetadata
from .config import TaggerConfig
from .vocabulary import VocabularyManager
from .surrealdb_retriever import SemanticTagRetriever, create_retriever
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
    # Factory functions
    "create_retriever",
    "create_normalizer",
]

__version__ = "0.2.0"
