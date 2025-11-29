"""US Navy Astronomical Data MCP Server.

Provides comprehensive celestial and astronomical data through configurable providers:
- Navy API: Official US Navy Astronomical Applications Department API
- Skyfield: Local calculations using JPL ephemeris data

Features:
- Moon phases with exact timing
- Sun and moon rise/set/transit times
- Solar eclipse predictions and local circumstances
- Earth's seasons and orbital events (equinoxes, solstices, perihelion, aphelion)

All responses use Pydantic models for type safety and validation.
No dictionary goop, no magic strings - everything is strongly typed with enums and constants.
"""

import logging
import sys
from typing import Optional

from chuk_mcp_server import run, tool

from .models import (
    MoonPhasesResponse,
    OneDayResponse,
    SeasonsResponse,
    SolarEclipseByDateResponse,
    SolarEclipseByYearResponse,
)
from .providers.factory import get_provider_for_tool

# Configure logging
# In STDIO mode, we need to be quiet to avoid polluting the JSON-RPC stream
# Only log to stderr, and only warnings/errors
logging.basicConfig(
    level=logging.WARNING, format="%(levelname)s:%(name)s:%(message)s", stream=sys.stderr
)
logger = logging.getLogger(__name__)


@tool  # type: ignore[arg-type]
async def get_moon_phases(
    date: str,
    num_phases: int = 12,
) -> MoonPhasesResponse:
    """Get upcoming moon phases starting from a given date.

    Returns the next N moon phase occurrences (New Moon, First Quarter, Full Moon, Last Quarter)
    with exact times. Useful for planning astronomical observations, photography, or understanding
    lunar cycles.

    Args:
        date: Start date in YYYY-MM-DD format. No leading zeros required (e.g., "2024-1-5" is valid).
            Valid range: 1700-01-01 to 2100-12-31
        num_phases: Number of phases to return (1-99). Default is 12 (about 3 months of phases).
            Each lunar cycle has 4 phases, so 12 phases = 3 complete cycles.

    Returns:
        MoonPhasesResponse: Contains:
            - phasedata: List of phase occurrences with exact dates and times
            - Each phase includes: phase name, year, month, day, time (in UT1)

    Tips for LLMs:
        - All times are in Universal Time (UT1), not local time
        - A complete lunar cycle is about 29.5 days (4 phases)
        - Use num_phases=4 for the next month, 12 for next quarter, 48 for next year
        - Moon phases are useful for: astronomy, photography (full moon lighting),
          fishing/hunting (activity patterns), gardening (traditional planting cycles)

    Example:
        # Get next 12 moon phases starting from May 3, 2009
        phases = await get_moon_phases("2009-5-3", num_phases=12)
        for phase in phases.phasedata:
            print(f"{phase.phase} on {phase.year}-{phase.month}-{phase.day} at {phase.time} UT")
    """
    provider = get_provider_for_tool("moon_phases")
    return await provider.get_moon_phases(date, num_phases)


@tool  # type: ignore[arg-type]
async def get_sun_moon_data(
    date: str,
    latitude: float,
    longitude: float,
    timezone: Optional[float] = None,
    dst: Optional[bool] = None,
    label: Optional[str] = None,
) -> OneDayResponse:
    """Get complete sun and moon data for one day at a specific location.

    Provides rise, set, and transit times for the sun and moon, twilight times,
    moon phase, and illumination percentage. Essential for planning outdoor activities,
    photography, navigation, and astronomical observations.

    Args:
        date: Date in YYYY-MM-DD format. No leading zeros required.
        latitude: Latitude in decimal degrees. Range: -90 to 90 (negative = South, positive = North)
        longitude: Longitude in decimal degrees. Range: -180 to 180 (negative = West, positive = East)
        timezone: Timezone offset from UTC in hours (e.g., -8 for PST, 1 for CET).
            Positive = East of UTC, Negative = West of UTC. If not provided, UTC (0) is used.
        dst: Whether to apply daylight saving time adjustment. If not provided, defaults to false.
        label: Optional user label (max 20 characters) to identify this query in the response

    Returns:
        OneDayResponse: GeoJSON Feature containing:
            - geometry: Location coordinates
            - properties.data: Complete sun and moon information:
                - sundata: List of sun events (rise, set, transit, civil twilight begin/end)
                - moondata: List of moon events (rise, set, transit)
                - curphase: Current moon phase description
                - fracillum: Percentage of moon illuminated (e.g., "92%")
                - closestphase: Details of the nearest moon phase

    Tips for LLMs:
        - Times are in the requested timezone (or UTC if not specified)
        - sundata and moondata may be empty in polar regions during extreme seasons
        - Civil twilight is when the sun is 6° below horizon - still enough light for outdoor activities
        - Use fracillum to determine moon brightness for night photography or stargazing
        - Moon transit time indicates when moon is highest in the sky (best viewing)
        - For sunrise/sunset times, look for "Rise" and "Set" in sundata
        - Events are in chronological order

    Example:
        # Get sun/moon data for Seattle on Sept 20, 2005 (PST timezone)
        data = await get_sun_moon_data(
            date="2005-9-20",
            latitude=47.60,
            longitude=-122.33,
            timezone=-8,
            dst=True
        )
        # Find sunrise
        sunrise = next(e for e in data.properties.data.sundata if e.phen == "Rise")
        print(f"Sunrise at {sunrise.time}")
    """
    provider = get_provider_for_tool("sun_moon_data")
    return await provider.get_sun_moon_data(date, latitude, longitude, timezone, dst, label)


@tool  # type: ignore[arg-type]
async def get_solar_eclipse_by_date(
    date: str,
    latitude: float,
    longitude: float,
    height: int = 0,
) -> SolarEclipseByDateResponse:
    """Get local solar eclipse circumstances for a specific date and location.

    Calculates whether a solar eclipse is visible from a given location on a specific date,
    and if so, provides detailed timing and positional information for all eclipse phases.

    Args:
        date: Date of the eclipse in YYYY-MM-DD format. No leading zeros required.
            Valid range: 1800-01-01 to 2050-12-31
        latitude: Observer's latitude in decimal degrees (-90 to 90)
        longitude: Observer's longitude in decimal degrees (-180 to 180)
        height: Observer's height above mean sea level in meters. Default is 0.
            Range: -200 to 10000 meters. Affects timing by seconds due to horizon position.

    Returns:
        SolarEclipseByDateResponse: GeoJSON Feature containing:
            - geometry: Observer location
            - properties: Eclipse details including:
                - description: Type of eclipse at this location (Total, Partial, Annular, or No Eclipse)
                - magnitude: Fraction of sun's diameter covered (1.0+ = total, <1.0 = partial)
                - obscuration: Percentage of sun's area covered
                - duration: Total duration of the eclipse
                - local_data: List of eclipse phases with:
                    - phenomenon: Eclipse Begins, Maximum Eclipse, Eclipse Ends
                    - time: Local time of the phase
                    - altitude/azimuth: Sun's position in the sky
                    - position_angle/vertex_angle: Eclipse geometry

    Tips for LLMs:
        - If description is "No Eclipse at this Location", the eclipse isn't visible here
        - magnitude >= 1.0 indicates a total solar eclipse (moon completely covers sun)
        - magnitude < 1.0 indicates a partial eclipse
        - obscuration shows percentage of sun's *area* covered (differs from magnitude)
        - altitude tells you how high the sun is (negative = below horizon)
        - azimuth tells you where to look (0=N, 90=E, 180=S, 270=W)
        - local_data is ordered chronologically (begins, maximum, ends)
        - Times in local_data are in the observer's local time (not UTC)
        - Use altitude to determine if eclipse is visible (must be > 0)

    Example:
        # Check eclipse visibility from Portland, OR on Aug 21, 2017
        eclipse = await get_solar_eclipse_by_date(
            date="2017-8-21",
            latitude=46.67,
            longitude=-122.65,
            height=15
        )
        print(f"Eclipse type: {eclipse.properties.description}")
        print(f"Maximum coverage: {eclipse.properties.obscuration}")
        for event in eclipse.properties.local_data:
            print(f"{event.phenomenon} at {event.time}, sun at {event.altitude}° altitude")
    """
    provider = get_provider_for_tool("solar_eclipse_date")
    return await provider.get_solar_eclipse_by_date(date, latitude, longitude, height)


@tool  # type: ignore[arg-type]
async def get_solar_eclipses_by_year(
    year: int,
) -> SolarEclipseByYearResponse:
    """Get a list of all solar eclipses occurring in a specific year.

    Returns all solar eclipses (total, annular, partial, and hybrid) that occur worldwide
    in the specified year. Use this to find eclipse dates, then use get_solar_eclipse_by_date
    to get detailed local circumstances.

    Args:
        year: Year to query (1800-2050)

    Returns:
        SolarEclipseByYearResponse: Contains:
            - year: The queried year
            - eclipses_in_year: List of eclipse events with:
                - year, month, day: Date of the eclipse
                - event: Full description (e.g., "Total Solar Eclipse of 2024 Apr. 08")

    Tips for LLMs:
        - Most years have 2 solar eclipses, some have 3, rarely 4, never more
        - Event description tells you the type (Total, Annular, Partial, Hybrid)
        - After finding an eclipse date, use get_solar_eclipse_by_date to check visibility
          from a specific location
        - Not all eclipses are visible from all locations on Earth
        - Total solar eclipses are rare from any given location (average 375 years between them)

    Example:
        # Find all solar eclipses in 2024
        eclipses = await get_solar_eclipses_by_year(2024)
        for eclipse in eclipses.eclipses_in_year:
            print(f"{eclipse.event} on {eclipse.year}-{eclipse.month}-{eclipse.day}")
    """
    provider = get_provider_for_tool("solar_eclipse_year")
    return await provider.get_solar_eclipses_by_year(year)


@tool  # type: ignore[arg-type]
async def get_earth_seasons(
    year: int,
    timezone: Optional[float] = None,
    dst: Optional[bool] = None,
) -> SeasonsResponse:
    """Get Earth's seasons and orbital events for a year.

    Returns dates and times for equinoxes (equal day/night), solstices (longest/shortest days),
    and Earth's perihelion (closest to sun) and aphelion (farthest from sun).

    Args:
        year: Year to query (1700-2100)
        timezone: Timezone offset from UTC in hours (e.g., -8 for PST, 1 for CET).
            Positive = East of UTC, Negative = West of UTC. If not provided, UTC (0) is used.
        dst: Whether to apply daylight saving time adjustment. If not provided, defaults to false.

    Returns:
        SeasonsResponse: Contains:
            - year: The queried year
            - tz: Timezone offset used
            - dst: Whether DST was applied
            - data: List of seasonal events (typically 6 per year):
                - Perihelion: Earth's closest approach to sun (~Jan 3, ~147M km)
                - March Equinox: Vernal/spring equinox in Northern Hemisphere (~Mar 20)
                - June Solstice: Summer solstice in Northern Hemisphere (~Jun 21, longest day)
                - Aphelion: Earth's farthest point from sun (~Jul 4, ~152M km)
                - September Equinox: Autumnal/fall equinox in Northern Hemisphere (~Sep 22)
                - December Solstice: Winter solstice in Northern Hemisphere (~Dec 21, shortest day)

    Tips for LLMs:
        - Times are in the specified timezone (or UTC if not specified)
        - Equinoxes: day and night are approximately equal length worldwide
        - Solstices: mark the longest and shortest days of the year in each hemisphere
        - Perihelion/Aphelion: Earth's orbit is elliptical, not circular
        - Despite being closest to sun in January, Northern Hemisphere has winter due to tilt
        - The tilt of Earth's axis (23.5°) causes seasons, not distance from sun
        - Exact times are precise to the minute for astronomical purposes
        - Seasons are opposite in Northern and Southern hemispheres:
            - June solstice: summer in north, winter in south
            - December solstice: winter in north, summer in south

    Example:
        # Get seasonal events for 2024 in UTC
        seasons = await get_earth_seasons(2024)
        for event in seasons.data:
            print(f"{event.phenom}: {event.month}/{event.day}/{event.year} at {event.time}")

        # Get seasonal events for 2024 in US Central Time with DST
        seasons = await get_earth_seasons(2024, timezone=-6, dst=True)
    """
    provider = get_provider_for_tool("earth_seasons")
    return await provider.get_earth_seasons(year, timezone, dst)


def main() -> None:
    """Run the US Navy Celestial MCP server."""
    # Check if transport is specified in command line args
    # Default to stdio for MCP compatibility (Claude Desktop, mcp-cli)
    transport = "stdio"

    # Allow HTTP mode via command line
    if len(sys.argv) > 1 and sys.argv[1] in ["http", "--http"]:
        transport = "http"
        # Only log in HTTP mode
        logger.warning("Starting Chuk MCP Celestial Server in HTTP mode")

    # Suppress chuk_mcp_server logging in STDIO mode
    if transport == "stdio":
        # Set chuk_mcp_server loggers to ERROR only
        logging.getLogger("chuk_mcp_server").setLevel(logging.ERROR)
        logging.getLogger("chuk_mcp_server.core").setLevel(logging.ERROR)
        logging.getLogger("chuk_mcp_server.stdio_transport").setLevel(logging.ERROR)
        # Suppress httpx logging (API calls)
        logging.getLogger("httpx").setLevel(logging.ERROR)

    run(transport=transport)


if __name__ == "__main__":
    main()
