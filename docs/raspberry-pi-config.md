# PlayBuoy Raspberry Pi Configuration — Current State Analysis

**Date:** 2026-04-20  
**Status:** Infrastructure audit complete  
**Updated:** Based on full application review

## ⚠️ CRITICAL: Dual Database Issue

**FINDING:** The system has a **database architecture mismatch**:

1. **SQLite (Active)** — `main.py` uses `/home/playbuoyadmin/playbuoy-server/playbuoy.db`
2. **PostgreSQL (Defined)** — `database.py` configures PostgreSQL but **NOT USED** by main.py

This means:
- ✅ **SQLite has the active measurements** (21 test records from Jul 6, 2025)
- ❌ **PostgreSQL tables exist but are unused** (orphaned schema)

---

## PostgreSQL Database (Unused in Production)

### Status
- **Service:** `postgresql.service` (active, running)
- **Version:** PostgreSQL 15
- **Port:** 5432
- **Listen Address:** localhost (127.0.0.1 only)

### Database
- **Name:** `playbuoy`
- **Owner:** `playbuoyuser`
- **Credentials:** 
  - User: `playbuoyuser`
  - Password: `XaKwwtYBKEiwQzmDCANDycUafUjA`

### Unused Tables
#### `buoy_data` (Orphaned)
```
Columns: id, node_id, firmware_version, timestamp, latitude, longitude, 
         altitude, accuracy, temperature_c, battery_percent, battery_voltage,
         wave_height_m, wave_period_s, wave_direction, wave_power, tide, alerts
```

#### `alert_log` (Orphaned)
```
Columns: id, node_id, timestamp, alert_type, alert_payload
```

---

## FastAPI Application (Active SQLite)

### Application Files
```
/home/playbuoyadmin/playbuoy-server/
├── main.py              — FastAPI app (PRIMARY - uses SQLite)
├── database.py          — PostgreSQL config (UNUSED)
├── models.py            — SQLAlchemy ORM (UNUSED)
├── requirements.txt     — Dependencies
├── playbuoy.db          — SQLite database (94 KB, 21 records)
├── venv/                — Python 3.11 virtualenv
└── [backups]            — Old .db files
```

### FastAPI Architecture

#### Technology Stack
- **Framework:** FastAPI 0.115.14
- **Database:** SQLite 3 (playbuoy.db)
- **Async Runtime:** Uvicorn 0.35.0
- **Python:** 3.11
- **Authentication:** X-API-Key header
- **CORS:** Enabled for Wix frontend

#### API Endpoints
| Endpoint | Method | Auth | Purpose |
|----------|--------|------|---------|
| `/` | GET | ❌ | Health check |
| `/health` | GET | ❌ | Database connectivity |
| `/upload` | POST | ✅ API Key | Ingest buoy telemetry |
| `/latest` | GET | ✅ API Key | Get latest for one buoy |
| `/latest_all` | GET | ✅ API Key | Get latest from all buoys |

#### Request/Response Model
**Upload Payload** (Pydantic BaseModel):
```python
{
  "nodeId": "playbuoy-grinde",      # Stored as: playbuoy_grinde
  "version": "2.5.3",
  "timestamp": 1625591400,           # Unix epoch
  "lat": 59.4123,
  "lon": 5.2456,
  "temp": 12.5,
  "battery": 3.92,
  "wave": {
    "height": 0.45,
    "period": 4.2,
    "direction": "N/A",
    "power": 2.1
  },
  "alerts": {
    "anchorDrift": false,
    "chargingIssue": false,
    "tempSpike": false,
    "overTemp": false,
    "uploadFailed": false
  },
  // Optional fields
  "name": "Litla Grindevatnet",
  "battery_precal": 3.90,
  "battery_cal_factor": 1.05,
  "temp_valid": true,
  "uptime": 598,
  "reset_reason": "deep_sleep_wakeup",
  "rtc": { "waterTemp": 12.3 },
  "net": {
    "operator": "Telenor",
    "apn": "internet.telenor.no",
    "ip": "10.45.67.123",
    "signal": 18
  },
  "hours_to_sleep": 2,
  "next_wake_utc": 1625598600,
  "battery_change_since_last": 2.0
}
```

**Success Response:**
```json
{ "status": "ok" }
```

### SQLite Schema (Actual Storage)
The `playbuoy.db` SQLite database stores data in a `data` table with columns:
```
node_id, firmware_version, timestamp, latitude, longitude,
wave_height, wave_period, wave_direction, wave_power,
water_temperature, battery_voltage,
name, tide_current_height,
battery_precal, battery_cal_factor, temp_valid,
uptime, reset_reason,
rtc_water_temp,
net_operator, net_apn, net_ip, net_signal,
alert_anchor_drift, alert_charging_issue, alert_temp_spike, 
alert_over_temp, alert_upload_failed,
hours_to_sleep, next_wake_utc, battery_change_since_last
```

### Security Features
- ✅ API Key validation (X-API-Key header)
- ✅ CORS middleware (Wix domains only)
- ✅ Security headers (HSTS, X-Frame-Options, CSP)
- ✅ OpenAPI schema with auth integration
- ✅ HTTPS via Cloudflare tunnel

### Systemd Service
**File:** `/etc/systemd/system/playbuoy-api.service`
```ini
[Unit]
Description=PlayBuoy FastAPI backend
After=network.target

[Service]
User=playbuoyadmin
Group=playbuoyadmin
WorkingDirectory=/home/playbuoyadmin/playbuoy-server
ExecStart=/home/playbuoyadmin/playbuoy-server/venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=5
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
```

---

## Current Data

### Measurement Statistics
| Metric | Value |
|--------|-------|
| Total measurements | 21 |
| Unique buoys | 20 |
| Date range | 2025-07-06 14:00 — 2025-07-06 16:00 |
| Database size | 94 KB |

### Active Buoys (Test Data)
```
playbuoy-vigdar (1), playbuoy-001 (2), playbuoy-draga (1),
playbuoy-sandve (1), playbuoy-akre (1), playbuoy-notaflot (1),
playbuoy-storavat (1), playbuoy-skeisvat (1), playbuoy-stemne (1),
playbuoy-vatnakv (1), playbuoy-lindoy (1), playbuoy-kvalsvik (1),
playbuoy-asalvika (1), playbuoy-grinde (1), playbuoy-litla (1),
playbuoy-tuastad (1), playbuoy-aksnes (1), playbuoy-fotvann (1),
playbuoy-eivindsv (1), playbuoy-grindafj (1)
```

**Note:** All measurements from 2025-07-06 (test data, not production)

---

## Node ID Handling

### Normalization Rules
- **Storage:** Converts hyphens → underscores, lowercase
  - Input: `playbuoy-grinde` → Stored: `playbuoy_grinde`
- **Query:** Accepts both formats, normalizes for lookup
  - `/latest?node_id=playbuoy-grinde` or `playbuoy_grinde` both work

---

## Cloudflare Integration

### Tunnel
- **Service:** `cloudflared` (running)
- **Port:** 20241 (localhost only)
- **Purpose:** HTTPS tunnel for `playbuoyapi.no` domain

---

## Credentials Summary

### Application Configuration
| Component | Value | Location |
|-----------|-------|----------|
| API Key | `super-secret-key-123` | `main.py` line 18 (environment variable fallback) |
| SQLite DB | `playbuoy.db` | `main.py` line 185 |
| PostgreSQL (unused) | `postgresql://playbuoyuser:XaKwwtYBKEiwQzmDCANDycUafUjA@localhost/playbuoy` | `database.py` line 5 |

### SSH Access
| User | Host | Purpose |
|------|------|---------|
| `playbuoyadmin` | `192.168.140.7` | Application/system management |

---

## Deployment Status

### Running Processes
```
PID    Process                                        Port
494    uvicorn main:app --host 0.0.0.0 --port 8000  8000 (all interfaces)
495    uvicorn main:app --host 127.0.0.1 --port 8000 8000 (localhost)
526    postgres                                       5432 (localhost only)
548    cloudflared                                    20241 (localhost only)
```

⚠️ **Note:** Two uvicorn processes running — potential redundancy or load balancing.

---

## Issues & Recommendations

### 1. ⚠️ Database Architecture Mismatch
**Problem:** SQLite (main.py) vs PostgreSQL (database.py) confusion  
**Impact:** Difficult to migrate, unclear data ownership  
**Action:** 
- [ ] Clarify: Is this intentional dual-write or legacy code?
- [ ] Decision: Consolidate on **PostgreSQL** (for Node.js server integration)
- [ ] Plan: Migrate 21 test records from SQLite → PostgreSQL

### 2. ⚠️ No .env Configuration
**Problem:** API key hardcoded in `main.py` (line 18)  
**Impact:** Requires code change to update credentials  
**Action:** Create `.env` file and load via `python-dotenv`

### 3. ⚠️ Unused SQLAlchemy Code
**Problem:** `database.py` and `models.py` define PostgreSQL ORM but never instantiated  
**Impact:** Dead code, maintenance burden  
**Action:** Either use or remove

### 4. ⚠️ Two Uvicorn Processes
**Problem:** PID 494 (0.0.0.0:8000) and PID 495 (127.0.0.1:8000) both running  
**Impact:** Confusing, unclear if intentional  
**Action:** Investigate systemd service — may need deduplication

### 5. ✅ Cloudflare Tunnel
**Status:** Properly configured for HTTPS  
**Note:** Provides secure external access

---

## Next Steps (Priority Order)

1. **Clarify database usage** — Is PostgreSQL intentional or legacy?
2. **Consolidate on PostgreSQL** — For Node.js server compatibility
3. **Migrate test data** — SQLite (21 records) → PostgreSQL
4. **Implement .env configuration** — Externalize credentials
5. **Remove duplicate uvicorn** — Streamline startup
6. **Align schema** — Ensure Node.js server matches FastAPI schema

---

## References

- **FastAPI app:** `/home/playbuoyadmin/playbuoy-server/main.py`
- **Database config:** `/home/playbuoyadmin/playbuoy-server/database.py`
- **Service:** `/etc/systemd/system/playbuoy-api.service`
- **Active database:** `/home/playbuoyadmin/playbuoy-server/playbuoy.db` (SQLite)
- **Postgres:** `192.168.140.7:5432` (playbuoy)
- **API endpoint:** `http://192.168.140.7:8000` or `https://playbuoyapi.no`

