"""Pydantic Logfire integration for Pydantic AI agents."""

import os
import sys
import io
import logfire
from pydantic_ai import Agent
from .config import get_logfire_config, is_logfire_enabled

# Global instrumentation state
_instrumentation_enabled = False

# UTF-8 compatible stdout wrapper for Windows
def get_utf8_output():
    """Get UTF-8 compatible output stream for Windows console."""
    if sys.platform == 'win32':
        # On Windows, wrap stdout with UTF-8 encoding
        return io.TextIOWrapper(
            sys.stdout.buffer,
            encoding='utf-8',
            errors='replace',  # Replace unencodable characters
            line_buffering=True
        )
    return sys.stdout


def initialize_logfire() -> bool:
    """
    Initialize Pydantic Logfire and enable Pydantic AI instrumentation.

    Returns:
        True if logfire was initialized, False otherwise.
    """
    global _instrumentation_enabled

    if not is_logfire_enabled():
        print("[Observability] Logfire disabled via config - skipping instrumentation")
        return False

    config = get_logfire_config()

    try:
        # Get UTF-8 compatible output for Windows
        utf8_output = get_utf8_output()

        # Configure logfire with verbose console output
        console_opts = logfire.ConsoleOptions(
            colors="auto",
            min_log_level="debug",  # Show debug-level details including parameters
            verbose=True,  # Enable verbose output with parameters
            include_timestamps=True,  # Show timestamps for each event
            span_style="indented",  # Use indented style (cleaner than show-parents)
            output=utf8_output,  # Use UTF-8 compatible output stream
        )

        if config.token:
            # Cloud/authenticated mode
            logfire.configure(
                token=config.token,
                project_name=config.project_name,
                console=console_opts,
            )
            print(f"[Observability] Logfire configured for project: {config.project_name}")
        else:
            # Local/console-only mode
            logfire.configure(
                send_to_logfire=False,  # Don't send to cloud
                console=console_opts,
            )
            print("[Observability] Logfire running in local/console mode")
            print("   (Traces will be displayed in console with full details)")
            print("   To enable cloud: Get token from https://logfire.pydantic.dev")

        # Enable Pydantic AI instrumentation globally
        if not _instrumentation_enabled:
            # Use logfire's instrument_pydantic_ai for better integration
            logfire.instrument_pydantic_ai()
            _instrumentation_enabled = True
            print("[Observability] Pydantic AI instrumentation enabled")
            print("   Tool parameters and return values will be logged")

        return True

    except Exception as e:
        print(f"[Observability] Failed to initialize Logfire: {e}")
        return False


def get_logfire():
    """
    Get the logfire module for manual instrumentation.

    Returns:
        The logfire module.
    """
    return logfire
