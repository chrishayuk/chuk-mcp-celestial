"""US Navy Astronomical Data MCP Server.

Provides comprehensive celestial and astronomical data through configurable providers:
- Navy API: Official US Navy Astronomical Applications Department API
- Skyfield: Local calculations using JPL ephemeris data

Features:
- Moon phases with exact timing
- Sun and moon rise/set/transit times
- Solar eclipse predictions and local circumstances
- Earth's seasons and orbital events (equinoxes, solstices, perihelion, aphelion)
- Planet positions (altitude, azimuth, distance, magnitude, constellation)
- Planet rise/set/transit times

All responses use Pydantic models for type safety and validation.
No dictionary goop, no magic strings - everything is strongly typed with enums and constants.
"""

import logging
import os
import sys
from pathlib import Path
from typing import Any, Optional

from chuk_mcp_server import run, tool

from .constants import EnvVar, SessionProvider, StorageProvider
from .core.celestial_storage import CelestialStorage
from .models import (
    GeoJSONPoint,
    MoonPhasesResponse,
    OneDayResponse,
    Planet,
    PlanetEventsResponse,
    PlanetPositionResponse,
    SeasonsResponse,
    SkyData,
    SkyMoonSummary,
    SkyPlanetSummary,
    SkyProperties,
    SkyResponse,
    SolarEclipseByDateResponse,
    SolarEclipseByYearResponse,
    VisibilityStatus,
)
from .providers.factory import get_provider_for_tool

# Configure logging
# In STDIO mode, we need to be quiet to avoid polluting the JSON-RPC stream
# Only log to stderr, and only warnings/errors
logging.basicConfig(
    level=logging.WARNING, format="%(levelname)s:%(name)s:%(message)s", stream=sys.stderr
)
logger = logging.getLogger(__name__)

# Module-level storage instance (initialised in main())
_storage: CelestialStorage = CelestialStorage()


# ============================================================================
# Artifact Store Initialization (following tides pattern)
# ============================================================================


def _init_artifact_store() -> bool:
    """Initialize the artifact store from environment variables.

    Returns True if artifact store was initialized, False otherwise.
    """
    global _storage

    provider = os.environ.get(EnvVar.ARTIFACTS_PROVIDER, StorageProvider.MEMORY)
    bucket = os.environ.get(EnvVar.BUCKET_NAME)
    redis_url = os.environ.get(EnvVar.REDIS_URL)
    artifacts_path = os.environ.get(EnvVar.ARTIFACTS_PATH)

    if provider == StorageProvider.S3:
        aws_key = os.environ.get(EnvVar.AWS_ACCESS_KEY_ID)
        aws_secret = os.environ.get(EnvVar.AWS_SECRET_ACCESS_KEY)

        if not all([bucket, aws_key, aws_secret]):
            logger.warning(
                "S3 provider configured but missing credentials. "
                f"Set {EnvVar.AWS_ACCESS_KEY_ID}, {EnvVar.AWS_SECRET_ACCESS_KEY}, "
                f"and {EnvVar.BUCKET_NAME}."
            )
            return False

    elif provider == StorageProvider.FILESYSTEM:
        if artifacts_path:
            path_obj = Path(artifacts_path)
            path_obj.mkdir(parents=True, exist_ok=True)
        else:
            logger.warning(
                f"Filesystem provider configured but {EnvVar.ARTIFACTS_PATH} not set. "
                "Defaulting to memory provider."
            )
            provider = StorageProvider.MEMORY

    try:
        from chuk_artifacts import ArtifactStore
        from chuk_mcp_server import set_global_artifact_store

        provider_str = provider.value if isinstance(provider, StorageProvider) else provider
        session_str = SessionProvider.REDIS.value if redis_url else SessionProvider.MEMORY.value

        store_kwargs: dict[str, Any] = {
            "storage_provider": provider_str,
            "session_provider": session_str,
        }

        if provider_str == StorageProvider.S3.value and bucket:
            store_kwargs["bucket"] = bucket
        elif provider_str == StorageProvider.FILESYSTEM.value and artifacts_path:
            store_kwargs["bucket"] = artifacts_path

        store = ArtifactStore(**store_kwargs)
        set_global_artifact_store(store)

        # Create storage wrapper with artifact store
        _storage = CelestialStorage(artifact_store=store)

        logger.info(f"Artifact store initialized successfully (provider: {provider})")
        return True

    except Exception as e:
        logger.warning(f"Artifact store not available: {e}")
        return False


# ============================================================================
# Existing Tools
# ============================================================================


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
        - Civil twilight is when the sun is 6 degrees below horizon
        - Use fracillum to determine moon brightness for night photography or stargazing
        - Moon transit time indicates when moon is highest in the sky (best viewing)

    Example:
        data = await get_sun_moon_data(
            date="2005-9-20", latitude=47.60, longitude=-122.33, timezone=-8, dst=True
        )
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
        date: Date of the eclipse in YYYY-MM-DD format. Valid range: 1800-01-01 to 2050-12-31
        latitude: Observer's latitude in decimal degrees (-90 to 90)
        longitude: Observer's longitude in decimal degrees (-180 to 180)
        height: Observer's height above mean sea level in meters. Default is 0.
            Range: -200 to 10000 meters.

    Returns:
        SolarEclipseByDateResponse: GeoJSON Feature with eclipse type, magnitude,
        obscuration, duration, and local circumstances.

    Tips for LLMs:
        - If description is "No Eclipse at this Location", the eclipse isn't visible here
        - magnitude >= 1.0 indicates total eclipse; < 1.0 is partial
        - altitude must be > 0 for eclipse to be visible (sun above horizon)
        - Use get_solar_eclipses_by_year first to find eclipse dates

    Example:
        eclipse = await get_solar_eclipse_by_date(
            date="2017-8-21", latitude=46.67, longitude=-122.65, height=15
        )
        print(f"Eclipse type: {eclipse.properties.description}")
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
        SolarEclipseByYearResponse with list of eclipse events.

    Tips for LLMs:
        - Most years have 2 solar eclipses, some have 3, rarely 4
        - After finding an eclipse date, use get_solar_eclipse_by_date to check visibility

    Example:
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
        timezone: Timezone offset from UTC in hours. If not provided, UTC (0) is used.
        dst: Whether to apply daylight saving time adjustment.

    Returns:
        SeasonsResponse with equinoxes, solstices, perihelion, and aphelion.

    Tips for LLMs:
        - Typically 6 events per year (2 equinoxes, 2 solstices, perihelion, aphelion)
        - Seasons are opposite in Northern and Southern hemispheres
        - Earth's 23.5 degree axial tilt causes seasons, not distance from sun

    Example:
        seasons = await get_earth_seasons(2024)
        for event in seasons.data:
            print(f"{event.phenom}: {event.month}/{event.day}/{event.year} at {event.time}")
    """
    provider = get_provider_for_tool("earth_seasons")
    return await provider.get_earth_seasons(year, timezone, dst)


# ============================================================================
# Planet Tools (v0.3.0)
# ============================================================================


@tool  # type: ignore[arg-type]
async def get_planet_position(
    planet: str,
    date: str,
    time: str,
    latitude: float,
    longitude: float,
    timezone: Optional[float] = None,
) -> PlanetPositionResponse:
    """Get position and observational data for a planet at a specific time and location.

    Returns altitude, azimuth, distance, phase illumination, apparent magnitude,
    constellation, equatorial coordinates (RA/Dec), elongation from the sun,
    and visibility status. Essential for planning astronomical observations
    and answering "where is [planet] tonight?" questions.

    Args:
        planet: Planet name. One of: Mercury, Venus, Mars, Jupiter, Saturn, Uranus, Neptune, Pluto
        date: Date in YYYY-MM-DD format (e.g., "2025-6-15")
        time: Time in HH:MM format, 24-hour (e.g., "22:30"). Interpreted as UTC unless
            timezone is specified.
        latitude: Observer's latitude in decimal degrees (-90 to 90)
        longitude: Observer's longitude in decimal degrees (-180 to 180)
        timezone: Timezone offset from UTC in hours (e.g., -8 for PST, 1 for CET).
            When provided, the time parameter is interpreted as local time.

    Returns:
        PlanetPositionResponse: GeoJSON Feature containing:
            - geometry: Observer location
            - properties.data: Planet position data:
                - altitude: Degrees above horizon (negative = below horizon)
                - azimuth: Degrees clockwise from north (0=N, 90=E, 180=S, 270=W)
                - distance_au / distance_km: Distance from observer
                - illumination: Phase illumination percentage (0-100)
                - magnitude: Apparent visual magnitude (lower = brighter)
                - constellation: IAU constellation abbreviation
                - right_ascension / declination: Equatorial coordinates (J2000)
                - elongation: Angular distance from sun in degrees
                - visibility: "visible", "below_horizon", or "lost_in_sunlight"
            - artifact_ref: Reference to stored computation (if artifact store configured)

    Tips for LLMs:
        - Lower magnitude = brighter. Venus can reach -4.4, Jupiter -2.7
        - Elongation < 10-15 degrees means planet is too close to the sun to see
        - altitude > 0 means the planet is above the horizon
        - azimuth tells you where to look: 0=North, 90=East, 180=South, 270=West
        - For "where is Mars tonight?", use time="21:00" with appropriate timezone
        - Mercury is hardest to see (small elongation), Venus and Jupiter are easiest

    Example:
        pos = await get_planet_position(
            planet="Mars", date="2025-6-15", time="22:00",
            latitude=47.6, longitude=-122.3, timezone=-7
        )
        data = pos.properties.data
        if data.visibility == "visible":
            print(f"Mars is at {data.altitude}° altitude, {data.azimuth}° azimuth")
            print(f"Magnitude: {data.magnitude}, in {data.constellation}")
    """
    try:
        provider = get_provider_for_tool("planet_position")
    except ValueError:
        raise RuntimeError(
            "Planet position requires the skyfield extra. "
            "Install with: pip install chuk-mcp-celestial[skyfield]"
        )
    result = await provider.get_planet_position(planet, date, time, latitude, longitude, timezone)

    # Store computation result
    artifact_ref = await _storage.save_position(
        planet=planet,
        date=date,
        time=time,
        lat=latitude,
        lon=longitude,
        data=result.properties.data.model_dump(),
    )
    if artifact_ref:
        result.artifact_ref = artifact_ref

    return result


@tool  # type: ignore[arg-type]
async def get_planet_events(
    planet: str,
    date: str,
    latitude: float,
    longitude: float,
    timezone: Optional[float] = None,
    dst: Optional[bool] = None,
) -> PlanetEventsResponse:
    """Get rise, set, and transit times for a planet on a given day at a location.

    Returns the times a planet rises above the horizon, transits the meridian
    (highest point), and sets below the horizon. Essential for planning when
    to observe a planet.

    Args:
        planet: Planet name. One of: Mercury, Venus, Mars, Jupiter, Saturn, Uranus, Neptune, Pluto
        date: Date in YYYY-MM-DD format (e.g., "2025-6-15")
        latitude: Observer's latitude in decimal degrees (-90 to 90)
        longitude: Observer's longitude in decimal degrees (-180 to 180)
        timezone: Timezone offset from UTC in hours (e.g., -8 for PST).
            When provided, event times are in local time.
        dst: Whether to apply daylight saving time adjustment.

    Returns:
        PlanetEventsResponse: GeoJSON Feature containing:
            - geometry: Observer location
            - properties.data:
                - planet: Planet name
                - date: Query date
                - events: List of rise/set/transit events with times
                - constellation: Current constellation
                - magnitude: Apparent visual magnitude
            - artifact_ref: Reference to stored computation (if artifact store configured)

    Tips for LLMs:
        - Events may be empty if the planet doesn't rise/set that day (polar regions)
        - Transit time is when the planet is highest — best viewing time
        - Use with get_planet_position to get full details at a specific time
        - Outer planets (Jupiter, Saturn) are above the horizon for ~12 hours
        - Inner planets (Mercury, Venus) are only visible near sunrise or sunset

    Example:
        events = await get_planet_events(
            planet="Jupiter", date="2025-6-15",
            latitude=51.5, longitude=-0.1, timezone=1
        )
        for event in events.properties.data.events:
            print(f"Jupiter {event.phen} at {event.time}")
    """
    try:
        provider = get_provider_for_tool("planet_events")
    except ValueError:
        raise RuntimeError(
            "Planet events requires the skyfield extra. "
            "Install with: pip install chuk-mcp-celestial[skyfield]"
        )
    result = await provider.get_planet_events(planet, date, latitude, longitude, timezone, dst)

    # Store computation result
    artifact_ref = await _storage.save_events(
        planet=planet,
        date=date,
        lat=latitude,
        lon=longitude,
        data=result.properties.data.model_dump(),
    )
    if artifact_ref:
        result.artifact_ref = artifact_ref

    return result


# ============================================================================
# Sky Summary Tool
# ============================================================================


def _azimuth_to_direction(az: float) -> str:
    """Convert azimuth degrees to compass direction."""
    directions = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]
    idx = round(az / 45) % 8
    return directions[idx]


@tool  # type: ignore[arg-type]
async def get_sky(
    date: str,
    time: str,
    latitude: float,
    longitude: float,
    timezone: Optional[float] = None,
) -> SkyResponse:
    """Get a complete sky summary — all planets, moon phase, and darkness — in one call.

    Returns which planets are visible, their positions and brightness, the current
    moon phase, and whether the sky is dark enough for observation. This is the
    recommended tool for "what's in the sky tonight?" questions.

    Args:
        date: Date in YYYY-MM-DD format (e.g., "2026-2-10")
        time: Time in HH:MM format, 24-hour (e.g., "21:00"). UTC unless timezone specified.
        latitude: Observer's latitude in decimal degrees (-90 to 90)
        longitude: Observer's longitude in decimal degrees (-180 to 180)
        timezone: Timezone offset from UTC in hours (e.g., 0 for GMT, -5 for EST, 1 for CET).
            When provided, the time parameter is interpreted as local time.

    Returns:
        SkyResponse: GeoJSON Feature containing:
            - properties.data.visible_planets: Planets above horizon and not lost in sunlight,
              sorted brightest first. Each has altitude, azimuth, direction, magnitude,
              constellation, and visibility status.
            - properties.data.all_planets: All 8 planets regardless of visibility
            - properties.data.moon: Current phase and illumination percentage
            - properties.data.is_dark: True if sun is below -6 degrees (civil twilight)
            - properties.data.summary: One-line text summary for quick display

    Tips for LLMs:
        - Use this instead of calling get_planet_position 8 times
        - The summary field gives a quick human-readable answer
        - visible_planets are sorted brightest first (lowest magnitude)
        - direction field gives compass bearing: "S" = look south, "NE" = northeast
        - is_dark=False means it's daytime or twilight — planets may not be visible even if above horizon
        - Combine with weather forecast to check if skies are clear enough to observe

    Example:
        sky = await get_sky(
            date="2026-2-10", time="21:00",
            latitude=51.99, longitude=0.84, timezone=0
        )
        for p in sky.properties.data.visible_planets:
            print(f"{p.planet}: {p.direction}, magnitude {p.magnitude}, in {p.constellation}")
        print(sky.properties.data.summary)
    """
    # Get planet provider (skyfield)
    try:
        planet_provider = get_provider_for_tool("sky")
    except ValueError:
        raise RuntimeError(
            "Sky summary requires the skyfield extra. "
            "Install with: pip install chuk-mcp-celestial[skyfield]"
        )

    # Compute all planet positions
    all_planets: list[SkyPlanetSummary] = []
    for planet_enum in Planet:
        try:
            result = await planet_provider.get_planet_position(
                planet_enum.value, date, time, latitude, longitude, timezone
            )
            data = result.properties.data
            all_planets.append(
                SkyPlanetSummary(
                    planet=data.planet,
                    altitude=data.altitude,
                    azimuth=data.azimuth,
                    magnitude=data.magnitude,
                    constellation=data.constellation,
                    elongation=data.elongation,
                    visibility=data.visibility,
                    direction=_azimuth_to_direction(data.azimuth),
                )
            )
        except Exception as exc:
            logger.warning("Failed to compute position for %s: %s", planet_enum.value, exc)

    # Filter visible planets (above horizon and not lost in sunlight), sort brightest first
    visible_planets = sorted(
        [p for p in all_planets if p.visibility == VisibilityStatus.VISIBLE],
        key=lambda p: p.magnitude,
    )

    # Get moon phase
    try:
        moon_provider = get_provider_for_tool("moon_phases")
        moon_result = await moon_provider.get_moon_phases(date, 4)
        first_phase = moon_result.phasedata[0] if moon_result.phasedata else None
        moon = SkyMoonSummary(
            phase="Unknown",
            illumination="Unknown",
            next_phase=(
                f"{first_phase.phase.value} on {first_phase.year}-{first_phase.month:02d}-{first_phase.day:02d}"
                if first_phase
                else None
            ),
            next_phase_date=(
                f"{first_phase.year}-{first_phase.month:02d}-{first_phase.day:02d}"
                if first_phase
                else None
            ),
        )
    except Exception as exc:
        logger.warning("Failed to get moon phases: %s", exc)
        moon = SkyMoonSummary(phase="Unknown", illumination="Unknown")

    # Determine if sky is dark (sun below -6 degrees = civil twilight)
    # We can check this by computing the sun's altitude using the skyfield provider
    is_dark = True
    try:
        eph = planet_provider.eph  # type: ignore[attr-defined]
        ts = planet_provider.ts  # type: ignore[attr-defined]
        from skyfield.api import wgs84

        year, month, day = map(int, date.split("-"))
        hour, minute = map(int, time.split(":"))
        utc_hour, utc_minute = hour, minute
        if timezone is not None:
            from datetime import datetime as dt
            from datetime import timedelta as td

            local = dt(year, month, day, hour, minute)
            utc = local - td(hours=timezone)
            year, month, day = utc.year, utc.month, utc.day
            utc_hour, utc_minute = utc.hour, utc.minute
        t = ts.utc(year, month, day, utc_hour, utc_minute)
        earth = eph["earth"]
        observer = earth + wgs84.latlon(latitude, longitude)
        sun = eph["sun"]
        sun_apparent = observer.at(t).observe(sun).apparent()
        sun_alt, _, _ = sun_apparent.altaz()
        is_dark = sun_alt.degrees < -6.0
    except Exception as exc:
        logger.warning("Failed to compute sun altitude: %s", exc)

    # Build summary string
    if visible_planets:
        planet_parts = [
            f"{p.planet.value} ({p.direction}, mag {p.magnitude})"
            for p in visible_planets
        ]
        summary = f"{len(visible_planets)} planet(s) visible: {', '.join(planet_parts)}."
    else:
        summary = "No planets currently visible."
    summary += f" Moon: {moon.phase} ({moon.illumination})."
    if not is_dark:
        summary += " Note: sky is not fully dark."

    sky_data = SkyData(
        date=date,
        time=time,
        is_dark=is_dark,
        visible_planets=visible_planets,
        all_planets=all_planets,
        moon=moon,
        summary=summary,
    )

    response = SkyResponse(
        apiversion="Skyfield 1.x",
        type="Feature",
        geometry=GeoJSONPoint(type="Point", coordinates=[longitude, latitude]),
        properties=SkyProperties(data=sky_data),
    )

    # Store result
    artifact_ref = await _storage.save_sky(
        date=date,
        time=time,
        lat=latitude,
        lon=longitude,
        data=sky_data.model_dump(),
    )
    if artifact_ref:
        response.artifact_ref = artifact_ref

    return response


# ============================================================================
# CLI Entry Point
# ============================================================================


def main() -> None:
    """Run the US Navy Celestial MCP server."""
    # Initialize artifact store at startup
    _init_artifact_store()

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
