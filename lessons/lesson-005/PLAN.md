# Lesson 005: Security & Guardrails

## Learning Objectives

- Understand security risks in AI agents
- Implement input validation to prevent prompt injection
- Add output validation for safe content
- Create custom validators for security checks
- Implement rate limiting to prevent abuse
- Build reusable guardrails for all agents

## Project Overview

Add security guardrails to existing agents using Pydantic AI's built-in validation
plus custom security validators.

**Security layers to implement:**
1. Input validation - Prevent malicious/unsafe inputs
2. Output validation - Ensure safe, appropriate responses
3. Content filtering - Block PII, profanity, harmful content
4. Rate limiting - Prevent abuse and excessive API costs
5. URL validation - Ensure safe URLs before processing

## Why Security Matters

**Risks without guardrails:**
- Prompt injection attacks
- Leaking sensitive information
- Generating inappropriate content
- Excessive API costs from abuse
- Processing malicious URLs

**What we'll protect against:**
- Injection attempts in URLs
- PII in outputs (emails, phone numbers, SSNs)
- Excessive requests (DoS)
- Malicious URLs
- Inappropriate content generation

## Technologies

- **Python 3.14** with shared .venv
- **Pydantic AI** - Built-in validation
- **Pydantic** - Custom validators
- **re** (regex) - Pattern matching for security
- **time** - Rate limiting
- **Existing agents** - YouTube, Webpage, Coordinator (from lessons 001-003)

## Architecture

### Before (Lesson 004)
```
User Input → Agent → LLM → Output
(No validation, no limits)
```

### After (Lesson 005)
```
User Input
    ↓
Input Validators (URL safety, injection detection)
    ↓
Rate Limiter (prevent abuse)
    ↓
Agent → LLM
    ↓
Output Validators (PII detection, content filtering)
    ↓
Safe Output
```

## Directory Structure

```
lesson-005/
├── guardrails/
│   ├── __init__.py
│   ├── input_validators.py    # Input validation
│   ├── output_validators.py   # Output validation
│   ├── rate_limiter.py         # Rate limiting
│   └── content_filter.py       # Content filtering
├── PLAN.md                     # This file
├── README.md                   # Quick reference
├── test_guardrails.py          # Test security features
└── COMPLETE.md                 # Post-completion summary
```

## Implementation Steps

### 1. Input Validation (~15 min)

**Create input validators:**
- URL safety checker (detect javascript:, data:, file: schemes)
- Length limits (prevent token overflow)
- Character validation (detect SQL injection patterns)
- Prompt injection detection (common patterns)

**Implementation:**
```python
def validate_url_safe(url: str) -> str:
    \"\"\"Validate URL is safe to process.\"\"\"
    # Check for dangerous schemes
    # Check for injection patterns
    # Return validated URL or raise ValueError
```

### 2. Output Validation (~15 min)

**Create output validators:**
- PII detection (emails, phone numbers, SSNs, credit cards)
- Profanity filter (optional, basic patterns)
- Sensitive data leakage detection
- Length validation

**Implementation:**
```python
def validate_no_pii(text: str) -> str:
    \"\"\"Ensure output doesn't contain PII.\"\"\"
    # Detect emails, phones, SSNs
    # Raise ValidationError if found
```

### 3. Rate Limiting (~10 min)

**Simple in-memory rate limiter:**
- Requests per minute limit
- Per-user limits (using simple string identifier)
- Cooldown periods

**Implementation:**
```python
class RateLimiter:
    def check_rate_limit(self, user_id: str) -> bool:
        # Check if user exceeded limits
        # Update request count
```

### 4. Content Filtering (~10 min)

**Content safety checks:**
- Basic profanity filter
- Harmful content patterns
- Safe-for-work validation

### 5. Integration with Agents (~15 min)

**Add guardrails to existing agents:**
- Wrap agent calls with validators
- Create guarded versions of agents
- Test with attack vectors

### 6. Testing & Validation (~10 min)

**Test scenarios:**
1. Normal inputs (should pass)
2. Prompt injection attempts (should block)
3. URL with javascript: scheme (should block)
4. Output with PII (should block/redact)
5. Rate limit exceeded (should block)
6. Malicious content (should block)

## Expected Output

### Safe Input
```bash
python test_guardrails.py

Input: https://www.youtube.com/watch?v=dQw4w9WgXcQ
✓ Input validation passed
✓ Rate limit check passed
✓ Agent processing...
✓ Output validation passed
Result: {tags: [...], summary: "..."}
```

### Blocked: Prompt Injection
```bash
Input: https://evil.com/"><script>alert('xss')</script>
✗ Input validation FAILED: Dangerous URL scheme detected
Request blocked for security.
```

### Blocked: PII in Output
```bash
Input: https://example.com/contact
Agent output: "Contact us at support@example.com or call 555-1234"
✗ Output validation FAILED: PII detected (email, phone)
Output redacted for privacy.
```

### Blocked: Rate Limit
```bash
Request 61 from user_123
✗ Rate limit exceeded: 60 requests/minute
Please wait 45 seconds before retrying.
```

## Security Patterns

### 1. Defense in Depth
- Multiple validation layers
- Input AND output checking
- Rate limiting as fallback

### 2. Fail Secure
- Block by default
- Explicit allow lists
- Clear error messages

### 3. Logging & Monitoring
- Log all security events
- Track blocked requests
- Monitor for attack patterns

## Success Criteria

- ✅ Input validation blocks malicious URLs
- ✅ Output validation detects PII
- ✅ Rate limiting prevents abuse
- ✅ Content filter blocks inappropriate content
- ✅ Normal requests pass through unchanged
- ✅ Clear error messages for blocked requests
- ✅ Minimal performance impact (<100ms overhead)

## Limitations & Trade-offs

**This is NOT a complete security solution:**
- Basic pattern matching (not ML-based detection)
- Simple rate limiting (not distributed)
- No CAPTCHA or advanced bot detection
- Basic PII patterns (won't catch everything)

**For production, you'd add:**
- More sophisticated NLP-based detection
- Distributed rate limiting (Redis)
- Integration with security services
- User authentication
- Audit logging
- Security headers and CORS

## Next Steps (Future Lessons)

After understanding basic security:
- **Lesson 006**: Long-term Memory (track user behavior for anomaly detection)
- **Lesson 011**: Error Handling (graceful security failures)
- **Advanced**: Integrate with Guardrails AI library
- **Advanced**: ML-based content moderation

## Resources

- [Pydantic Validators](https://docs.pydantic.dev/latest/concepts/validators/)
- [OWASP LLM Top 10](https://owasp.org/www-project-top-10-for-large-language-model-applications/)
- [Pydantic AI Output Validation](https://ai.pydantic.dev/output/)
- [Prompt Injection Examples](https://github.com/jthack/PIPE)

## Notes

This lesson focuses on **practical, implementable security** rather than comprehensive enterprise-grade security. It teaches:
- How to think about AI security
- Basic patterns you can implement immediately
- Foundation for more advanced security later

**Philosophy**: Start with simple, working security today, enhance iteratively.
