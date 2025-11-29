"""Configuration for chuk-mcp-celestial server.

This module handles configuration loading from YAML files and environment variables.
Configuration sources (in order of precedence):
1. Environment variables
2. YAML configuration file (celestial.yaml)
3. Default values
"""

import logging
import os
from enum import Enum
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Try to import yaml, but don't fail if not available
try:
    import yaml

    YAML_AVAILABLE = True
except ImportError:
    YAML_AVAILABLE = False
    logger.debug("PyYAML not available, using environment variables only")


def load_yaml_config() -> dict[str, Any]:
    """Load configuration from YAML file if it exists.

    Looks for celestial.yaml in:
    1. Current working directory
    2. User's home directory (~/.config/chuk-mcp-celestial/)
    3. Environment variable CELESTIAL_CONFIG_PATH

    Returns:
        Dictionary of configuration values, or empty dict if no file found
    """
    if not YAML_AVAILABLE:
        return {}

    config_paths = [
        Path.cwd() / "celestial.yaml",
        Path.home() / ".config" / "chuk-mcp-celestial" / "celestial.yaml",
    ]

    # Add path from environment variable if set
    if env_path := os.getenv("CELESTIAL_CONFIG_PATH"):
        config_paths.insert(0, Path(env_path))

    for config_path in config_paths:
        if config_path.exists():
            try:
                with open(config_path) as f:
                    config = yaml.safe_load(f)
                    logger.info(f"Loaded configuration from {config_path}")
                    return config or {}
            except Exception as e:
                logger.warning(f"Failed to load config from {config_path}: {e}")

    logger.debug("No YAML config file found, using environment variables and defaults")
    return {}


class ProviderType(str, Enum):
    """Available provider types."""

    NAVY_API = "navy_api"
    SKYFIELD = "skyfield"
    # Future providers can be added here
    # ASTROPLAN = "astroplan"
    # CUSTOM = "custom"


# Load YAML config once at module import
_yaml_config = load_yaml_config()


class ProviderConfig:
    """Configuration for provider selection.

    Providers can be configured globally or per-tool via:
    1. Environment variables (highest priority)
    2. YAML configuration file
    3. Default values

    Example YAML:
        default_provider: skyfield
        providers:
          moon_phases: skyfield
          sun_moon_data: navy_api
    """

    # Default provider for all tools
    # Priority: env var > YAML > hardcoded default
    DEFAULT_PROVIDER = os.getenv(
        "CELESTIAL_PROVIDER",
        _yaml_config.get("default_provider", ProviderType.NAVY_API.value),
    )

    # Per-tool provider overrides
    _providers_yaml = _yaml_config.get("providers", {})

    MOON_PHASES_PROVIDER = os.getenv(
        "CELESTIAL_MOON_PHASES_PROVIDER",
        _providers_yaml.get("moon_phases", DEFAULT_PROVIDER),
    )
    SUN_MOON_DATA_PROVIDER = os.getenv(
        "CELESTIAL_SUN_MOON_DATA_PROVIDER",
        _providers_yaml.get("sun_moon_data", DEFAULT_PROVIDER),
    )
    SOLAR_ECLIPSE_DATE_PROVIDER = os.getenv(
        "CELESTIAL_SOLAR_ECLIPSE_DATE_PROVIDER",
        _providers_yaml.get("solar_eclipse_date", DEFAULT_PROVIDER),
    )
    SOLAR_ECLIPSE_YEAR_PROVIDER = os.getenv(
        "CELESTIAL_SOLAR_ECLIPSE_YEAR_PROVIDER",
        _providers_yaml.get("solar_eclipse_year", DEFAULT_PROVIDER),
    )
    EARTH_SEASONS_PROVIDER = os.getenv(
        "CELESTIAL_EARTH_SEASONS_PROVIDER",
        _providers_yaml.get("earth_seasons", DEFAULT_PROVIDER),
    )


class SkyfieldConfig:
    """Configuration for Skyfield provider.

    Loads from (in order of precedence):
    1. Environment variables
    2. YAML config skyfield section
    3. Default values
    """

    _skyfield_yaml = _yaml_config.get("skyfield", {})

    # Ephemeris file to use
    # Default: de440s.bsp (32 MB, covers 1849-2150, recommended for 2020+)
    # Alternative: de421.bsp (17 MB, covers 1900-2050, older/smaller)
    EPHEMERIS_FILE = os.getenv(
        "SKYFIELD_EPHEMERIS",
        _skyfield_yaml.get("ephemeris", "de440s.bsp"),
    )

    # Storage backend: local, s3, or memory
    STORAGE_BACKEND = os.getenv(
        "SKYFIELD_STORAGE_BACKEND",
        _skyfield_yaml.get("storage_backend", "s3"),
    )

    # Directory to store Skyfield data files (used for local backend)
    DATA_DIR = os.getenv(
        "SKYFIELD_DATA_DIR",
        _skyfield_yaml.get("data_dir", "~/.skyfield"),
    )

    # Auto-download ephemeris if not present
    AUTO_DOWNLOAD = (
        os.getenv("SKYFIELD_AUTO_DOWNLOAD", str(_skyfield_yaml.get("auto_download", True))).lower()
        == "true"
    )

    # S3 configuration
    _s3_yaml = _skyfield_yaml.get("s3", {})

    S3_BUCKET = os.getenv(
        "SKYFIELD_S3_BUCKET",
        _s3_yaml.get("bucket", "chuk-celestial-ephemeris"),
    )

    S3_REGION = os.getenv(
        "SKYFIELD_S3_REGION",
        _s3_yaml.get("region", "us-east-1"),
    )

    S3_PREFIX = os.getenv(
        "SKYFIELD_S3_PREFIX",
        _s3_yaml.get("prefix", "ephemeris/"),
    )

    S3_PROFILE = os.getenv(
        "SKYFIELD_S3_PROFILE",
        _s3_yaml.get("profile"),
    )


class NavyAPIConfig:
    """Configuration for Navy API provider.

    Loads from (in order of precedence):
    1. Environment variables
    2. YAML config navy_api section
    3. Default values
    """

    _navy_api_yaml = _yaml_config.get("navy_api", {})

    # Base API URL
    BASE_URL = os.getenv(
        "NAVY_API_BASE_URL",
        _navy_api_yaml.get("base_url", "https://aa.usno.navy.mil/api"),
    )

    # Request timeout in seconds
    TIMEOUT = float(
        os.getenv(
            "NAVY_API_TIMEOUT",
            str(_navy_api_yaml.get("timeout", 30.0)),
        )
    )

    # Retry configuration
    MAX_RETRIES = int(
        os.getenv(
            "NAVY_API_MAX_RETRIES",
            str(_navy_api_yaml.get("max_retries", 3)),
        )
    )
    RETRY_DELAY = float(
        os.getenv(
            "NAVY_API_RETRY_DELAY",
            str(_navy_api_yaml.get("retry_delay", 1.0)),
        )
    )
