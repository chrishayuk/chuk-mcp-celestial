"""Skyfield-based celestial calculations provider.

This provider uses the Skyfield library for local astronomical calculations.
Requires skyfield package and ephemeris data files.

Storage backends:
- local: Traditional local filesystem storage
- s3: Cloud storage using chuk-virtual-fs with S3 backend
- memory: In-memory storage for testing
"""

import logging
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from chuk_virtual_fs import AsyncVirtualFileSystem

from ..config import SkyfieldConfig
from ..models import (
    MoonPhase,
    MoonPhaseData,
    MoonPhasesResponse,
    OneDayResponse,
    SeasonsResponse,
    SolarEclipseByDateResponse,
    SolarEclipseByYearResponse,
)
from .base import CelestialProvider

logger = logging.getLogger(__name__)

try:
    from skyfield import almanac
    from skyfield.iokit import Loader

    SKYFIELD_AVAILABLE = True
except ImportError:
    SKYFIELD_AVAILABLE = False
    logger.warning("Skyfield library not available. Install with: pip install skyfield")


class SkyfieldProvider(CelestialProvider):
    """Provider implementation using Skyfield for local calculations.

    This provider performs astronomical calculations locally using the
    Skyfield library and JPL ephemeris data.

    Advantages:
    - Offline calculations (after ephemeris download)
    - Faster (no network latency)
    - Research-grade accuracy

    Limitations:
    - Solar eclipse local circumstances not natively supported (workaround available)
    - Requires ~10-50 MB ephemeris data download
    """

    def __init__(
        self,
        ephemeris_file: str | None = None,
        storage_backend: str | None = None,
        auto_download: bool | None = None,
    ):
        """Initialize Skyfield provider.

        Args:
            ephemeris_file: Ephemeris file to use (default: from config)
            storage_backend: Storage backend - 'local', 's3', or 'memory' (default: from config)
            auto_download: Auto-download ephemeris if not present (default: True)

        Raises:
            ImportError: If skyfield is not installed
        """
        if not SKYFIELD_AVAILABLE:
            raise ImportError(
                "Skyfield library is required for this provider. Install with: pip install skyfield"
            )

        self.ephemeris_file = ephemeris_file or SkyfieldConfig.EPHEMERIS_FILE
        self.storage_backend = storage_backend or SkyfieldConfig.STORAGE_BACKEND
        self.auto_download = (
            auto_download if auto_download is not None else SkyfieldConfig.AUTO_DOWNLOAD
        )

        # Virtual filesystem for ephemeris storage
        self._vfs: Optional[AsyncVirtualFileSystem] = None
        self._vfs_initialized = False

        # Local cache directory for Skyfield to read from
        # Skyfield needs actual files on disk, so we cache from VFS
        self.cache_dir = Path(tempfile.gettempdir()) / "chuk-celestial-cache"
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        # Initialize Skyfield loader with cache directory
        self.loader = Loader(str(self.cache_dir), verbose=False)

        # Load timescale (small file, auto-downloaded by Skyfield)
        self.ts = self.loader.timescale()

        # Load ephemeris (lazy loaded on first use)
        self._eph = None

        logger.debug(
            f"Skyfield provider initialized: backend={self.storage_backend}, "
            f"ephemeris={self.ephemeris_file}, cache={self.cache_dir}"
        )

    async def _initialize_vfs(self):
        """Initialize virtual filesystem if not already done."""
        if self._vfs_initialized:
            return

        if self.storage_backend == "local":
            # Local storage - use traditional directory
            data_dir = Path(SkyfieldConfig.DATA_DIR).expanduser()
            self._vfs = AsyncVirtualFileSystem(provider="filesystem", root_path=str(data_dir))
        elif self.storage_backend == "s3":
            # S3 storage with chuk-virtual-fs
            self._vfs = AsyncVirtualFileSystem(
                provider="s3",
                bucket_name=SkyfieldConfig.S3_BUCKET,
                prefix=SkyfieldConfig.S3_PREFIX,
                region_name=SkyfieldConfig.S3_REGION,
            )
        elif self.storage_backend == "memory":
            # In-memory storage (for testing)
            self._vfs = AsyncVirtualFileSystem(provider="memory")
        else:
            raise ValueError(
                f"Unknown storage backend: {self.storage_backend}. "
                "Must be 'local', 's3', or 'memory'"
            )

        await self._vfs.initialize()
        self._vfs_initialized = True
        logger.debug(f"Initialized VFS with {self.storage_backend} backend")

    async def _ensure_ephemeris_cached(self):
        """Ensure ephemeris file is available in local cache.

        Downloads from VFS storage if needed.
        """
        await self._initialize_vfs()

        cache_path = self.cache_dir / self.ephemeris_file
        vfs_path = f"/{self.ephemeris_file}"

        # Check if already in cache
        if cache_path.exists():
            logger.debug(f"Ephemeris {self.ephemeris_file} found in cache")
            return

        # Try to download from VFS storage
        if await self._vfs.exists(vfs_path):
            logger.info(
                f"Downloading ephemeris {self.ephemeris_file} from {self.storage_backend} to cache"
            )
            content = await self._vfs.read_file(vfs_path)
            cache_path.write_bytes(content)
            logger.info(f"Cached ephemeris: {cache_path}")
        elif self.auto_download:
            # Let Skyfield download it, then upload to VFS
            logger.info(f"Ephemeris not found, letting Skyfield download {self.ephemeris_file}")
            # Skyfield will download to cache_dir via loader
            # After loading, we'll upload to VFS storage
        else:
            raise FileNotFoundError(
                f"Ephemeris file {self.ephemeris_file} not found in {self.storage_backend} "
                f"and auto_download is disabled"
            )

    @property
    def eph(self):
        """Lazy-load ephemeris data."""
        if self._eph is None:
            try:
                # Note: This is sync, but loading happens in async context
                # The actual caching is done in async methods before this is called
                self._eph = self.loader(self.ephemeris_file)
                logger.info(f"Loaded ephemeris: {self.ephemeris_file}")
            except Exception as e:
                logger.error(f"Failed to load ephemeris {self.ephemeris_file}: {e}")
                raise

        return self._eph

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
        """
        # Ensure ephemeris is available in cache
        await self._ensure_ephemeris_cached()

        # Parse date
        year, month, day = map(int, date.split("-"))

        # Create time range
        t0 = self.ts.utc(year, month, day)

        # Estimate end time (num_phases * 7.4 days average per phase)
        # A lunar cycle is ~29.5 days, so 4 phases = 7.4 days per phase
        days = int(num_phases * 7.4) + 2  # Add buffer

        # Calculate end date
        start_dt = datetime(year, month, day)
        end_dt = start_dt + timedelta(days=days)
        t1 = self.ts.utc(end_dt.year, end_dt.month, end_dt.day)

        # Find phase events using Skyfield
        t, phase_codes = almanac.find_discrete(t0, t1, almanac.moon_phases(self.eph))

        # Convert to our Pydantic models
        phases = []
        for time_obj, code in zip(t[:num_phases], phase_codes[:num_phases]):
            utc_time = time_obj.utc_datetime()

            # Map Skyfield phase codes (0-3) to our enum
            phase_map = {
                0: MoonPhase.NEW_MOON,
                1: MoonPhase.FIRST_QUARTER,
                2: MoonPhase.FULL_MOON,
                3: MoonPhase.LAST_QUARTER,
            }

            phases.append(
                MoonPhaseData(
                    phase=phase_map[code],
                    year=utc_time.year,
                    month=utc_time.month,
                    day=utc_time.day,
                    time=f"{utc_time.hour:02d}:{utc_time.minute:02d}",
                )
            )

        return MoonPhasesResponse(
            apiversion="Skyfield 1.x",
            year=year,
            month=month,
            day=day,
            numphases=len(phases),
            phasedata=phases,
        )

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

        Note: This is a placeholder implementation. Full implementation requires
        converting Skyfield results to Navy API GeoJSON format.

        Args:
            date: Date in YYYY-MM-DD format
            latitude: Latitude in decimal degrees
            longitude: Longitude in decimal degrees
            timezone: Timezone offset from UTC in hours
            dst: Whether to apply daylight saving time
            label: Optional user label

        Returns:
            OneDayResponse with sun/moon rise/set/transit times

        Raises:
            NotImplementedError: This method is not yet fully implemented
        """
        raise NotImplementedError(
            "Sun/Moon rise/set calculations with Skyfield are coming soon. "
            "Use Navy API provider for this functionality."
        )

    async def get_solar_eclipse_by_date(
        self,
        date: str,
        latitude: float,
        longitude: float,
        height: int = 0,
    ) -> SolarEclipseByDateResponse:
        """Get local solar eclipse circumstances for a specific date and location.

        Note: Skyfield does not natively support solar eclipse local circumstances.
        A workaround using angular separation is possible but not yet implemented.

        Args:
            date: Date of the eclipse in YYYY-MM-DD format
            latitude: Observer's latitude in decimal degrees
            longitude: Observer's longitude in decimal degrees
            height: Observer's height above mean sea level in meters

        Returns:
            SolarEclipseByDateResponse with eclipse details

        Raises:
            NotImplementedError: This method is not yet implemented
        """
        raise NotImplementedError(
            "Solar eclipse calculations are not supported in Skyfield provider. "
            "Use Navy API provider for this functionality."
        )

    async def get_solar_eclipses_by_year(
        self,
        year: int,
    ) -> SolarEclipseByYearResponse:
        """Get a list of all solar eclipses occurring in a specific year.

        Note: Skyfield does not have built-in solar eclipse search.

        Args:
            year: Year to query

        Returns:
            SolarEclipseByYearResponse with list of eclipse events

        Raises:
            NotImplementedError: This method is not yet implemented
        """
        raise NotImplementedError(
            "Solar eclipse search is not supported in Skyfield provider. "
            "Use Navy API provider for this functionality."
        )

    async def get_earth_seasons(
        self,
        year: int,
        timezone: Optional[float] = None,
        dst: Optional[bool] = None,
    ) -> SeasonsResponse:
        """Get Earth's seasons and orbital events for a year.

        Uses Skyfield's almanac.seasons() to find equinoxes and solstices.
        Note: Perihelion and aphelion are not yet implemented.

        Args:
            year: Year to query
            timezone: Timezone offset from UTC in hours
            dst: Whether to apply daylight saving time

        Returns:
            SeasonsResponse with equinoxes and solstices
        """
        # Ensure ephemeris is available in cache
        await self._ensure_ephemeris_cached()

        from ..models import SeasonEvent, SeasonPhenomenon

        # Create time range for the year
        t0 = self.ts.utc(year, 1, 1)
        t1 = self.ts.utc(year + 1, 1, 1)

        # Find season events using Skyfield
        t, season_codes = almanac.find_discrete(t0, t1, almanac.seasons(self.eph))

        # Map Skyfield season codes to our enums
        # Skyfield: 0=March Equinox, 1=June Solstice, 2=September Equinox, 3=December Solstice
        season_map = {
            0: ("March Equinox", SeasonPhenomenon.EQUINOX),
            1: ("June Solstice", SeasonPhenomenon.SOLSTICE),
            2: ("September Equinox", SeasonPhenomenon.EQUINOX),
            3: ("December Solstice", SeasonPhenomenon.SOLSTICE),
        }

        # Convert to our Pydantic models
        season_events = []
        for time_obj, code in zip(t, season_codes):
            # Apply timezone offset if specified
            if timezone is not None:
                # Convert to UTC datetime, then adjust for timezone
                utc_time = time_obj.utc_datetime()
                offset_hours = timezone
                if dst:
                    offset_hours += 1  # Add DST hour
                adjusted_time = utc_time + timedelta(hours=offset_hours)
            else:
                adjusted_time = time_obj.utc_datetime()

            phenom_name, phenom_type = season_map[code]

            season_events.append(
                SeasonEvent(
                    phenom=phenom_type,  # Use the enum directly
                    year=adjusted_time.year,
                    month=adjusted_time.month,
                    day=adjusted_time.day,
                    time=f"{adjusted_time.hour:02d}:{adjusted_time.minute:02d}",
                )
            )

        # Note: Perihelion and Aphelion are not calculated by Skyfield's almanac
        # They would require orbital mechanics calculations

        return SeasonsResponse(
            apiversion="Skyfield 1.x",
            year=year,
            tz=timezone if timezone is not None else 0.0,
            dst=dst if dst is not None else False,
            data=season_events,
        )
