"""
Prompt registry module for ASKTHEPEOPLE.

Provides versioned prompt management with SHA256 hashing for audit trails.
"""

from .registry import PromptRegistry

__all__ = ["PromptRegistry"]
