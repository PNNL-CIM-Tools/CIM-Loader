"""Shared configuration utilities for CIM database connectors.

This module provides helper functions to manage configuration state
from the cimgraph library, reducing code duplication across connectors.
"""

from cimgraph.databases import (
    get_cim_profile,
    get_database,
    get_host,
    get_iec61970_552,
    get_namespace,
    get_password,
    get_port,
    get_url,
    get_username,
)

# cimgraph memoises these with @cache so env-var changes are not picked up
# until the cache is cleared. Which getters are cached varies by cimgraph
# version -- get_iec61970_301 was deprecated and un-cached in 0.5.x -- so
# each is cleared only if it actually exposes cache_clear().
_CACHED_GETTERS = (
    get_url,
    get_namespace,
    get_cim_profile,
    get_iec61970_552,
    get_username,
    get_password,
    get_database,
    get_host,
    get_port,
)


def clear_cim_config_cache():
    """Clear all cached CIM configuration values from cimgraph.

    Call this before retrieving fresh configuration to ensure
    environment variable changes are reflected.
    """
    for getter in _CACHED_GETTERS:
        cache_clear = getattr(getter, 'cache_clear', None)
        if cache_clear is not None:
            cache_clear()
