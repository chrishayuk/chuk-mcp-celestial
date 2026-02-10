"""Tests for get_sky tool — all-sky summary."""

import pytest

# Check if Skyfield is available
try:
    from chuk_mcp_celestial.providers.skyfield_provider import (
        SKYFIELD_AVAILABLE,
        SkyfieldProvider,
    )
except ImportError:
    SKYFIELD_AVAILABLE = False
    SkyfieldProvider = None  # type: ignore

from chuk_mcp_celestial.models import Planet, VisibilityStatus
from chuk_mcp_celestial.server import _azimuth_to_direction, get_sky


pytestmark = pytest.mark.skipif(not SKYFIELD_AVAILABLE, reason="Skyfield not installed")


# ============================================================================
# Direction helper
# ============================================================================


class TestAzimuthToDirection:
    """Test compass direction from azimuth."""

    def test_north(self):
        assert _azimuth_to_direction(0) == "N"

    def test_east(self):
        assert _azimuth_to_direction(90) == "E"

    def test_south(self):
        assert _azimuth_to_direction(180) == "S"

    def test_west(self):
        assert _azimuth_to_direction(270) == "W"

    def test_northeast(self):
        assert _azimuth_to_direction(45) == "NE"

    def test_southeast(self):
        assert _azimuth_to_direction(135) == "SE"

    def test_southwest(self):
        assert _azimuth_to_direction(225) == "SW"

    def test_northwest(self):
        assert _azimuth_to_direction(315) == "NW"

    def test_wrap_360(self):
        assert _azimuth_to_direction(360) == "N"

    def test_boundary_22(self):
        """22 degrees rounds to N (0)."""
        assert _azimuth_to_direction(22) == "N"

    def test_boundary_23(self):
        """23 degrees rounds to NE (45)."""
        assert _azimuth_to_direction(23) == "NE"


# ============================================================================
# get_sky tool
# ============================================================================


@pytest.mark.asyncio
async def test_get_sky_basic(greenwich_coords):
    """Test basic get_sky call returns expected structure."""
    result = await get_sky(
        date="2025-6-15",
        time="22:00",
        latitude=greenwich_coords["latitude"],
        longitude=greenwich_coords["longitude"],
    )

    assert result is not None
    assert result.type == "Feature"
    assert result.apiversion == "Skyfield 1.x"
    assert result.geometry.type == "Point"
    assert result.geometry.coordinates == [
        greenwich_coords["longitude"],
        greenwich_coords["latitude"],
    ]

    data = result.properties.data
    assert data.date == "2025-6-15"
    assert data.time == "22:00"
    assert isinstance(data.is_dark, bool)
    assert isinstance(data.summary, str)
    assert len(data.summary) > 0


@pytest.mark.asyncio
async def test_get_sky_all_planets(greenwich_coords):
    """Test that all 8 planets are returned in all_planets."""
    result = await get_sky(
        date="2025-6-15",
        time="22:00",
        latitude=greenwich_coords["latitude"],
        longitude=greenwich_coords["longitude"],
    )

    data = result.properties.data
    assert len(data.all_planets) == 8

    planet_names = {p.planet for p in data.all_planets}
    expected = {p for p in Planet}
    assert planet_names == expected


@pytest.mark.asyncio
async def test_get_sky_visible_subset(greenwich_coords):
    """Test that visible_planets is a valid subset of all_planets."""
    result = await get_sky(
        date="2025-6-15",
        time="22:00",
        latitude=greenwich_coords["latitude"],
        longitude=greenwich_coords["longitude"],
    )

    data = result.properties.data

    # All visible planets must be in all_planets
    visible_names = {p.planet for p in data.visible_planets}
    all_names = {p.planet for p in data.all_planets}
    assert visible_names.issubset(all_names)

    # All visible planets must actually be visible
    for p in data.visible_planets:
        assert p.visibility == VisibilityStatus.VISIBLE


@pytest.mark.asyncio
async def test_get_sky_visible_sorted_brightest(greenwich_coords):
    """Test that visible_planets are sorted brightest first (lowest magnitude)."""
    result = await get_sky(
        date="2025-6-15",
        time="22:00",
        latitude=greenwich_coords["latitude"],
        longitude=greenwich_coords["longitude"],
    )

    mags = [p.magnitude for p in result.properties.data.visible_planets]
    assert mags == sorted(mags)


@pytest.mark.asyncio
async def test_get_sky_planet_fields(greenwich_coords):
    """Test that planet summaries have valid field values."""
    result = await get_sky(
        date="2025-6-15",
        time="22:00",
        latitude=greenwich_coords["latitude"],
        longitude=greenwich_coords["longitude"],
    )

    for p in result.properties.data.all_planets:
        assert -90 <= p.altitude <= 90
        assert 0 <= p.azimuth <= 360
        assert 0 <= p.elongation <= 180
        assert p.direction in ("N", "NE", "E", "SE", "S", "SW", "W", "NW")
        assert isinstance(p.constellation, str)
        assert len(p.constellation) > 0
        assert p.visibility in VisibilityStatus


@pytest.mark.asyncio
async def test_get_sky_moon(greenwich_coords):
    """Test that moon data is populated."""
    result = await get_sky(
        date="2025-6-15",
        time="22:00",
        latitude=greenwich_coords["latitude"],
        longitude=greenwich_coords["longitude"],
    )

    moon = result.properties.data.moon
    assert isinstance(moon.phase, str)
    assert isinstance(moon.illumination, str)


@pytest.mark.asyncio
async def test_get_sky_with_timezone(seattle_coords):
    """Test get_sky with timezone offset."""
    result = await get_sky(
        date="2025-6-15",
        time="22:00",
        latitude=seattle_coords["latitude"],
        longitude=seattle_coords["longitude"],
        timezone=-7,
    )

    data = result.properties.data
    assert len(data.all_planets) == 8
    assert isinstance(data.is_dark, bool)


@pytest.mark.asyncio
async def test_get_sky_daytime(greenwich_coords):
    """Test get_sky during daytime — is_dark should be False."""
    result = await get_sky(
        date="2025-6-15",
        time="12:00",
        latitude=greenwich_coords["latitude"],
        longitude=greenwich_coords["longitude"],
    )

    assert result.properties.data.is_dark is False


@pytest.mark.asyncio
async def test_get_sky_nighttime(greenwich_coords):
    """Test get_sky at night — is_dark should be True."""
    # December midnight in Greenwich — definitely dark
    result = await get_sky(
        date="2025-12-15",
        time="00:00",
        latitude=greenwich_coords["latitude"],
        longitude=greenwich_coords["longitude"],
    )

    assert result.properties.data.is_dark is True


@pytest.mark.asyncio
async def test_get_sky_summary_contains_planet_count(greenwich_coords):
    """Test that summary string mentions visible planet count."""
    result = await get_sky(
        date="2025-6-15",
        time="22:00",
        latitude=greenwich_coords["latitude"],
        longitude=greenwich_coords["longitude"],
    )

    data = result.properties.data
    n = len(data.visible_planets)
    if n > 0:
        assert "visible" in data.summary.lower()
    else:
        assert "no planets" in data.summary.lower()
