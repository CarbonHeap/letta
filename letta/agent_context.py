"""
Agent context utilities for passing agent-specific settings through the call stack.
This module provides a thread-safe way to pass agent settings like include_timestamps
without modifying every function signature in the call chain.
"""

from contextvars import ContextVar
from typing import Optional

# Context variable to store agent-specific settings
_agent_settings: ContextVar[Optional[dict]] = ContextVar('agent_settings', default=None)


def set_agent_settings(settings: dict) -> None:
    """Set agent-specific settings in the current context."""
    _agent_settings.set(settings)


def get_agent_settings() -> Optional[dict]:
    """Get agent-specific settings from the current context."""
    return _agent_settings.get()


def get_include_timestamps() -> bool:
    """Get the include_timestamps setting for the current agent."""
    settings = get_agent_settings()
    if settings and 'include_timestamps' in settings:
        return settings['include_timestamps']
    return False


def clear_agent_settings() -> None:
    """Clear agent settings from the current context."""
    _agent_settings.set(None)