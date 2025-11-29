"""US Navy Astronomical Applications API provider.

This provider uses the official US Navy API for all celestial calculations.
Data source: https://aa.usno.navy.mil/data/api
"""

import logging
from typing import Optional

import httpx

from ..config import NavyAPIConfig
from ..models import (
    MoonPhasesResponse,
    OneDayResponse,
    SeasonsResponse,
    SolarEclipseByDateResponse,
    SolarEclipseByYearResponse,
)
from .base import CelestialProvider

logger = logging.getLogger(__name__)


# API Endpoints
class NavyAPIEndpoints:
    """Navy API endpoint URLs."""

    def __init__(self, base_url: str):
        self.base = base_url
        self.moon_phases = f"{base_url}/moon/phases/date"
        self.rstt_oneday = f"{base_url}/rstt/oneday"
        self.solar_eclipse_date = f"{base_url}/eclipses/solar/date"
        self.solar_eclipse_year = f"{base_url}/eclipses/solar/year"
        self.seasons = f"{base_url}/seasons"


# API parameter limits (from Navy API documentation)
MIN_MOON_PHASES = 1
MAX_MOON_PHASES = 99
MIN_YEAR_MOON = 1700
MAX_YEAR_MOON = 2100
MIN_YEAR_ECLIPSE = 1800
MAX_YEAR_ECLIPSE = 2050
MIN_YEAR_SEASONS = 1700
MAX_YEAR_SEASONS = 2100
MIN_LATITUDE = -90.0
MAX_LATITUDE = 90.0
MIN_LONGITUDE = -180.0
MAX_LONGITUDE = 180.0
MIN_HEIGHT = -200  # meters
MAX_HEIGHT = 10000  # meters


class NavyAPIProvider(CelestialProvider):
    """Provider implementation using US Navy Astronomical Applications API.

    This is the reference implementation that calls the official Navy API
    for all astronomical calculations.
    """

    def __init__(
        self,
        base_url: str | None = None,
        timeout: float | None = None,
    ):
        """Initialize Navy API provider.

        Args:
            base_url: Base URL for Navy API (uses config default if None)
            timeout: Request timeout in seconds (uses config default if None)
        """
        self.base_url = base_url or NavyAPIConfig.BASE_URL
        self.timeout = timeout or NavyAPIConfig.TIMEOUT
        self.endpoints = NavyAPIEndpoints(self.base_url)
        logger.debug(f"Navy API provider initialized with base URL: {self.base_url}")

    async def get_moon_phases(
        self,
        date: str,
        num_phases: int = 12,
    ) -> MoonPhasesResponse:
        """Get upcoming moon phases starting from a given date.

        Args:
            date: Start date in YYYY-MM-DD format
            num_phases: Number of phases to return (1-99)

        Returns:
            MoonPhasesResponse with list of phase data

        Raises:
            ValueError: If num_phases is out of valid range
            httpx.HTTPError: If API request fails
        """
        if num_phases < MIN_MOON_PHASES or num_phases > MAX_MOON_PHASES:
            raise ValueError(f"num_phases must be between {MIN_MOON_PHASES} and {MAX_MOON_PHASES}")

        params = {
            "date": date,
            "nump": num_phases,
        }

        async with httpx.AsyncClient() as client:
            response = await client.get(
                self.endpoints.moon_phases,
                params=params,
                timeout=self.timeout,  # type: ignore[arg-type]
            )
            response.raise_for_status()
            data = response.json()

        return MoonPhasesResponse(**data)

    async def get_sun_moon_data(
        self,
        date: str,
        latitude: float,
        longitude: float,
        timezone: Optional[float] = None,
        dst: Optional[bool] = None,
        label: Optional[str] = None,
    ) -> OneDayResponse:
        """Get complete sun and moon data for one day at a specific location.

        Args:
            date: Date in YYYY-MM-DD format
            latitude: Latitude in decimal degrees (-90 to 90)
            longitude: Longitude in decimal degrees (-180 to 180)
            timezone: Timezone offset from UTC in hours
            dst: Whether to apply daylight saving time
            label: Optional user label (max 20 characters)

        Returns:
            OneDayResponse with sun/moon rise/set/transit times and moon phase

        Raises:
            httpx.HTTPError: If API request fails
        """
        params = {
            "date": date,
            "coords": f"{latitude},{longitude}",
        }

        if timezone is not None:
            params["tz"] = str(timezone)

        if dst is not None:
            params["dst"] = "true" if dst else "false"

        if label is not None:
            params["label"] = label[:20]  # API limit

        async with httpx.AsyncClient() as client:
            response = await client.get(
                self.endpoints.rstt_oneday,
                params=params,
                timeout=self.timeout,
            )
            response.raise_for_status()
            data = response.json()

        return OneDayResponse(**data)

    async def get_solar_eclipse_by_date(
        self,
        date: str,
        latitude: float,
        longitude: float,
        height: int = 0,
    ) -> SolarEclipseByDateResponse:
        """Get local solar eclipse circumstances for a specific date and location.

        Args:
            date: Date of the eclipse in YYYY-MM-DD format
            latitude: Observer's latitude in decimal degrees
            longitude: Observer's longitude in decimal degrees
            height: Observer's height above mean sea level in meters

        Returns:
            SolarEclipseByDateResponse with eclipse details and local circumstances

        Raises:
            ValueError: If height is out of valid range
            httpx.HTTPError: If API request fails
        """
        if height < MIN_HEIGHT or height > MAX_HEIGHT:
            raise ValueError(f"height must be between {MIN_HEIGHT} and {MAX_HEIGHT} meters")

        params = {
            "date": date,
            "coords": f"{latitude},{longitude}",
            "height": str(height),
        }

        async with httpx.AsyncClient() as client:
            response = await client.get(
                self.endpoints.solar_eclipse_date,
                params=params,
                timeout=self.timeout,
            )
            response.raise_for_status()
            data = response.json()

        return SolarEclipseByDateResponse(**data)

    async def get_solar_eclipses_by_year(
        self,
        year: int,
    ) -> SolarEclipseByYearResponse:
        """Get a list of all solar eclipses occurring in a specific year.

        Args:
            year: Year to query (1800-2050)

        Returns:
            SolarEclipseByYearResponse with list of eclipse events

        Raises:
            ValueError: If year is out of valid range
            httpx.HTTPError: If API request fails
        """
        if year < MIN_YEAR_ECLIPSE or year > MAX_YEAR_ECLIPSE:
            raise ValueError(f"year must be between {MIN_YEAR_ECLIPSE} and {MAX_YEAR_ECLIPSE}")

        params = {"year": str(year)}

        async with httpx.AsyncClient() as client:
            response = await client.get(
                self.endpoints.solar_eclipse_year,
                params=params,
                timeout=self.timeout,
            )
            response.raise_for_status()
            data = response.json()

        return SolarEclipseByYearResponse(**data)

    async def get_earth_seasons(
        self,
        year: int,
        timezone: Optional[float] = None,
        dst: Optional[bool] = None,
    ) -> SeasonsResponse:
        """Get Earth's seasons and orbital events for a year.

        Args:
            year: Year to query (1700-2100)
            timezone: Timezone offset from UTC in hours
            dst: Whether to apply daylight saving time

        Returns:
            SeasonsResponse with equinoxes, solstices, perihelion, and aphelion

        Raises:
            ValueError: If year is out of valid range
            httpx.HTTPError: If API request fails
        """
        if year < MIN_YEAR_SEASONS or year > MAX_YEAR_SEASONS:
            raise ValueError(f"year must be between {MIN_YEAR_SEASONS} and {MAX_YEAR_SEASONS}")

        params = {"year": str(year)}

        if timezone is not None:
            params["tz"] = str(timezone)

        if dst is not None:
            params["dst"] = "true" if dst else "false"

        async with httpx.AsyncClient() as client:
            response = await client.get(
                self.endpoints.seasons,
                params=params,
                timeout=self.timeout,
            )
            response.raise_for_status()
            data = response.json()

        return SeasonsResponse(**data)
