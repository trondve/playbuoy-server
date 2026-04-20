# PlayBuoy Incremental Upgrade Path

**Strategy:** Enhance existing FastAPI/SQLite, gradually add missing payload fields  
**Timeline:** Phase-based evolution, no breaking changes  
**Goal:** Support full buoy.md specification without major rewrites

---

## Phase 1: Foundation (Current State)

### Current SQLite Schema
The `data` table already captures these core fields:

| Category | Fields | Status |
|----------|--------|--------|
| **Device Identity** | node_id, firmware_version | ✅ |
| **Location** | latitude, longitude | ✅ |
| **Temperature** | water_temperature | ⚠️ Missing: temp_valid, temp_trend |
| **Battery** | battery_voltage | ⚠️ Missing: battery_percent, battery_change_since_last |
| **Wave Data** | wave_height, wave_period, wave_direction, wave_power | ✅ |
| **Network** | net_operator, net_apn, net_ip, net_signal | ✅ |
| **RTC** | rtc_water_temp | ⚠️ Missing: other RTC fields |
| **Alerts** | alert_anchor_drift, alert_charging_issue, alert_temp_spike, alert_over_temp, alert_upload_failed | ✅ |
| **Sleep Schedule** | hours_to_sleep, next_wake_utc | ✅ |
| **Diagnostics** | uptime, reset_reason | ✅ |
| **Tide** | tide_current_height | ✅ (custom) |

### Missing Fields (Phase 2+)

| Field | Type | Category | Priority | Notes |
|-------|------|----------|----------|-------|
| `battery_percent` | INT | Battery | HIGH | SoC percentage (0-100) |
| `battery_change_since_last` | FLOAT | Battery | HIGH | Delta from previous cycle |
| `temp_valid` | BOOL | Temperature | MEDIUM | Sensor health flag |
| `temp_trend` | FLOAT | Temperature | MEDIUM | 5-cycle moving average delta |
| `buoy_tilt` | FLOAT | Buoy Health | MEDIUM | Physical tilt angle (degrees) |
| `buoy_accel_rms` | FLOAT | Buoy Health | MEDIUM | RMS acceleration (m/s²) |
| `gps_hdop` | FLOAT | GPS | MEDIUM | Horizontal dilution of precision |
| `gps_ttf` | INT | GPS | MEDIUM | Time-to-fix (seconds) |
| `boot_count` | INT | Device | LOW | Cycle counter |
| `name` | VARCHAR | Device | LOW | Buoy display name (already in code) |
| `altitude_gps` | FLOAT | Location | LOW | GPS elevation |
| `accuracy_gps` | FLOAT | Location | LOW | GPS accuracy (CEP) |

---

## Phase 1→2 Transition: Add Missing Columns

### SQLite Migration Strategy

Run **one migration at a time**, test, then deploy to production.

#### Migration 1.1: Add Battery Percent & Change (PRIORITY: HIGH)
```sql
-- This is the single most important field from buoys
ALTER TABLE data ADD COLUMN battery_percent INTEGER DEFAULT NULL;
ALTER TABLE data ADD COLUMN battery_change_since_last REAL DEFAULT NULL;

-- Backfill from existing records (if possible)
-- If buoy sends battery_percent, extract from payload archives
```

#### Migration 1.2: Add GPS Quality Metrics (PRIORITY: MEDIUM)
```sql
ALTER TABLE data ADD COLUMN gps_hdop REAL DEFAULT NULL;
ALTER TABLE data ADD COLUMN gps_ttf INTEGER DEFAULT NULL;
```

#### Migration 1.3: Add Temperature Metadata (PRIORITY: MEDIUM)
```sql
ALTER TABLE data ADD COLUMN temp_valid BOOLEAN DEFAULT NULL;
ALTER TABLE data ADD COLUMN temp_trend REAL DEFAULT NULL;
```

#### Migration 1.4: Add Buoy Health Diagnostics (PRIORITY: MEDIUM)
```sql
ALTER TABLE data ADD COLUMN buoy_tilt REAL DEFAULT NULL;
ALTER TABLE data ADD COLUMN buoy_accel_rms REAL DEFAULT NULL;
```

#### Migration 1.5: Add Device Diagnostics (PRIORITY: LOW)
```sql
ALTER TABLE data ADD COLUMN boot_count INTEGER DEFAULT NULL;
ALTER TABLE data ADD COLUMN altitude_gps REAL DEFAULT NULL;
ALTER TABLE data ADD COLUMN accuracy_gps REAL DEFAULT NULL;
```

---

## Phase 2: Enhanced API Models

### Update Pydantic Models in `main.py`

Extend existing models to accept all new fields without breaking existing payloads:

```python
# Add these to WaveModel, RtcModel, etc.

class BuoyModel(BaseModel):
    tilt: Optional[float] = None
    accel_rms: Optional[float] = None

class GpsModel(BaseModel):
    hdop: Optional[float] = None
    ttf: Optional[int] = None

# Update UploadModel
class UploadModel(BaseModel):
    # ... existing fields ...
    
    # NEW: Battery metrics (HIGH PRIORITY)
    battery_percent: Optional[int] = None
    battery_change_since_last: Optional[float] = None
    
    # NEW: Temperature metadata (MEDIUM)
    temp_valid: Optional[bool] = None
    temp_trend: Optional[float] = None
    
    # NEW: Buoy diagnostics (MEDIUM)
    buoy: Optional[BuoyModel] = None
    
    # NEW: GPS quality (MEDIUM)
    gps: Optional[GpsModel] = None
    
    # NEW: Device counters (LOW)
    boot_count: Optional[int] = None
```

---

## Phase 3: Version Management

### How to Update Safely

**Step 1: Plan the change**
```
Decide which fields to add in this release
Estimate work: Schema migration + API model + tests = 1-2 days
```

**Step 2: Create a migration script**
```sql
-- File: migrations/001_add_battery_percent.sql
ALTER TABLE data ADD COLUMN battery_percent INTEGER DEFAULT NULL;
ALTER TABLE data ADD COLUMN battery_change_since_last REAL DEFAULT NULL;
```

**Step 3: Update requirements.txt if needed**
```bash
cd /home/playbuoyadmin/playbuoy-server
pip list --format=freeze > requirements.txt
```

**Step 4: Update FastAPI code**
- Add new fields to Pydantic models
- Add to INSERT statement
- No breaking changes to existing fields

**Step 5: Test locally**
```bash
# Test with enhanced payload
curl -X POST http://localhost:8000/upload \
  -H "X-API-Key: super-secret-key-123" \
  -H "Content-Type: application/json" \
  -d '{"nodeId": "test", "battery_percent": 75, ...}'
```

**Step 6: Deploy to production**
```bash
# SSH into Raspberry Pi
ssh playbuoyadmin@192.168.140.7

# Backup database before migration
cp playbuoy.db playbuoy-backup-$(date +%Y%m%d-%H%M%S).db

# Run migration
sqlite3 playbuoy.db < migrations/001_add_battery_percent.sql

# Restart FastAPI service
sudo systemctl restart playbuoy-api

# Verify
curl http://localhost:8000/health
```

---

## Dependency & Version Management

### Current Versions (Raspberry Pi)
| Package | Version | Status |
|---------|---------|--------|
| FastAPI | 0.115.14 | ✅ Current (as of 2026-04) |
| Uvicorn | 0.35.0 | ✅ Current |
| SQLAlchemy | 2.0.41 | ✅ Not used, can remove |
| Python | 3.11 | ✅ Current |

### How to Check for Updates
```bash
# SSH into Raspberry Pi
ssh playbuoyadmin@192.168.140.7
cd /home/playbuoyadmin/playbuoy-server

# Check outdated packages
source venv/bin/activate
pip list --outdated

# Check FastAPI release notes
# https://github.com/tiangolo/fastapi/releases
```

### How to Update Safely

**For FastAPI (minor updates):**
```bash
# 1. Test in dev environment first
pip install --upgrade fastapi==0.116.0  # next minor version

# 2. Run tests
pytest tests/

# 3. If tests pass, update requirements.txt
pip freeze > requirements.txt

# 4. Deploy to production
# (Commit changes, deploy to Raspberry Pi)
```

**For critical dependencies (security patches):**
```bash
# 1. Check security advisory
# 2. Update immediately if available
pip install --upgrade requests==2.x.x

# 3. Restart service
sudo systemctl restart playbuoy-api
```

**For major updates (breaking changes):**
- Read changelog carefully
- Test extensively in staging
- Plan migration with buoys (coordinate with field teams)
- Never deploy during active measurement season

---

## Potential Problems & Solutions

### Problem 1: New Fields Break Existing Buoys
**Scenario:** You add `battery_percent` as required, old buoys don't send it

**Solution:** Always make new fields OPTIONAL with `= None` defaults
```python
battery_percent: Optional[int] = None  # ✅ Backwards compatible
battery_percent: int  # ❌ Breaks old buoys
```

### Problem 2: Database Schema Mismatch
**Scenario:** FastAPI expects 30 columns, SQLite only has 25

**Solution:** Check before every deploy
```bash
# Verify schema matches code
sqlite3 playbuoy.db ".schema data"
# Count columns and cross-reference with main.py INSERT statement
```

### Problem 3: SQLite Performance Degradation
**Scenario:** After 10,000+ records, queries slow down

**Solution:** Add indexes strategically
```sql
CREATE INDEX IF NOT EXISTS idx_nodeid_timestamp 
ON data(lower(node_id), timestamp DESC);

CREATE INDEX IF NOT EXISTS idx_timestamp 
ON data(timestamp DESC);
```

### Problem 4: Accidental Data Loss
**Scenario:** Run wrong migration, overwrite production

**Solution:** Always backup first
```bash
# Before ANY migration
cp playbuoy.db playbuoy-backup-$(date +%Y%m%d-%H%M%S).db

# Verify backup exists
ls -lh playbuoy*.db
```

### Problem 5: Missing Environment Variables
**Scenario:** API key changes, FastAPI still uses old hardcoded value

**Solution:** Use `.env` file (recommended future improvement)
```bash
# Create /home/playbuoyadmin/playbuoy-server/.env
PLAYBUOY_API_KEY=super-secret-key-123
```

Then in `main.py`:
```python
from dotenv import load_dotenv
load_dotenv()
API_KEY = os.getenv("PLAYBUOY_API_KEY", "super-secret-key-123")
```

---

## Recommended Timeline

| Phase | Milestone | Timeline | Effort |
|-------|-----------|----------|--------|
| **0** | Current state (21 test records) | Complete | — |
| **1.1** | Add battery_percent, battery_change_since_last | Week 1 | 2 hours |
| **1.2** | Add GPS quality metrics (hdop, ttf) | Week 2 | 2 hours |
| **1.3** | Add temperature metadata (temp_valid, temp_trend) | Week 3 | 2 hours |
| **1.4** | Add buoy diagnostics (tilt, accel_rms) | Week 4 | 2 hours |
| **1.5** | Add device counters (boot_count, altitude) | Week 5 | 1 hour |
| **2.0** | Full buoy.md compliance achieved | End of month | 9 hours total |

---

## References

- Current FastAPI app: `/home/playbuoyadmin/playbuoy-server/main.py`
- SQLite database: `/home/playbuoyadmin/playbuoy-server/playbuoy.db`
- Full spec: `docs/buoy.md`
- Dependencies: `/home/playbuoyadmin/playbuoy-server/requirements.txt`
- Service: `/etc/systemd/system/playbuoy-api.service`
