"""Utility modules for Authoricy SEO Analyzer."""

from .config import Settings, get_settings
from .ordering import (
    generate_first_position,
    generate_position_at_end,
    generate_position_at_start,
    generate_position_between,
    generate_n_positions,
    validate_position,
    normalize_positions,
)

__all__ = [
    "Settings",
    "get_settings",
    # Lexicographic ordering
    "generate_first_position",
    "generate_position_at_end",
    "generate_position_at_start",
    "generate_position_between",
    "generate_n_positions",
    "validate_position",
    "normalize_positions",
]
