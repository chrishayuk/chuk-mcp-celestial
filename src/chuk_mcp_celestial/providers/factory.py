"""Provider factory for creating celestial data providers.

This module provides a factory pattern for instantiating providers
based on configuration.
"""

import logging
from enum import Enum

from ..config import ProviderConfig
from .base import CelestialProvider

logger = logging.getLogger(__name__)


class ProviderType(str, Enum):
    """Available provider types."""

    NAVY_API = "navy_api"
    SKYFIELD = "skyfield"


# Cache provider instances for reuse
_provider_cache: dict[str, CelestialProvider] = {}


def get_provider(provider_type: str | None = None) -> CelestialProvider:
    """Get a provider instance based on type.

    Args:
        provider_type: Type of provider to create. If None, uses default from config.

    Returns:
        CelestialProvider instance

    Raises:
        ValueError: If provider_type is invalid or provider cannot be created
    """
    if provider_type is None:
        provider_type = ProviderConfig.DEFAULT_PROVIDER

    # Return cached instance if available
    if provider_type in _provider_cache:
        return _provider_cache[provider_type]

    # Create new provider instance
    provider: CelestialProvider
    try:
        if provider_type == ProviderType.NAVY_API.value:
            from .navy import NavyAPIProvider

            provider = NavyAPIProvider()
            logger.info("Created Navy API provider")

        elif provider_type == ProviderType.SKYFIELD.value:
            from .skyfield_provider import SkyfieldProvider

            provider = SkyfieldProvider()
            logger.info("Created Skyfield provider")

        else:
            raise ValueError(
                f"Unknown provider type: {provider_type}. "
                f"Available: {[p.value for p in ProviderType]}"
            )

        # Cache the provider
        _provider_cache[provider_type] = provider
        return provider

    except ImportError as e:
        raise ValueError(f"Provider '{provider_type}' requires additional dependencies: {e}") from e


def get_provider_for_tool(tool_name: str) -> CelestialProvider:
    """Get the configured provider for a specific tool.

    This allows per-tool provider configuration.

    Args:
        tool_name: Name of the tool (moon_phases, sun_moon_data, etc.)

    Returns:
        CelestialProvider instance configured for this tool
    """
    provider_type = None

    # Map tool names to config attributes
    tool_config_map = {
        "moon_phases": ProviderConfig.MOON_PHASES_PROVIDER,
        "sun_moon_data": ProviderConfig.SUN_MOON_DATA_PROVIDER,
        "solar_eclipse_date": ProviderConfig.SOLAR_ECLIPSE_DATE_PROVIDER,
        "solar_eclipse_year": ProviderConfig.SOLAR_ECLIPSE_YEAR_PROVIDER,
        "earth_seasons": ProviderConfig.EARTH_SEASONS_PROVIDER,
    }

    provider_type = tool_config_map.get(tool_name)

    if provider_type is None:
        logger.warning(f"No specific provider configured for tool '{tool_name}', using default")
        provider_type = ProviderConfig.DEFAULT_PROVIDER

    return get_provider(provider_type)


def clear_provider_cache() -> None:
    """Clear the provider cache.

    Useful for testing or forcing provider re-initialization.
    """
    global _provider_cache
    _provider_cache.clear()
    logger.debug("Provider cache cleared")
