# chuk-mcp-celestial Specification

Version 0.3.1

## Overview

chuk-mcp-celestial is an MCP (Model Context Protocol) server that provides
comprehensive astronomical and celestial data from the US Navy Astronomical
Applications Department API and local Skyfield calculations.

- **8 tools** for moon phases, sun/moon data, solar eclipses, Earth seasons, planetary positions/events, and all-sky summaries
- **Multi-provider** — Navy API (authoritative) and Skyfield (fast, offline)
- **Hybrid mode** — per-tool provider selection for optimal speed/coverage
- **Async-first** — all tool entry points are async with httpx
- **Type-safe** — Pydantic v2 models with enums for all responses
- **GeoJSON output** — location-based responses follow GeoJSON Feature spec
- **Artifact storage** — computation results stored via chuk-artifacts (S3, filesystem, memory)

## Supported Providers

| Name | URL | Speed | Offline | Auth | Notes |
|------|-----|-------|---------|------|-------|
| `navy_api` (default) | `https://aa.usno.navy.mil/api` | ~700ms | No | None | Free. Official US government source. 5 tools (no planets). |
| `skyfield` | N/A (local) | ~25ms | Yes | None | JPL ephemeris. Moon phases, seasons, and all planetary tools. |

The `default_provider` setting or per-tool overrides in `celestial.yaml`
control which provider handles each request. When omitted, the server uses
`navy_api`. Planet tools default to `skyfield`.

---

## Enums

All constant values use enums to prevent magic strings.

### MoonPhase

| Value | Description |
|-------|-------------|
| `New Moon` | Moon between Earth and Sun, not visible |
| `First Quarter` | Right half illuminated (Northern Hemisphere) |
| `Full Moon` | Fully illuminated |
| `Last Quarter` | Left half illuminated (Northern Hemisphere) |

### MoonCurPhase

| Value | Description |
|-------|-------------|
| `New Moon` | 0% illuminated |
| `Waxing Crescent` | 1-49% illuminated, growing |
| `First Quarter` | 50% illuminated, growing |
| `Waxing Gibbous` | 51-99% illuminated, growing |
| `Full Moon` | 100% illuminated |
| `Waning Gibbous` | 99-51% illuminated, shrinking |
| `Last Quarter` | 50% illuminated, shrinking |
| `Waning Crescent` | 49-1% illuminated, shrinking |

### CelestialPhenomenon

| Value | Description |
|-------|-------------|
| `Rise` | Object rises above horizon |
| `Set` | Object sets below horizon |
| `Upper Transit` | Object crosses meridian (highest point) |
| `Begin Civil Twilight` | Sun is 6 degrees below horizon (dawn) |
| `End Civil Twilight` | Sun is 6 degrees below horizon (dusk) |

### EclipsePhenomenon

| Value | Description |
|-------|-------------|
| `Eclipse Begins` | First contact — moon starts covering sun |
| `Maximum Eclipse` | Greatest obscuration at this location |
| `Eclipse Ends` | Last contact — moon fully uncovers sun |

### SeasonPhenomenon

| Value | Description |
|-------|-------------|
| `Equinox` | Day and night approximately equal (March, September) |
| `Solstice` | Longest or shortest day (June, December) |
| `Perihelion` | Earth closest to Sun (~Jan 3) |
| `Aphelion` | Earth farthest from Sun (~Jul 4) |

### Planet

| Value | Description |
|-------|-------------|
| `Mercury` | Closest planet to Sun, hard to observe |
| `Venus` | Brightest planet, visible near sunrise/sunset |
| `Mars` | The Red Planet |
| `Jupiter` | Largest planet, easily visible |
| `Saturn` | Ringed planet, easily visible |
| `Uranus` | Dim, requires binoculars |
| `Neptune` | Very dim, requires telescope |
| `Pluto` | Dwarf planet, extremely dim |

### VisibilityStatus

| Value | Description |
|-------|-------------|
| `visible` | Planet is above the horizon and far enough from the Sun to be seen |
| `below_horizon` | Planet is below the horizon (altitude < 0) |
| `lost_in_sunlight` | Planet is above the horizon but too close to the Sun |

---

## Tools

### `get_moon_phases`

Get upcoming moon phases starting from a given date.

**Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `date` | `str` | *required* | Start date `YYYY-MM-DD` (range: 1700–2100) |
| `num_phases` | `int` | `12` | Number of phases to return (1–99) |

**Response:** `MoonPhasesResponse`

| Field | Type | Description |
|-------|------|-------------|
| `apiversion` | `str` | API version string |
| `year` | `int` | Query year |
| `month` | `int` | Query month |
| `day` | `int` | Query day |
| `numphases` | `int` | Number of phases returned |
| `phasedata` | `MoonPhaseData[]` | Phase, year, month, day, time (UT1) |

**Notes:**
- All times are in Universal Time (UT1), not local time
- A complete lunar cycle is ~29.5 days (4 phases)
- `num_phases=4` for next month, `12` for next quarter, `48` for next year
- Supported by both Navy API and Skyfield providers

---

### `get_sun_moon_data`

Get complete sun and moon data for one day at a specific location.

**Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `date` | `str` | *required* | Date `YYYY-MM-DD` |
| `latitude` | `float` | *required* | Latitude (-90 to 90) |
| `longitude` | `float` | *required* | Longitude (-180 to 180) |
| `timezone` | `float?` | `None` | Timezone offset from UTC in hours |
| `dst` | `bool?` | `None` | Apply daylight saving time |
| `label` | `str?` | `None` | User label (max 20 chars) |

**Response:** `OneDayResponse` (GeoJSON Feature)

| Field | Type | Description |
|-------|------|-------------|
| `apiversion` | `str` | API version |
| `type` | `str` | `Feature` (GeoJSON) |
| `geometry` | `GeoJSONPoint` | Location as `[lon, lat]` |
| `properties.data.sundata` | `CelestialEventData[]` | Sun rise/set/transit/twilight events |
| `properties.data.moondata` | `CelestialEventData[]` | Moon rise/set/transit events |
| `properties.data.curphase` | `MoonCurPhase` | Current moon phase |
| `properties.data.fracillum` | `str` | Moon illumination percentage |
| `properties.data.closestphase` | `ClosestPhaseData` | Nearest moon phase |
| `properties.data.day_of_week` | `DayOfWeek` | Day of week |

**Notes:**
- Times are in the requested timezone (or UTC if not specified)
- `sundata` and `moondata` may be empty in polar regions during extreme seasons
- Navy API only — Skyfield provider raises `NotImplementedError`

---

### `get_solar_eclipse_by_date`

Get local solar eclipse circumstances for a specific date and location.

**Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `date` | `str` | *required* | Eclipse date `YYYY-MM-DD` (range: 1800–2050) |
| `latitude` | `float` | *required* | Observer latitude (-90 to 90) |
| `longitude` | `float` | *required* | Observer longitude (-180 to 180) |
| `height` | `int` | `0` | Height above sea level in metres (-200 to 10000) |

**Response:** `SolarEclipseByDateResponse` (GeoJSON Feature)

| Field | Type | Description |
|-------|------|-------------|
| `apiversion` | `str` | API version |
| `type` | `str` | `Feature` (GeoJSON) |
| `geometry` | `GeoJSONPoint` | Observer location |
| `properties.event` | `str` | Full eclipse description |
| `properties.description` | `str` | Eclipse type at this location |
| `properties.magnitude` | `str?` | Fraction of sun's diameter covered |
| `properties.obscuration` | `str?` | Percentage of sun's area covered |
| `properties.duration` | `str?` | Eclipse duration at this location |
| `properties.delta_t` | `str` | Delta T (TT − UT1) used |
| `properties.local_data` | `EclipseLocalData[]` | Per-phase timing with sun altitude/azimuth |

**Notes:**
- `magnitude >= 1.0` indicates total eclipse; `< 1.0` is partial
- `obscuration` shows percentage of sun's *area* covered (differs from magnitude)
- `local_data` is chronological: begins, maximum, ends
- Altitude must be > 0 for eclipse to be visible (sun above horizon)
- Navy API only — Skyfield provider raises `NotImplementedError`

---

### `get_solar_eclipses_by_year`

Get a list of all solar eclipses occurring in a specific year.

**Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `year` | `int` | *required* | Year to query (1800–2050) |

**Response:** `SolarEclipseByYearResponse`

| Field | Type | Description |
|-------|------|-------------|
| `apiversion` | `str` | API version |
| `year` | `int` | Query year |
| `eclipses_in_year` | `SolarEclipseEvent[]` | Year, month, day, event description |

**Notes:**
- Most years have 2 solar eclipses; some have 3, rarely 4
- Event description includes type: Total, Annular, Partial, Hybrid
- Use `get_solar_eclipse_by_date` to check visibility from a specific location
- Navy API only — Skyfield provider raises `NotImplementedError`

---

### `get_earth_seasons`

Get Earth's seasons and orbital events for a year.

**Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `year` | `int` | *required* | Year to query (1700–2100) |
| `timezone` | `float?` | `None` | Timezone offset from UTC in hours |
| `dst` | `bool?` | `None` | Apply daylight saving time |

**Response:** `SeasonsResponse`

| Field | Type | Description |
|-------|------|-------------|
| `apiversion` | `str` | API version |
| `year` | `int` | Query year |
| `tz` | `float` | Timezone offset used |
| `dst` | `bool` | Whether DST was applied |
| `data` | `SeasonEvent[]` | Seasonal events with phenom, date, time |

**Typical events per year (Navy API — 6 events):**

| Event | Approximate Date | Description |
|-------|-----------------|-------------|
| Perihelion | ~Jan 3 | Earth closest to Sun (~147M km) |
| March Equinox | ~Mar 20 | Equal day/night, spring in Northern Hemisphere |
| June Solstice | ~Jun 21 | Longest day in Northern Hemisphere |
| Aphelion | ~Jul 4 | Earth farthest from Sun (~152M km) |
| September Equinox | ~Sep 22 | Equal day/night, autumn in Northern Hemisphere |
| December Solstice | ~Dec 21 | Shortest day in Northern Hemisphere |

**Notes:**
- Skyfield returns 4 events (equinoxes and solstices only, no perihelion/aphelion)
- Seasons are opposite in Northern and Southern hemispheres
- Earth's 23.5 degree axial tilt causes seasons, not distance from Sun

---

### `get_planet_position`

Get position and observational data for a planet at a specific time and location.

**Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `planet` | `str` | *required* | Planet name: Mercury, Venus, Mars, Jupiter, Saturn, Uranus, Neptune, Pluto |
| `date` | `str` | *required* | Date `YYYY-MM-DD` |
| `time` | `str` | *required* | Time `HH:MM` (24-hour). UTC unless timezone specified. |
| `latitude` | `float` | *required* | Observer latitude (-90 to 90) |
| `longitude` | `float` | *required* | Observer longitude (-180 to 180) |
| `timezone` | `float?` | `None` | Timezone offset from UTC in hours. When provided, time is local. |

**Response:** `PlanetPositionResponse` (GeoJSON Feature)

| Field | Type | Description |
|-------|------|-------------|
| `apiversion` | `str` | API version |
| `type` | `str` | `Feature` (GeoJSON) |
| `geometry` | `GeoJSONPoint` | Observer location as `[lon, lat]` |
| `properties.data.planet` | `Planet` | Planet name |
| `properties.data.altitude` | `float` | Degrees above horizon (-90 to 90) |
| `properties.data.azimuth` | `float` | Degrees clockwise from north (0-360) |
| `properties.data.distance_au` | `float` | Distance from observer in AU |
| `properties.data.distance_km` | `float` | Distance from observer in km |
| `properties.data.illumination` | `float` | Phase illumination percentage (0-100) |
| `properties.data.magnitude` | `float` | Apparent visual magnitude |
| `properties.data.constellation` | `str` | IAU constellation abbreviation |
| `properties.data.right_ascension` | `str` | RA in `HH:MM:SS.s` (J2000) |
| `properties.data.declination` | `str` | Dec in `+DD:MM:SS.s` (J2000) |
| `properties.data.elongation` | `float` | Angular distance from Sun (0-180 degrees) |
| `properties.data.visibility` | `VisibilityStatus` | visible, below_horizon, or lost_in_sunlight |
| `artifact_ref` | `str?` | Artifact reference for stored result |

**Notes:**
- Lower magnitude = brighter (Venus reaches -4.4, Jupiter -2.7)
- Elongation < 10-15 degrees means the planet is lost in the Sun's glare
- Altitude > 0 means the planet is above the horizon
- Skyfield only — Navy API provider raises `NotImplementedError`
- Computation results stored via chuk-artifacts when configured

---

### `get_planet_events`

Get rise, set, and transit times for a planet on a given day at a location.

**Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `planet` | `str` | *required* | Planet name: Mercury, Venus, Mars, Jupiter, Saturn, Uranus, Neptune, Pluto |
| `date` | `str` | *required* | Date `YYYY-MM-DD` |
| `latitude` | `float` | *required* | Observer latitude (-90 to 90) |
| `longitude` | `float` | *required* | Observer longitude (-180 to 180) |
| `timezone` | `float?` | `None` | Timezone offset from UTC in hours |
| `dst` | `bool?` | `None` | Apply daylight saving time |

**Response:** `PlanetEventsResponse` (GeoJSON Feature)

| Field | Type | Description |
|-------|------|-------------|
| `apiversion` | `str` | API version |
| `type` | `str` | `Feature` (GeoJSON) |
| `geometry` | `GeoJSONPoint` | Observer location |
| `properties.data.planet` | `Planet` | Planet name |
| `properties.data.date` | `str` | Query date |
| `properties.data.events` | `PlanetEventData[]` | Rise/Set/Upper Transit events with times |
| `properties.data.constellation` | `str` | Constellation at noon |
| `properties.data.magnitude` | `float` | Approximate apparent magnitude at noon |
| `artifact_ref` | `str?` | Artifact reference for stored result |

**Notes:**
- Events may be empty if the planet doesn't rise/set that day (polar regions)
- Transit time is when the planet is highest — best viewing time
- Skyfield only — Navy API provider raises `NotImplementedError`
- Computation results stored via chuk-artifacts when configured

---

### `get_sky`

Get a complete sky summary — all planets, moon phase, and darkness — in one call.

**Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `date` | `str` | *required* | Date `YYYY-MM-DD` |
| `time` | `str` | *required* | Time `HH:MM` (24-hour). UTC unless timezone specified. |
| `latitude` | `float` | *required* | Observer latitude (-90 to 90) |
| `longitude` | `float` | *required* | Observer longitude (-180 to 180) |
| `timezone` | `float?` | `None` | Timezone offset from UTC in hours |

**Response:** `SkyResponse` (GeoJSON Feature)

| Field | Type | Description |
|-------|------|-------------|
| `apiversion` | `str` | API version |
| `type` | `str` | `Feature` (GeoJSON) |
| `geometry` | `GeoJSONPoint` | Observer location |
| `properties.data.date` | `str` | Query date |
| `properties.data.time` | `str` | Query time |
| `properties.data.is_dark` | `bool` | True if sun is below -6° (civil twilight) |
| `properties.data.visible_planets` | `SkyPlanetSummary[]` | Planets above horizon, not lost in sunlight, sorted brightest first |
| `properties.data.all_planets` | `SkyPlanetSummary[]` | All 8 planets regardless of visibility |
| `properties.data.moon` | `SkyMoonSummary` | Phase, illumination, next phase date |
| `properties.data.summary` | `str` | One-line human-readable summary |
| `artifact_ref` | `str?` | Artifact reference for stored result |

**SkyPlanetSummary fields:** planet, altitude, azimuth, magnitude, constellation, elongation, visibility, direction (compass: N/NE/E/SE/S/SW/W/NW)

**Notes:**
- Recommended for "what's in the sky tonight?" — one call instead of 8 `get_planet_position` calls
- `visible_planets` filtered to `altitude > 0` and `visibility == "visible"`
- `direction` gives human-readable compass bearing
- `is_dark=False` means daylight/twilight — planets may not be observable
- Skyfield only — composes `get_planet_position()` for all planets + `get_moon_phases()`

---

## Error Handling

All tools raise exceptions on failure with descriptive messages:

| Scenario | Error |
|----------|-------|
| Invalid date format | `ValueError: Invalid date format` |
| Date out of range | API returns error; Pydantic validation fails |
| Provider unavailable | `httpx.HTTPStatusError` or `ConnectionError` |
| Skyfield not installed | `RuntimeError` with install instructions |
| Unsupported tool on Skyfield | `NotImplementedError` with feature description |
| Invalid coordinates | `ValueError` from parameter validation |

---

## Configuration

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `CELESTIAL_PROVIDER` | No | `navy_api` | Default provider for all tools |
| `CELESTIAL_MOON_PHASES_PROVIDER` | No | default | Provider for moon phases |
| `CELESTIAL_SUN_MOON_DATA_PROVIDER` | No | default | Provider for sun/moon data |
| `CELESTIAL_SOLAR_ECLIPSE_DATE_PROVIDER` | No | default | Provider for eclipse by date |
| `CELESTIAL_SOLAR_ECLIPSE_YEAR_PROVIDER` | No | default | Provider for eclipses by year |
| `CELESTIAL_EARTH_SEASONS_PROVIDER` | No | default | Provider for Earth seasons |
| `CELESTIAL_PLANET_POSITION_PROVIDER` | No | `skyfield` | Provider for planet position |
| `CELESTIAL_PLANET_EVENTS_PROVIDER` | No | `skyfield` | Provider for planet events |
| `CELESTIAL_SKY_PROVIDER` | No | `skyfield` | Provider for sky summary |
| `CELESTIAL_CONFIG_PATH` | No | — | Path to celestial.yaml |
| `CHUK_ARTIFACTS_PROVIDER` | No | `memory` | Artifact storage: `memory`, `s3`, `filesystem` |
| `BUCKET_NAME` | No | — | S3 bucket for artifact storage |
| `CHUK_ARTIFACTS_PATH` | No | — | Filesystem path for artifact storage |
| `REDIS_URL` | No | — | Redis URL for artifact sessions |
| `SKYFIELD_EPHEMERIS` | No | `de440s.bsp` | Ephemeris file |
| `SKYFIELD_STORAGE_BACKEND` | No | `s3` | Storage: `local`, `s3`, `memory` |
| `SKYFIELD_DATA_DIR` | No | `~/.skyfield` | Local ephemeris directory |
| `SKYFIELD_AUTO_DOWNLOAD` | No | `true` | Auto-download ephemeris |
| `SKYFIELD_S3_BUCKET` | No | `chuk-celestial-ephemeris` | S3 bucket |
| `SKYFIELD_S3_REGION` | No | `us-east-1` | S3 region |
| `SKYFIELD_S3_PREFIX` | No | `ephemeris/` | S3 key prefix |
| `SKYFIELD_S3_PROFILE` | No | — | AWS profile |
| `NAVY_API_BASE_URL` | No | `https://aa.usno.navy.mil/api` | Navy API base URL |
| `NAVY_API_TIMEOUT` | No | `30.0` | Request timeout (seconds) |
| `NAVY_API_MAX_RETRIES` | No | `3` | Max retry attempts |
| `NAVY_API_RETRY_DELAY` | No | `1.0` | Delay between retries (seconds) |

### YAML Configuration (celestial.yaml)

```yaml
default_provider: navy_api

providers:
  moon_phases: skyfield
  sun_moon_data: navy_api
  solar_eclipse_date: navy_api
  solar_eclipse_year: navy_api
  earth_seasons: skyfield
  planet_position: skyfield
  planet_events: skyfield
  sky: skyfield

skyfield:
  ephemeris: de440s.bsp
  storage_backend: s3
  auto_download: true
  data_dir: ~/.skyfield
  s3:
    bucket: chuk-celestial-ephemeris
    region: us-east-1
    prefix: ephemeris/

navy_api:
  base_url: https://aa.usno.navy.mil/api
  timeout: 30.0
  max_retries: 3
  retry_delay: 1.0
```

**Config file locations** (checked in order):
1. `$CELESTIAL_CONFIG_PATH`
2. `./celestial.yaml`
3. `~/.config/chuk-mcp-celestial/celestial.yaml`

---

## Ephemeris Files

Skyfield provider requires JPL Development Ephemeris files for local
astronomical calculations.

| File | Size | Coverage | Notes |
|------|------|----------|-------|
| `de440s.bsp` | 32 MB | 1849–2150 | Recommended. Default. |
| `de421.bsp` | 17 MB | 1900–2050 | Smaller, older |
| `de440.bsp` | 114 MB | 1550–2650 | Most comprehensive |

Storage backends via chuk-virtual-fs:

| Backend | Use Case | Persistent | Shared |
|---------|----------|------------|--------|
| S3 | Production | Yes | Yes |
| Local | Development | Yes | No |
| Memory | Testing | No | No |

---

## Cross-Server Workflows

chuk-mcp-celestial integrates with the broader MCP ecosystem:

### Celestial + Time: Timezone-Aware Astronomy

1. `get_sun_moon_data` → sunrise/sunset in UTC
2. `get_time_for_timezone` → current local time
3. Combine: "Sunrise is at 07:41 GMT, that's 6h 12m from now"

### Celestial + Weather: Observation Planning

1. `get_moon_phases` → find next full moon date
2. `get_weather_forecast` → check cloud cover for that date
3. Combine: "Full moon on [date], forecast: partly cloudy, 60% viewing chance"

### Celestial + Weather: Eclipse Viewing

1. `get_solar_eclipses_by_year` → find eclipse dates
2. `get_solar_eclipse_by_date` → check visibility from location
3. `get_weather_forecast` → weather for eclipse date
4. Combine: eclipse timing + local visibility + weather forecast

### Celestial + Tides: Coastal Photography

1. `get_sun_moon_data` → golden hour (sunrise/sunset timing)
2. `tides_predict` → tide level at golden hour
3. Combine: "Best photography window: sunset at 18:42, low tide at 18:15"

---

## Performance

### Navy API

- ~700ms per request (network-bound)
- No rate limit published (be reasonable)
- Retry with exponential backoff (configurable)

### Skyfield

- ~25ms per computation (28x faster than Navy API)
- One-time ephemeris download (~32 MB)
- No network required after download
- Local temp cache persists across provider instances

---

## Roadmap

See [ROADMAP.md](ROADMAP.md) for version history and planned features.
