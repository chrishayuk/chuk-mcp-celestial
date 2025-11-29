"""Comparison tests between Navy API and Skyfield providers.

This module tests both providers with the same inputs and compares results
to verify accuracy and consistency.
"""

import pytest
from datetime import datetime

from chuk_mcp_celestial.providers.navy import NavyAPIProvider
from chuk_mcp_celestial.providers.skyfield_provider import SkyfieldProvider


@pytest.fixture
def navy_provider():
    """Get Navy API provider instance."""
    return NavyAPIProvider()


@pytest.fixture
def skyfield_provider():
    """Get Skyfield provider instance."""
    try:
        return SkyfieldProvider(storage_backend="memory", auto_download=True)
    except ImportError:
        pytest.skip("Skyfield not installed")


class TestMoonPhasesComparison:
    """Compare moon phase calculations between providers."""

    @pytest.mark.asyncio
    @pytest.mark.network
    async def test_moon_phases_same_date(self, navy_provider, skyfield_provider):
        """Compare moon phases for the same date from both providers."""
        date = "2024-1-1"
        num_phases = 4

        # Get results from both providers
        navy_result = await navy_provider.get_moon_phases(date, num_phases)
        skyfield_result = await skyfield_provider.get_moon_phases(date, num_phases)

        # Both should return same number of phases
        assert len(navy_result.phasedata) == len(skyfield_result.phasedata) == num_phases

        # Compare each phase
        print("\n=== Moon Phases Comparison ===")
        print(f"Date: {date}, Phases: {num_phases}\n")

        for i, (navy_phase, skyfield_phase) in enumerate(
            zip(navy_result.phasedata, skyfield_result.phasedata), 1
        ):
            print(f"Phase {i}:")
            print(f"  Type: {navy_phase.phase.value}")
            print(
                f"  Navy API:    {navy_phase.year}-{navy_phase.month:02d}-{navy_phase.day:02d} {navy_phase.time}"
            )
            print(
                f"  Skyfield:    {skyfield_phase.year}-{skyfield_phase.month:02d}-{skyfield_phase.day:02d} {skyfield_phase.time}"
            )

            # Phases should be the same type
            assert navy_phase.phase == skyfield_phase.phase

            # Dates should match (year, month, day)
            assert navy_phase.year == skyfield_phase.year
            assert navy_phase.month == skyfield_phase.month
            assert navy_phase.day == skyfield_phase.day

            # Times should be within a few minutes (allowing for calculation differences)
            navy_time = datetime.strptime(
                f"{navy_phase.year}-{navy_phase.month}-{navy_phase.day} {navy_phase.time}",
                "%Y-%m-%d %H:%M",
            )
            skyfield_time = datetime.strptime(
                f"{skyfield_phase.year}-{skyfield_phase.month}-{skyfield_phase.day} {skyfield_phase.time}",
                "%Y-%m-%d %H:%M",
            )

            time_diff = abs((navy_time - skyfield_time).total_seconds())
            print(f"  Time difference: {time_diff:.1f} seconds")

            # Times should be within 2 minutes (120 seconds)
            assert time_diff < 120, f"Time difference too large: {time_diff} seconds"
            print()

    @pytest.mark.asyncio
    @pytest.mark.network
    async def test_moon_phases_accuracy_2024(self, navy_provider, skyfield_provider):
        """Test accuracy for all moon phases in 2024."""
        date = "2024-1-1"
        num_phases = 48  # Full year of phases

        navy_result = await navy_provider.get_moon_phases(date, num_phases)
        skyfield_result = await skyfield_provider.get_moon_phases(date, num_phases)

        max_diff = 0
        total_diff = 0
        differences = []

        for navy_phase, skyfield_phase in zip(navy_result.phasedata, skyfield_result.phasedata):
            navy_time = datetime.strptime(
                f"{navy_phase.year}-{navy_phase.month}-{navy_phase.day} {navy_phase.time}",
                "%Y-%m-%d %H:%M",
            )
            skyfield_time = datetime.strptime(
                f"{skyfield_phase.year}-{skyfield_phase.month}-{skyfield_phase.day} {skyfield_phase.time}",
                "%Y-%m-%d %H:%M",
            )

            time_diff = abs((navy_time - skyfield_time).total_seconds())
            differences.append(time_diff)
            max_diff = max(max_diff, time_diff)
            total_diff += time_diff

        avg_diff = total_diff / len(differences)

        print("\n=== Moon Phases 2024 Accuracy Report ===")
        print(f"Total phases compared: {len(differences)}")
        print(f"Average time difference: {avg_diff:.2f} seconds ({avg_diff / 60:.2f} minutes)")
        print(f"Maximum time difference: {max_diff:.2f} seconds ({max_diff / 60:.2f} minutes)")
        print(f"Minimum time difference: {min(differences):.2f} seconds")

        # All should be within 2 minutes
        assert max_diff < 120


class TestSeasonsComparison:
    """Compare seasons calculations between providers."""

    @pytest.mark.asyncio
    @pytest.mark.network
    async def test_seasons_2024_comparison(self, navy_provider, skyfield_provider):
        """Compare seasons for 2024 from both providers."""
        year = 2024

        # Get results from both providers
        navy_result = await navy_provider.get_earth_seasons(year)
        skyfield_result = await skyfield_provider.get_earth_seasons(year)

        print("\n=== Seasons 2024 Comparison ===")
        print(f"Navy API events: {len(navy_result.data)}")
        print(f"Skyfield events: {len(skyfield_result.data)}")
        print()

        # Navy API includes perihelion/aphelion, Skyfield doesn't
        # So we filter to only equinoxes and solstices
        navy_equinox_solstice = [
            event
            for event in navy_result.data
            if "Equinox" in event.phenom or "Solstice" in event.phenom
        ]

        assert len(navy_equinox_solstice) == 4, "Should have 4 equinox/solstice events"
        assert len(skyfield_result.data) == 4, "Skyfield should have 4 equinox/solstice events"

        # Compare the 4 seasonal events
        for navy_event, skyfield_event in zip(navy_equinox_solstice, skyfield_result.data):
            print(f"Event: {navy_event.phenom}")
            print(
                f"  Navy API:    {navy_event.year}-{navy_event.month:02d}-{navy_event.day:02d} {navy_event.time}"
            )
            print(
                f"  Skyfield:    {skyfield_event.year}-{skyfield_event.month:02d}-{skyfield_event.day:02d} {skyfield_event.time}"
            )

            # Dates should match
            assert navy_event.year == skyfield_event.year
            assert navy_event.month == skyfield_event.month
            assert navy_event.day == skyfield_event.day

            # Calculate time difference
            navy_time = datetime.strptime(
                f"{navy_event.year}-{navy_event.month}-{navy_event.day} {navy_event.time}",
                "%Y-%m-%d %H:%M",
            )
            skyfield_time = datetime.strptime(
                f"{skyfield_event.year}-{skyfield_event.month}-{skyfield_event.day} {skyfield_event.time}",
                "%Y-%m-%d %H:%M",
            )

            time_diff = abs((navy_time - skyfield_time).total_seconds())
            print(f"  Time difference: {time_diff:.1f} seconds ({time_diff / 60:.2f} minutes)")

            # Times should be within 2 minutes
            assert time_diff < 120, f"Time difference too large: {time_diff} seconds"
            print()

    @pytest.mark.asyncio
    @pytest.mark.network
    async def test_seasons_accuracy_multi_year(self, navy_provider, skyfield_provider):
        """Test accuracy for seasons across multiple years."""
        years = [2020, 2021, 2022, 2023, 2024, 2025]

        all_differences = []

        for year in years:
            navy_result = await navy_provider.get_earth_seasons(year)
            skyfield_result = await skyfield_provider.get_earth_seasons(year)

            # Filter to equinox/solstice only
            navy_events = [
                e for e in navy_result.data if "Equinox" in e.phenom or "Solstice" in e.phenom
            ]

            for navy_event, skyfield_event in zip(navy_events, skyfield_result.data):
                navy_time = datetime.strptime(
                    f"{navy_event.year}-{navy_event.month}-{navy_event.day} {navy_event.time}",
                    "%Y-%m-%d %H:%M",
                )
                skyfield_time = datetime.strptime(
                    f"{skyfield_event.year}-{skyfield_event.month}-{skyfield_event.day} {skyfield_event.time}",
                    "%Y-%m-%d %H:%M",
                )

                time_diff = abs((navy_time - skyfield_time).total_seconds())
                all_differences.append(time_diff)

        print("\n=== Seasons Multi-Year Accuracy Report ===")
        print(f"Years tested: {years}")
        print(f"Total events compared: {len(all_differences)}")
        print(f"Average time difference: {sum(all_differences) / len(all_differences):.2f} seconds")
        print(f"Maximum time difference: {max(all_differences):.2f} seconds")
        print(f"Minimum time difference: {min(all_differences):.2f} seconds")

        # All should be within 2 minutes
        assert max(all_differences) < 120


class TestProviderPerformance:
    """Compare performance between providers."""

    @pytest.mark.asyncio
    @pytest.mark.network
    async def test_moon_phases_performance(self, navy_provider, skyfield_provider):
        """Compare execution time for moon phases."""
        import time

        date = "2024-1-1"
        num_phases = 12

        # Time Navy API
        start = time.time()
        await navy_provider.get_moon_phases(date, num_phases)
        navy_time = time.time() - start

        # Time Skyfield (includes initial ephemeris load)
        start = time.time()
        await skyfield_provider.get_moon_phases(date, num_phases)
        skyfield_time_first = time.time() - start

        # Time Skyfield again (ephemeris already loaded)
        start = time.time()
        await skyfield_provider.get_moon_phases(date, num_phases)
        skyfield_time_cached = time.time() - start

        print("\n=== Performance Comparison: Moon Phases ===")
        print(f"Navy API: {navy_time * 1000:.1f}ms")
        print(f"Skyfield (first call): {skyfield_time_first * 1000:.1f}ms")
        print(f"Skyfield (cached): {skyfield_time_cached * 1000:.1f}ms")
        print(f"Speedup (cached): {navy_time / skyfield_time_cached:.1f}x faster")

    @pytest.mark.asyncio
    @pytest.mark.network
    async def test_seasons_performance(self, navy_provider, skyfield_provider):
        """Compare execution time for seasons."""
        import time

        year = 2024

        # Time Navy API
        start = time.time()
        await navy_provider.get_earth_seasons(year)
        navy_time = time.time() - start

        # Time Skyfield
        start = time.time()
        await skyfield_provider.get_earth_seasons(year)
        skyfield_time = time.time() - start

        print("\n=== Performance Comparison: Seasons ===")
        print(f"Navy API: {navy_time * 1000:.1f}ms")
        print(f"Skyfield: {skyfield_time * 1000:.1f}ms")
        print(f"Speedup: {navy_time / skyfield_time:.1f}x faster")
