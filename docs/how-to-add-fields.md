# How to Add New Payload Fields to FastAPI

**Quick Guide:** Step-by-step instructions to add a new field to the PlayBuoy API

---

## Example: Adding `battery_percent` Field

### Step 1: Update SQLite Schema

**SSH into Raspberry Pi:**
```bash
ssh playbuoyadmin@192.168.140.7
cd /home/playbuoyadmin/playbuoy-server
```

**Backup the database:**
```bash
cp playbuoy.db playbuoy-backup-$(date +%Y%m%d-%H%M%S).db
```

**Add the column:**
```bash
sqlite3 playbuoy.db "ALTER TABLE data ADD COLUMN battery_percent INTEGER DEFAULT NULL;"
```

**Verify:**
```bash
sqlite3 playbuoy.db "PRAGMA table_info(data);" | grep battery_percent
```

### Step 2: Update FastAPI Models

**Edit `main.py` in the UploadModel class:**

```python
class UploadModel(BaseModel):
    nodeId: str
    version: str
    timestamp: int
    lat: float
    lon: float
    temp: float
    battery: float
    wave: WaveModel
    alerts: AlertsModel
    
    # ... existing fields ...
    
    # NEW FIELD
    battery_percent: Optional[int] = None  # Add this line
    battery_change_since_last: Optional[float] = None
```

### Step 3: Update INSERT Statement

**Find the INSERT statement in the `/upload` route:**

```python
@app.post("/upload")
def upload_data(data: UploadModel, _: str = Security(verify_api_key)):
    # ... validation code ...
    
    # Column list (ALL except auto-increment id)
    cols: List[str] = [
        "node_id", "firmware_version", "timestamp",
        "latitude", "longitude",
        "wave_height", "wave_period", "wave_direction", "wave_power",
        "water_temperature", "battery_voltage",
        "name", "tide_current_height",
        "battery_precal", "battery_cal_factor", "temp_valid",
        "uptime", "reset_reason",
        "rtc_water_temp",
        "net_operator", "net_apn", "net_ip", "net_signal",
        "alert_anchor_drift", "alert_charging_issue", "alert_temp_spike", "alert_over_temp", "alert_upload_failed",
        "hours_to_sleep", "next_wake_utc", "battery_change_since_last",
        "battery_percent",  # ADD THIS LINE
    ]
```

**And in the values tuple:**

```python
    values: Tuple = (
        normalized_node,
        data.version,
        int(data.timestamp),
        float(data.lat),
        float(data.lon),

        float(wave.height or 0),
        float(wave.period or 0),
        (wave.direction or "N/A"),
        float(wave.power or 0),

        float(data.temp),
        float(data.battery),

        data.name,
        None if tide.current_height is None else float(tide.current_height),

        None if data.battery_precal is None else float(data.battery_precal),
        None if data.battery_cal_factor is None else float(data.battery_cal_factor),
        b2i(data.temp_valid),

        None if data.uptime is None else int(data.uptime),
        data.reset_reason,

        None if rtc.waterTemp is None else float(rtc.waterTemp),

        net.operator,
        net.apn,
        net.ip,
        None if net.signal is None else int(net.signal),

        b2i(alerts.anchorDrift),
        b2i(alerts.chargingIssue),
        b2i(alerts.tempSpike),
        b2i(alerts.overTemp),
        b2i(alerts.uploadFailed),

        None if data.hours_to_sleep is None else int(data.hours_to_sleep),
        None if data.next_wake_utc is None else int(data.next_wake_utc),
        None if data.battery_change_since_last is None else float(data.battery_change_since_last),
        None if data.battery_percent is None else int(data.battery_percent),  # ADD THIS LINE
    )
```

**Critical:** The order of values MUST match the order of cols.

### Step 4: Test Locally (Optional)

**If you have Python environment locally:**
```bash
# Create test payload with new field
curl -X POST http://localhost:8000/upload \
  -H "X-API-Key: super-secret-key-123" \
  -H "Content-Type: application/json" \
  -d '{
    "nodeId": "test-buoy",
    "version": "2.5.3",
    "timestamp": 1625591400,
    "lat": 59.4123,
    "lon": 5.2456,
    "temp": 12.5,
    "battery": 3.92,
    "battery_percent": 65,
    "wave": {"height": 0.45, "period": 4.2, "direction": "N/A", "power": 2.1},
    "alerts": {"anchorDrift": false, "chargingIssue": false, "tempSpike": false, "overTemp": false, "uploadFailed": false}
  }'
```

### Step 5: Deploy to Raspberry Pi

**SSH into Raspberry Pi:**
```bash
ssh playbuoyadmin@192.168.140.7
cd /home/playbuoyadmin/playbuoy-server
```

**Stop the API service:**
```bash
sudo systemctl stop playbuoy-api
```

**Update the code:**
```bash
# You can either:
# Option A: Edit main.py directly in nano
nano main.py

# Or Option B: Copy updated file from your dev machine
# On your dev machine:
# scp main.py playbuoyadmin@192.168.140.7:/home/playbuoyadmin/playbuoy-server/
```

**Restart the service:**
```bash
sudo systemctl start playbuoy-api
```

**Verify it's running:**
```bash
curl http://localhost:8000/health
# Should return: {"ok": true}
```

**Check logs:**
```bash
sudo journalctl -u playbuoy-api -n 20
# Should show: "Application startup complete"
```

### Step 6: Verify in Database

**Check that new data was inserted:**
```bash
sqlite3 playbuoy.db "SELECT node_id, timestamp, battery_percent FROM data ORDER BY timestamp DESC LIMIT 1;"
```

---

## Checklist for Adding Any New Field

- [ ] Add column to SQLite schema (with `DEFAULT NULL`)
- [ ] Add field to Pydantic model (as `Optional[type] = None`)
- [ ] Add to `cols` list in INSERT statement
- [ ] Add to `values` tuple in same order as cols
- [ ] Backup database before deploying
- [ ] Test with curl or client
- [ ] Restart service
- [ ] Verify data appears in database
- [ ] Check logs for errors

---

## Common Mistakes

### ❌ Mistake 1: Column order mismatch
```python
cols = [..., "battery_percent", "temp_trend"]
values = (..., temp_trend_value, battery_percent_value)  # WRONG ORDER!
```
**Fix:** Ensure `values` tuple matches `cols` order exactly.

### ❌ Mistake 2: Forgetting Optional and None
```python
battery_percent: int  # ❌ Old buoys won't send this, will break
battery_percent: Optional[int] = None  # ✅ Correct
```
**Fix:** Always use `Optional[type] = None` for new fields.

### ❌ Mistake 3: Wrong type conversion
```python
values = (..., float(data.battery_percent), ...)  # ❌ battery_percent is int
values = (..., int(data.battery_percent), ...)  # ✅ Correct
```
**Fix:** Match type conversion to SQLite column type.

### ❌ Mistake 4: Forgetting to backup
```bash
# Never do this without backup!
sqlite3 playbuoy.db "ALTER TABLE data ADD COLUMN ..."
```
**Fix:** Always backup first.
```bash
cp playbuoy.db playbuoy-backup-$(date +%Y%m%d-%H%M%S).db
```

---

## Rollback Procedure (If Something Goes Wrong)

**If the update breaks the API:**

```bash
# 1. Stop the service
sudo systemctl stop playbuoy-api

# 2. Restore backup database
cp playbuoy-backup-YYYYMMDD-HHMMSS.db playbuoy.db

# 3. Revert code changes
git checkout main.py  # If using git
# OR
nano main.py  # Edit manually

# 4. Restart service
sudo systemctl start playbuoy-api

# 5. Verify
curl http://localhost:8000/health
```

---

## Resources

- FastAPI docs: https://fastapi.tiangolo.com/
- SQLite docs: https://www.sqlite.org/
- Pydantic docs: https://docs.pydantic.dev/
- PlayBuoy spec: `docs/buoy.md`
- Upgrade path: `docs/fastapi-upgrade-path.md`
