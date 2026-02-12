"""Shared configuration utilities for CIM database connectors.

This module provides helper functions to manage configuration state
from the cimgraph library, reducing code duplication across connectors.
"""

from cimgraph.databases import (
    get_cim_profile,
    get_database,
    get_host,
    get_iec61970_301,
    get_namespace,
    get_password,
    get_port,
    get_url,
    get_username,
)


def clear_cim_config_cache():
    """Clear all cached CIM configuration values from cimgraph.

    Call this before retrieving fresh configuration to ensure
    environment variable changes are reflected. The cimgraph library
    uses @lru_cache decorators on its getter functions, so we must
    explicitly clear them to pick up new values.
    """
    get_url.cache_clear()
    get_namespace.cache_clear()
    get_cim_profile.cache_clear()
    get_iec61970_301.cache_clear()
    get_username.cache_clear()
    get_password.cache_clear()
    get_database.cache_clear()
    get_host.cache_clear()
    get_port.cache_clear()
