#!/usr/bin/env python3
"""Example: Using the Skyfield Provider

This example shows how to use the Skyfield provider for fast,
offline astronomical calculations.

Features:
- 28-33x faster than Navy API (~25ms vs ~700ms)
- Offline calculations (after ephemeris download)
- Research-grade accuracy
- Supports moon phases and seasons

Limitations:
- Solar eclipses not supported (use Navy API)
- Rise/set times not yet implemented (use Navy API)
- Requires ephemeris files (~17-32 MB)

Setup:
  python scripts/download_ephemeris.py --backend local
"""

import asyncio
from datetime import datetime

from chuk_mcp_celestial.providers import SkyfieldProvider


async def main():
    print("=" * 70)
    print("Skyfield Provider Example")
    print("=" * 70)

    # Create Skyfield provider with memory backend for demo
    # In production, use "local" or "s3"
    provider = SkyfieldProvider(
        ephemeris_file="de421.bsp",  # 17 MB, covers 1900-2050
        storage_backend="local",  # Use local filesystem
        auto_download=True,  # Download if not present
    )

    print("\n✓ Initialized Skyfield provider")
    print(f"  Ephemeris: {provider.ephemeris_file}")
    print(f"  Storage: {provider.storage_backend}")
    print(f"  Cache: {provider.cache_dir}")

    # 1. Moon Phases (FAST!)
    print("\n" + "=" * 70)
    print("1. MOON PHASES - Next 12 phases (FAST!)")
    print("=" * 70)

    start_time = datetime.now()
    phases = await provider.get_moon_phases("2024-12-1", num_phases=12)
    elapsed = (datetime.now() - start_time).total_seconds() * 1000

    print(f"\n⚡ Completed in {elapsed:.1f}ms (vs ~700ms for Navy API)")
    print(f"\nAPI Version: {phases.apiversion}")
    print(f"Starting from: {phases.year}-{phases.month:02d}-{phases.day:02d}")
    print(f"Phases returned: {phases.numphases}\n")

    for i, phase in enumerate(phases.phasedata, 1):
        phase_emoji = {
            "New Moon": "🌑",
            "First Quarter": "🌓",
            "Full Moon": "🌕",
            "Last Quarter": "🌗",
        }.get(phase.phase.value, "🌙")

        print(
            f"{i:2d}. {phase_emoji} {phase.phase.value:15s} - {phase.year}-{phase.month:02d}-{phase.day:02d} at {phase.time} UTC"
        )

    # 2. Full Year of Moon Phases
    print("\n" + "=" * 70)
    print("2. FULL YEAR OF MOON PHASES - All 48 phases in 2024")
    print("=" * 70)

    start_time = datetime.now()
    year_phases = await provider.get_moon_phases("2024-1-1", num_phases=48)
    elapsed = (datetime.now() - start_time).total_seconds() * 1000

    print(f"\n⚡ Completed in {elapsed:.1f}ms")
    print("   Navy API would take ~700ms (28x slower!)")

    # Count each phase type
    phase_counts = {}
    for phase in year_phases.phasedata:
        phase_counts[phase.phase.value] = phase_counts.get(phase.phase.value, 0) + 1

    print("\nPhase distribution in 2024:")
    for phase_name, count in sorted(phase_counts.items()):
        print(f"  {phase_name:15s}: {count}")

    # 3. Earth Seasons (FAST!)
    print("\n" + "=" * 70)
    print("3. EARTH SEASONS - Equinoxes & Solstices 2024")
    print("=" * 70)

    start_time = datetime.now()
    seasons = await provider.get_earth_seasons(2024, timezone=0, dst=False)
    elapsed = (datetime.now() - start_time).total_seconds() * 1000

    print(f"\n⚡ Completed in {elapsed:.1f}ms (vs ~800ms for Navy API)")
    print(f"\nYear: {seasons.year}")
    print(f"Timezone: UTC+{seasons.tz}")
    print(f"Events: {len(seasons.data)}\n")

    season_emoji = {
        "March Equinox": "🌸",  # Spring
        "June Solstice": "☀️",  # Summer
        "September Equinox": "🍂",  # Fall
        "December Solstice": "❄️",  # Winter
    }

    for event in seasons.data:
        date_str = f"{event.year}-{event.month:02d}-{event.day:02d} {event.time}"
        # Try to infer season name from month
        season_name = ""
        if event.month == 3:
            season_name = "March Equinox"
        elif event.month == 6:
            season_name = "June Solstice"
        elif event.month == 9:
            season_name = "September Equinox"
        elif event.month == 12:
            season_name = "December Solstice"

        emoji = season_emoji.get(season_name, "🌍")
        print(f"  {emoji} {event.phenom.value:12s} - {date_str} UTC")

    # 4. Multi-year Seasons
    print("\n" + "=" * 70)
    print("4. MULTI-YEAR SEASONS - 2020-2025")
    print("=" * 70)

    start_time = datetime.now()

    all_seasons = []
    for year in range(2020, 2026):
        year_seasons = await provider.get_earth_seasons(year)
        all_seasons.append((year, year_seasons))

    elapsed = (datetime.now() - start_time).total_seconds() * 1000

    print(f"\n⚡ Completed 6 years in {elapsed:.1f}ms ({elapsed / 6:.1f}ms per year)")
    print("   Navy API would take ~4800ms total (33x slower!)")
    print(f"\nTotal events: {sum(len(s.data) for _, s in all_seasons)}")

    # 5. Limitations Demo
    print("\n" + "=" * 70)
    print("5. LIMITATIONS - Features Not Supported")
    print("=" * 70)

    print("\n⚠️  The following features are NOT supported by Skyfield provider:")
    print("    Use Navy API provider for these features.\n")

    # Try solar eclipse (will raise NotImplementedError)
    try:
        await provider.get_solar_eclipse_by_date(date="2024-4-8", latitude=40.71, longitude=-74.01)
    except NotImplementedError as e:
        print(f"  ❌ Solar eclipses: {e}")

    # Try rise/set times (will raise NotImplementedError)
    try:
        await provider.get_sun_moon_data(date="2024-12-21", latitude=47.60, longitude=-122.33)
    except NotImplementedError as e:
        print(f"  ❌ Sun/Moon rise/set: {e}")

    print("\n" + "=" * 70)
    print("✅ Skyfield Provider Demo Complete!")
    print("=" * 70)
    print("\nAdvantages:")
    print("  ✓ 28-33x faster than Navy API")
    print("  ✓ Offline calculations (after download)")
    print("  ✓ Research-grade accuracy")
    print("  ✓ No rate limits")
    print("  ✓ Excellent for moon phases and seasons")
    print("\nLimitations:")
    print("  - Solar eclipses not supported")
    print("  - Rise/set times not yet implemented")
    print("  - Requires ephemeris files (~17-32 MB)")
    print("\n💡 Tip: Use hybrid mode to get the best of both providers!")


if __name__ == "__main__":
    asyncio.run(main())
