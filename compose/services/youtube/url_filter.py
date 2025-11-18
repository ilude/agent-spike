"""URL filtering service for YouTube video descriptions.

Extracts URLs from video descriptions and filters them using:
1. Heuristic/rule-based filtering (blocks marketing/sponsor URLs)
2. LLM classification for ambiguous URLs (Claude Haiku)
"""

import re
import os
import json
from typing import Optional
from anthropic import Anthropic


# Heuristic blocklist patterns
BLOCKED_DOMAINS = [
    # Checkout/payment
    "gumroad.com",
    "patreon.com/join",
    "ko-fi.com",
    "buymeacoffee.com",
    "circle.so/checkout",
    "memberful.com",
    "teachable.com",
    # Affiliate/tracking
    "bit.ly",
    "tinyurl.com",
    "amzn.to",
    "amazon.com/dp",  # Usually affiliate links
    "shareasale.com",
    "linksynergy.com",
    # Link aggregators
    "linktree",
    "beacons.ai",
    "linktr.ee",
    "bio.link",
    "hoo.be",
    "carrd.co",
]

BLOCKED_URL_PATTERNS = [
    r"checkout",
    r"buy",
    r"order",
    r"cart",
    r"payment",
    r"subscribe",
    r"join",
    r"membership",
    r"\?ref=",
    r"\?affiliate=",
    r"\?utm_",
    r"amzn\.to",
]

SOCIAL_PROFILE_PATTERNS = [
    r"twitter\.com/[^/]+$",  # Profile only, not tweets
    r"x\.com/[^/]+$",
    r"instagram\.com/[^/]+/?$",  # Profile only, not posts
    r"tiktok\.com/@[^/]+$",
    r"facebook\.com/[^/]+$",
    r"linkedin\.com/in/[^/]+$",
    r"youtube\.com/@[^/]+$",  # Channel profile
    r"youtube\.com/c/[^/]+$",
]


def extract_urls(text: str) -> list[str]:
    """Extract all URLs from text using regex.

    Args:
        text: Text to extract URLs from (usually video description)

    Returns:
        List of URLs found in text (deduplicated, preserving order)

    Example:
        >>> extract_urls("Check out https://github.com/user/repo and http://example.com")
        ['https://github.com/user/repo', 'http://example.com']
    """
    # Match http:// and https:// URLs
    url_pattern = r'https?://[^\s<>"{}|\\^`\[\]]+'

    urls = re.findall(url_pattern, text)

    # Remove trailing punctuation (common in descriptions)
    cleaned_urls = []
    for url in urls:
        # Remove trailing punctuation
        url = url.rstrip(".,;:!?)")
        # Remove trailing parenthesis if not balanced
        if url.endswith(")") and url.count("(") < url.count(")"):
            url = url.rstrip(")")
        cleaned_urls.append(url)

    # Deduplicate while preserving order
    seen = set()
    unique_urls = []
    for url in cleaned_urls:
        if url not in seen:
            seen.add(url)
            unique_urls.append(url)

    return unique_urls


def is_blocked_by_heuristic(url: str) -> tuple[bool, Optional[str]]:
    """Check if URL should be blocked by heuristic rules.

    Args:
        url: URL to check

    Returns:
        Tuple of (is_blocked: bool, reason: str | None)

    Example:
        >>> is_blocked_by_heuristic("https://gumroad.com/product")
        (True, "Blocked domain: gumroad.com")
        >>> is_blocked_by_heuristic("https://github.com/user/repo")
        (False, None)
    """
    url_lower = url.lower()

    # Check blocked domains
    for domain in BLOCKED_DOMAINS:
        if domain in url_lower:
            return True, f"Blocked domain: {domain}"

    # Check blocked URL patterns
    for pattern in BLOCKED_URL_PATTERNS:
        if re.search(pattern, url_lower):
            return True, f"Blocked pattern: {pattern}"

    # Check social profile patterns
    for pattern in SOCIAL_PROFILE_PATTERNS:
        if re.search(pattern, url_lower):
            return True, "Social media profile (not content)"

    return False, None


def apply_heuristic_filter(urls: list[str]) -> dict:
    """Apply heuristic filtering to list of URLs.

    Args:
        urls: List of URLs to filter

    Returns:
        Dict with:
            - blocked: list of (url, reason) tuples for blocked URLs
            - remaining: list of URLs that passed heuristic filter

    Example:
        >>> urls = ["https://github.com/user/repo", "https://gumroad.com/product"]
        >>> result = apply_heuristic_filter(urls)
        >>> len(result['blocked'])
        1
        >>> len(result['remaining'])
        1
    """
    blocked = []
    remaining = []

    for url in urls:
        is_blocked, reason = is_blocked_by_heuristic(url)
        if is_blocked:
            blocked.append((url, reason))
        else:
            remaining.append(url)

    return {
        "blocked": blocked,
        "remaining": remaining,
    }


def classify_url_with_llm(
    url: str,
    video_context: dict,
    api_key: Optional[str] = None,
) -> tuple[str, float, str, Optional[dict], float]:
    """Classify URL as 'content' or 'marketing' using Claude Haiku with confidence scoring.

    Args:
        url: URL to classify
        video_context: Dict with video_title, description, etc.
        api_key: Optional Anthropic API key (uses ANTHROPIC_API_KEY env var if not provided)

    Returns:
        Tuple of (classification, confidence, reason, suggested_pattern, cost_usd)
        - classification: "content" or "marketing"
        - confidence: 0.0-1.0 confidence score
        - reason: Explanation of classification
        - suggested_pattern: Dict with pattern info (if confidence > 0.7), or None
        - cost_usd: Estimated cost of API call

    Example:
        >>> context = {"video_title": "Python Tutorial", "description": "Learn Python..."}
        >>> classification, confidence, reason, pattern, cost = classify_url_with_llm("https://docs.python.org", context)
        >>> classification
        'content'
        >>> confidence
        0.95
    """
    api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY not set")

    client = Anthropic(api_key=api_key)

    prompt = f"""You are analyzing a URL found in a YouTube video description.

Video Title: {video_context.get('video_title', 'N/A')}
Video Description (first 500 chars): {video_context.get('description', '')[:500]}

URL to classify: {url}

Task: Classify this URL as either "content" or "marketing" with a confidence score.

- "content" = Educational resources, documentation, tools, code repos, articles, tutorials, relevant references
- "marketing" = Sponsorships, paid products, memberships, affiliate links, promotional content

Also, if you're confident (>0.7) about the classification, suggest a pattern that could be used to auto-classify similar URLs in the future.

Respond in JSON format:
{{
  "classification": "content" or "marketing",
  "confidence": 0.95,  // 0.0-1.0 score
  "reason": "Brief explanation (1 sentence)",
  "suggested_pattern": {{  // Only if confidence > 0.7
    "pattern": "github.com",  // Domain, URL substring, or path component
    "type": "domain",  // "domain", "url_pattern", or "path"
    "rationale": "Why this pattern is reliable"
  }}
}}

If confidence <= 0.7, omit suggested_pattern field."""

    response = client.messages.create(
        model="claude-3-5-haiku-20241022",
        max_tokens=250,  # Increased for pattern suggestion
        messages=[{"role": "user", "content": prompt}],
    )

    # Parse response
    response_text = response.content[0].text.strip()

    # Extract JSON from response (handle markdown code blocks and nested objects)
    # Match nested JSON with suggested_pattern
    json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
    if json_match:
        result = json.loads(json_match.group(0))
        classification = result.get("classification", "marketing")  # Default to marketing if uncertain
        confidence = result.get("confidence", 0.5)  # Default to medium confidence
        reason = result.get("reason", "No reason provided")
        suggested_pattern = result.get("suggested_pattern")  # May be None
    else:
        # Fallback parsing
        classification = "marketing"
        confidence = 0.5
        reason = "Failed to parse LLM response"
        suggested_pattern = None

    # Calculate cost (approximate)
    # Haiku pricing: $0.25 per 1M input tokens, $1.25 per 1M output tokens
    input_tokens = response.usage.input_tokens
    output_tokens = response.usage.output_tokens
    cost_usd = (input_tokens / 1_000_000 * 0.25) + (output_tokens / 1_000_000 * 1.25)

    return classification, confidence, reason, suggested_pattern, cost_usd


def filter_urls(
    description: str,
    video_context: dict,
    video_id: Optional[str] = None,
    use_llm: bool = True,
    pattern_tracker = None,  # Type hint omitted to avoid circular import
    api_key: Optional[str] = None,
) -> dict:
    """Extract and filter URLs from video description with pattern learning.

    Main orchestrator that:
    1. Extracts URLs from description
    2. Applies heuristic filter
    3. Checks learned patterns (if pattern_tracker provided)
    4. Classifies remaining URLs with LLM (if enabled)
    5. Records classifications and learns patterns

    Args:
        description: Video description text
        video_context: Dict with video_title, etc.
        video_id: YouTube video ID (required for pattern_tracker)
        use_llm: Whether to use LLM for classification (default: True)
        pattern_tracker: Optional PatternTracker instance for learning
        api_key: Optional Anthropic API key

    Returns:
        Dict with:
            - all_urls: list[str] - All URLs found
            - blocked_urls: list[str] - URLs blocked by heuristic
            - content_urls: list[str] - URLs classified as content
            - marketing_urls: list[str] - URLs classified as marketing
            - learned_pattern_urls: list[str] - URLs matched by learned patterns
            - llm_classifications: list[dict] - LLM classification details
            - learned_patterns_applied: list[dict] - Learned pattern matches
            - total_llm_cost: float - Total LLM cost in USD

    Example:
        >>> from compose.services.analytics import create_pattern_tracker
        >>> tracker = create_pattern_tracker()
        >>> desc = "Check https://github.com/user/repo and https://gumroad.com/product"
        >>> context = {"video_title": "Tutorial"}
        >>> result = filter_urls(desc, context, video_id="abc123", pattern_tracker=tracker)
        >>> result['content_urls']
        ['https://github.com/user/repo']
    """
    # Extract URLs
    all_urls = extract_urls(description)

    # Apply heuristic filter
    heuristic_result = apply_heuristic_filter(all_urls)
    blocked_urls = [url for url, _ in heuristic_result["blocked"]]
    blocked_reasons = {url: reason for url, reason in heuristic_result["blocked"]}
    remaining_urls = heuristic_result["remaining"]

    # Initialize result
    result = {
        "all_urls": all_urls,
        "blocked_urls": blocked_urls,
        "content_urls": [],
        "marketing_urls": [],
        "learned_pattern_urls": [],
        "llm_classifications": [],
        "learned_patterns_applied": [],
        "total_llm_cost": 0.0,
    }

    # Record heuristic blocks (if pattern tracker provided)
    if pattern_tracker and video_id:
        for url in blocked_urls:
            pattern_tracker.record_classification(
                url=url,
                video_id=video_id,
                classification="marketing",  # Heuristic blocks are assumed marketing
                confidence=1.0,  # Heuristic rules are 100% confident
                method="heuristic",
                reason=blocked_reasons.get(url, "Blocked by heuristic filter"),
            )

    # If no remaining URLs, return early
    if not remaining_urls:
        return result

    # Check learned patterns before LLM
    urls_after_learned_patterns = []
    if pattern_tracker:
        for url in remaining_urls:
            pattern_match = pattern_tracker.check_learned_patterns(url)
            if pattern_match:
                classification, reason, confidence = pattern_match

                result["learned_patterns_applied"].append({
                    "url": url,
                    "classification": classification,
                    "confidence": confidence,
                    "reason": reason,
                })

                result["learned_pattern_urls"].append(url)

                if classification == "content":
                    result["content_urls"].append(url)
                else:
                    result["marketing_urls"].append(url)

                # Record classification
                if video_id:
                    pattern_tracker.record_classification(
                        url=url,
                        video_id=video_id,
                        classification=classification,
                        confidence=confidence,
                        method="learned_pattern",
                        reason=reason,
                    )
            else:
                # No pattern match, needs LLM
                urls_after_learned_patterns.append(url)
    else:
        urls_after_learned_patterns = remaining_urls

    # If no LLM or no URLs left, assume remaining are content
    if not use_llm or not urls_after_learned_patterns:
        result["content_urls"].extend(urls_after_learned_patterns)
        return result

    # Classify remaining URLs with LLM
    for url in urls_after_learned_patterns:
        try:
            classification, confidence, reason, suggested_pattern, cost = classify_url_with_llm(
                url, video_context, api_key
            )

            result["llm_classifications"].append({
                "url": url,
                "classification": classification,
                "confidence": confidence,
                "reason": reason,
                "suggested_pattern": suggested_pattern,
                "cost_usd": cost,
            })

            result["total_llm_cost"] += cost

            if classification == "content":
                result["content_urls"].append(url)
            else:
                result["marketing_urls"].append(url)

            # Record classification
            if pattern_tracker and video_id:
                pattern_tracker.record_classification(
                    url=url,
                    video_id=video_id,
                    classification=classification,
                    confidence=confidence,
                    method="llm",
                    reason=reason,
                    pattern_suggested=suggested_pattern.get("pattern") if suggested_pattern else None,
                )

                # Add high-confidence patterns to learned patterns
                if suggested_pattern and confidence >= 0.7:
                    pattern_tracker.add_learned_pattern(
                        pattern=suggested_pattern.get("pattern"),
                        pattern_type=suggested_pattern.get("type", "domain"),
                        classification=classification,
                        confidence=confidence,
                    )

        except Exception as e:
            # On error, default to marketing (safer to exclude than include)
            result["marketing_urls"].append(url)
            result["llm_classifications"].append({
                "url": url,
                "classification": "marketing",
                "confidence": 0.0,
                "reason": f"LLM error: {str(e)}",
                "suggested_pattern": None,
                "cost_usd": 0.0,
            })

            # Record error classification
            if pattern_tracker and video_id:
                pattern_tracker.record_classification(
                    url=url,
                    video_id=video_id,
                    classification="marketing",
                    confidence=0.0,
                    method="llm",
                    reason=f"LLM error: {str(e)}",
                )

    return result
