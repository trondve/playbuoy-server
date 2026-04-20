# PlayBuoy Database Server — Project Context

**Project:** Database & API server for PlayBuoy IoT buoys  
**Repository:** `trondve/playbuoy-server`  
**Created:** 2026-04-20  
**Status:** Initial setup

## Project Overview

This project implements a **Node.js/Express backend** for PlayBuoy to unify and enhance the existing FastAPI infrastructure.

### Current State
- **Existing FastAPI server** running on Raspberry Pi using SQLite (21 test measurements)
- **PostgreSQL database** configured but unused (orphaned tables: `buoy_data`, `alert_log`)
- **Architecture task:** Consolidate on PostgreSQL and implement Node.js API server for better integration

### Goals
1. **Receive telemetry** from buoys via HTTP POST (`/upload` endpoint) — matching FastAPI contract
2. **Store in PostgreSQL** with proper time-series partitioning (10-year retention)
3. **Process alerts** (drift, charging issues, temperature anomalies)
4. **Serve dashboards & APIs** for monitoring and historical analysis
5. **Migrate existing data** from SQLite to PostgreSQL without data loss

## Architecture

### Core Components

```
API Layer (Express.js or similar)
├── POST /upload — Accept buoy telemetry, validate, store
├── GET /buoys — List all registered buoys
├── GET /buoys/:id/latest — Latest measurement for a buoy
└── GET /buoys/:id/history — Time-series data with filtering

Database Layer (PostgreSQL with time-series extension)
├── buoys — Metadata (node_id, name, location, installed_date, etc.)
└── measurements — Partitioned by month, indexed for fast queries

Storage Strategy
├── Hot data (last 30 days) — Fast SSD access
├── Warm data (1–10 years) — Compressed, archive-ready
└── Cold data (archived) — Long-term retention
```

### Key Files

- `src/api/` — Express routes, validation, error handling
- `src/persistence/` — Database migrations, queries, schema
- `docs/buoy.md` — Complete PlayBuoy system specification
- `docs/architecture.md` — Database design, indexing, scaling considerations

## Data Model

### Table: `buoys`
```
node_id (TEXT, PK)  — e.g., "playbuoy_grinde"
name (TEXT)         — "Litla Grindevatnet"
location (POINT)    — GPS coordinates
installed_date      — Deployment timestamp
status              — "active" | "inactive" | "lost"
last_heartbeat      — Latest measurement timestamp
firmware_version    — Current buoy firmware
```

### Table: `measurements` (time-series, partitioned by month)
```
timestamp (TIMESTAMP, PK)          — Measurement time (UTC)
node_id (TEXT, FK)                 — Buoy identifier
temperature (FLOAT)                — Water temp in °C
battery_voltage (FLOAT)            — Cell voltage (3.0–4.2V)
battery_percent (INT)              — SoC 0–100%
wave_height (FLOAT)                — Significant wave height (m)
wave_period (FLOAT)                — Peak period (s)
wave_power (FLOAT)                 — Spectral power (kW/m)
gps_lat (FLOAT), gps_lon (FLOAT)   — Position
gps_hdop (FLOAT)                   — Horizontal dilution of precision
gps_ttf (INT)                      — Time-to-fix (seconds)
net_operator (TEXT)                — Mobile network operator
net_signal (INT)                   — Signal strength (0–31 RSRP)
buoy_tilt (FLOAT)                  — Physical tilt (degrees)
boot_count (INT)                   — Cycle counter
alerts (JSONB)                     — {anchorDrift, chargingIssue, ...}

INDEXES:
  (node_id, timestamp DESC)  — Query buoy's last N measurements
  (timestamp DESC)           — Find latest overall
  node_id                    — List all buoys
  timestamp                  — Purge old data
```

## Validation Rules

**API must reject payloads that:**
- Have missing required fields (`nodeId`, `timestamp`, `lat`, `lon`, `temp`, `battery`, `version`)
- Have out-of-range values (e.g., battery_percent > 100, temp > 60°C for water)
- Have invalid floats (NaN, Inf) without sanitization
- Have timestamps >24h away from current UTC (clock skew detection)
- Have invalid lat/lon (accept ±0.0001 GPS noise, reject exact 0,0 "Null Island")
- Have messages older than 30 days (assume lost comms, reject stale uploads)

**Success response:** HTTP 201 with `{"status": "success", "timestamp": "ISO-8601"}`

**Error response:** HTTP 400 with `{"error": "...", "field": "...", "value": ...}`

## Alert Processing

The server detects and flags these anomalies:

| Alert | Trigger | Action |
|-------|---------|--------|
| `anchorDrift` | GPS position >50m from first recorded location | Email ops |
| `chargingIssue` | Battery % not increasing for 5 consecutive cycles | Email ops |
| `tempSpike` | Current temp differs >5°C from 5-cycle mean | Log, tag measurement |
| `overTemp` | Temp >60°C (impossible for water in Norway) | Mark as sensor error |
| `uploadFailed` | Previous cycle's JSON still in buoy RTC buffer | Retry next cycle |

## Development Workflow

1. **Database migrations** — Use a versioned migration system (Flyway, Alembic, etc.)
2. **API validation** — Parse & validate payload schema before write
3. **Time-series indexing** — Optimize for (node_id, timestamp) queries
4. **Alert triggers** — Background job that checks conditions after each measurement
5. **Retention policy** — Automated purge of data older than 10 years
6. **Testing** — Unit tests for validation rules, integration tests for API endpoint

## Security

- **API Key validation** — Always verify `X-API-Key` header matches `super-secret-key-123`
- **Input sanitization** — Replace NaN/Inf, reject invalid lat/lon ranges
- **SQL injection prevention** — Use parameterized queries
- **Rate limiting** — Per-buoy upload limit (e.g., max 1 upload per 60 seconds)
- **Logging** — Audit all uploads, track rejected payloads

## Deployment

- **Runtime:** Node.js 18+ or Python 3.9+ (TBD)
- **Database:** PostgreSQL 13+ with TimescaleDB extension (optional, for hypertable partitioning)
- **Container:** Docker (dockerfile in `tools/docker/`)
- **Existing Infrastructure:**
  - Database: Raspberry Pi (IP: 192.168.140.7)
  - SSH user: `playbuoyadmin`
  - Cloudflare managed DNS
- **Environment variables:**
  - `DB_HOST` — Database hostname/IP
  - `DB_PORT` — Database port (default 5432)
  - `DB_NAME` — Database name
  - `DB_USER` — Database user
  - `DB_PASSWORD` — PostgreSQL password (⚠️ keep in .env, never in code)
  - `API_KEY` — Shared secret for X-API-Key header
  - `CLOUDFLARE_API_KEY` — For DNS management (⚠️ keep in .env)
  - `API_PORT` (default 3000)
  - `LOG_LEVEL` (debug|info|warn|error)
  - `SSH_USER` — SSH username for Raspberry Pi admin access

**⚠️ SECURITY:** All credentials stored in `.env` (git-ignored), never committed to repository.

## Performance Targets

- **API latency:** <100ms (parse, validate, insert)
- **Database insert:** <10ms per measurement
- **Query latency:** <500ms for historical time-range query
- **Buoy data volume:** ~12 msg/day summer, ~0.4 msg/day winter
- **Annual data:** ~4000–5000 measurements/buoy, ~50–100MB storage for 10-year retention

## Documentation

- `CLAUDE.md` — This file (project memory & context)
- `docs/buoy.md` — Complete PlayBuoy hardware & protocol specification
- `docs/architecture.md` — Database design, schema decisions, scaling strategy (TBD)
- `docs/decisions/` — ADRs (Architecture Decision Records) for major choices (TBD)
- `docs/runbooks/` — Operational guides (deployment, scaling, debugging) (TBD)

## Existing FastAPI Server (Raspberry Pi)

### Current Implementation
- **Location:** `/home/playbuoyadmin/playbuoy-server/main.py`
- **Database:** SQLite (`playbuoy.db`, 94 KB, 21 test records)
- **Port:** 8000 (via uvicorn)
- **Endpoints:** `/upload`, `/latest`, `/latest_all`, `/health`
- **Authentication:** X-API-Key: `super-secret-key-123`
- **CORS:** Configured for Wix frontend

### Data Currently Stored
- **Measurements:** 21 test records (2025-07-06, 2-hour interval)
- **Buoys:** 20 test node_ids (playbuoy-grinde, playbuoy-vigdar, etc.)
- **Format:** Matches schema defined in `docs/buoy.md`

### ⚠️ Architecture Issue
**Dual Database Problem:**
- FastAPI uses **SQLite** (active)
- PostgreSQL is configured but **unused** (orphaned `buoy_data` and `alert_log` tables)
- Must consolidate: SQLite test data → PostgreSQL for production

### FastAPI Upload Schema
The existing FastAPI `/upload` endpoint accepts:
```json
{
  "nodeId": "playbuoy-grinde",
  "version": "2.5.3",
  "timestamp": 1625591400,
  "lat": 59.4123, "lon": 5.2456,
  "temp": 12.5, "battery": 3.92,
  "wave": { "height": 0.45, "period": 4.2, "direction": "N/A", "power": 2.1 },
  "alerts": { "anchorDrift": false, "chargingIssue": false, ... },
  "rtc": { "waterTemp": 12.3 },
  "net": { "operator": "Telenor", "apn": "...", "ip": "...", "signal": 18 },
  "hours_to_sleep": 2, "next_wake_utc": 1625598600
}
```

## Next Steps (Priority Order)

1. **Consolidate databases** — Decide: Keep SQLite or migrate to PostgreSQL?
   - **Recommended:** Migrate to PostgreSQL (for Node.js integration)
   - **Action:** Write migration script to transfer 21 test records
2. **Design Node.js schema** — Create migrations for `buoys` and `measurements` tables
3. **Implement Express API** — `/upload` endpoint compatible with FastAPI contract
4. **Data validation** — Validate incoming payloads against schema rules
5. **Alert processing** — Background job to detect anomalies
6. **Write tests** — Unit + integration test suite
7. **Gradual migration** — Run Node.js alongside FastAPI, test with real buoys
8. **Deploy & sunset FastAPI** — Once Node.js proves stable

## Team & Responsibilities

- **Development:** Claude Code (this session)
- **Review:** (TBD)
- **Deployment:** (TBD)

## 🔑 Infrastructure Credentials (Claude Code Memory)

**IMPORTANT:** Credentials are stored in `.claude/credentials.json` (git-ignored, local only) for Claude Code persistence across sessions.

### Database Access
- **Host:** 192.168.140.7 (Raspberry Pi)
- **Username:** playbuoyadmin
- **Database:** playbuoy
- **Connection string:** `postgresql://playbuoyadmin:<password>@192.168.140.7:5432/playbuoy`

### API Authentication
- **X-API-Key:** super-secret-key-123 (for buoy uploads)

### External Services
- **Cloudflare API Key:** Available in `.claude/credentials.json` for DNS management

**Reference:** See `.claude/credentials.json` for all credentials. Regenerate and update this file if credentials are ever exposed.

## References

- PlayBuoy Hardware Spec: `docs/buoy.md`
- API Contract: `/upload` endpoint, see `docs/buoy.md` for payload format
- Example Payload: See `docs/buoy.md` for complete JSON structure
- Infrastructure Setup: `docs/setup.md`
- Credentials (local, git-ignored): `.claude/credentials.json`
