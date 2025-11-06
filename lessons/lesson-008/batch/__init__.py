"""Batch processing module for lesson-008: OpenAI Batch API integration.

This module provides tools for cost-effective batch processing of large datasets
using OpenAI's Batch API (50% cost savings compared to real-time API).

Example:
    >>> from batch import BatchProcessor
    >>> from cache import QdrantCache
    >>> cache = QdrantCache(collection_name="content")
    >>> processor = BatchProcessor(cache, api_key="sk-...")
    >>> processor.prepare_batch_input(filters={}, output_file=Path("batch.jsonl"))
    >>> batch_id = processor.submit_batch(Path("batch.jsonl"))
    >>> results = processor.process_results(batch_id)
"""

from .processor import BatchProcessor
from .models import BatchRequest, BatchResult, TaggingOutput
from .prompts import DEFAULT_TAGGING_PROMPT

__all__ = [
    "BatchProcessor",
    "BatchRequest",
    "BatchResult",
    "TaggingOutput",
    "DEFAULT_TAGGING_PROMPT",
]
