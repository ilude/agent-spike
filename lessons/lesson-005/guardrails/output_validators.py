"""Output validation for security guardrails."""

import re
from typing import Tuple


class OutputValidationError(ValueError):
    """Raised when output validation fails for security reasons."""

    pass


# PII Detection Patterns
EMAIL_PATTERN = r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"
PHONE_PATTERN = r"\b\d{3}[-.]?\d{3}[-.]?\d{4}\b"
SSN_PATTERN = r"\b\d{3}-\d{2}-\d{4}\b"
CREDIT_CARD_PATTERN = r"\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b"

# Profanity patterns (basic - extend as needed)
PROFANITY_PATTERNS = [
    r"\bass\b",
    r"\bdamn\b",
    r"\bhell\b",
    r"\bshit\b",
]


def detect_pii(text: str) -> list[Tuple[str, str]]:
    """
    Detect PII (Personally Identifiable Information) in text.

    Detects:
    - Email addresses
    - Phone numbers
    - Social Security Numbers
    - Credit card numbers

    Args:
        text: Text to scan for PII

    Returns:
        List of (pii_type, matched_text) tuples
    """
    pii_found = []

    # Check for emails
    emails = re.findall(EMAIL_PATTERN, text)
    for email in emails:
        pii_found.append(("email", email))

    # Check for phone numbers
    phones = re.findall(PHONE_PATTERN, text)
    for phone in phones:
        pii_found.append(("phone", phone))

    # Check for SSNs
    ssns = re.findall(SSN_PATTERN, text)
    for ssn in ssns:
        pii_found.append(("ssn", ssn))

    # Check for credit cards
    cards = re.findall(CREDIT_CARD_PATTERN, text)
    for card in cards:
        pii_found.append(("credit_card", card))

    return pii_found


def validate_no_pii(text: str, allow_emails: bool = False) -> str:
    """
    Validate that output contains no PII.

    Args:
        text: Text to validate
        allow_emails: If True, email addresses are allowed

    Returns:
        Validated text (same as input)

    Raises:
        OutputValidationError: If PII is detected
    """
    pii_found = detect_pii(text)

    # Filter out emails if allowed
    if allow_emails:
        pii_found = [(type_, val) for type_, val in pii_found if type_ != "email"]

    if pii_found:
        pii_types = {type_ for type_, _ in pii_found}
        raise OutputValidationError(
            f"PII detected in output: {', '.join(sorted(pii_types))}. "
            f"Output blocked for privacy protection."
        )

    return text


def redact_pii(text: str, allow_emails: bool = False) -> str:
    """
    Redact PII from text instead of blocking entirely.

    Args:
        text: Text to redact PII from
        allow_emails: If True, don't redact email addresses

    Returns:
        Text with PII redacted
    """
    result = text

    # Redact emails
    if not allow_emails:
        result = re.sub(EMAIL_PATTERN, "[EMAIL_REDACTED]", result)

    # Redact phone numbers
    result = re.sub(PHONE_PATTERN, "[PHONE_REDACTED]", result)

    # Redact SSNs
    result = re.sub(SSN_PATTERN, "[SSN_REDACTED]", result)

    # Redact credit cards
    result = re.sub(CREDIT_CARD_PATTERN, "[CARD_REDACTED]", result)

    return result


def detect_profanity(text: str) -> list[str]:
    """
    Detect profanity in text (basic filter).

    Args:
        text: Text to check

    Returns:
        List of profane words found
    """
    profanity_found = []
    text_lower = text.lower()

    for pattern in PROFANITY_PATTERNS:
        matches = re.findall(pattern, text_lower, re.IGNORECASE)
        profanity_found.extend(matches)

    return profanity_found


def validate_content_safe(
    text: str,
    check_profanity: bool = False,
    max_length: int = 50000,
) -> str:
    """
    Validate content is safe and appropriate.

    Args:
        text: Text to validate
        check_profanity: If True, check for profanity
        max_length: Maximum allowed output length

    Returns:
        Validated text (same as input)

    Raises:
        OutputValidationError: If content is unsafe
    """
    # Length check
    if len(text) > max_length:
        raise OutputValidationError(
            f"Output exceeds maximum length ({len(text)} > {max_length})"
        )

    # Profanity check (if enabled)
    if check_profanity:
        profanity = detect_profanity(text)
        if profanity:
            raise OutputValidationError(
                f"Inappropriate content detected. Output blocked."
            )

    # Check for code injection attempts in output
    dangerous_patterns = [
        r"<script",
        r"javascript:",
        r"eval\s*\(",
        r"__import__",
    ]

    for pattern in dangerous_patterns:
        if re.search(pattern, text, re.IGNORECASE):
            raise OutputValidationError(
                "Potentially dangerous pattern detected in output"
            )

    return text


def validate_output_complete(
    text: str,
    allow_pii: bool = False,
    allow_emails: bool = False,
    check_profanity: bool = False,
) -> str:
    """
    Complete output validation pipeline.

    Args:
        text: Text to validate
        allow_pii: If True, skip PII check entirely
        allow_emails: If True, allow emails (but check other PII)
        check_profanity: If True, check for profanity

    Returns:
        Validated text

    Raises:
        OutputValidationError: If any validation fails
    """
    # Content safety check
    validate_content_safe(text, check_profanity=check_profanity)

    # PII check
    if not allow_pii:
        validate_no_pii(text, allow_emails=allow_emails)

    return text
