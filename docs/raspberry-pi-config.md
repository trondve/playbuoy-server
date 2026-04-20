# PlayBuoy Raspberry Pi Configuration — Current State Analysis

**Date:** 2026-04-20  
**Status:** Initial infrastructure audit  
**Updated:** Based on SSH reconnaissance

## Infrastructure Summary

### Operating System
- **Device:** Raspberry Pi
- **OS:** Debian-based Linux
- **Storage:** 29GB total, 2.9GB used (11%)
- **Python Version:** 3.11

---

## PostgreSQL Database

### Status
- **Service:** `postgresql.service` (active, running since 13:34:09)
- **Version:** PostgreSQL 15
- **Config:** `/etc/postgresql/15/main/postgresql.conf`
- **Port:** 5432
- **Listen Address:** localhost (127.0.0.1 only — not network accessible)

### Database Structure
- **Database Name:** `playbuoy`
- **Database Owner:** `playbuoyuser` (⚠️ Not `playbuoyadmin`)
- **Encoding:** UTF-8, en_GB.UTF-8 locale

### Tables

#### `buoy_data` (Measurements)
```
Columns:
  - id (PRIMARY KEY, integer, auto-increment)
  - node_id (character varying) — Buoy identifier
  - firmware_version (character varying)
  - timestamp (timestamp without time zone)
  - latitude (double precision)
  - longitude (double precision)
  - altitude (double precision)
  - accuracy (double precision)
  - temperature_c (double precision) — Water temperature
  - battery_percent (double precision)
  - battery_voltage (double precision)
  - wave_height_m (double precision)
  - wave_period_s (double precision)
  - wave_direction (character varying)
  - wave_power (double precision)
  - tide (character varying)
  - alerts (JSON)

Indexes:
  - id (PRIMARY KEY, btree)
  - node_id (btree)
```

#### `alert_log` (Alert History)
```
Columns:
  - id (PRIMARY KEY, integer, auto-increment)
  - node_id (character varying)
  - timestamp (timestamp without time zone)
  - alert_type (character varying)
  - alert_payload (JSON)

Indexes:
  - id (PRIMARY KEY, btree)
  - node_id (btree)
```

### Measurement Statistics
*To be populated with:*
- Total measurement count
- Date range (first & latest measurement)
- Active buoys (distinct node_ids)

---

## FastAPI API Server

### Status
- **Service Name:** `playbuoy-api.service`
- **Status:** active (running)
- **Started:** Mon 2026-04-20 13:34:03 CEST (7h ago)
- **Process:** Uvicorn

### Running Instances
| PID | Binding | Status |
|-----|---------|--------|
| 494 | `0.0.0.0:8000` | All interfaces (external access) |
| 495 | `127.0.0.1:8000` | Localhost only (internal) |

**Note:** Two uvicorn processes running simultaneously — investigate if this is intentional or misconfiguration.

### Network Configuration
- **Port:** 8000 (HTTP, not HTTPS)
- **Protocol:** HTTP (over Cloudflare tunnel for HTTPS)
- **Network Access:** Currently listening on all interfaces

### Application Structure
- **Location:** `/home/playbuoyadmin/playbuoy-server/`
- **Owner:** `playbuoyadmin` user
- **Python Environment:** Virtual environment at `/venv/`

### Application Files
```
/home/playbuoyadmin/playbuoy-server/
├── main.py           — FastAPI application entry point
├── database.py       — Database connection & ORM models
├── models.py         — Pydantic/data models
├── requirements.txt  — Python dependencies
└── venv/             — Python 3.11 virtual environment
```

### Systemd Service Configuration
*Location:* `/etc/systemd/system/playbuoy-api.service`  
*Details:* To be reviewed

### Logs
- **Recent logs:** Application startup complete
- **Status:** No errors visible
- **Log location:** Via `journalctl -u playbuoy-api`

---

## Cloudflare Integration

### Tunnel
- **Process:** `cloudflared` (running)
- **Port:** 20241 (localhost only)
- **Purpose:** HTTPS tunnel to external DNS (playbuoyapi.no)

---

## Connectivity Analysis

### Database Accessibility
- ✅ PostgreSQL listening on `127.0.0.1:5432` (localhost)
- ✅ PostgreSQL listening on `[::1]:5432` (IPv6 localhost)
- ❌ **NOT** accessible from remote (no 0.0.0.0 binding)
- ⚠️ **Credentials Issue:** 
  - User told us: `playbuoyadmin` with password `@6Kv2pUQE2HoPZfT.PhozJVPcxFC`
  - Actual DB owner: `playbuoyuser`
  - Requires clarification

### API Accessibility
- ✅ FastAPI listening on `0.0.0.0:8000` (all interfaces)
- ✅ Cloudflare tunnel routing HTTPS traffic
- ⚠️ Two uvicorn instances running (investigate redundancy)

---

## Credentials & Authentication

### Known Credentials
| Service | User | Location | Status |
|---------|------|----------|--------|
| PostgreSQL | playbuoyuser | Local DB | ✅ Active |
| SSH | playbuoyadmin | Raspberry Pi | ✅ Active |
| API Key | super-secret-key-123 | FastAPI | ✅ Stored in project |
| Cloudflare | roJKZfZmQMLhALNDYgBVtnpbjRXt | API Key | ✅ Stored in project |

### ⚠️ Authentication Gaps
1. **PostgreSQL User Mismatch:** 
   - Expected: `playbuoyadmin`
   - Actual: `playbuoyuser`
   - Needs: Clarify remote vs. local access methods

2. **Database Access from Node.js Server:**
   - The FastAPI app uses `playbuoyuser` locally
   - Our Node.js server needs different credentials for remote access
   - Stored in `.claude/credentials.json` (user: `playbuoyadmin`)

---

## Pending Information

*Waiting for output from Raspberry Pi:*

1. ✅ Application code (`main.py`, `database.py`, `models.py`)
2. ✅ Dependencies (`requirements.txt`)
3. ✅ Systemd service configuration
4. ✅ Directory structure
5. ✅ Database measurement statistics
6. ✅ Git repository status
7. ✅ Environment variables (`.env`)

---

## Next Steps

Once additional data is provided:

1. **Document the FastAPI application architecture** — Routes, validation, error handling
2. **Validate schema alignment** — Compare with CLAUDE.md specifications
3. **Identify migration needs** — Bridge Python/FastAPI backend with Node.js implementation
4. **Update credentials management** — Clarify `playbuoyadmin` vs. `playbuoyuser` usage
5. **Review current API implementation** — Check if `/upload` endpoint exists and how it works
6. **Plan data migration strategy** — Ensure existing measurements are preserved

---

## References

- Database: `playbuoy` on `192.168.140.7:5432`
- API: Listening on `0.0.0.0:8000`
- Application: `/home/playbuoyadmin/playbuoy-server/`
- Credentials stored: `.claude/credentials.json`
