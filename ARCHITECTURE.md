# chuk-mcp-celestial Architecture

## Design Principles

1. **Async-first** — All tool entry points are async; sync I/O (HTTP calls, ephemeris computation) runs via `asyncio.to_thread()`
2. **Single responsibility** — Tools validate inputs, providers handle API specifics, factory dispatches to the correct backend
3. **Pydantic v2 native** — All responses are strongly-typed models with validation; no dictionary goop
4. **No magic strings** — All constants (moon phases, phenomena, seasons) use enums in `models.py`
5. **Pluggable providers** — Unified interface across Navy API and Skyfield via abstract base class
6. **Hybrid mode** — Per-tool provider selection (e.g., Skyfield for moon phases, Navy API for eclipses)
7. **70%+ coverage** — Test coverage enforced in CI

## Module Structure

```
src/chuk_mcp_celestial/
├── __init__.py              # Package init with version
├── server.py                # CLI entry point, @tool registration, get_sky composition, artifact store init
├── models.py                # Pydantic v2 response models and enums
├── config.py                # Configuration loading (YAML + env vars + defaults)
├── constants.py             # Planet name mappings, visibility thresholds, storage enums
├── core/
│   ├── __init__.py          # Core module exports
│   └── celestial_storage.py # Artifact storage wrapper (chuk-artifacts integration)
└── providers/
    ├── __init__.py          # Public API exports
    ├── base.py              # Abstract CelestialProvider interface (7 methods)
    ├── factory.py           # Provider factory with instance caching
    ├── navy.py              # NavyAPIProvider (US Navy API client)
    └── skyfield_provider.py # SkyfieldProvider (local JPL ephemeris + planets)
```

## Data Flow

```
LLM / Client
    │
    ▼
MCP Transport (stdio / HTTP)
    │
    ▼
Tool Layer (server.py @tool functions)
    │  - Input validation
    │  - Parameter defaults
    ▼
Provider Factory (providers/factory.py)
    │  - Per-tool provider selection
    │  - Instance caching
    ▼
Provider Layer (providers/*.py)
    │  - API-specific HTTP calls (Navy)
    │  - Local computation (Skyfield)
    │  - Response normalisation
    ▼
External API / Local Engine
    │  - US Navy Astronomical Applications API
    │  - Skyfield + JPL ephemeris (de440s.bsp)
```

## Tool Groups

| Group | Tools | Count |
|-------|-------|-------|
| Moon Phases | get_moon_phases | 1 |
| Sun & Moon | get_sun_moon_data | 1 |
| Solar Eclipses | get_solar_eclipse_by_date, get_solar_eclipses_by_year | 2 |
| Earth Seasons | get_earth_seasons | 1 |
| Planets | get_planet_position, get_planet_events | 2 |
| Sky Summary | get_sky | 1 |
| | **Total** | **8** |

## Provider Architecture

Each provider implements the `CelestialProvider` abstract interface:

- `get_moon_phases()` — Upcoming moon phase occurrences with exact timing
- `get_sun_moon_data()` — Sun/moon rise/set/transit times for a location
- `get_solar_eclipse_by_date()` — Local eclipse circumstances at a location
- `get_solar_eclipses_by_year()` — All solar eclipses in a year
- `get_earth_seasons()` — Equinoxes, solstices, perihelion, aphelion
- `get_planet_position()` — Planet alt/az, RA/Dec, distance, magnitude, visibility
- `get_planet_events()` — Planet rise/set/transit times

The `get_sky` tool in `server.py` composes `get_planet_position()` for all 8 planets
and `get_moon_phases()` into a single all-sky summary response.

The factory dispatches to the correct provider based on per-tool configuration
or the global default. Provider instances are cached for reuse. Planet tools
default to `skyfield` since the Navy API does not support planetary queries.

### Provider Comparison

| Feature | Navy API | Skyfield |
|---------|----------|----------|
| Speed | ~700ms (network) | ~25ms (local) |
| Accuracy | Authoritative (US Gov) | Research-grade (JPL) |
| Offline | No | Yes (after ephemeris download) |
| Moon phases | Yes | Yes |
| Sun/moon rise/set | Yes | Not implemented |
| Solar eclipses | Yes | Not implemented |
| Earth seasons | Yes (6 events) | Yes (4 events, no perihelion/aphelion) |
| Planet position | Not supported | Yes |
| Planet events | Not supported | Yes |

## Configuration Strategy

Configuration loads in priority order:

1. **Environment variables** (highest) — `CELESTIAL_PROVIDER`, `CELESTIAL_MOON_PHASES_PROVIDER`, etc.
2. **YAML file** — `celestial.yaml` searched in: `$CELESTIAL_CONFIG_PATH`, `./`, `~/.config/chuk-mcp-celestial/`
3. **Hardcoded defaults** — Navy API provider, de440s.bsp ephemeris

Per-tool provider overrides allow hybrid mode where fast Skyfield handles
moon phases and seasons while Navy API handles eclipses and rise/set times.

## Ephemeris Storage

Skyfield requires JPL ephemeris files for local computation. Storage is
abstracted via chuk-virtual-fs:

- **S3** — Production deployments, shared across instances
- **Local** — Development and offline use (`~/.skyfield`)
- **Memory** — Testing only (ephemeral)

On first use, ephemeris files are copied from the configured backend to a
local temp cache. Skyfield reads from the cache for performance. The cache
persists across provider instances.

## Artifact Storage

Computation results are stored via chuk-artifacts for retrieval, audit, and
cross-server integration. The `CelestialStorage` class in `core/celestial_storage.py`
wraps the artifact store with an in-memory cache.

```
Tool Layer (server.py)
    │ compute result via provider
    ▼
CelestialStorage
    ├── In-memory cache (fast repeated lookups)
    └── chuk-artifacts store (S3, filesystem, or memory)
```

Storage is optional — all operations are no-ops when no artifact store is
configured (graceful degradation).

## Testing

Tests are in `tests/` with 10 test modules:

- `test_server.py` — Integration tests for all 7 tools, CLI modes
- `test_base.py` — Abstract base provider validation
- `test_config.py` — Configuration loading and env var overrides
- `test_factory.py` — Provider factory, instance caching, tool mappings
- `test_planet_position.py` — Planet position: all planets, visibility, GeoJSON, timezone
- `test_planet_events.py` — Planet events: rise/set/transit, timezone, DST, sort order
- `test_celestial_storage.py` — Artifact storage: save/load, metadata, error handling
- `test_sky.py` — Sky summary: all-sky composition, direction helper, visibility filtering
- `test_provider_comparison.py` — Navy API vs Skyfield accuracy comparison
- `test_skyfield_vfs.py` — Virtual filesystem integration tests

Network tests marked with `@pytest.mark.network` are skipped in CI.
Multi-platform CI runs on Ubuntu, Windows, macOS across Python 3.11, 3.12, 3.13.
