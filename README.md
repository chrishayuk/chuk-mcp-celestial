# chuk-mcp-celestial

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)

Astronomical & Celestial Data MCP Server

An MCP (Model Context Protocol) server providing moon phases, sun/moon rise/set
times, solar eclipse predictions, Earth's seasons, planetary positions/events,
and all-sky summaries from the US Navy Astronomical Applications Department API
and local Skyfield calculations.

> This is a demonstration project provided as-is for learning and testing purposes.

🌐 **[Try it now - Hosted version available!](https://celestial.chukai.io/mcp)** - No installation required.

## Features

🌙 **Comprehensive Celestial Data:**
- Moon phases with exact timing (New Moon, First Quarter, Full Moon, Last Quarter)
- Sun and moon rise/set/transit times for any location
- Solar eclipse predictions with local circumstances
- Earth's seasons (equinoxes, solstices, perihelion, aphelion)
- Planetary positions (altitude, azimuth, distance, magnitude, constellation, RA/Dec, elongation, visibility)
- Planetary events (rise, set, transit times)

⚡ **Flexible Providers:**
- **Navy API** - Authoritative US Navy data, all features
- **Skyfield** - 28x faster, offline calculations, research-grade accuracy (included by default)
- **Hybrid mode** - Mix providers per-tool (e.g., Skyfield for moon phases, Navy for eclipses)
- **S3 storage** - Cloud-based ephemeris storage via chuk-virtual-fs
- **Artifact storage** - Computation results persisted via chuk-artifacts (S3, filesystem, memory)
- **GeoJSON output** - Location-based responses follow GeoJSON Feature spec

🔒 **Type-Safe & Robust:**
- Pydantic v2 models for all responses - no dictionary goop!
- Enums for all constants - no magic strings!
- Full async/await support with httpx
- Comprehensive error handling

🔗 **Multi-Server Integration:**
- Works seamlessly with [time](https://time.chukai.io/mcp) and [weather](https://weather.chukai.io/mcp) servers
- Combine celestial + time + weather for comprehensive astronomical intelligence
- Answer complex questions like "Will the moon be visible tonight with current weather?"

✅ **Quality Assured:**
- 70%+ test coverage with pytest
- GitHub Actions CI/CD
- Automated releases to PyPI
- Type checking with mypy
- Code quality with ruff

## Installation

### Comparison of Installation Methods

| Method | Setup Time | Requires Internet | Updates | Best For |
|--------|-----------|-------------------|---------|----------|
| **Hosted** | Instant | Yes | Automatic | Quick testing, production use |
| **uvx** | Instant | Yes (first run) | Automatic | No local install, always latest |
| **Local** | 1-2 min | Only for install | Manual | Offline use, custom deployments |

### Option 1: Use Hosted Version (Recommended)

No installation needed! Use our public hosted version:

```json
{
  "mcpServers": {
    "celestial": {
      "url": "https://celestial.chukai.io/mcp"
    }
  }
}
```

### Option 2: Install via uvx (No Installation Required)

Run directly without installing:

```json
{
  "mcpServers": {
    "celestial": {
      "command": "uvx",
      "args": ["chuk-mcp-celestial"]
    }
  }
}
```

### Option 3: Install Locally

```bash
# With pip
pip install chuk-mcp-celestial

# Or with uv (recommended)
uv pip install chuk-mcp-celestial

# Or with pipx (isolated installation)
pipx install chuk-mcp-celestial
```

Skyfield and NumPy are included by default — all 7 tools work out of the box.

**With S3 artifact storage (optional):**
```bash
pip install "chuk-mcp-celestial[s3]"
```

Then configure in your MCP client:

```json
{
  "mcpServers": {
    "celestial": {
      "command": "chuk-mcp-celestial"
    }
  }
}
```

**Optional: Configure hybrid provider mode** (create `celestial.yaml`):
```yaml
# Use Skyfield for fast queries, Navy API for everything else
default_provider: navy_api
providers:
  moon_phases: skyfield     # 28x faster
  earth_seasons: skyfield   # 33x faster
```

## Quick Start

### Install

```bash
# No installation required (runs directly)
uvx chuk-mcp-celestial

# Or install from PyPI
uv pip install chuk-mcp-celestial

# Or install from source with dev tools
git clone https://github.com/chuk-ai/chuk-mcp-celestial.git
cd chuk-mcp-celestial
uv pip install -e ".[dev]"
```

### Claude Desktop Configuration

```json
{
  "mcpServers": {
    "celestial": {
      "url": "https://celestial.chukai.io/mcp"
    }
  }
}
```

Or run locally:

```json
{
  "mcpServers": {
    "celestial": {
      "command": "uvx",
      "args": ["chuk-mcp-celestial"]
    }
  }
}
```

### Run

```bash
# STDIO mode (Claude Desktop, mcp-cli)
chuk-mcp-celestial stdio

# HTTP mode (API access)
chuk-mcp-celestial http --port 8080
```

## Supported Providers

| Provider | Speed | Offline | Features |
|----------|-------|---------|----------|
| **Navy API** (default) | ~700ms | No | Moon, sun/moon, eclipses, seasons. Official US government source. |
| **Skyfield** | ~25ms | Yes | Moon phases, seasons, planet position, planet events. JPL ephemeris. |

Both providers are included by default — no extras needed.

## Tools

### Moon Phases (1 tool)

| Tool | Description |
|------|-------------|
| `get_moon_phases` | Upcoming moon phases with exact timing (UT1) |

### Sun & Moon (1 tool)

| Tool | Description |
|------|-------------|
| `get_sun_moon_data` | Rise/set/transit times, twilight, moon phase, illumination for a location |

### Solar Eclipses (2 tools)

| Tool | Description |
|------|-------------|
| `get_solar_eclipse_by_date` | Local eclipse circumstances (type, magnitude, obscuration, timing) |
| `get_solar_eclipses_by_year` | All solar eclipses in a year |

### Earth Seasons (1 tool)

| Tool | Description |
|------|-------------|
| `get_earth_seasons` | Equinoxes, solstices, perihelion, aphelion for a year |

### Planets (2 tools)

| Tool | Description |
|------|-------------|
| `get_planet_position` | Altitude, azimuth, distance, magnitude, constellation, RA/Dec, elongation, visibility |
| `get_planet_events` | Rise, set, and transit times for a planet on a given date |

Supported: Mercury, Venus, Mars, Jupiter, Saturn, Uranus, Neptune, Pluto

### Sky Summary (1 tool)

| Tool | Description |
|------|-------------|
| `get_sky` | All-sky summary: every planet's position, moon phase, darkness check — one call |

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `CELESTIAL_PROVIDER` | No | `navy_api` | Default provider |
| `CELESTIAL_MOON_PHASES_PROVIDER` | No | default | Provider for moon phases |
| `CELESTIAL_EARTH_SEASONS_PROVIDER` | No | default | Provider for Earth seasons |
| `CELESTIAL_PLANET_POSITION_PROVIDER` | No | `skyfield` | Provider for planet position |
| `CELESTIAL_PLANET_EVENTS_PROVIDER` | No | `skyfield` | Provider for planet events |
| `CELESTIAL_SKY_PROVIDER` | No | `skyfield` | Provider for sky summary |
| `CELESTIAL_CONFIG_PATH` | No | — | Path to celestial.yaml |
| `SKYFIELD_STORAGE_BACKEND` | No | `s3` | Ephemeris storage: `local`, `s3`, `memory` |
| `SKYFIELD_S3_BUCKET` | No | `chuk-celestial-ephemeris` | S3 bucket for ephemeris |
| `NAVY_API_TIMEOUT` | No | `30.0` | Request timeout (seconds) |

## Hybrid Provider Mode

Create `celestial.yaml` to mix providers per-tool:

```yaml
default_provider: navy_api
providers:
  moon_phases: skyfield      # 28x faster, offline
  earth_seasons: skyfield    # 33x faster, offline
  sun_moon_data: navy_api    # Full features
  solar_eclipse_date: navy_api
  solar_eclipse_year: navy_api
  planet_position: skyfield     # Only provider with planet support
  planet_events: skyfield
  sky: skyfield                # All-sky summary
```

## Development

```bash
# Install with dev dependencies
uv pip install -e ".[dev]"

# Run tests
make test

# Run tests with coverage
make test-cov

# Lint and format
make lint
make format

# All checks
make check
```

## Deployment

### Hosted Version

No installation required:

```json
{
  "mcpServers": {
    "celestial": {
      "url": "https://celestial.chukai.io/mcp"
    }
  }
}
```

### Docker

```bash
make docker-build
make docker-run
```

### Fly.io

```bash
fly launch
fly secrets set AWS_ACCESS_KEY_ID=your_key AWS_SECRET_ACCESS_KEY=your_secret
make fly-deploy
```

## Cross-Server Workflows

chuk-mcp-celestial integrates with the broader chuk MCP ecosystem:

- **Celestial + Time** — Timezone-aware astronomy (sunrise in local time, time until next event)
- **Celestial + Weather** — Observation planning (moon phase + cloud cover forecast)
- **Celestial + Tides** — Coastal photography (golden hour + tide level)
- **Celestial + Weather** — Eclipse viewing (eclipse visibility + weather forecast)

```json
{
  "mcpServers": {
    "celestial": { "url": "https://celestial.chukai.io/mcp" },
    "time": { "url": "https://time.chukai.io/mcp" },
    "weather": { "url": "https://weather.chukai.io/mcp" }
  }
}
```

## License

Apache License 2.0 - See LICENSE for details.

## Credits

- Built on chuk-mcp-server
- Data provided by [US Navy Astronomical Applications Department](https://aa.usno.navy.mil/)

## Links

- [US Navy API Documentation](https://aa.usno.navy.mil/data/api)
- [MCP Protocol](https://modelcontextprotocol.io/)
