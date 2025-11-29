"""Tests for provider factory."""

import pytest
from unittest.mock import patch

from chuk_mcp_celestial.providers.factory import (
    ProviderType,
    get_provider,
    _provider_cache,
)
from chuk_mcp_celestial.providers.navy import NavyAPIProvider
from chuk_mcp_celestial.providers.skyfield_provider import SkyfieldProvider


class TestProviderType:
    """Test ProviderType enum."""

    def test_navy_api_value(self):
        """Test Navy API provider type."""
        assert ProviderType.NAVY_API.value == "navy_api"

    def test_skyfield_value(self):
        """Test Skyfield provider type."""
        assert ProviderType.SKYFIELD.value == "skyfield"

    def test_enum_members(self):
        """Test all enum members."""
        members = list(ProviderType)
        assert len(members) == 2
        assert ProviderType.NAVY_API in members
        assert ProviderType.SKYFIELD in members


class TestGetProvider:
    """Test get_provider factory function."""

    def setup_method(self):
        """Clear cache before each test."""
        _provider_cache.clear()

    def test_get_navy_provider(self):
        """Test getting Navy API provider."""
        provider = get_provider("navy_api")
        assert isinstance(provider, NavyAPIProvider)

    def test_get_skyfield_provider(self):
        """Test getting Skyfield provider."""
        provider = get_provider("skyfield")
        assert isinstance(provider, SkyfieldProvider)

    def test_default_provider(self):
        """Test getting default provider (no args)."""
        provider = get_provider()
        assert provider is not None
        # Should be either Navy or Skyfield
        assert isinstance(provider, (NavyAPIProvider, SkyfieldProvider))

    def test_provider_caching(self):
        """Test that providers are cached."""
        provider1 = get_provider("navy_api")
        provider2 = get_provider("navy_api")
        # Should return same instance
        assert provider1 is provider2

    def test_different_providers_not_cached_together(self):
        """Test that different provider types have separate cache entries."""
        navy = get_provider("navy_api")
        skyfield = get_provider("skyfield")
        assert navy is not skyfield
        assert isinstance(navy, NavyAPIProvider)
        assert isinstance(skyfield, SkyfieldProvider)

    def test_invalid_provider_type(self):
        """Test error handling for invalid provider type."""
        with pytest.raises(ValueError, match="Unknown provider type"):
            get_provider("invalid_provider")

    def test_cache_contains_entries(self):
        """Test that cache is populated after provider creation."""
        _provider_cache.clear()
        assert len(_provider_cache) == 0

        get_provider("navy_api")
        assert len(_provider_cache) == 1

        get_provider("skyfield")
        assert len(_provider_cache) == 2

    def test_exception_during_creation(self):
        """Test handling of exceptions during provider creation."""
        # This would test error handling in the factory
        # Currently, errors should be raised naturally
        with pytest.raises(ValueError):
            get_provider("nonexistent")

    @patch("chuk_mcp_celestial.providers.factory.ProviderConfig")
    def test_uses_config_default(self, mock_config):
        """Test that factory uses config default when no type specified."""
        mock_config.DEFAULT_PROVIDER = "navy_api"
        _provider_cache.clear()

        provider = get_provider(None)
        assert isinstance(provider, NavyAPIProvider)
