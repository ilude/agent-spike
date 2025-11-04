"""Simple test script for the URL router."""

from coordinator_agent.router import URLRouter, URLType


def test_router():
    """Test URL router with various URLs."""
    test_cases = [
        ("https://www.youtube.com/watch?v=i5kwX7jeWL8", URLType.YOUTUBE),
        ("https://youtu.be/i5kwX7jeWL8", URLType.YOUTUBE),
        ("https://m.youtube.com/watch?v=test", URLType.YOUTUBE),
        ("https://github.com/docling-project/docling", URLType.WEBPAGE),
        ("https://example.com", URLType.WEBPAGE),
        ("not-a-url", URLType.INVALID),
        ("", URLType.INVALID),
    ]

    print("Testing URL Router")
    print("=" * 80)

    all_passed = True
    for url, expected in test_cases:
        actual = URLRouter.classify_url(url)
        passed = actual == expected
        all_passed = all_passed and passed

        status = "PASS" if passed else "FAIL"
        url_display = url if url else "(empty)"
        print(f"{status} {url_display[:50]:50} | Expected: {expected.value:10} | Got: {actual.value}")

    print("=" * 80)
    if all_passed:
        print("All tests PASSED!")
    else:
        print("Some tests FAILED!")

    return all_passed


if __name__ == "__main__":
    success = test_router()
    exit(0 if success else 1)
