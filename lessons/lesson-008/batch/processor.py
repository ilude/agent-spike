"""Batch processor for OpenAI Batch API integration."""

import json
import time
from pathlib import Path
from typing import Optional, Any
from datetime import datetime

from openai import OpenAI
from rich.console import Console

# Import cache from lesson-007 (will be in path when running)
try:
    from cache import QdrantCache
except ImportError:
    # For type hints when cache module isn't in path
    QdrantCache = Any

from .models import (
    BatchRequest,
    BatchRequestBody,
    BatchResult,
    TaggingOutput,
    BatchJobInfo,
)
from .prompts import DEFAULT_TAGGING_PROMPT

console = Console()


class BatchProcessor:
    """Processor for OpenAI Batch API operations.

    Handles the complete batch processing workflow:
    1. Prepare batch input from cached content
    2. Submit batch to OpenAI
    3. Monitor batch status
    4. Download and process results
    5. Update cache with tagged content
    """

    def __init__(
        self,
        cache: QdrantCache,
        api_key: str,
        model: str = "gpt-5-nano"
    ):
        """Initialize batch processor.

        Args:
            cache: QdrantCache instance for content storage
            api_key: OpenAI API key
            model: Model to use for batch processing (default: gpt-5-nano)
        """
        self.cache = cache
        self.client = OpenAI(api_key=api_key)
        self.model = model
        self.DEFAULT_TAGGING_PROMPT = DEFAULT_TAGGING_PROMPT

    def prepare_batch_input(
        self,
        filters: Optional[dict[str, Any]] = None,
        system_prompt: Optional[str] = None,
        output_file: Path = Path("batch_input.jsonl"),
        limit: Optional[int] = None,
        transcript_field: str = "transcript",
    ) -> int:
        """Prepare JSONL batch input file from cached content.

        Args:
            filters: Optional metadata filters for cache query
            system_prompt: System prompt for tagging (default: DEFAULT_TAGGING_PROMPT)
            output_file: Path to write JSONL file
            limit: Optional limit on number of items to process
            transcript_field: Field name containing text to analyze

        Returns:
            Number of requests written to file
        """
        if system_prompt is None:
            system_prompt = self.DEFAULT_TAGGING_PROMPT

        # Get content from cache
        console.print(f"[cyan]Loading content from cache...[/cyan]")

        if filters:
            items = self.cache.filter(filters, limit=limit or 1000)
        else:
            # Get all items
            items = self.cache.filter({}, limit=limit or 1000)

        if not items:
            console.print("[yellow]No items found in cache matching filters[/yellow]")
            return 0

        if limit:
            items = items[:limit]

        console.print(f"[green]Found {len(items)} items to process[/green]")

        # Write JSONL file
        console.print(f"[cyan]Writing batch input to {output_file}...[/cyan]")

        with open(output_file, 'w', encoding='utf-8') as f:
            for item in items:
                # Extract transcript/content
                text_content = item.get(transcript_field) or item.get("markdown") or item.get("text")

                if not text_content:
                    console.print(f"[yellow]Skipping item (no text content): {item.get('url', 'unknown')}[/yellow]")
                    continue

                # Truncate if too long (leave room for system prompt)
                max_content_tokens = 120000  # gpt-4o-mini has 128k context
                if len(text_content) > max_content_tokens * 4:  # Rough char-to-token estimate
                    text_content = text_content[:max_content_tokens * 4]
                    console.print(f"[yellow]Truncated long content: {item.get('url', 'unknown')}[/yellow]")

                # Create custom_id (use existing cache key or generate from URL)
                metadata = item.get("_metadata", {})
                custom_id = item.get("video_id") or item.get("url") or str(hash(text_content[:100]))

                # Build request
                request = BatchRequest(
                    custom_id=custom_id,
                    body=BatchRequestBody(
                        model=self.model,
                        messages=[
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": text_content}
                        ],
                        temperature=0.7,
                        max_tokens=500
                    )
                )

                # Write as JSONL (one JSON object per line)
                f.write(request.model_dump_json() + '\n')

        console.print(f"[green]✓ Wrote {len(items)} requests to {output_file}[/green]")
        return len(items)

    def submit_batch(
        self,
        input_file: Path,
        description: Optional[str] = None,
        metadata: Optional[dict] = None
    ) -> str:
        """Submit batch job to OpenAI.

        Args:
            input_file: Path to JSONL input file
            description: Optional description for batch job
            metadata: Optional metadata to attach to batch

        Returns:
            Batch ID for monitoring

        Raises:
            Exception if upload or batch creation fails
        """
        console.print(f"[cyan]Uploading batch file: {input_file}...[/cyan]")

        # Upload file
        with open(input_file, 'rb') as f:
            file_response = self.client.files.create(
                file=f,
                purpose="batch"
            )

        console.print(f"[green]✓ Uploaded file: {file_response.id}[/green]")

        # Create batch
        console.print("[cyan]Creating batch job...[/cyan]")

        batch_metadata = metadata or {}
        if description:
            batch_metadata["description"] = description

        batch_response = self.client.batches.create(
            input_file_id=file_response.id,
            endpoint="/v1/chat/completions",
            completion_window="24h",
            metadata=batch_metadata if batch_metadata else None
        )

        console.print(f"[green]✓ Created batch: {batch_response.id}[/green]")
        console.print(f"[cyan]Status: {batch_response.status}[/cyan]")

        if batch_response.request_counts:
            console.print(f"[cyan]Total requests: {batch_response.request_counts.total}[/cyan]")

        return batch_response.id

    def check_status(self, batch_id: str) -> dict[str, Any]:
        """Check status of a batch job.

        Args:
            batch_id: Batch job ID

        Returns:
            Dictionary with status information
        """
        batch = self.client.batches.retrieve(batch_id)

        status_info = {
            "id": batch.id,
            "status": batch.status,
            "created_at": datetime.fromtimestamp(batch.created_at).isoformat(),
        }

        if batch.in_progress_at:
            status_info["started_at"] = datetime.fromtimestamp(batch.in_progress_at).isoformat()

        if batch.completed_at:
            status_info["completed_at"] = datetime.fromtimestamp(batch.completed_at).isoformat()

        if batch.request_counts:
            counts = batch.request_counts
            status_info["total"] = counts.total
            status_info["completed"] = counts.completed
            status_info["failed"] = counts.failed

            if counts.total > 0:
                progress = (counts.completed / counts.total) * 100
                status_info["progress_pct"] = round(progress, 1)

        if batch.output_file_id:
            status_info["output_file_id"] = batch.output_file_id

        if batch.error_file_id:
            status_info["error_file_id"] = batch.error_file_id

        return status_info

    def download_results(
        self,
        batch_id: str,
        output_file: Path = Path("batch_results.jsonl")
    ) -> Path:
        """Download batch results to file.

        Args:
            batch_id: Batch job ID
            output_file: Path to save results

        Returns:
            Path to downloaded file

        Raises:
            Exception if batch not completed or download fails
        """
        # Check status first
        batch = self.client.batches.retrieve(batch_id)

        if batch.status != "completed":
            raise Exception(f"Batch not completed yet. Status: {batch.status}")

        if not batch.output_file_id:
            raise Exception("No output file available")

        console.print(f"[cyan]Downloading results from {batch.output_file_id}...[/cyan]")

        # Download file content
        file_response = self.client.files.content(batch.output_file_id)

        # Write to file
        with open(output_file, 'wb') as f:
            f.write(file_response.content)

        console.print(f"[green]✓ Downloaded results to {output_file}[/green]")

        # Also download error file if exists
        if batch.error_file_id:
            error_file = output_file.parent / f"{output_file.stem}_errors.jsonl"
            console.print(f"[yellow]Downloading error file to {error_file}...[/yellow]")

            error_response = self.client.files.content(batch.error_file_id)
            with open(error_file, 'wb') as f:
                f.write(error_response.content)

            console.print(f"[yellow]✓ Downloaded errors to {error_file}[/yellow]")

        return output_file

    def process_results(
        self,
        results_file: Path,
        update_cache: bool = True
    ) -> dict[str, Any]:
        """Process batch results and optionally update cache.

        Args:
            results_file: Path to downloaded results JSONL file
            update_cache: Whether to update cache with tags

        Returns:
            Dictionary with processing statistics
        """
        console.print(f"[cyan]Processing results from {results_file}...[/cyan]")

        stats = {
            "total": 0,
            "successful": 0,
            "failed": 0,
            "cache_updated": 0,
            "errors": []
        }

        with open(results_file, 'r', encoding='utf-8') as f:
            for line in f:
                stats["total"] += 1
                result = BatchResult.model_validate_json(line)

                # Check if request was successful
                if result.response.status_code != 200:
                    stats["failed"] += 1
                    error_info = {
                        "custom_id": result.custom_id,
                        "status": result.response.status_code,
                        "error": result.response.body.get("error", {})
                    }
                    stats["errors"].append(error_info)
                    console.print(f"[red]✗ Failed: {result.custom_id} ({result.response.status_code})[/red]")
                    continue

                # Extract tags from response
                try:
                    body = result.response.body
                    content = body["choices"][0]["message"]["content"]

                    # Parse JSON response
                    tagging_output = json.loads(content)
                    tags = tagging_output.get("tags", [])
                    summary = tagging_output.get("summary", "")

                    stats["successful"] += 1

                    # Update cache if requested
                    if update_cache:
                        # Find item in cache by custom_id
                        # Construct cache key (this depends on your caching strategy)
                        cache_key = f"youtube:transcript:{result.custom_id}"

                        if self.cache.exists(cache_key):
                            # Get current item
                            item = self.cache.get(cache_key)

                            # Add tags
                            item["tags"] = tags
                            item["summary"] = summary
                            item["tagged_at"] = datetime.now().isoformat()

                            # Update cache
                            self.cache.set(
                                cache_key,
                                item,
                                metadata={
                                    **item.get("_metadata", {}),
                                    "tags": tags,
                                    "has_summary": True
                                }
                            )

                            stats["cache_updated"] += 1

                except Exception as e:
                    stats["failed"] += 1
                    stats["errors"].append({
                        "custom_id": result.custom_id,
                        "error": str(e),
                        "type": "parsing_error"
                    })
                    console.print(f"[yellow]⚠ Parse error for {result.custom_id}: {e}[/yellow]")

        # Print summary
        console.print("\n[bold green]Processing Complete![/bold green]")
        console.print(f"Total: {stats['total']}")
        console.print(f"[green]Successful: {stats['successful']}[/green]")

        if stats["failed"] > 0:
            console.print(f"[red]Failed: {stats['failed']}[/red]")

        if update_cache:
            console.print(f"[cyan]Cache updated: {stats['cache_updated']} items[/cyan]")

        return stats
