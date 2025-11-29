"""Tests for base provider abstract class."""

import pytest

from chuk_mcp_celestial.providers.base import CelestialProvider


class ConcreteProvider(CelestialProvider):
    """Concrete implementation for testing abstract base."""

    async def get_moon_phases(self, date: str, num_phases: int = 12):
        """Test implementation."""
        pass

    async def get_sun_moon_data(
        self,
        date: str,
        latitude: float,
        longitude: float,
        timezone: float | None = None,
        dst: bool | None = None,
        label: str | None = None,
    ):
        """Test implementation."""
        pass

    async def get_solar_eclipse_by_date(
        self,
        date: str,
        latitude: float,
        longitude: float,
        height: int = 0,
    ):
        """Test implementation."""
        pass

    async def get_solar_eclipses_by_year(self, year: int):
        """Test implementation."""
        pass

    async def get_earth_seasons(
        self,
        year: int,
        timezone: float | None = None,
        dst: bool | None = None,
    ):
        """Test implementation."""
        pass


class TestCelestialProvider:
    """Test abstract base provider."""

    def test_cannot_instantiate_abstract(self):
        """Test that abstract class cannot be instantiated."""
        with pytest.raises(TypeError):
            CelestialProvider()  # type: ignore

    @pytest.mark.asyncio
    async def test_concrete_implementation(self):
        """Test that concrete implementation can be instantiated."""
        provider = ConcreteProvider()
        assert isinstance(provider, CelestialProvider)

        # Test all methods can be called
        await provider.get_moon_phases("2024-01-01")
        await provider.get_sun_moon_data("2024-01-01", 40.7, -74.0)
        await provider.get_solar_eclipse_by_date("2024-04-08", 40.7, -74.0)
        await provider.get_solar_eclipses_by_year(2024)
        await provider.get_earth_seasons(2024)
