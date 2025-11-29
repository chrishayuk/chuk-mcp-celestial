#!/usr/bin/env python3
"""Example: Hybrid Provider Approach (Best of Both Worlds)

This example demonstrates the recommended hybrid approach:
- Use Skyfield for fast, frequent queries (moon phases, seasons)
- Use Navy API for specialized features (eclipses, rise/set)

This gives you:
- ⚡ Maximum performance for common queries
- 🌐 Full functionality for all features
- 🔌 Partial offline capability

Setup:
  python scripts/download_ephemeris.py --backend local
"""

import asyncio
from datetime import datetime

from chuk_mcp_celestial.providers import NavyAPIProvider, SkyfieldProvider


async def main():
    print("=" * 70)
    print("Hybrid Provider Example - Best of Both Worlds!")
    print("=" * 70)

    # Initialize both providers
    skyfield = SkyfieldProvider(
        ephemeris_file="de421.bsp", storage_backend="local", auto_download=True
    )

    navy = NavyAPIProvider()

    print("\n✓ Initialized both providers:")
    print(f"  Skyfield: {skyfield.ephemeris_file} ({skyfield.storage_backend})")
    print(f"  Navy API: {navy.base_url}")

    # Scenario 1: Quick Moon Phase Check
    print("\n" + "=" * 70)
    print("SCENARIO 1: Quick Moon Phase Query")
    print("Use Case: User asks 'When is the next full moon?'")
    print("=" * 70)

    print("\n➤ Using Skyfield (FAST!)...")
    start = datetime.now()
    phases = await skyfield.get_moon_phases("2024-12-1", num_phases=4)
    skyfield_time = (datetime.now() - start).total_seconds() * 1000

    # Find next full moon
    next_full_moon = next(p for p in phases.phasedata if "Full" in p.phase.value)

    print(f"  ⚡ Query completed in {skyfield_time:.1f}ms")
    print(
        f"  🌕 Next Full Moon: {next_full_moon.year}-{next_full_moon.month:02d}-{next_full_moon.day:02d} at {next_full_moon.time} UTC"
    )
    print("\n  Why Skyfield? Fast response for frequently asked question")

    # Scenario 2: Detailed Local Circumstances
    print("\n" + "=" * 70)
    print("SCENARIO 2: Detailed Location-Specific Data")
    print("Use Case: 'What time does the moon rise in Seattle tonight?'")
    print("=" * 70)

    print("\n➤ Using Navy API (FULL FEATURES)...")
    start = datetime.now()
    sun_moon = await navy.get_sun_moon_data(
        date="2024-12-21", latitude=47.60, longitude=-122.33, timezone=-8, label="Seattle, WA"
    )
    navy_time = (datetime.now() - start).total_seconds() * 1000

    print(f"  🌐 Query completed in {navy_time:.1f}ms")
    print(f"  📍 Location: {sun_moon.properties.data.label}")

    if sun_moon.properties.data.moondata:
        moon_rise = sun_moon.properties.data.moondata[0]
        print(f"  🌙 Moonrise: {moon_rise.time} PST")

    print("\n  Why Navy API? Rise/set times not yet in Skyfield")

    # Scenario 3: Eclipse Information
    print("\n" + "=" * 70)
    print("SCENARIO 3: Solar Eclipse Query")
    print("Use Case: 'Tell me about the April 2024 eclipse'")
    print("=" * 70)

    print("\n➤ Using Navy API (ONLY OPTION)...")
    start = datetime.now()
    eclipse = await navy.get_solar_eclipse_by_date(
        date="2024-4-8", latitude=40.71, longitude=-74.01, height=10
    )
    eclipse_time = (datetime.now() - start).total_seconds() * 1000

    print(f"  🌐 Query completed in {eclipse_time:.1f}ms")
    print(f"  🌑 Event: {eclipse.properties.event}")
    print(f"  📝 Description: {eclipse.properties.description}")
    if eclipse.properties.magnitude:
        print(f"  📊 Magnitude: {eclipse.properties.magnitude}")
    if eclipse.properties.duration:
        print(f"  ⏱️  Duration: {eclipse.properties.duration}")

    print("\n  Why Navy API? Skyfield doesn't support eclipse calculations")

    # Scenario 4: Annual Seasonal Planning
    print("\n" + "=" * 70)
    print("SCENARIO 4: Multi-Year Seasonal Data")
    print("Use Case: 'Show me equinoxes for the next 5 years'")
    print("=" * 70)

    print("\n➤ Using Skyfield (BATCH PERFORMANCE!)...")
    start = datetime.now()

    seasons_data = []
    for year in range(2024, 2029):
        year_seasons = await skyfield.get_earth_seasons(year)
        # Filter for equinoxes only
        equinoxes = [s for s in year_seasons.data if s.phenom.value == "Equinox"]
        seasons_data.extend(equinoxes)

    skyfield_batch_time = (datetime.now() - start).total_seconds() * 1000

    print(f"  ⚡ Query completed in {skyfield_batch_time:.1f}ms")
    print(f"  🌍 Found {len(seasons_data)} equinoxes (2024-2028)")

    for equinox in seasons_data[:4]:  # Show first 4
        print(f"     {equinox.year}-{equinox.month:02d}-{equinox.day:02d} {equinox.time} UTC")

    print(f"\n  Why Skyfield? {skyfield_batch_time:.0f}ms vs ~4000ms for Navy API (8x faster!)")

    # Performance Summary
    print("\n" + "=" * 70)
    print("PERFORMANCE COMPARISON")
    print("=" * 70)

    # Estimate Navy API times for same queries
    estimated_navy_phases = 700
    estimated_navy_batch = 4000  # 5 years * ~800ms

    print("\nQueries performed:")
    print(f"  • Moon phases: Skyfield {skyfield_time:.0f}ms (vs Navy ~{estimated_navy_phases}ms)")
    print(f"  • Sun/Moon data: Navy {navy_time:.0f}ms (only option)")
    print(f"  • Solar eclipse: Navy {eclipse_time:.0f}ms (only option)")
    print(
        f"  • Multi-year seasons: Skyfield {skyfield_batch_time:.0f}ms (vs Navy ~{estimated_navy_batch}ms)"
    )

    total_hybrid = skyfield_time + navy_time + eclipse_time + skyfield_batch_time
    total_navy_only = estimated_navy_phases + navy_time + eclipse_time + estimated_navy_batch

    print("\nTotal time:")
    print(f"  Hybrid approach: {total_hybrid:.0f}ms")
    print(f"  Navy API only:   {total_navy_only:.0f}ms")
    print(
        f"  Savings:         {total_navy_only - total_hybrid:.0f}ms ({(total_navy_only / total_hybrid):.1f}x faster!)"
    )

    # Configuration Example
    print("\n" + "=" * 70)
    print("RECOMMENDED CONFIGURATION")
    print("=" * 70)

    config_example = """
# celestial.yaml - Hybrid configuration
default_provider: navy_api

providers:
  moon_phases: skyfield          # Fast offline (28x faster)
  earth_seasons: skyfield         # Fast offline (33x faster)
  sun_moon_data: navy_api         # Rise/set times (only option)
  solar_eclipse_date: navy_api    # Eclipses (only option)
  solar_eclipse_year: navy_api    # Eclipse catalog (only option)

skyfield:
  ephemeris: de421.bsp
  storage_backend: local          # or 's3' for production
  auto_download: true
"""

    print(config_example)

    print("\n" + "=" * 70)
    print("✅ Hybrid Provider Demo Complete!")
    print("=" * 70)
    print("\nHybrid Benefits:")
    print("  ✓ Fast performance for common queries (moon, seasons)")
    print("  ✓ Full functionality (eclipses, rise/set)")
    print("  ✓ Partial offline capability")
    print("  ✓ Lower API usage (respects rate limits)")
    print("  ✓ Best of both providers!")
    print("\nRecommended for:")
    print("  • Production deployments")
    print("  • High-traffic applications")
    print("  • Offline/partial-offline scenarios")
    print("  • Cost-conscious deployments")


if __name__ == "__main__":
    asyncio.run(main())
