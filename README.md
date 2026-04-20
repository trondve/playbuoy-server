# PlayBuoy Database Server

A backend infrastructure for **PlayBuoy**—a fleet of permanently sealed, solar-powered IoT buoys deployed in Norwegian lakes to monitor water conditions autonomously for years.

## Overview

This project provides:

- **HTTP API** (`POST /upload`) to receive buoy telemetry payloads
- **Time-series database** (PostgreSQL) to store 10 years of measurements
- **Data validation** and anomaly detection (drift, charging issues, temperature spikes)
- **Dashboard-ready APIs** for querying buoy data and historical trends

## Quick Start

### Prerequisites

- Node.js 18+ or Python 3.9+
- PostgreSQL 13+
- Docker (optional, for containerized deployment)

### Installation

```bash
# Clone the repository
git clone https://github.com/trondve/playbuoy-server.git
cd playbuoy-server

# Install dependencies (Node.js example)
npm install

# Set up environment variables
cp .env.example .env
# Edit .env with database credentials and API key

# Run database migrations
npm run migrate

# Start the server
npm start
```

The API will be available at `http://localhost:3000`.

## API Endpoint

### POST /upload

Accepts telemetry payloads from buoys.

**Headers:**
```
X-API-Key: super-secret-key-123
Content-Type: application/json
```

**Request body:** JSON payload with ~40 fields (see [`docs/buoy.md`](docs/buoy.md) for complete schema)

**Success response (201):**
```json
{
  "status": "success",
  "timestamp": "2026-04-20T15:30:45Z"
}
```

**Error response (400):**
```json
{
  "error": "Invalid field: battery_percent must be 0-100",
  "field": "battery_percent",
  "value": 105
}
```

## Project Structure

```
playbuoy-server/
├── CLAUDE.md                  # Project context & memory
├── README.md                  # This file
├── docs/
│   ├── buoy.md               # PlayBuoy hardware & protocol specification
│   ├── architecture.md        # Database design & schema decisions (TBD)
│   ├── decisions/             # Architecture Decision Records (TBD)
│   └── runbooks/              # Operational guides (TBD)
├── .claude/
│   ├── settings.json          # Claude Code configuration
│   ├── hooks/                 # Automation hooks (TBD)
│   └── skills/                # Custom Claude skills (TBD)
├── src/
│   ├── api/                   # Express routes, controllers, middleware
│   └── persistence/           # Database queries, migrations, schema
├── tests/                     # Unit & integration tests
└── tools/
    ├── scripts/               # Utility scripts (backups, migrations, etc.)
    └── prompts/               # Reusable Claude prompts
```

## Data Model

### Buoys Table
Metadata about registered buoys.

| Column | Type | Description |
|--------|------|-------------|
| `node_id` | TEXT (PK) | Unique identifier (e.g., "playbuoy_grinde") |
| `name` | TEXT | Human-readable name |
| `location` | POINT | GPS coordinates |
| `installed_date` | TIMESTAMP | Deployment timestamp |
| `status` | TEXT | "active" \| "inactive" \| "lost" |
| `last_heartbeat` | TIMESTAMP | Latest measurement time |
| `firmware_version` | TEXT | Current firmware version |

### Measurements Table
Time-series data, partitioned by month.

| Column | Type | Description |
|--------|------|-------------|
| `timestamp` | TIMESTAMP (PK) | Measurement time (UTC) |
| `node_id` | TEXT (FK) | Buoy identifier |
| `temperature` | FLOAT | Water temperature (°C) |
| `battery_voltage` | FLOAT | Cell voltage (3.0–4.2V) |
| `battery_percent` | INT | State-of-charge (0–100%) |
| `wave_height` | FLOAT | Significant wave height (m) |
| `wave_period` | FLOAT | Peak period (s) |
| `wave_power` | FLOAT | Spectral power (kW/m) |
| `gps_lat` | FLOAT | Latitude |
| `gps_lon` | FLOAT | Longitude |
| `gps_hdop` | FLOAT | Horizontal dilution of precision |
| `gps_ttf` | INT | Time-to-fix (seconds) |
| `net_operator` | TEXT | Mobile network operator |
| `net_signal` | INT | Signal strength (0–31 RSRP units) |
| `buoy_tilt` | FLOAT | Physical tilt (degrees) |
| `boot_count` | INT | Cycle counter |
| `alerts` | JSONB | Alert flags (anchorDrift, chargingIssue, etc.) |

**Indexes:**
- `(node_id, timestamp DESC)` — Query buoy's latest measurements
- `(timestamp DESC)` — Find latest overall measurements
- `node_id` — List all buoys
- `timestamp` — Purge old data (10-year retention)

## Validation Rules

The API validates all incoming payloads:

- **Required fields:** `nodeId`, `timestamp`, `lat`, `lon`, `temp`, `battery`, `version`
- **Ranges:**
  - `battery_percent`: 0–100 (not >100)
  - `temp`: -30 to +60°C (water temperature)
  - `lat`/`lon`: ±90 / ±180 (reject Null Island at 0,0)
  - `wave_height`: 0–2.0m (lakes only)
  - `timestamp`: Within ±24h of current UTC
- **Float sanitization:** Replace NaN/Inf with 0

## Alert Processing

The server detects and flags anomalies:

| Alert | Condition |
|-------|-----------|
| `anchorDrift` | GPS position >50m from first recorded location |
| `chargingIssue` | Battery % not increasing for 5 consecutive cycles |
| `tempSpike` | Temperature changes >5°C in one cycle |
| `overTemp` | Temperature >60°C (impossible for water) |
| `uploadFailed` | Previous cycle's JSON still in buoy RTC buffer |

## Deployment

### Docker

```bash
docker build -t playbuoy-server:latest .
docker run -p 3000:3000 \
  -e DB_HOST=postgres \
  -e DB_NAME=playbuoy \
  -e DB_USER=postgres \
  -e DB_PASSWORD=<secret> \
  -e API_KEY=super-secret-key-123 \
  playbuoy-server:latest
```

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DB_HOST` | localhost | PostgreSQL hostname |
| `DB_PORT` | 5432 | PostgreSQL port |
| `DB_NAME` | playbuoy | Database name |
| `DB_USER` | postgres | Database user |
| `DB_PASSWORD` | (required) | Database password |
| `API_KEY` | (required) | X-API-Key shared secret |
| `API_PORT` | 3000 | Server port |
| `LOG_LEVEL` | info | Logging level (debug\|info\|warn\|error) |

## Development

### Running Tests

```bash
npm test
```

### Running Migrations

```bash
npm run migrate
npm run migrate:rollback
```

### Database Console

```bash
npm run db:shell
```

## Documentation

- **[`CLAUDE.md`](CLAUDE.md)** — Project memory, architecture, next steps
- **[`docs/buoy.md`](docs/buoy.md)** — Complete PlayBuoy hardware & protocol spec
- **[`docs/architecture.md`](docs/architecture.md)** — Database design decisions (TBD)
- **[`docs/decisions/`](docs/decisions)** — ADRs for major architectural choices (TBD)
- **[`docs/runbooks/`](docs/runbooks)** — Operational guides (TBD)

## Performance Targets

- **API latency:** <100ms (parse, validate, insert)
- **Database insert:** <10ms per measurement
- **Query latency:** <500ms for historical time-range query
- **Annual volume:** ~4000–5000 measurements/buoy
- **10-year storage:** ~50–100MB per buoy

## License

(TBD)

## Support

For questions or issues, see:
- Project context: [`CLAUDE.md`](CLAUDE.md)
- PlayBuoy specification: [`docs/buoy.md`](docs/buoy.md)
- GitHub Issues: https://github.com/trondve/playbuoy-server/issues