#!/usr/bin/env python3
"""Example: Using the Navy API Provider

This example shows how to use the Navy API provider directly for
authoritative US Navy astronomical data.

Features:
- All tools supported (moon phases, eclipses, rise/set, seasons)
- Authoritative US Navy data
- Network required (~700-800ms per request)
- No local setup needed
"""

import asyncio

from chuk_mcp_celestial.providers import NavyAPIProvider


async def main():
    print("=" * 70)
    print("Navy API Provider Example")
    print("=" * 70)

    # Create Navy API provider
    provider = NavyAPIProvider()
    print("\n✓ Initialized Navy API provider")
    print(f"  API: {provider.base_url}")
    print(f"  Timeout: {provider.timeout}s")

    # 1. Moon Phases
    print("\n" + "=" * 70)
    print("1. MOON PHASES - Next 4 phases")
    print("=" * 70)

    phases = await provider.get_moon_phases("2024-12-1", num_phases=4)
    print(f"\nAPI Version: {phases.apiversion}")
    print(f"Starting from: {phases.year}-{phases.month:02d}-{phases.day:02d}")
    print(f"Phases returned: {phases.numphases}\n")

    for i, phase in enumerate(phases.phasedata, 1):
        print(
            f"{i}. {phase.phase.value:15s} - {phase.year}-{phase.month:02d}-{phase.day:02d} at {phase.time} UTC"
        )

    # 2. Sun and Moon Data for a Location
    print("\n" + "=" * 70)
    print("2. SUN & MOON DATA - Seattle, WA")
    print("=" * 70)

    data = await provider.get_sun_moon_data(
        date="2024-12-21",  # Winter solstice
        latitude=47.60,
        longitude=-122.33,
        timezone=-8,
        label="Seattle, WA",
    )

    print(f"\nLocation: {data.properties.data.label}")
    print(
        f"Date: {data.properties.data.year}-{data.properties.data.month:02d}-{data.properties.data.day:02d}"
    )
    print(f"Day of week: {data.properties.data.day_of_week.value}")
    print(f"Coordinates: {data.geometry.coordinates}")

    # Sun data
    if data.properties.data.sundata:
        sun = data.properties.data.sundata[0]
        print("\n☀️  SUN:")
        print(f"  Rise: {sun.time}")
        print(f"  Phenomenon: {sun.phen}")

    # Moon data
    if data.properties.data.moondata:
        moon = data.properties.data.moondata[0]
        print("\n🌙 MOON:")
        print(f"  Rise: {moon.time}")
        print(f"  Phase: {data.properties.data.curphase}")
        print(f"  Illumination: {data.properties.data.fracillum}")

    # 3. Solar Eclipse Information
    print("\n" + "=" * 70)
    print("3. SOLAR ECLIPSE - April 8, 2024 (Total Eclipse)")
    print("=" * 70)

    eclipse = await provider.get_solar_eclipse_by_date(
        date="2024-4-8",
        latitude=40.71,  # New York City
        longitude=-74.01,
        height=10,
    )

    print(f"\nEvent: {eclipse.properties.event}")
    print(f"Description: {eclipse.properties.description}")
    if eclipse.properties.magnitude:
        print(f"Magnitude: {eclipse.properties.magnitude}")
    if eclipse.properties.obscuration:
        print(f"Obscuration: {eclipse.properties.obscuration}")
    if eclipse.properties.duration:
        print(f"Duration: {eclipse.properties.duration}")

    # 4. Solar Eclipses in a Year
    print("\n" + "=" * 70)
    print("4. SOLAR ECLIPSES - Year 2024")
    print("=" * 70)

    year_eclipses = await provider.get_solar_eclipses_by_year(2024)
    print(f"\nTotal eclipses in 2024: {len(year_eclipses.eclipses_in_year)}\n")

    for i, ecl in enumerate(year_eclipses.eclipses_in_year, 1):
        date_str = f"{ecl.year}-{ecl.month:02d}-{ecl.day:02d}"
        print(f"{i}. {date_str} - {ecl.event}")

    # 5. Earth Seasons
    print("\n" + "=" * 70)
    print("5. EARTH SEASONS - Year 2024")
    print("=" * 70)

    seasons = await provider.get_earth_seasons(2024, timezone=0, dst=False)
    print(f"\nYear: {seasons.year}")
    print(f"Timezone: UTC+{seasons.tz}")
    print(f"Events: {len(seasons.data)}\n")

    for event in seasons.data:
        date_str = f"{event.year}-{event.month:02d}-{event.day:02d} {event.time}"
        print(f"  {event.phenom.value:12s} - {date_str} UTC")

    print("\n" + "=" * 70)
    print("✅ Navy API Provider Demo Complete!")
    print("=" * 70)
    print("\nAdvantages:")
    print("  ✓ Authoritative US Navy data")
    print("  ✓ All features supported (eclipses, rise/set, etc.)")
    print("  ✓ No local setup required")
    print("  ✓ Always up to date")
    print("\nConsiderations:")
    print("  - Requires internet connection")
    print("  - ~700-800ms per request")
    print("  - Rate limits may apply")


if __name__ == "__main__":
    asyncio.run(main())
