"""Composable services for agent-spike project.

Each service follows composition-over-inheritance principles:
- Protocol-first design (interfaces)
- Dependency injection
- Configuration objects
- Factory functions for defaults

Services are designed to be:
- Testable (protocol-based mocking)
- Composable (mix and match implementations)
- Independent (no cross-service imports)
- Reusable (lessons use these, not each other)
"""
