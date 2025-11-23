"""Two-phase tag normalization agent."""

import json
import os
from typing import Dict, List, Optional, Set

from pydantic_ai import Agent

from .config import DEFAULT_MODEL, get_ollama_url
from .models import StructuredMetadata, NormalizedMetadata
from .retriever import SemanticTagRetriever
from .vocabulary import VocabularyManager


def _configure_ollama_host(model: str) -> None:
    """Configure OLLAMA_BASE_URL environment variable for remote Ollama server."""
    if model.startswith("ollama:"):
        ollama_url = get_ollama_url()
        # pydantic-ai uses OLLAMA_BASE_URL env var
        os.environ["OLLAMA_BASE_URL"] = ollama_url


class TagNormalizer:
    """Two-phase tag normalization system."""

    def __init__(
        self,
        model: str = DEFAULT_MODEL,
        retriever: Optional[SemanticTagRetriever] = None,
        vocabulary: Optional[VocabularyManager] = None,
    ):
        """Initialize normalizer.

        Args:
            model: LLM model to use (e.g., "ollama:qwen2.5:7b" or "claude-3-5-haiku-20241022")
            retriever: Semantic tag retriever for context
            vocabulary: Vocabulary manager for canonical forms
        """
        self.model = model
        self.retriever = retriever
        self.vocabulary = vocabulary

        # Configure Ollama host if using Ollama model
        _configure_ollama_host(model)

        # Create Phase 1 agent (raw extraction)
        self.phase1_agent = Agent(
            self.model,
            system_prompt=self._get_phase1_prompt(),
        )

        # Create Phase 2 agent (normalization)
        self.phase2_agent = Agent(
            self.model,
            system_prompt=self._get_phase2_prompt(),
        )

    def _get_phase1_prompt(self) -> str:
        """Get Phase 1 system prompt for raw extraction."""
        return """You are an expert content analyzer that extracts structured metadata from text.

Your task is to analyze the provided content and extract comprehensive metadata as a JSON object.

Return ONLY valid JSON in the following structure:

**Title**: Generate a clear, descriptive title (5-10 words)

**Summary**: Write a 1-2 sentence summary of the main points

**Subject Matter**: Extract 3-7 specific topics covered (e.g., "ai-agent-tools", "llm-optimization")
- Use lowercase with hyphens
- Be specific, not generic (e.g., "prompt-engineering" not "ai")
- Cover the main topics comprehensively

**Entities**: Named things mentioned
- people: Names of individuals
- companies: Organizations, companies, products
- named_things: Specific tools, technologies, frameworks

**Techniques or Concepts**: Methods, patterns, domain-specific terminology
- Examples: "few-shot-prompting", "retrieval-augmented-generation", "fine-tuning"

**Tools or Materials**: Software, libraries, frameworks, physical tools
- Examples: "langchain", "openai-api", "qdrant", "docker"

**Content Style**: The presentation style (pick one)
- tutorial | demonstration | critique | analysis | news | interview | review | guide | walkthrough

**Difficulty**: Technical complexity level
- beginner | intermediate | advanced | null (if unclear)

**Key Points**: 3-5 specific takeaways with numbers/measurements when applicable
- Focus on actionable insights
- Include concrete details

**References**: External resources mentioned (blog posts, repos, docs, papers)
- Include URLs or clear references

IMPORTANT:
- Return ONLY valid JSON, no markdown formatting
- Be thorough but accurate
- Extract what's actually in the content, don't infer
- Use consistent formatting (lowercase-with-hyphens for tags)
- Avoid generic terms like "ai" or "technology" unless they're the main focus

Example output format:
{
  "title": "Building AI Agents with Claude",
  "summary": "Tutorial on creating AI agents using Claude API and prompt engineering techniques.",
  "subject_matter": ["ai-agents", "claude-api", "prompt-engineering"],
  "entities": {
    "people": [],
    "companies": ["anthropic"],
    "named_things": ["claude"]
  },
  "techniques_or_concepts": ["few-shot-prompting", "chain-of-thought"],
  "tools_or_materials": ["claude-api", "python"],
  "content_style": "tutorial",
  "difficulty": "intermediate",
  "key_points": ["Learn to build agents", "Use Claude API", "Apply prompt patterns"],
  "references": []
}
"""

    def _get_phase2_prompt(self) -> str:
        """Get Phase 2 system prompt for normalization."""
        return """You are an expert tag normalizer that ensures consistent vocabulary across a content corpus.

Your task is to normalize the provided raw metadata to match the existing vocabulary used in similar content.

**Normalization Guidelines:**

1. **Use Existing Tags When Possible**
   - If a concept matches an existing tag, use the existing tag
   - Example: If raw tag is "llm" but corpus uses "large-language-models", use the corpus version

2. **Preserve New Concepts**
   - If the raw tag represents a truly new concept not in the corpus, keep it
   - Don't force-fit new ideas into existing tags

3. **Consolidate Variations**
   - "ai-agents" and "artificial-intelligence-agents" → pick the more common one
   - "llm" and "large-language-models" → use "large-language-models"

4. **Maintain Specificity**
   - Don't merge specific tags into generic ones
   - "prompt-engineering" should not become "ai"

5. **Consistency Rules**
   - Always use lowercase-with-hyphens format
   - Singular vs plural: follow corpus conventions
   - Abbreviations: prefer full forms if corpus uses them

**Process:**
1. Compare each raw tag with the context tags
2. If there's a semantic match, use the context tag
3. If it's a new concept, keep the raw tag
4. Ensure final output uses consistent formatting

The goal is vocabulary consistency while preserving semantic accuracy.

**Output Format:**
Return ONLY valid JSON with the same structure as the input, just with normalized tag values.
No markdown formatting, no explanations, just the JSON object.
"""

    async def extract_raw_metadata(
        self,
        transcript: str,
        video_title: str = "unknown",
    ) -> StructuredMetadata:
        """Phase 1: Extract raw structured metadata from transcript.

        Args:
            transcript: Video transcript or content text
            video_title: Optional video title

        Returns:
            Raw structured metadata
        """
        # Build prompt
        prompt = f"Analyze this content and extract structured metadata as JSON.\n\n"
        prompt += f"Content:\n{transcript[:15000]}"

        # Run Phase 1 agent
        result = await self.phase1_agent.run(prompt)

        # Parse JSON response
        response_text = result.output if hasattr(result, 'output') else str(result)

        # Strip markdown code blocks if present
        if "```json" in response_text:
            response_text = response_text.split("```json")[1].split("```")[0].strip()
        elif "```" in response_text:
            response_text = response_text.split("```")[1].split("```")[0].strip()

        # Parse JSON
        data = json.loads(response_text)
        return StructuredMetadata(**data)

    async def normalize_metadata(
        self,
        raw_metadata: StructuredMetadata,
        context_tags: Optional[Dict[str, Set[str]]] = None,
        vocabulary_tags: Optional[List[str]] = None,
    ) -> NormalizedMetadata:
        """Phase 2: Normalize metadata using context and vocabulary.

        Args:
            raw_metadata: Raw metadata from Phase 1
            context_tags: Tags from similar content
            vocabulary_tags: Canonical tags from vocabulary

        Returns:
            Normalized metadata
        """
        # Build normalization prompt
        prompt = "Normalize this raw metadata to match the existing vocabulary.\n\n"

        # Add raw metadata
        prompt += "**Raw Metadata:**\n"
        prompt += f"Title: {raw_metadata.title}\n"
        prompt += f"Subject Matter: {', '.join(raw_metadata.subject_matter)}\n"
        if raw_metadata.entities:
            for entity_type, entities in raw_metadata.entities.items():
                prompt += f"{entity_type.title()}: {', '.join(entities)}\n"
        prompt += f"Techniques: {', '.join(raw_metadata.techniques_or_concepts)}\n"
        prompt += f"Tools: {', '.join(raw_metadata.tools_or_materials)}\n\n"

        # Add context from similar content
        if context_tags:
            prompt += "**Context from Similar Content:**\n"
            for category, tags in context_tags.items():
                if tags:
                    tag_list = sorted(list(tags))[:15]
                    category_name = category.replace("_", " ").title()
                    prompt += f"{category_name}: {', '.join(tag_list)}\n"
            prompt += "\n"

        # Add vocabulary reference
        if vocabulary_tags:
            prompt += "**Common Vocabulary (Top Tags):**\n"
            prompt += f"{', '.join(vocabulary_tags[:30])}\n\n"

        prompt += "Now normalize the raw metadata to use consistent vocabulary.\n"
        prompt += "Return ONLY the JSON object with normalized values."

        # Run Phase 2 agent
        result = await self.phase2_agent.run(prompt)

        # Parse JSON response
        response_text = result.output if hasattr(result, 'output') else str(result)

        # Strip markdown code blocks if present
        if "```json" in response_text:
            response_text = response_text.split("```json")[1].split("```")[0].strip()
        elif "```" in response_text:
            response_text = response_text.split("```")[1].split("```")[0].strip()

        # Parse JSON
        data = json.loads(response_text)

        # Fields that should be lists
        list_fields = {
            "subject_matter", "techniques_or_concepts", "tools_or_materials",
            "key_points", "references"
        }

        # Normalize field names (handle LLM returning capitalized keys)
        normalized_data = {}
        for key, value in data.items():
            # Convert to lowercase to match model field names
            normalized_key = key.lower().replace(" ", "_")

            # Handle string values that should be lists
            if normalized_key in list_fields and isinstance(value, str):
                # Split comma-separated strings into lists
                value = [v.strip() for v in value.split(",") if v.strip()]

            normalized_data[normalized_key] = value

        return NormalizedMetadata(**normalized_data)

    async def normalize_from_transcript(
        self,
        transcript: str,
        video_title: str = "unknown",
        use_semantic_context: bool = True,
        use_vocabulary: bool = True,
    ) -> Dict[str, StructuredMetadata]:
        """Full two-phase normalization pipeline.

        Args:
            transcript: Video transcript or content text
            video_title: Optional video title
            use_semantic_context: Use context from similar content
            use_vocabulary: Use vocabulary for canonical forms

        Returns:
            Dict with both raw and normalized metadata
        """
        # Phase 1: Extract raw metadata
        raw = await self.extract_raw_metadata(transcript, video_title)

        # Get context for normalization
        context_tags = None
        if use_semantic_context and self.retriever:
            context_tags = self.retriever.get_context_tags(
                transcript[:1000],  # Use first 1000 chars for similarity
                limit=5
            )

        # Get vocabulary tags
        vocabulary_tags = None
        if use_vocabulary and self.vocabulary:
            vocabulary_tags = self.vocabulary.get_all_tags()

        # Phase 2: Normalize
        normalized = await self.normalize_metadata(
            raw,
            context_tags=context_tags,
            vocabulary_tags=vocabulary_tags
        )

        return {
            "raw": raw,
            "normalized": normalized,
        }


def create_normalizer(
    model: str = DEFAULT_MODEL,
    retriever: Optional[SemanticTagRetriever] = None,
    vocabulary: Optional[VocabularyManager] = None,
) -> TagNormalizer:
    """Create a tag normalizer.

    Args:
        model: LLM model to use (default: ollama:qwen2.5:7b for free local inference)
        retriever: Optional semantic retriever for context
        vocabulary: Optional vocabulary manager

    Returns:
        TagNormalizer instance
    """
    return TagNormalizer(
        model=model,
        retriever=retriever,
        vocabulary=vocabulary
    )
