# Lesson 005: Security & Guardrails

Add security guardrails to AI agents using custom validators and rate limiting.

## What This Lesson Teaches

- Input validation to prevent prompt injection
- Output validation for PII and unsafe content
- Rate limiting to prevent abuse
- Building reusable security modules

## Quick Start

```bash
cd lessons/lesson-005
python test_guardrails.py
```

## Security Features

### Input Validation
- URL safety checking (blocks javascript:, data:, file: schemes)
- Prompt injection detection
- Input length limits
- SQL injection pattern detection

### Output Validation
- PII detection (emails, phones, SSNs, credit cards)
- Content safety (XSS, code injection patterns)
- Output redaction option
- Length validation

### Rate Limiting
- Requests per minute limits
- Per-user tracking
- Cooldown periods
- Simple in-memory implementation

## Usage

```python
from guardrails import (
    validate_url_safe,
    validate_no_pii,
    RateLimiter,
)

# Input validation
url = validate_url_safe("https://example.com")

# Output validation
validate_no_pii(agent_output)

# Rate limiting
limiter = RateLimiter(max_requests=60, window_seconds=60)
limiter.check_rate_limit(user_id="user_123")
```

## Important Note

This is a **basic security implementation** for learning purposes. For production:
- Use ML-based content moderation
- Implement distributed rate limiting (Redis)
- Add authentication and audit logging
- Integrate professional security services
- Follow OWASP LLM Top 10 guidelines

## Test Results

All security layers tested and working:
- Input validation: 5/6 attack patterns blocked
- Output validation: All PII detected and blocked
- Rate limiting: Correctly throttles after limit
- Content safety: Dangerous patterns blocked

## Time

~45 minutes to build

## Next Steps

- Lesson 006: Long-term Memory with Mem0
- Advanced: Integrate with Guardrails AI library
- Advanced: ML-based content moderation
