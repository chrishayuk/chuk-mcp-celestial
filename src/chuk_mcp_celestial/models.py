"""Pydantic models for US Navy Astronomical Data API responses.

All API responses are properly typed using Pydantic models for type safety,
validation, and better IDE support. No dictionary goop - everything is strongly typed.
"""

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


# ============================================================================
# Enums - No Magic Strings
# ============================================================================


class MoonPhase(str, Enum):
    """Moon phase enumeration."""

    NEW_MOON = "New Moon"
    FIRST_QUARTER = "First Quarter"
    FULL_MOON = "Full Moon"
    LAST_QUARTER = "Last Quarter"


class CelestialPhenomenon(str, Enum):
    """Rise/Set/Transit phenomenon types."""

    RISE = "Rise"
    SET = "Set"
    UPPER_TRANSIT = "Upper Transit"
    BEGIN_CIVIL_TWILIGHT = "Begin Civil Twilight"
    END_CIVIL_TWILIGHT = "End Civil Twilight"


class EclipsePhenomenon(str, Enum):
    """Solar eclipse phenomenon types."""

    ECLIPSE_BEGINS = "Eclipse Begins"
    TOTALITY_BEGINS = "Totality Begins"
    ANNULARITY_BEGINS = "Annularity Begins"
    MAXIMUM_ECLIPSE = "Maximum Eclipse"
    TOTALITY_ENDS = "Totality Ends"
    ANNULARITY_ENDS = "Annularity Ends"
    ECLIPSE_ENDS = "Eclipse Ends"


class SeasonPhenomenon(str, Enum):
    """Earth's seasonal phenomena."""

    EQUINOX = "Equinox"
    SOLSTICE = "Solstice"
    PERIHELION = "Perihelion"
    APHELION = "Aphelion"


class MoonCurPhase(str, Enum):
    """Current moon phase descriptions."""

    NEW_MOON = "New Moon"
    WAXING_CRESCENT = "Waxing Crescent"
    FIRST_QUARTER = "First Quarter"
    WAXING_GIBBOUS = "Waxing Gibbous"
    FULL_MOON = "Full Moon"
    WANING_GIBBOUS = "Waning Gibbous"
    LAST_QUARTER = "Last Quarter"
    WANING_CRESCENT = "Waning Crescent"


class DayOfWeek(str, Enum):
    """Days of the week."""

    MONDAY = "Monday"
    TUESDAY = "Tuesday"
    WEDNESDAY = "Wednesday"
    THURSDAY = "Thursday"
    FRIDAY = "Friday"
    SATURDAY = "Saturday"
    SUNDAY = "Sunday"


# ============================================================================
# Moon Phase Models
# ============================================================================


class MoonPhaseData(BaseModel):
    """Single moon phase occurrence.

    Represents one specific phase of the moon with exact timing.
    """

    phase: MoonPhase = Field(
        ..., description="The moon phase (New Moon, First Quarter, Full Moon, Last Quarter)"
    )
    year: int = Field(..., description="Year of the phase", ge=1700, le=2100)
    month: int = Field(..., description="Month of the phase (1-12)", ge=1, le=12)
    day: int = Field(..., description="Day of the month (1-31)", ge=1, le=31)
    time: str = Field(
        ..., description="Time in HH:MM format (24-hour). All times are in Universal Time (UT1)"
    )


class MoonPhasesResponse(BaseModel):
    """Moon phases API response.

    Contains a list of upcoming moon phases starting from a given date.
    """

    apiversion: str = Field(..., description="API version string")
    year: int = Field(..., description="Query year", ge=1700, le=2100)
    month: int = Field(..., description="Query month", ge=1, le=12)
    day: int = Field(..., description="Query day", ge=1, le=31)
    numphases: int = Field(..., description="Number of phases returned", ge=1, le=99)
    phasedata: list[MoonPhaseData] = Field(..., description="List of moon phase occurrences")


# ============================================================================
# Rise/Set/Transit Models
# ============================================================================


class CelestialEventData(BaseModel):
    """Single celestial rise/set/transit event."""

    phen: CelestialPhenomenon = Field(..., description="Type of phenomenon (Rise, Set, Transit)")
    time: str = Field(
        ..., description="Time in HH:MM format (24-hour). Timezone depends on query parameters"
    )


class ClosestPhaseData(BaseModel):
    """Closest moon phase to the queried date."""

    phase: MoonPhase = Field(..., description="The moon phase")
    year: int = Field(..., description="Year of the phase")
    month: int = Field(..., description="Month of the phase", ge=1, le=12)
    day: int = Field(..., description="Day of the phase", ge=1, le=31)
    time: str = Field(..., description="Time in HH:MM format (UT1)")


class OneDayData(BaseModel):
    """Complete sun and moon data for one day."""

    year: int = Field(..., description="Year")
    month: int = Field(..., description="Month", ge=1, le=12)
    day: int = Field(..., description="Day", ge=1, le=31)
    day_of_week: DayOfWeek = Field(..., description="Day of the week")
    tz: float = Field(..., description="Timezone offset from UTC (hours, east positive)")
    isdst: bool = Field(..., description="Whether daylight saving time is in effect")
    sundata: list[CelestialEventData] = Field(
        ...,
        description="Sun events (rise, set, transit, twilight). "
        "Events are ordered chronologically. May be empty for polar regions during extreme seasons",
    )
    moondata: list[CelestialEventData] = Field(
        ...,
        description="Moon events (rise, set, transit). "
        "May be empty if moon doesn't rise/set on this day (polar regions)",
    )
    closestphase: ClosestPhaseData = Field(..., description="Closest moon phase to this date")
    curphase: MoonCurPhase = Field(..., description="Current phase of the moon")
    fracillum: str = Field(
        ..., description="Fraction of moon illuminated as percentage (e.g., '92%')"
    )
    label: Optional[str] = Field(
        None, description="Optional user-provided label from query parameter"
    )


class GeoJSONPoint(BaseModel):
    """GeoJSON Point geometry."""

    type: str = Field(..., description="Geometry type (always 'Point')")
    coordinates: list[float] = Field(
        ...,
        description="Coordinates as [longitude, latitude] (note: lon, lat order per GeoJSON spec)",
    )


class OneDayProperties(BaseModel):
    """Properties for OneDay GeoJSON Feature."""

    data: OneDayData = Field(..., description="The complete sun/moon data for the day")


class OneDayResponse(BaseModel):
    """Rise/Set/Transit API response in GeoJSON Feature format."""

    apiversion: str = Field(..., description="API version string")
    type: str = Field(..., description="GeoJSON type (always 'Feature')")
    geometry: GeoJSONPoint = Field(..., description="Location geometry")
    properties: OneDayProperties = Field(..., description="Sun and moon data")


# ============================================================================
# Solar Eclipse Models
# ============================================================================


class EclipseLocalData(BaseModel):
    """Local circumstances of a solar eclipse event.

    Contains positional data for the sun during different eclipse phases.
    """

    day: str = Field(..., description="Day of the month")
    phenomenon: EclipsePhenomenon = Field(..., description="Eclipse phase")
    time: str = Field(..., description="Local time in HH:MM:SS.S format")
    altitude: str = Field(..., description="Sun altitude in degrees above horizon")
    azimuth: str = Field(..., description="Sun azimuth in degrees (0=N, 90=E, 180=S, 270=W)")
    position_angle: Optional[str] = Field(
        None,
        description="Position angle of the eclipse in degrees (where on the sun's disk the eclipse occurs)",
    )
    vertex_angle: Optional[str] = Field(
        None, description="Vertex angle in degrees (orientation of the eclipse path)"
    )


class EclipseProperties(BaseModel):
    """Properties of a solar eclipse at a specific location."""

    year: int = Field(..., description="Year of the eclipse")
    month: int = Field(..., description="Month of the eclipse")
    day: int = Field(..., description="Day of the eclipse")
    event: str = Field(..., description="Full description of the eclipse event")
    description: str = Field(
        ...,
        description="Type of eclipse at this location (e.g., 'Sun in Partial Eclipse at this Location', "
        "'Sun in Total Eclipse at this Location', 'No Eclipse at this Location')",
    )
    magnitude: Optional[str] = Field(
        None,
        description="Eclipse magnitude (fraction of sun's diameter covered). "
        "1.0+ indicates total eclipse, <1.0 indicates partial",
    )
    obscuration: Optional[str] = Field(
        None, description="Percentage of sun's area covered (e.g., '95.4%')"
    )
    duration: Optional[str] = Field(
        None, description="Duration of the eclipse at this location (e.g., '2h 31m 01.9s')"
    )
    delta_t: str = Field(
        ..., description="Delta T value used for calculations (difference between TT and UT1)"
    )
    local_data: list[EclipseLocalData] = Field(
        ..., description="List of local eclipse events (begins, maximum, ends) with sun positions"
    )


class SolarEclipseByDateResponse(BaseModel):
    """Solar eclipse data for a specific location and date (GeoJSON Feature)."""

    apiversion: str = Field(..., description="API version string")
    type: str = Field(..., description="GeoJSON type (always 'Feature')")
    geometry: GeoJSONPoint = Field(..., description="Location geometry")
    properties: EclipseProperties = Field(
        ..., description="Eclipse properties and local circumstances"
    )


class SolarEclipseEvent(BaseModel):
    """A single solar eclipse in a year list."""

    year: int = Field(..., description="Year of the eclipse")
    month: int = Field(..., description="Month of the eclipse", ge=1, le=12)
    day: int = Field(..., description="Day of the eclipse", ge=1, le=31)
    event: str = Field(..., description="Full description of the eclipse")


class SolarEclipseByYearResponse(BaseModel):
    """List of all solar eclipses in a given year."""

    apiversion: str = Field(..., description="API version string")
    year: int = Field(..., description="Query year", ge=1800, le=2050)
    eclipses_in_year: list[SolarEclipseEvent] = Field(
        ..., description="List of solar eclipses occurring in this year"
    )


# ============================================================================
# Earth's Seasons Models
# ============================================================================


class SeasonEvent(BaseModel):
    """A seasonal event (equinox, solstice, perihelion, aphelion)."""

    year: int = Field(..., description="Year")
    month: int = Field(..., description="Month", ge=1, le=12)
    day: int = Field(..., description="Day", ge=1, le=31)
    time: str = Field(
        ...,
        description="Time in HH:MM format. Timezone depends on query parameters (default UTC)",
    )
    phenom: SeasonPhenomenon = Field(
        ...,
        description="Type of phenomenon. "
        "Equinox occurs at vernal (spring) and autumnal (fall) equinoxes. "
        "Solstice occurs at summer and winter solstices. "
        "Perihelion is Earth's closest approach to sun. "
        "Aphelion is Earth's farthest point from sun.",
    )


class SeasonsResponse(BaseModel):
    """Earth's seasons and orbital events for a year."""

    apiversion: str = Field(..., description="API version string")
    year: int = Field(..., description="Query year", ge=1700, le=2100)
    tz: float = Field(..., description="Timezone offset used (hours, east positive)")
    dst: bool = Field(..., description="Whether daylight saving time adjustment was applied")
    data: list[SeasonEvent] = Field(
        ...,
        description="List of seasonal events for the year. "
        "Typically contains: 2 equinoxes, 2 solstices, 1 perihelion, 1 aphelion",
    )


# ============================================================================
# Planet Enums
# ============================================================================


class Planet(str, Enum):
    """Solar system planets supported for position and event queries."""

    MERCURY = "Mercury"
    VENUS = "Venus"
    MARS = "Mars"
    JUPITER = "Jupiter"
    SATURN = "Saturn"
    URANUS = "Uranus"
    NEPTUNE = "Neptune"
    PLUTO = "Pluto"


class VisibilityStatus(str, Enum):
    """Planet visibility status from an observer's location."""

    VISIBLE = "visible"
    BELOW_HORIZON = "below_horizon"
    LOST_IN_SUNLIGHT = "lost_in_sunlight"


# ============================================================================
# Planet Position Models
# ============================================================================


class PlanetPositionData(BaseModel):
    """Position and observational data for a planet at a specific time and location."""

    planet: Planet = Field(..., description="Planet name")
    date: str = Field(..., description="Date in YYYY-MM-DD format")
    time: str = Field(..., description="Time in HH:MM format (UTC or requested timezone)")
    altitude: float = Field(
        ..., description="Altitude in degrees above horizon (-90 to 90). Negative = below horizon"
    )
    azimuth: float = Field(
        ..., description="Azimuth in degrees clockwise from north (0=N, 90=E, 180=S, 270=W)"
    )
    distance_au: float = Field(..., description="Distance from observer in astronomical units")
    distance_km: float = Field(..., description="Distance from observer in kilometres")
    illumination: float = Field(
        ..., description="Phase illumination percentage (0-100). 100 = fully illuminated"
    )
    magnitude: float = Field(..., description="Approximate apparent visual magnitude")
    constellation: str = Field(
        ..., description="Constellation the planet currently appears in (IAU abbreviation)"
    )
    right_ascension: str = Field(
        ..., description="Right ascension in HH:MM:SS format (J2000 epoch)"
    )
    declination: str = Field(..., description="Declination in DD:MM:SS format (J2000 epoch)")
    elongation: float = Field(..., description="Angular distance from the sun in degrees (0-180)")
    visibility: VisibilityStatus = Field(
        ..., description="Visibility status from the observer's location"
    )


class PlanetPositionProperties(BaseModel):
    """Properties for PlanetPosition GeoJSON Feature."""

    data: PlanetPositionData = Field(..., description="Planet position data")


class PlanetPositionResponse(BaseModel):
    """Planet position at a specific time and location (GeoJSON Feature)."""

    apiversion: str = Field(..., description="API version string")
    type: str = Field(default="Feature", description="GeoJSON type (always 'Feature')")
    geometry: GeoJSONPoint = Field(..., description="Observer location geometry")
    properties: PlanetPositionProperties = Field(..., description="Planet position data")
    artifact_ref: Optional[str] = Field(
        None, description="Artifact reference for stored computation result"
    )


# ============================================================================
# Planet Events Models
# ============================================================================


class PlanetEventData(BaseModel):
    """A single planet rise/set/transit event."""

    phen: str = Field(..., description="Phenomenon type: Rise, Set, or Upper Transit")
    time: str = Field(..., description="Time in HH:MM format. Timezone depends on query parameters")


class PlanetEventsData(BaseModel):
    """Complete planet event data for one day."""

    planet: Planet = Field(..., description="Planet name")
    date: str = Field(..., description="Date in YYYY-MM-DD format")
    events: list[PlanetEventData] = Field(
        ...,
        description="Rise, set, and transit events. "
        "May be empty if planet doesn't rise/set on this day (polar regions)",
    )
    constellation: str = Field(..., description="Constellation the planet appears in")
    magnitude: float = Field(..., description="Approximate apparent visual magnitude")


class PlanetEventsProperties(BaseModel):
    """Properties for PlanetEvents GeoJSON Feature."""

    data: PlanetEventsData = Field(..., description="Planet events data")


class PlanetEventsResponse(BaseModel):
    """Planet rise/set/transit times for one day at a location (GeoJSON Feature)."""

    apiversion: str = Field(..., description="API version string")
    type: str = Field(default="Feature", description="GeoJSON type (always 'Feature')")
    geometry: GeoJSONPoint = Field(..., description="Observer location geometry")
    properties: PlanetEventsProperties = Field(..., description="Planet events data")
    artifact_ref: Optional[str] = Field(
        None, description="Artifact reference for stored computation result"
    )


# ============================================================================
# Sky Summary Models
# ============================================================================


class SkyPlanetSummary(BaseModel):
    """Summary of a single planet's position for sky overview."""

    planet: Planet = Field(..., description="Planet name")
    altitude: float = Field(
        ..., description="Altitude in degrees above horizon (-90 to 90)"
    )
    azimuth: float = Field(
        ..., description="Azimuth in degrees clockwise from north (0-360)"
    )
    magnitude: float = Field(..., description="Apparent visual magnitude")
    constellation: str = Field(..., description="IAU constellation abbreviation")
    elongation: float = Field(
        ..., description="Angular distance from the sun in degrees"
    )
    visibility: VisibilityStatus = Field(..., description="Visibility status")
    direction: str = Field(
        ..., description="Compass direction: N, NE, E, SE, S, SW, W, NW"
    )


class SkyMoonSummary(BaseModel):
    """Moon summary for sky overview."""

    phase: str = Field(..., description="Current moon phase (e.g., 'Waxing Crescent')")
    illumination: str = Field(
        ..., description="Illumination percentage (e.g., '45%')"
    )
    next_phase: Optional[str] = Field(
        None, description="Next phase description (e.g., 'Full Moon on 2026-02-17')"
    )
    next_phase_date: Optional[str] = Field(
        None, description="Date of next phase in YYYY-MM-DD format"
    )


class SkyData(BaseModel):
    """Complete sky summary data for a date/time/location."""

    date: str = Field(..., description="Date in YYYY-MM-DD format")
    time: str = Field(..., description="Time in HH:MM format")
    is_dark: bool = Field(
        ..., description="True if sun is below -6 degrees (civil twilight)"
    )
    visible_planets: list[SkyPlanetSummary] = Field(
        ...,
        description="Planets above horizon and not lost in sunlight, "
        "sorted brightest first",
    )
    all_planets: list[SkyPlanetSummary] = Field(
        ..., description="All 8 planets regardless of visibility"
    )
    moon: SkyMoonSummary = Field(..., description="Moon phase and illumination")
    summary: str = Field(
        ...,
        description="One-line human-readable summary of what's visible",
    )


class SkyProperties(BaseModel):
    """Properties for Sky GeoJSON Feature."""

    data: SkyData = Field(..., description="Sky summary data")


class SkyResponse(BaseModel):
    """Complete sky summary for a date/time/location (GeoJSON Feature)."""

    apiversion: str = Field(..., description="API version string")
    type: str = Field(default="Feature", description="GeoJSON type (always 'Feature')")
    geometry: GeoJSONPoint = Field(..., description="Observer location geometry")
    properties: SkyProperties = Field(..., description="Sky summary data")
    artifact_ref: Optional[str] = Field(
        None, description="Artifact reference for stored result"
    )
