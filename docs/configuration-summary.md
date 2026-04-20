# PlayBuoy Configuration Summary

**Last Updated:** 2026-04-20  
**Environment:** Raspberry Pi (192.168.140.7)  
**Status:** ✅ Production Ready

---

## Quick Reference

| Component | Value | Status |
|-----------|-------|--------|
| **API Endpoint** | http://192.168.140.7:8000 | ✅ Active |
| **Database** | SQLite (playbuoy.db) | ✅ 317 records |
| **Service** | playbuoy-api (systemd) | ✅ Running |
| **Python Version** | 3.x (venv) | ✅ Updated |
| **Uptime** | Auto-restart enabled | ✅ Protected |
| **Memory Limit** | 256MB | ✅ Safe |
| **Authentication** | X-API-Key header | ✅ Required |
| **CORS** | Wix frontend allowed | ✅ Configured |

---

## Architecture

```
┌─────────────────────────────────────────────────┐
│         Raspberry Pi (192.168.140.7)            │
├─────────────────────────────────────────────────┤
│                                                 │
│  FastAPI Application (main.py)                  │
│  ├─ POST /upload — Accept buoy telemetry       │
│  ├─ GET /latest — Latest measurement           │
│  ├─ GET /latest_all — All latest               │
│  └─ GET /health — Status check                 │
│                                                 │
│  ↓                                              │
│                                                 │
│  Uvicorn ASGI Server                           │
│  └─ Port 8000, 0.0.0.0                         │
│                                                 │
│  ↓                                              │
│                                                 │
│  SQLite Database (playbuoy.db)                 │
│  └─ Table: data (39 columns, 317 records)      │
│                                                 │
│  ↓                                              │
│                                                 │
│  Systemd Service (playbuoy-api.service)        │
│  └─ Auto-restart, memory protection, logging   │
│                                                 │
└─────────────────────────────────────────────────┘
```

---

## Deployment Details

### Python Environment
- **Type:** Virtual environment (venv)
- **Location:** `/home/playbuoyadmin/playbuoy-server/venv/`
- **Python:** 3.9+
- **Packages:** 23 total (see requirements.txt)
- **Last Updated:** 2026-04-20

### FastAPI Application
- **Framework:** FastAPI 0.115.14
- **Server:** Uvicorn 0.35.0
- **File:** `/home/playbuoyadmin/playbuoy-server/main.py`
- **Models:** Pydantic v2 (validation & serialization)

### Database
- **Engine:** SQLite 3
- **File:** `/home/playbuoyadmin/playbuoy-server/playbuoy.db`
- **Size:** ~100 KB (317 records)
- **Schema:** 39 columns, 2 indexes
- **Retention:** Unlimited (manual purge required)

### Service Management
- **Init System:** systemd
- **Service File:** `/etc/systemd/system/playbuoy-api.service`
- **User:** playbuoyadmin
- **Auto-start:** Yes (multi-user.target)
- **Restart Policy:** on-failure (3 tries in 60s)
- **Memory Limit:** 256MB (OOM protection)
- **Logging:** systemd journal (journalctl)

---

## API Specification

### Base URL
```
http://192.168.140.7:8000
```

### Authentication
- **Header:** `X-API-Key`
- **Value:** `super-secret-key-123`
- **Required For:** `/upload`, `/latest`, `/latest_all`
- **Security:** HTTPS recommended for production

### Endpoints

#### 1. POST /upload
**Upload buoy telemetry**

```bash
curl -X POST http://192.168.140.7:8000/upload \
  -H "X-API-Key: super-secret-key-123" \
  -H "Content-Type: application/json" \
  -d '{
    "nodeId": "playbuoy_grinde",
    "version": "2.5.3",
    "timestamp": 1713638553,
    "lat": 59.4123,
    "lon": 5.2456,
    "temp": 12.5,
    "battery": 3.92,
    "wave": {...},
    "alerts": {...},
    ...
  }'
```

**Response:** `{"status": "ok"}`

---

#### 2. GET /latest
**Get latest measurement for a buoy**

```bash
curl -H "X-API-Key: super-secret-key-123" \
  "http://192.168.140.7:8000/latest?node_id=playbuoy_grinde"
```

**Response:** Array with latest record

---

#### 3. GET /latest_all
**Get latest measurement for all buoys**

```bash
curl -H "X-API-Key: super-secret-key-123" \
  "http://192.168.140.7:8000/latest_all"
```

**Response:** Array of all latest records, sorted by temperature (descending)

---

#### 4. GET /health
**Check API health**

```bash
curl http://192.168.140.7:8000/health
```

**Response:** `{"ok": true}` if database accessible

---

## Database Schema

### Table: data (39 columns)

**Primary Key:**
- `id` — Auto-incrementing record ID

**Identifiers:**
- `node_id` — Buoy identifier (TEXT, normalized to lowercase)
- `firmware_version` — Firmware version (TEXT)
- `timestamp` — Unix timestamp (INTEGER, seconds UTC)

**Location:**
- `latitude` — GPS latitude (REAL)
- `longitude` — GPS longitude (REAL)
- `altitude_gps` — GPS altitude (REAL, optional)
- `accuracy_gps` — GPS accuracy (REAL, optional)

**Wave Data:**
- `wave_height` — Significant wave height (REAL, meters)
- `wave_period` — Peak period (REAL, seconds)
- `wave_direction` — Direction (TEXT, e.g., "N/A", "NW")
- `wave_power` — Spectral power (REAL, kW/m)

**Temperature & Battery:**
- `water_temperature` — Water temperature (REAL, °C)
- `battery_voltage` — Battery voltage (REAL, V)
- `battery_percent` — Battery SoC (INTEGER, 0-100%)
- `battery_precal` — Pre-calibration value (REAL, optional)
- `battery_cal_factor` — Calibration factor (REAL, optional)
- `battery_change_since_last` — Change since last (REAL, optional)

**Sensors & Diagnostics:**
- `rtc_water_temp` — RTC water temperature (REAL, optional)
- `buoy_tilt` — Physical tilt (REAL, degrees)
- `buoy_accel_rms` — Acceleration RMS (REAL, optional)
- `temp_valid` — Temperature sensor valid (INTEGER, 0/1)
- `temp_trend` — Temperature trend (REAL, °C/hour)
- `boot_count` — Boot cycles (INTEGER, optional)

**Network & Communications:**
- `net_operator` — Mobile operator (TEXT, optional)
- `net_apn` — APN (TEXT, optional)
- `net_ip` — Assigned IP (TEXT, optional)
- `net_signal` — Signal strength (INTEGER, 0-31 RSRP)
- `gps_hdop` — Horizontal dilution (REAL, optional)
- `gps_ttf` — Time-to-fix (INTEGER, seconds, optional)

**Operations:**
- `tide_current_height` — Tide height (REAL, optional)
- `hours_to_sleep` — Sleep duration (INTEGER, optional)
- `next_wake_utc` — Next wake time (TEXT, ISO format)
- `uptime` — Device uptime (INTEGER, seconds)
- `reset_reason` — Last reset cause (TEXT, optional)
- `name` — Buoy display name (TEXT, optional)

**Alerts:**
- `alert_anchor_drift` — Drift detected (INTEGER, 0/1)
- `alert_charging_issue` — Charging problem (INTEGER, 0/1)
- `alert_temp_spike` — Temperature anomaly (INTEGER, 0/1)
- `alert_over_temp` — Over-temperature (INTEGER, 0/1)
- `alert_upload_failed` — Upload retry pending (INTEGER, 0/1)

**Indexes:**
```sql
CREATE INDEX idx_data_node_ts ON data(lower(node_id), timestamp);
CREATE INDEX idx_data_ts ON data(timestamp);
```

---

## Python Dependencies

**Total:** 23 packages (see requirements.txt)

### Core Framework
- fastapi==0.115.14
- starlette==0.46.2
- uvicorn==0.35.0
- pydantic==2.11.7
- pydantic_core==2.33.2

### Database
- aiosqlite==0.21.0
- SQLAlchemy==2.0.41

### Utilities
- python-dotenv==1.1.1
- PyYAML==6.0.2
- click==8.2.1
- typing_extensions==4.14.1
- typing-inspection==0.4.1

### Performance
- uvloop==0.21.0
- httptools==0.6.4
- watchfiles==1.1.0
- websockets==15.0.1

### Standards
- anyio==4.9.0
- sniffio==1.3.1
- h11==0.16.0
- idna==3.10
- annotated-types==0.7.0
- greenlet==3.2.3

---

## Monitoring & Maintenance

### Health Checks
- **Automated:** Systemd monitors service every 5 seconds
- **Manual:** `curl http://192.168.140.7:8000/health`
- **Alerting:** Configure nagios, Zabbix, or similar for production

### Backups
- **Database:** Manual timestamped backups recommended
  ```bash
  cp playbuoy.db playbuoy-backup-$(date +%Y%m%d-%H%M%S).db
  ```
- **Service:** Backed up in GitHub
- **Logs:** Systemd journal (retention depends on disk)

### Resource Usage
- **Memory:** Limited to 256MB (systemd enforcement)
- **CPU:** Single-threaded Uvicorn (non-blocking)
- **Disk:** SQLite grows ~1MB per year at current load

### Update Cycle
- **System Packages:** Monthly (apt-get upgrade)
- **Python Packages:** Quarterly or on security advisory
- **FastAPI:** Track releases for security patches

---

## Security

### API Security
- ✅ X-API-Key authentication (all write/read endpoints)
- ✅ Input validation (Pydantic models)
- ✅ CORS configured (Wix frontend only)
- ✅ Security headers (HSTS, X-Frame-Options, CSP, etc.)
- ⚠️ HTTP only (use reverse proxy for HTTPS in production)

### Database Security
- ✅ Parameterized queries (SQL injection prevention)
- ✅ Default NULL for optional fields
- ✅ Timestamp validation (reject >24h clock skew)
- ⚠️ SQLite not encrypted (add encryption layer if needed)

### System Security
- ✅ Service runs as non-root (playbuoyadmin user)
- ✅ Memory limit enforced (prevents DoS via memory exhaustion)
- ✅ Restart limits (prevents crash loops)
- ⚠️ API key in code (consider environment variables)

---

## Documentation Files

| File | Purpose |
|------|---------|
| `CLAUDE.md` | Project context and strategy |
| `docs/buoy.md` | Hardware & payload specification |
| `docs/how-to-add-fields.md` | Adding new fields to API & database |
| `docs/remote-development.md` | SSH deployment guide |
| `docs/command-cheatsheet.md` | Common commands reference |
| `docs/database-schema.md` | Database schema details |
| `docs/service-configuration.md` | Service setup details |
| `docs/configuration-summary.md` | This file |

---

## Quick Start for New Developers

1. **SSH to Pi:**
   ```bash
   ssh playbuoyadmin@192.168.140.7
   ```

2. **Check service:**
   ```bash
   sudo systemctl status playbuoy-api
   ```

3. **View logs:**
   ```bash
   sudo journalctl -u playbuoy-api -f
   ```

4. **Test API:**
   ```bash
   curl -H "X-API-Key: super-secret-key-123" http://localhost:8000/latest_all
   ```

5. **Query database:**
   ```bash
   sqlite3 playbuoy.db "SELECT COUNT(*) FROM data;"
   ```

---

## Emergency Procedures

### Service Won't Start
```bash
sudo systemctl status playbuoy-api
sudo journalctl -u playbuoy-api -n 50
# Fix issue in main.py, then:
sudo systemctl restart playbuoy-api
```

### Port 8000 Blocked
```bash
sudo lsof -i :8000
sudo kill -9 <PID>
sudo systemctl restart playbuoy-api
```

### Database Corrupted
```bash
# Restore from backup
cp playbuoy-backup-20260420.db playbuoy.db
sudo systemctl restart playbuoy-api
```

### Memory Limit Hit
```bash
# Service will be killed by systemd
# Check logs for memory leak:
sudo journalctl -u playbuoy-api | grep "Killed"
# Restart and monitor:
sudo systemctl restart playbuoy-api
ps aux | grep uvicorn
```

---

## References

- **GitHub:** https://github.com/trondve/playbuoy-server
- **API Docs:** /docs endpoint (Swagger UI)
- **FastAPI:** https://fastapi.tiangolo.com/
- **SQLite:** https://www.sqlite.org/
- **Systemd:** https://www.freedesktop.org/software/systemd/

---

**For questions or updates, see CLAUDE.md or contact the maintainers.**
