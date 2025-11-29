# chuk-mcp-celestial

[![PyPI version](https://badge.fury.io/py/chuk-mcp-celestial.svg)](https://badge.fury.io/py/chuk-mcp-celestial)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**MCP server for US Navy astronomical and celestial data** - The definitive celestial MCP server providing moon phases, solar eclipses, sun/moon rise/set times, and Earth's seasons from the official US Navy Astronomical Applications API.

🌐 **[Try it now - Hosted version available!](https://celestial.chukai.io/mcp)** - No installation required.

## Features

🌙 **Comprehensive Celestial Data:**
- Moon phases with exact timing (New Moon, First Quarter, Full Moon, Last Quarter)
- Sun and moon rise/set/transit times for any location
- Solar eclipse predictions with local circumstances
- Earth's seasons (equinoxes, solstices, perihelion, aphelion)

⚡ **Flexible Providers:**
- **Navy API** - Authoritative US Navy data, all features
- **Skyfield** - 28x faster, offline calculations, research-grade accuracy
- **Hybrid mode** - Mix providers per-tool (e.g., Skyfield for moon phases, Navy for eclipses)
- **S3 storage** - Cloud-based ephemeris storage via chuk-virtual-fs

🔒 **Type-Safe & Robust:**
- Pydantic v2 models for all responses - no dictionary goop!
- Enums for all constants - no magic strings!
- Full async/await support with httpx
- Comprehensive error handling

🔗 **Multi-Server Integration:**
- Works seamlessly with [time](https://time.chukai.io/mcp) and [weather](https://weather.chukai.io/mcp) servers
- Combine celestial + time + weather for comprehensive astronomical intelligence
- Answer complex questions like "Will the moon be visible tonight with current weather?"

✅ **Production Ready:**
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

**Basic Installation (Navy API only):**
```bash
# With pip
pip install chuk-mcp-celestial

# Or with uv (recommended)
uv pip install chuk-mcp-celestial

# Or with pipx (isolated installation)
pipx install chuk-mcp-celestial
```

**With Skyfield Support (offline calculations, 28x faster):**
```bash
# Install with Skyfield and S3 support
pip install "chuk-mcp-celestial[skyfield]"

# Or with uv
uv pip install "chuk-mcp-celestial[skyfield]"

# Download ephemeris files (one-time setup)
python scripts/download_ephemeris.py --backend local
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

### Claude Desktop Configuration

Choose one of the installation methods above and add to your Claude Desktop config:

**macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
**Windows**: `%APPDATA%/Claude/claude_desktop_config.json`

**Hosted version (easiest):**
```json
{
  "mcpServers": {
    "celestial": {
      "url": "https://celestial.chukai.io/mcp"
    }
  }
}
```

**uvx version (no install):**
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

**Local installation:**
```json
{
  "mcpServers": {
    "celestial": {
      "command": "chuk-mcp-celestial"
    }
  }
}
```

Then ask questions like:
- "When is the next full moon?"
- "What time does the sun rise in Seattle tomorrow?"
- "Are there any solar eclipses visible from New York in 2024?"
- "When are the equinoxes this year?"

### Using with mcp-cli

Test the server interactively with mcp-cli:

```bash
# Using hosted version
uv run mcp-cli --server https://celestial.chukai.io/mcp --provider openai --model gpt-4o-mini

# Using uvx (local execution)
uv run mcp-cli --server celestial --provider openai --model gpt-4o-mini
```

Example session:
```
> when does the sunrise tomorrow in london
✓ Completed: get_sun_moon_data (0.50s)

Sunrise in London tomorrow (2025-11-29) is at 07:41 GMT (UTC).

Additional info:
- Begin civil twilight: 07:02 GMT
- Sunset: 15:56 GMT
- Daylight length: about 8 h 15 m
```

### As a Python Library

#### Using MCP Server Tools (Default Provider)

```python
import asyncio
from chuk_mcp_celestial.server import (
    get_moon_phases,
    get_sun_moon_data,
    get_solar_eclipse_by_date,
    get_earth_seasons,
)

async def main():
    # Get next 4 moon phases (uses configured provider)
    phases = await get_moon_phases(date="2024-12-1", num_phases=4)
    for phase in phases.phasedata:
        print(f"{phase.phase}: {phase.year}-{phase.month:02d}-{phase.day:02d} at {phase.time} UT")

    # Get sun/moon times for Seattle
    data = await get_sun_moon_data(
        date="2024-12-21",
        latitude=47.60,
        longitude=-122.33,
        timezone=-8
    )
    print(f"Moon phase: {data.properties.data.curphase}")
    print(f"Illumination: {data.properties.data.fracillum}")

    # Check eclipse visibility
    eclipse = await get_solar_eclipse_by_date(
        date="2024-4-8",
        latitude=40.71,  # New York
        longitude=-74.01
    )
    print(f"Eclipse: {eclipse.properties.description}")
    print(f"Magnitude: {eclipse.properties.magnitude}")

asyncio.run(main())
```

#### Using Providers Directly

```python
import asyncio
from chuk_mcp_celestial.providers import NavyAPIProvider, SkyfieldProvider

async def main():
    # Use Navy API provider
    navy = NavyAPIProvider()
    phases_navy = await navy.get_moon_phases("2024-1-1", num_phases=4)
    print("Navy API moon phases:")
    for phase in phases_navy.phasedata:
        print(f"  {phase.phase}: {phase.year}-{phase.month:02d}-{phase.day:02d} {phase.time}")

    # Use Skyfield provider (faster, offline)
    skyfield = SkyfieldProvider(
        ephemeris_file="de421.bsp",
        storage_backend="memory",  # or "s3" or "local"
        auto_download=True
    )
    phases_skyfield = await skyfield.get_moon_phases("2024-1-1", num_phases=4)
    print("\nSkyfield moon phases:")
    for phase in phases_skyfield.phasedata:
        print(f"  {phase.phase}: {phase.year}-{phase.month:02d}-{phase.day:02d} {phase.time}")

    # Earth seasons with Skyfield (fast!)
    seasons = await skyfield.get_earth_seasons(2024)
    print("\nEarth seasons 2024:")
    for event in seasons.data:
        print(f"  {event.phenom}: {event.year}-{event.month:02d}-{event.day:02d} {event.time}")

asyncio.run(main())
```

#### Hybrid Approach (Best of Both Worlds)

```python
import asyncio
from chuk_mcp_celestial.providers import NavyAPIProvider, SkyfieldProvider

async def main():
    # Use Skyfield for fast offline calculations
    skyfield = SkyfieldProvider(storage_backend="local")

    # Use Navy API for features not in Skyfield
    navy = NavyAPIProvider()

    # Fast moon phases from Skyfield
    phases = await skyfield.get_moon_phases("2024-12-1", num_phases=12)

    # Detailed rise/set times from Navy API
    sun_moon = await navy.get_sun_moon_data(
        date="2024-12-21",
        latitude=47.60,
        longitude=-122.33
    )

    # Solar eclipses only from Navy API (not in Skyfield)
    eclipse = await navy.get_solar_eclipse_by_date(
        date="2024-4-8",
        latitude=40.71,
        longitude=-74.01
    )

    print(f"Next moon phase: {phases.phasedata[0].phase}")
    print(f"Sunrise: {sun_moon.properties.data.sundata[0].time}")
    print(f"Eclipse: {eclipse.properties.description}")

asyncio.run(main())
```

## Available Tools

### `get_moon_phases(date, num_phases)`
Get upcoming moon phases starting from a given date.

**Parameters:**
- `date` (str): Start date (YYYY-MM-DD)
- `num_phases` (int): Number of phases to return (1-99, default 12)

**Returns:** `MoonPhasesResponse` with list of phase data

### `get_sun_moon_data(date, latitude, longitude, timezone?, dst?, label?)`
Get complete sun and moon data for one day at a specific location.

**Parameters:**
- `date` (str): Date (YYYY-MM-DD)
- `latitude` (float): Latitude in decimal degrees (-90 to 90)
- `longitude` (float): Longitude in decimal degrees (-180 to 180)
- `timezone` (float, optional): Timezone offset from UTC in hours
- `dst` (bool, optional): Apply daylight saving time
- `label` (str, optional): User label for the query

**Returns:** `OneDayResponse` (GeoJSON Feature) with sun/moon rise/set/transit times, twilight, moon phase, and illumination

### `get_solar_eclipse_by_date(date, latitude, longitude, height?)`
Get local solar eclipse circumstances for a specific date and location.

**Parameters:**
- `date` (str): Eclipse date (YYYY-MM-DD)
- `latitude` (float): Observer latitude
- `longitude` (float): Observer longitude
- `height` (int, optional): Height above sea level in meters (default 0)

**Returns:** `SolarEclipseByDateResponse` (GeoJSON Feature) with eclipse type, magnitude, obscuration, duration, and local circumstances

### `get_solar_eclipses_by_year(year)`
Get a list of all solar eclipses occurring in a specific year.

**Parameters:**
- `year` (int): Year to query (1800-2050)

**Returns:** `SolarEclipseByYearResponse` with list of eclipse events

### `get_earth_seasons(year, timezone?, dst?)`
Get Earth's seasons and orbital events for a year.

**Parameters:**
- `year` (int): Year to query (1700-2100)
- `timezone` (float, optional): Timezone offset from UTC
- `dst` (bool, optional): Apply daylight saving time

**Returns:** `SeasonsResponse` with equinoxes, solstices, perihelion, and aphelion

## Architecture

### No Dictionary Goop

All responses are strongly-typed Pydantic models:

```python
# ❌ Bad (dictionary goop)
phase = data["phasedata"][0]["phase"]

# ✅ Good (typed models)
phase = data.phasedata[0].phase  # IDE autocomplete works!
```

### No Magic Strings

All constants use enums:

```python
from chuk_mcp_celestial.models import MoonPhase, SeasonPhenomenon

# ❌ Bad (magic strings)
if phase == "Full Moon":

# ✅ Good (enums)
if phase == MoonPhase.FULL_MOON:
```

### Async Native

All API calls use async/await with httpx:

```python
async with httpx.AsyncClient() as client:
    response = await client.get(API_URL, params=params, timeout=30.0)
    response.raise_for_status()
    data = response.json()
return PydanticModel(**data)
```

### Provider Architecture

This server supports **multiple calculation providers** via a factory pattern, allowing you to choose between different astronomical calculation backends:

#### Available Providers

| Provider | Speed | Accuracy | Offline | Features |
|----------|-------|----------|---------|----------|
| **Navy API** | Standard (~700ms) | Authoritative | ❌ | All features |
| **Skyfield** | Fast (~25ms) | Research-grade | ✅ | Moon phases, seasons |

#### Configuration

Create a `celestial.yaml` file to configure providers:

```yaml
# Default provider for all tools
default_provider: navy_api

# Per-tool provider configuration (mix and match!)
providers:
  moon_phases: skyfield          # Fast offline calculations
  sun_moon_data: navy_api         # Rise/set times
  solar_eclipse_date: navy_api    # Eclipse circumstances
  solar_eclipse_year: navy_api    # Eclipse catalogs
  earth_seasons: skyfield         # Fast offline seasons

# Skyfield configuration
skyfield:
  # Ephemeris file to use
  ephemeris: de440s.bsp  # 32 MB, covers 1849-2150

  # Storage backend for ephemeris files
  storage_backend: s3    # Options: local, s3, memory

  # S3 configuration (when storage_backend=s3)
  s3:
    bucket: chuk-celestial-ephemeris
    region: us-east-1
    prefix: ephemeris/
    # profile: default  # Optional AWS profile

  # Local directory (when storage_backend=local)
  data_dir: ~/.skyfield

  # Auto-download ephemeris if not present
  auto_download: true

# Navy API configuration
navy_api:
  base_url: https://aa.usno.navy.mil/api
  timeout: 30.0
  max_retries: 3
  retry_delay: 1.0
```

**Config file locations** (checked in order):
1. Path from `CELESTIAL_CONFIG_PATH` environment variable
2. `./celestial.yaml` (current directory)
3. `~/.config/chuk-mcp-celestial/celestial.yaml` (user config)

**Environment variable overrides:**
- `CELESTIAL_PROVIDER` - Default provider
- `CELESTIAL_MOON_PHASES_PROVIDER` - Provider for moon phases
- `SKYFIELD_STORAGE_BACKEND` - Storage backend (local/s3/memory)
- `SKYFIELD_S3_BUCKET` - S3 bucket name
- `SKYFIELD_S3_REGION` - S3 region
- See `celestial.yaml.example` for all options

#### Ephemeris Storage with chuk-virtual-fs

Skyfield requires JPL ephemeris files (~32 MB) for astronomical calculations. This server uses **chuk-virtual-fs** to provide flexible storage options:

**Storage Backends:**

1. **S3 (Recommended for production)** - Cloud storage with AWS S3
   - Persistent across deployments
   - Shared across multiple instances
   - No local disk required
   - Easy CDN integration

2. **Local** - Traditional filesystem storage
   - Good for development and offline use
   - No cloud dependencies
   - Requires local disk space

3. **Memory** - In-memory storage for testing
   - Ephemeral storage
   - Fast but non-persistent

**Download Ephemeris Files:**

```bash
# Download recommended ephemeris (de440s.bsp) to S3
python scripts/download_ephemeris.py

# Download all ephemeris files to S3
python scripts/download_ephemeris.py --all

# Download specific ephemeris to S3
python scripts/download_ephemeris.py --file de421.bsp

# Force re-download even if file exists
python scripts/download_ephemeris.py --force

# Download to local filesystem
python scripts/download_ephemeris.py --backend local

# Download all files to local storage
python scripts/download_ephemeris.py --all --backend local

# List available ephemeris files
python scripts/download_ephemeris.py --list
```

**Features:**
- ✅ Auto-creates S3 bucket if it doesn't exist
- ✅ Skips files that already exist in storage
- ✅ Use `--force` to re-download existing files
- ✅ Batch download with `--all` flag

**Note:** For S3 backend, create a `.env` file with AWS credentials:
```bash
cp .env.example .env
# Edit .env with your AWS credentials
```

**Available ephemeris files:**
- `de440s.bsp` - 32 MB, covers 1849-2150 (⭐ recommended)
- `de421.bsp` - 17 MB, covers 1900-2050 (smaller, older)
- `de440.bsp` - 114 MB, covers 1550-2650 (most comprehensive)

**How it works:**
1. Ephemeris files are stored in your configured backend (S3, local, or memory)
2. On first use, Skyfield provider downloads files to a local temp cache
3. Skyfield reads from the cache for fast calculations
4. Cache persists across provider instances for performance

See [COMPARISON_REPORT.md](COMPARISON_REPORT.md) for detailed accuracy and performance comparison between providers.

## Deployment

### Docker

Build and run with Docker:

```bash
# Build Docker image
make docker-build

# Run container
make docker-run

# Or build and run in one command
make docker-up
```

The server will be available at `http://localhost:8000` in HTTP mode.

### Fly.io

Deploy to Fly.io:

```bash
# First time setup
fly launch

# Set AWS secrets for S3 ephemeris storage
fly secrets set AWS_ACCESS_KEY_ID=your_key AWS_SECRET_ACCESS_KEY=your_secret

# Deploy
make fly-deploy

# Check status
make fly-status

# View logs
make fly-logs

# Open in browser
make fly-open
```

**Configuration** (`fly.toml`):
- Environment variables for provider settings
- S3 bucket configuration
- AWS credentials via `fly secrets` (not in file)
- Auto-scales to 0 when not in use

**Ephemeris Setup for Production:**
```bash
# Download ephemeris files to S3 before first deployment
cp .env.example .env
# Edit .env with your AWS credentials
python scripts/download_ephemeris.py --backend s3

# Or download all files
python scripts/download_ephemeris.py --all --backend s3
```

## Development

### Setup

```bash
# Clone the repo
git clone https://github.com/yourusername/chuk-mcp-celestial
cd chuk-mcp-celestial

# Install with all dependencies (dev + skyfield)
uv sync --extra dev --extra skyfield

# Or with pip
pip install -e ".[dev,skyfield]"

# Set up environment variables for S3 (optional)
cp .env.example .env
# Edit .env with your AWS credentials

# Download ephemeris files for local development
python scripts/download_ephemeris.py --backend local
```

### Testing

```bash
# Run tests
make test

# Run tests with coverage
make test-cov

# Run specific test
pytest tests/test_server.py::test_get_moon_phases -v
```

### Code Quality

```bash
# Format code
make format

# Run linters
make lint

# Type checking
make typecheck

# Security checks
make security

# Run all checks
make check
```

## Quick Reference

### Common Tasks

**Download ephemeris files:**
```bash
# Recommended (auto-select de440s.bsp)
python scripts/download_ephemeris.py

# All files
python scripts/download_ephemeris.py --all

# To S3 (production)
python scripts/download_ephemeris.py --backend s3

# List available files
python scripts/download_ephemeris.py --list
```

**Configure providers (celestial.yaml):**
```yaml
default_provider: navy_api
providers:
  moon_phases: skyfield      # Fast offline
  earth_seasons: skyfield    # Fast offline
  sun_moon_data: navy_api    # Full features
  solar_eclipse_date: navy_api
```

**Environment variables (.env):**
```bash
# AWS credentials
AWS_ACCESS_KEY_ID=your_key
AWS_SECRET_ACCESS_KEY=your_secret
AWS_REGION=us-east-1

# Provider selection
CELESTIAL_PROVIDER=navy_api
CELESTIAL_MOON_PHASES_PROVIDER=skyfield
```

**Test provider comparison:**
```bash
# Run comparison tests
uv run pytest tests/test_provider_comparison.py -v

# See detailed report
cat COMPARISON_REPORT.md
```

## Multi-Server Integration

The **chuk-mcp-celestial** server works beautifully with other MCP servers to answer complex questions:

### Recommended Server Combinations

**Celestial + Time + Weather = Complete Astronomical Intelligence**

```json
{
  "mcpServers": {
    "celestial": {
      "url": "https://celestial.chukai.io/mcp"
    },
    "time": {
      "url": "https://time.chukai.io/mcp"
    },
    "weather": {
      "url": "https://weather.chukai.io/mcp"
    }
  }
}
```

### Example Multi-Server Queries

**1. Moon Visibility with Location Intelligence**
```
Q: "Where will the moon be in Leavenheath Suffolk tonight at 10:30pm?
    Will it be visible and what phase will it be?"

Uses:
- weather server → geocode_location (find coordinates)
- celestial server → get_sun_moon_data (moon position & phase)
- AI reasoning → combine data for comprehensive answer

Result:
✓ Moon will be visible in western sky at 22:30 GMT
✓ Phase: Waxing Gibbous (52% illuminated)
✓ Position: Descending from upper transit at 18:21
```

**2. Sunrise + Current Time**
```
Q: "When does the sun rise in London and what time is it there now?"

Uses:
- time server → get_time_for_timezone (current time in Europe/London)
- celestial server → get_sun_moon_data (sunrise time)
- weather server → geocode_location (confirm location)

Result:
✓ Current time: 21:43:19 GMT
✓ Sunrise tomorrow: 07:41 GMT
✓ Time until sunrise: 9h 58m
```

**3. Eclipse + Weather Forecast**
```
Q: "Will the next solar eclipse be visible from New York, and what will the weather be like?"

Uses:
- celestial server → get_solar_eclipses_by_year, get_solar_eclipse_by_date
- weather server → get_weather_forecast (for eclipse date)
- time server → timezone conversions

Result:
✓ Eclipse visibility and timing
✓ Weather forecast for eclipse day
✓ Optimal viewing conditions
```

### Why Multi-Server Works Better

| Single Server | Multi-Server Combination |
|---------------|-------------------------|
| "Moon rises at 12:55 UTC" | "Moon rises at 12:55 (7:55am local time)" |
| "Sunrise at 07:41" | "Sunrise at 07:41, currently 21:43, sunset was at 15:56" |
| "Eclipse on 2024-4-8" | "Eclipse on 2024-4-8, weather: partly cloudy, 60% visibility chance" |

### Server Responsibilities

**Celestial Server (this server):**
- 🌙 Moon phases, positions, rise/set times
- ☀️ Sun rise/set times, twilight, transit
- 🌑 Solar eclipse predictions and local circumstances
- 🌍 Earth's seasons and orbital events

**Time Server:**
- ⏰ Precise current time with NTP synchronization
- 🌐 Timezone conversions and DST handling
- 📅 Date/time calculations

**Weather Server:**
- 🗺️ Geocoding (convert place names to coordinates)
- ⛅ Weather forecasts and current conditions
- 📊 Historical weather data
- 💨 Air quality information

### Testing Multi-Server Setup

```bash
# Test all three servers together
uv run mcp-cli --server celestial,time,weather \
  --provider openai \
  --model gpt-4o-mini
```

Then ask questions like:
- "When is sunset in Tokyo and what time is it there now?"
- "What phase is the moon tonight and will it be cloudy?"
- "When is the next eclipse visible from London and what's the forecast?"

## Data Source

This MCP server uses the official **US Navy Astronomical Applications Department API** (https://aa.usno.navy.mil/data/api), which provides:

- Highly accurate astronomical data
- Historical data from 1700-2100 (varies by endpoint)
- Solar eclipse data from 1800-2050
- Official US government source

## Comparison with Other Services

| Feature | chuk-mcp-celestial | Other Services |
|---------|-------------------|----------------|
| Data Source | US Navy (official) | Various APIs |
| Type Safety | Full Pydantic models | Often dictionaries |
| Enums | Yes (no magic strings) | Usually strings |
| Async | Native httpx | Mixed |
| Eclipse Data | Local circumstances | Often just dates |
| Historical Range | 200-400 years | Usually limited |
| Test Coverage | 70%+ | Varies |

## Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Run tests and checks (`make check`)
5. Commit your changes
6. Push to the branch
7. Open a Pull Request

## License

MIT License - see LICENSE file for details

## Credits

- Built on [chuk-mcp-server](https://github.com/yourusername/chuk-mcp-server)
- Data provided by [US Navy Astronomical Applications Department](https://aa.usno.navy.mil/)
- Inspired by [chuk-mcp-open-meteo](https://github.com/yourusername/chuk-mcp-open-meteo)

## Links

- [PyPI Package](https://pypi.org/project/chuk-mcp-celestial/)
- [GitHub Repository](https://github.com/yourusername/chuk-mcp-celestial)
- [US Navy API Documentation](https://aa.usno.navy.mil/data/api)
- [MCP Protocol](https://modelcontextprotocol.io/)
