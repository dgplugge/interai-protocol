"""ACAL (AICP Compressed Agent Language) converter module.

Provides bidirectional conversion between ACAL compact format
and standard AICP message format, per the ACAL v0.1 specification.
"""

from .converter import (
    parse_acal,
    acal_to_aicp,
    aicp_to_acal,
    parse_operations,
    validate_roundtrip,
    MSG_TYPES,
    AGENTS,
    STATUS,
    PRIORITY,
    ROLES,
    PROJECTS,
    DOMAINS,
    ACTIONS,
    LAYERS,
    PHRASES,
)

__all__ = [
    "parse_acal",
    "acal_to_aicp",
    "aicp_to_acal",
    "parse_operations",
    "validate_roundtrip",
    "MSG_TYPES",
    "AGENTS",
    "STATUS",
    "PRIORITY",
    "ROLES",
    "PROJECTS",
    "DOMAINS",
    "ACTIONS",
    "LAYERS",
    "PHRASES",
]
