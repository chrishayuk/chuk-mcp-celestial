"""Tests for US Navy Celestial MCP Server."""

import pytest
from chuk_mcp_celestial.server import (
    get_earth_seasons,
    get_moon_phases,
    get_solar_eclipse_by_date,
    get_solar_eclipses_by_year,
    get_sun_moon_data,
)


# ============================================================================
# Basic Functionality Tests
# ============================================================================


@pytest.mark.asyncio
@pytest.mark.network
async def test_get_moon_phases():
    """Test getting moon phases."""
    result = await get_moon_phases(date="2009-5-3", num_phases=5)

    assert result is not None
    assert result.apiversion is not None
    assert result.year == 2009
    assert result.month == 5
    assert result.day == 3
    assert result.numphases == 5
    assert len(result.phasedata) == 5

    # Check first phase structure
    first_phase = result.phasedata[0]
    assert first_phase.phase is not None
    assert first_phase.year is not None
    assert first_phase.month is not None
    assert first_phase.day is not None
    assert first_phase.time is not None


@pytest.mark.asyncio
@pytest.mark.network
async def test_get_sun_moon_data(seattle_coords):
    """Test getting sun and moon data for one day."""
    result = await get_sun_moon_data(
        date="2005-9-20",
        latitude=seattle_coords["latitude"],
        longitude=seattle_coords["longitude"],
    )

    assert result is not None
    assert result.apiversion is not None
    assert result.type == "Feature"
    assert result.geometry is not None
    assert result.geometry.type == "Point"
    assert len(result.geometry.coordinates) == 2

    data = result.properties.data
    assert data.year == 2005
    assert data.month == 9
    assert data.day == 20
    assert data.sundata is not None
    assert data.moondata is not None
    assert data.curphase is not None
    assert data.fracillum is not None


@pytest.mark.asyncio
@pytest.mark.network
async def test_get_solar_eclipse_by_date(portland_coords):
    """Test getting solar eclipse data for specific location and date."""
    result = await get_solar_eclipse_by_date(
        date="2017-8-21",
        latitude=portland_coords["latitude"],
        longitude=portland_coords["longitude"],
        height=15,
    )

    assert result is not None
    assert result.apiversion is not None
    assert result.type == "Feature"
    assert result.properties is not None
    assert result.properties.year == 2017
    assert result.properties.month == 8
    assert result.properties.day == 21
    assert result.properties.description is not None
    assert result.properties.local_data is not None
    assert len(result.properties.local_data) > 0


@pytest.mark.asyncio
@pytest.mark.network
async def test_get_solar_eclipses_by_year():
    """Test getting all solar eclipses in a year."""
    result = await get_solar_eclipses_by_year(year=2024)

    assert result is not None
    assert result.apiversion is not None
    assert result.year == 2024
    assert result.eclipses_in_year is not None
    assert len(result.eclipses_in_year) >= 2  # Most years have 2+ eclipses

    # Check first eclipse structure
    if result.eclipses_in_year:
        first_eclipse = result.eclipses_in_year[0]
        assert first_eclipse.year == 2024
        assert first_eclipse.month is not None
        assert first_eclipse.day is not None
        assert first_eclipse.event is not None


@pytest.mark.asyncio
@pytest.mark.network
async def test_get_earth_seasons():
    """Test getting Earth's seasons."""
    result = await get_earth_seasons(year=2024)

    assert result is not None
    assert result.apiversion is not None
    assert result.year == 2024
    assert result.tz == 0.0  # Default UTC
    assert result.dst is False  # Default no DST
    assert result.data is not None
    assert len(result.data) == 6  # 2 equinoxes, 2 solstices, perihelion, aphelion

    # Verify we have expected phenomena (check the enum value, not string repr)
    phenomena = [event.phenom.value for event in result.data]
    assert any("Equinox" in str(p) for p in phenomena)
    assert any("Solstice" in str(p) for p in phenomena)


# ============================================================================
# Feature Tests
# ============================================================================


@pytest.mark.asyncio
@pytest.mark.network
async def test_moon_phases_max_count():
    """Test requesting maximum number of moon phases."""
    result = await get_moon_phases(date="2024-1-1", num_phases=48)

    assert result is not None
    assert result.numphases == 48
    assert len(result.phasedata) == 48


@pytest.mark.asyncio
@pytest.mark.network
async def test_sun_moon_data_with_timezone(greenwich_coords):
    """Test getting sun/moon data with custom timezone."""
    result = await get_sun_moon_data(
        date="2024-6-21",
        latitude=greenwich_coords["latitude"],
        longitude=greenwich_coords["longitude"],
        timezone=0,  # UTC
        dst=False,
    )

    assert result is not None
    assert result.properties.data.tz == 0.0
    assert result.properties.data.isdst is False


@pytest.mark.asyncio
@pytest.mark.network
async def test_sun_moon_data_with_label(seattle_coords):
    """Test sun/moon data with custom label."""
    label = "Test Location"
    result = await get_sun_moon_data(
        date="2024-1-1",
        latitude=seattle_coords["latitude"],
        longitude=seattle_coords["longitude"],
        label=label,
    )

    assert result is not None
    assert result.properties.data.label == label


@pytest.mark.asyncio
@pytest.mark.network
async def test_solar_eclipse_no_eclipse_location():
    """Test eclipse query for location where eclipse is visible."""
    # New York for 2024 eclipse - should have eclipse data
    result = await get_solar_eclipse_by_date(
        date="2024-4-8",
        latitude=40.71,
        longitude=-74.01,
    )

    assert result is not None
    assert result.properties is not None
    # Should have eclipse data for this location


@pytest.mark.asyncio
@pytest.mark.network
async def test_earth_seasons_with_timezone():
    """Test seasons with custom timezone and DST."""
    result = await get_earth_seasons(year=2024, timezone=-6, dst=True)

    assert result is not None
    assert result.tz == -6.0
    assert result.dst is True


# ============================================================================
# Southern Hemisphere Tests
# ============================================================================


@pytest.mark.asyncio
@pytest.mark.network
async def test_sun_moon_data_southern_hemisphere(sydney_coords):
    """Test sun/moon data for Southern Hemisphere location."""
    result = await get_sun_moon_data(
        date="2024-1-1",
        latitude=sydney_coords["latitude"],
        longitude=sydney_coords["longitude"],
    )

    assert result is not None
    assert result.geometry.coordinates[0] == pytest.approx(sydney_coords["longitude"], abs=0.1)
    assert result.geometry.coordinates[1] == pytest.approx(sydney_coords["latitude"], abs=0.1)
    assert result.properties.data.sundata is not None


# ============================================================================
# Model Validation Tests
# ============================================================================


@pytest.mark.asyncio
@pytest.mark.network
async def test_pydantic_validation():
    """Test that Pydantic models properly validate and serialize."""
    result = await get_moon_phases(date="2024-1-1", num_phases=4)

    # Test model_dump() works
    data = result.model_dump()
    assert isinstance(data, dict)
    assert "phasedata" in data
    assert isinstance(data["phasedata"], list)


@pytest.mark.asyncio
@pytest.mark.network
async def test_nested_model_access():
    """Test accessing nested model fields."""
    result = await get_sun_moon_data(
        date="2024-6-21",
        latitude=51.48,
        longitude=0.0,
    )

    # Test nested access
    assert result.properties.data.year == 2024
    assert result.properties.data.month == 6
    assert result.properties.data.day == 21
    assert result.geometry.coordinates[1] == pytest.approx(51.48, abs=0.1)


# ============================================================================
# Enum Tests
# ============================================================================


@pytest.mark.asyncio
@pytest.mark.network
async def test_moon_phase_enum():
    """Test that moon phase enum values are properly used."""
    result = await get_moon_phases(date="2024-1-1", num_phases=4)

    # Verify phases use enum values - check the .value property
    phase_values = [p.phase.value for p in result.phasedata]
    valid_phases = {"New Moon", "First Quarter", "Full Moon", "Last Quarter"}

    for phase_value in phase_values:
        assert phase_value in valid_phases


@pytest.mark.asyncio
@pytest.mark.network
async def test_season_phenomenon_enum():
    """Test that season phenomenon enum values are properly used."""
    result = await get_earth_seasons(year=2024)

    # Verify phenomena use enum values - check the .value property
    phenomena_values = [event.phenom.value for event in result.data]
    valid_phenomena = {"Equinox", "Solstice", "Perihelion", "Aphelion"}

    for phenom_value in phenomena_values:
        assert phenom_value in valid_phenomena


# ============================================================================
# Parameter Validation Tests
# ============================================================================


@pytest.mark.asyncio
async def test_moon_phases_invalid_num_phases():
    """Test that invalid num_phases raises error."""
    with pytest.raises(ValueError, match="num_phases must be between"):
        await get_moon_phases(date="2024-1-1", num_phases=100)


@pytest.mark.asyncio
async def test_solar_eclipse_invalid_height():
    """Test that invalid height raises error."""
    with pytest.raises(ValueError, match="height must be between"):
        await get_solar_eclipse_by_date(
            date="2024-1-1",
            latitude=0.0,
            longitude=0.0,
            height=20000,  # Too high
        )


@pytest.mark.asyncio
async def test_seasons_invalid_year():
    """Test that invalid year raises error."""
    with pytest.raises(ValueError, match="year must be between"):
        await get_earth_seasons(year=1600)  # Too early


# ============================================================================
# Import Tests
# ============================================================================


def test_imports():
    """Test that all expected functions and models can be imported."""
    from chuk_mcp_celestial import models, server

    # Check server functions
    assert hasattr(server, "get_moon_phases")
    assert hasattr(server, "get_sun_moon_data")
    assert hasattr(server, "get_solar_eclipse_by_date")
    assert hasattr(server, "get_solar_eclipses_by_year")
    assert hasattr(server, "get_earth_seasons")

    # Check models
    assert hasattr(models, "MoonPhasesResponse")
    assert hasattr(models, "OneDayResponse")
    assert hasattr(models, "SolarEclipseByDateResponse")
    assert hasattr(models, "SolarEclipseByYearResponse")
    assert hasattr(models, "SeasonsResponse")

    # Check enums
    assert hasattr(models, "MoonPhase")
    assert hasattr(models, "CelestialPhenomenon")
    assert hasattr(models, "EclipsePhenomenon")
    assert hasattr(models, "SeasonPhenomenon")


# ============================================================================
# Historical Data Tests
# ============================================================================


@pytest.mark.asyncio
@pytest.mark.network
async def test_moon_phases_historical():
    """Test getting historical moon phases."""
    result = await get_moon_phases(date="1900-1-1", num_phases=4)

    assert result is not None
    assert result.year == 1900


@pytest.mark.asyncio
@pytest.mark.network
async def test_earth_seasons_historical():
    """Test getting historical seasons."""
    result = await get_earth_seasons(year=1800)

    assert result is not None
    assert result.year == 1800


# ============================================================================
# Future Data Tests
# ============================================================================


@pytest.mark.asyncio
@pytest.mark.network
async def test_moon_phases_future():
    """Test getting future moon phases."""
    result = await get_moon_phases(date="2099-12-31", num_phases=4)

    assert result is not None
    assert result.year == 2099


@pytest.mark.asyncio
@pytest.mark.network
async def test_solar_eclipses_future():
    """Test getting future solar eclipses."""
    result = await get_solar_eclipses_by_year(year=2045)

    assert result is not None
    assert result.year == 2045


# ============================================================================
# Main Function and CLI Tests
# ============================================================================


def test_main_stdio_mode():
    """Test main() function with default stdio mode."""
    from unittest.mock import patch
    from chuk_mcp_celestial.server import main
    import sys

    # Mock sys.argv to not have http argument
    with patch.object(sys, "argv", ["server.py"]):
        with patch("chuk_mcp_celestial.server.run") as mock_run:
            main()
            mock_run.assert_called_once_with(transport="stdio")


def test_main_http_mode():
    """Test main() function with http mode."""
    from unittest.mock import patch
    from chuk_mcp_celestial.server import main
    import sys

    # Test with 'http' argument
    with patch.object(sys, "argv", ["server.py", "http"]):
        with patch("chuk_mcp_celestial.server.run") as mock_run:
            main()
            mock_run.assert_called_once_with(transport="http")


def test_main_http_flag():
    """Test main() function with --http flag."""
    from unittest.mock import patch
    from chuk_mcp_celestial.server import main
    import sys

    # Test with '--http' argument
    with patch.object(sys, "argv", ["server.py", "--http"]):
        with patch("chuk_mcp_celestial.server.run") as mock_run:
            main()
            mock_run.assert_called_once_with(transport="http")


def test_main_logging_configuration():
    """Test that logging is configured properly in different modes."""
    from unittest.mock import patch
    from chuk_mcp_celestial.server import main
    import sys
    import logging

    # Test stdio mode suppresses logging
    with patch.object(sys, "argv", ["server.py"]):
        with patch("chuk_mcp_celestial.server.run"):
            main()
            # Check that loggers are set to ERROR level
            assert logging.getLogger("chuk_mcp_server").level == logging.ERROR
            assert logging.getLogger("httpx").level == logging.ERROR
