# chuk-mcp-celestial Roadmap

## v0.1.0 — Foundation (Complete)

Ship-ready scaffold with Navy API provider.

- [x] Project scaffold (pyproject.toml, Makefile, CI/CD, Dockerfile)
- [x] Pydantic v2 response models with enums (no dictionary goop, no magic strings)
- [x] Abstract CelestialProvider base class
- [x] Navy API provider (moon phases, sun/moon data, eclipses, seasons)
- [x] Provider factory with instance caching
- [x] 5 MCP tools (get_moon_phases, get_sun_moon_data, get_solar_eclipse_by_date, get_solar_eclipses_by_year, get_earth_seasons)
- [x] GeoJSON Feature output for location-based responses
- [x] STDIO and HTTP transport modes
- [x] Test suite with integration and unit tests
- [x] README documentation

## v0.2.0 — Skyfield & Configuration (Complete)

Offline calculations, hybrid provider mode, flexible configuration.

- [x] Skyfield provider (moon phases, Earth seasons via JPL ephemeris)
- [x] YAML configuration with environment variable overrides
- [x] Per-tool provider selection (hybrid mode)
- [x] Ephemeris storage via chuk-virtual-fs (S3, local, memory)
- [x] Ephemeris download script (`scripts/download_ephemeris.py`)
- [x] Provider comparison tests (Navy API vs Skyfield accuracy)
- [x] Virtual filesystem integration tests
- [x] Docker and Fly.io deployment
- [x] Hosted version at celestial.chukai.io/mcp
- [x] Multi-platform CI (Ubuntu, Windows, macOS; Python 3.11, 3.12, 3.13)
- [x] ARCHITECTURE, SPEC, ROADMAP documentation

## v0.3.0 — Planetary Ephemeris & Artifact Storage (Complete)

Planet positions and visibility — the biggest gap vs CelestialMCP. Skyfield
handles planetary positions natively. Artifact storage via chuk-artifacts
for computation persistence.

- [x] `get_planet_position` — altitude, azimuth, distance, phase illumination, magnitude, constellation, RA/Dec, elongation, visibility for any solar system body at a given time and location
- [x] `get_planet_events` — rise, transit, set times for a planet on a given date and location
- [x] Supported bodies: Mercury, Venus, Mars, Jupiter, Saturn, Uranus, Neptune, Pluto
- [x] Visibility status (visible, below_horizon, lost_in_sunlight)
- [x] Pydantic models for all planetary responses (PlanetPositionResponse, PlanetEventsResponse)
- [x] Skyfield provider implementation (primary — planets are a natural Skyfield strength)
- [x] Navy API NotImplementedError stubs with guidance to use Skyfield
- [x] Per-tool provider defaults (planet tools default to Skyfield)
- [x] Artifact storage via chuk-artifacts (CelestialStorage with in-memory cache + store)
- [x] Constants module (planet Skyfield name mappings, visibility thresholds, absolute magnitudes)
- [x] Tests for planetary tools, storage, factory mappings, config, base class
- [x] Updated SPEC, ARCHITECTURE, README, ROADMAP documentation

## v0.3.1 — Skyfield as Core Dependency (Complete)

Skyfield moved from optional to core dependency so all 8 tools work out of the box.

- [x] Moved `skyfield` and `numpy` from `[project.optional-dependencies]` to `dependencies`
- [x] Renamed optional `[skyfield]` extra to `[s3]` (boto3, aioboto3, python-dotenv for S3 storage)
- [x] Graceful error messages in planet tools when skyfield is somehow unavailable
- [x] Changed ephemeris storage default from `s3` to `local` (no AWS creds required)
- [x] `get_sky` — single-call all-sky summary: all planet positions, visibility, moon phase, darkness check
- [x] Tests for sky summary tool (21 tests)
- [x] Updated README, SPEC, ARCHITECTURE, ROADMAP documentation

## v0.4.0 — Conjunctions & Visibility Calendar

High-level LLM-friendly tools for planning observations.

- [ ] `get_conjunctions` — upcoming close approaches between solar system bodies (Venus-Moon, Jupiter-Saturn, etc.) within a date range
- [ ] `get_planet_visibility_calendar` — which planets are visible evening/morning over a date range for a location
- [ ] Conjunction detection algorithm (angular separation thresholds)
- [ ] Tests for conjunction and calendar tools

## v0.5.0 — Lunar Eclipses & Extended Skyfield

Lunar eclipses and full offline capability.

- [ ] `get_lunar_eclipse_by_date` — local lunar eclipse circumstances (type, timing, umbral magnitude)
- [ ] `get_lunar_eclipses_by_year` — all lunar eclipses in a year
- [ ] Skyfield sun/moon rise/set/transit calculations
- [ ] Skyfield solar eclipse predictions
- [ ] Perihelion/aphelion in Skyfield seasons
- [ ] Full offline capability (all tools via Skyfield)

## v0.6.0 — Production Hardening

Performance, reliability, and observability.

- [ ] ResilientClient with connection pooling and rate limiting
- [ ] Response caching with TTL (in-memory LRU)
- [ ] Structured error responses (ErrorResponse model)
- [ ] Health check endpoint
- [ ] Metrics and logging improvements
- [ ] 90%+ test coverage
