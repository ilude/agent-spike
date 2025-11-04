"""Input validation for security guardrails."""

import re
from urllib.parse import urlparse
from typing import Optional


class InputValidationError(ValueError):
    """Raised when input validation fails for security reasons."""

    pass


# Dangerous URL schemes
DANGEROUS_SCHEMES = {"javascript", "data", "file", "vbscript"}

# Prompt injection patterns
INJECTION_PATTERNS = [
    r"ignore\s+(previous|all|above)\s+instructions",
    r"disregard\s+(previous|all|above)",
    r"system\s*:\s*you\s+are",
    r"</?\s*system\s*>",
    r"<\s*script\s*>",
    r"eval\s*\(",
    r"__import__\s*\(",
]

# SQL injection patterns (basic)
SQL_INJECTION_PATTERNS = [
    r";\s*drop\s+table",
    r";\s*delete\s+from",
    r"union\s+select",
    r"'.*or.*'.*=.*'",
]


def validate_url_safe(url: str) -> str:
    """
    Validate URL is safe to process.

    Checks for:
    - Dangerous URL schemes (javascript:, data:, etc.)
    - Basic injection patterns
    - Malformed URLs

    Args:
        url: URL to validate

    Returns:
        Validated URL (same as input)

    Raises:
        InputValidationError: If URL is potentially unsafe
    """
    if not url or not isinstance(url, str):
        raise InputValidationError("URL must be a non-empty string")

    # Check length
    if len(url) > 2048:
        raise InputValidationError("URL exceeds maximum length (2048 characters)")

    try:
        parsed = urlparse(url)
    except Exception as e:
        raise InputValidationError(f"Malformed URL: {e}")

    # Check for dangerous schemes
    scheme = parsed.scheme.lower()
    if scheme in DANGEROUS_SCHEMES:
        raise InputValidationError(
            f"Dangerous URL scheme detected: {scheme}://"
        )

    # Check for common injection patterns in URL
    url_lower = url.lower()
    for pattern in INJECTION_PATTERNS + SQL_INJECTION_PATTERNS:
        if re.search(pattern, url_lower, re.IGNORECASE):
            raise InputValidationError(
                "Potential injection pattern detected in URL"
            )

    # Basic XSS check
    if "<script" in url_lower or "javascript:" in url_lower:
        raise InputValidationError("Potential XSS pattern detected in URL")

    return url


def validate_input_length(
    text: str, max_length: int = 10000, field_name: str = "input"
) -> str:
    """
    Validate input length is within acceptable limits.

    Args:
        text: Input text to validate
        max_length: Maximum allowed length (default: 10000)
        field_name: Name of field for error message

    Returns:
        Validated text (same as input)

    Raises:
        InputValidationError: If text exceeds max_length
    """
    if not isinstance(text, str):
        raise InputValidationError(f"{field_name} must be a string")

    if len(text) > max_length:
        raise InputValidationError(
            f"{field_name} exceeds maximum length "
            f"({len(text)} > {max_length} characters)"
        )

    if len(text) == 0:
        raise InputValidationError(f"{field_name} cannot be empty")

    return text


def detect_prompt_injection(text: str) -> Optional[str]:
    """
    Detect potential prompt injection attempts.

    Checks for common prompt injection patterns like:
    - "Ignore previous instructions"
    - System prompt override attempts
    - Code execution patterns

    Args:
        text: Text to check for injection patterns

    Returns:
        Description of detected pattern, or None if no injection detected

    Raises:
        InputValidationError: If potential injection is detected
    """
    text_lower = text.lower()

    # Check each pattern
    for pattern in INJECTION_PATTERNS:
        match = re.search(pattern, text_lower, re.IGNORECASE)
        if match:
            raise InputValidationError(
                f"Potential prompt injection detected: {match.group()}"
            )

    # Check for excessive special characters (potential obfuscation)
    special_chars = sum(1 for c in text if not c.isalnum() and not c.isspace())
    if len(text) > 0 and (special_chars / len(text)) > 0.3:
        raise InputValidationError(
            "Excessive special characters detected (potential obfuscation)"
        )

    return None


def validate_url_input(url: str) -> str:
    """
    Complete input validation for URL inputs.

    Combines multiple validation checks:
    - URL safety
    - Length validation
    - Injection detection

    Args:
        url: URL to validate

    Returns:
        Validated URL

    Raises:
        InputValidationError: If any validation check fails
    """
    # Length check
    validate_input_length(url, max_length=2048, field_name="URL")

    # Injection check
    detect_prompt_injection(url)

    # URL safety check
    validate_url_safe(url)

    return url
