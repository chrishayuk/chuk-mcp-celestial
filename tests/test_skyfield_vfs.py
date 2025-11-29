"""Test Skyfield provider with virtual filesystem storage."""

import pytest

pytestmark = pytest.mark.asyncio


class TestSkyfieldVFS:
    """Test Skyfield provider with different storage backends."""

    async def test_memory_backend(self):
        """Test Skyfield with memory storage backend."""
        from chuk_mcp_celestial.providers.skyfield_provider import SkyfieldProvider

        # Create provider with memory backend
        provider = SkyfieldProvider(
            ephemeris_file="de421.bsp", storage_backend="memory", auto_download=True
        )

        # Should be able to initialize VFS
        await provider._initialize_vfs()
        assert provider._vfs_initialized
        assert provider._vfs is not None
        assert provider.storage_backend == "memory"

    async def test_local_backend(self):
        """Test Skyfield with local storage backend."""
        from chuk_mcp_celestial.providers.skyfield_provider import SkyfieldProvider

        # Create provider with local backend
        provider = SkyfieldProvider(
            ephemeris_file="de421.bsp", storage_backend="local", auto_download=True
        )

        # Should be able to initialize VFS
        await provider._initialize_vfs()
        assert provider._vfs_initialized
        assert provider._vfs is not None
        assert provider.storage_backend == "local"

    @pytest.mark.network
    async def test_moon_phases_with_vfs(self):
        """Test moon phases calculation with VFS-backed ephemeris."""
        from chuk_mcp_celestial.providers.skyfield_provider import SkyfieldProvider

        # Create provider with memory backend for testing
        provider = SkyfieldProvider(
            ephemeris_file="de421.bsp", storage_backend="memory", auto_download=True
        )

        # Get moon phases - this should download ephemeris if needed
        result = await provider.get_moon_phases("2024-1-1", num_phases=4)

        # Verify we got results
        assert result is not None
        assert len(result.phasedata) == 4
        assert result.year == 2024
        assert result.month == 1

    @pytest.mark.network
    async def test_seasons_with_vfs(self):
        """Test seasons calculation with VFS-backed ephemeris."""
        from chuk_mcp_celestial.providers.skyfield_provider import SkyfieldProvider

        # Create provider with memory backend for testing
        provider = SkyfieldProvider(
            ephemeris_file="de421.bsp", storage_backend="memory", auto_download=True
        )

        # Get seasons - this should download ephemeris if needed
        result = await provider.get_earth_seasons(2024)

        # Verify we got 4 season events
        assert result is not None
        assert len(result.data) == 4
        assert result.year == 2024

    async def test_cache_dir_created(self):
        """Test that cache directory is created."""
        from chuk_mcp_celestial.providers.skyfield_provider import SkyfieldProvider

        provider = SkyfieldProvider(storage_backend="memory")

        # Cache dir should exist
        assert provider.cache_dir.exists()
        assert provider.cache_dir.is_dir()
        assert "chuk-celestial-cache" in str(provider.cache_dir)

    async def test_invalid_backend(self):
        """Test that invalid backend raises error."""
        from chuk_mcp_celestial.providers.skyfield_provider import SkyfieldProvider

        provider = SkyfieldProvider(storage_backend="invalid_backend")

        # Should raise ValueError when initializing VFS
        with pytest.raises(ValueError, match="Unknown storage backend"):
            await provider._initialize_vfs()

    async def test_not_implemented_methods(self):
        """Test that unimplemented methods raise NotImplementedError."""
        from chuk_mcp_celestial.providers.skyfield_provider import SkyfieldProvider

        provider = SkyfieldProvider(storage_backend="memory")

        # Sun/moon data not implemented
        with pytest.raises(
            NotImplementedError,
            match="Sun/Moon rise/set calculations with Skyfield are coming soon",
        ):
            await provider.get_sun_moon_data(date="2024-01-01", latitude=40.7, longitude=-74.0)

        # Solar eclipse by date not implemented
        with pytest.raises(
            NotImplementedError,
            match="Solar eclipse calculations are not supported in Skyfield provider",
        ):
            await provider.get_solar_eclipse_by_date(
                date="2024-04-08", latitude=40.7, longitude=-74.0
            )

        # Solar eclipse by year not implemented
        with pytest.raises(
            NotImplementedError,
            match="Solar eclipse search is not supported in Skyfield provider",
        ):
            await provider.get_solar_eclipses_by_year(year=2024)

    async def test_config_defaults(self):
        """Test that config defaults are used when not specified."""
        from chuk_mcp_celestial.providers.skyfield_provider import SkyfieldProvider

        provider = SkyfieldProvider()

        # Should use config defaults - verify they're valid values
        assert provider.ephemeris_file in ["de421.bsp", "de440s.bsp", "de440.bsp"]
        assert provider.storage_backend in ["local", "s3", "memory"]
        assert isinstance(provider.auto_download, bool)

    async def test_custom_config(self):
        """Test that custom config overrides defaults."""
        from chuk_mcp_celestial.providers.skyfield_provider import SkyfieldProvider

        provider = SkyfieldProvider(
            ephemeris_file="de440s.bsp",
            storage_backend="local",
            auto_download=False,
        )

        assert provider.ephemeris_file == "de440s.bsp"
        assert provider.storage_backend == "local"
        assert provider.auto_download is False

    async def test_vfs_reinitialization(self):
        """Test that VFS is not reinitialized if already initialized."""
        from chuk_mcp_celestial.providers.skyfield_provider import SkyfieldProvider

        provider = SkyfieldProvider(storage_backend="memory")

        # Initialize first time
        await provider._initialize_vfs()
        vfs1 = provider._vfs

        # Initialize again
        await provider._initialize_vfs()
        vfs2 = provider._vfs

        # Should be same instance
        assert vfs1 is vfs2
