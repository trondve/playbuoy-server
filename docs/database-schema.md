# PlayBuoy Database Schema

**Database:** SQLite (`playbuoy.db`)  
**Table:** `data`  
**Purpose:** Store time-series telemetry from PlayBuoy IoT buoys

---

## Table Definition

```sql
CREATE TABLE data (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    node_id TEXT,
    firmware_version TEXT,
    timestamp INTEGER,
    latitude REAL,
    longitude REAL,
    wave_height REAL,
    wave_period REAL,
    wave_direction TEXT,
    wave_power REAL,
    water_temperature REAL,
    battery_voltage REAL,
    name TEXT,
    tide_current_height REAL,
    battery_precal REAL,
    battery_cal_factor REAL,
    temp_valid INTEGER,
    uptime INTEGER,
    reset_reason TEXT,
    rtc_water_temp REAL,
    net_operator TEXT,
    net_apn TEXT,
    net_ip TEXT,
    net_signal INTEGER,
    alert_anchor_drift INTEGER,
    alert_charging_issue INTEGER,
    alert_temp_spike INTEGER,
    alert_over_temp INTEGER,
    alert_upload_failed INTEGER,
    hours_to_sleep INTEGER,
    next_wake_utc TEXT,
    battery_change_since_last REAL,
    battery_percent INTEGER DEFAULT NULL,
    temp_trend REAL DEFAULT NULL,
    buoy_tilt REAL DEFAULT NULL,
    buoy_accel_rms REAL DEFAULT NULL,
    gps_hdop REAL DEFAULT NULL,
    gps_ttf INTEGER DEFAULT NULL,
    boot_count INTEGER DEFAULT NULL,
    altitude_gps REAL DEFAULT NULL,
    accuracy_gps REAL DEFAULT NULL
);
```

---

## Column Reference

| Column | Type | Description | Example |
|--------|------|-------------|---------|
| **id** | INTEGER PK | Auto-incrementing record ID | 1, 2, 3... |
| **node_id** | TEXT | Unique buoy identifier | playbuoy_grinde |
| **firmware_version** | TEXT | Buoy firmware version | 2.5.3 |
| **timestamp** | INTEGER | Unix timestamp (seconds UTC) | 1625591400 |
| **latitude** | REAL | GPS latitude | 59.4123 |
| **longitude** | REAL | GPS longitude | 5.2456 |
| **wave_height** | REAL | Significant wave height (m) | 0.45 |
| **wave_period** | REAL | Peak period (s) | 4.2 |
| **wave_direction** | TEXT | Wave direction | N/A, NW, SE, etc. |
| **wave_power** | REAL | Spectral power (kW/m) | 2.1 |
| **water_temperature** | REAL | Water temperature (°C) | 12.5 |
| **battery_voltage** | REAL | Cell voltage (V) | 3.92 |
| **name** | TEXT | Buoy display name (optional) | Litla Grindevatnet |
| **tide_current_height** | REAL | Tide height (m) | NULL, 0.5, -0.3 |
| **battery_precal** | REAL | Battery pre-calibration value | NULL |
| **battery_cal_factor** | REAL | Battery calibration factor | NULL |
| **temp_valid** | INTEGER | Temperature sensor valid (0/1) | 1, 0 |
| **uptime** | INTEGER | Buoy uptime (seconds) | 864000 |
| **reset_reason** | TEXT | Last reset reason | watchdog, power_loss, etc. |
| **rtc_water_temp** | REAL | RTC-recorded water temp (°C) | 12.3 |
| **net_operator** | TEXT | Mobile network operator | Telenor, Telia, etc. |
| **net_apn** | TEXT | Mobile APN | internet |
| **net_ip** | TEXT | Assigned IP address | 10.135.245.120 |
| **net_signal** | INTEGER | Signal strength (0-31 RSRP) | 18 |
| **alert_anchor_drift** | INTEGER | Position drift detected (0/1) | 0, 1 |
| **alert_charging_issue** | INTEGER | Battery not charging (0/1) | 0, 1 |
| **alert_temp_spike** | INTEGER | Temperature anomaly (0/1) | 0, 1 |
| **alert_over_temp** | INTEGER | Over-temperature condition (0/1) | 0, 1 |
| **alert_upload_failed** | INTEGER | Previous upload failed (0/1) | 0, 1 |
| **hours_to_sleep** | INTEGER | Sleep duration (hours) | 2, 6, 24 |
| **next_wake_utc** | TEXT | Next wake time (ISO format) | 2026-04-20T23:00:00Z |
| **battery_change_since_last** | REAL | Battery % change since last measurement | 0.5, -1.2 |
| **battery_percent** | INTEGER | Battery state of charge (0-100) | 75 |
| **temp_trend** | REAL | Temperature trend (°C/hour) | 0.3, -0.1 |
| **buoy_tilt** | REAL | Physical tilt angle (degrees) | 8.5 |
| **buoy_accel_rms** | REAL | Acceleration RMS | 0.2 |
| **gps_hdop** | REAL | Horizontal dilution of precision | 1.2 |
| **gps_ttf** | INTEGER | Time-to-fix (seconds) | 45 |
| **boot_count** | INTEGER | Total boot cycles | 234 |
| **altitude_gps** | REAL | GPS altitude (m) | 12.5 |
| **accuracy_gps** | REAL | GPS accuracy (m) | 5.0 |

---

## Indexes

```sql
CREATE INDEX idx_data_node_ts ON data(lower(node_id), timestamp);
CREATE INDEX idx_data_ts ON data(timestamp);
```

| Index | Columns | Purpose |
|-------|---------|---------|
| `idx_data_node_ts` | `lower(node_id), timestamp DESC` | Query buoy's last N measurements |
| `idx_data_ts` | `timestamp DESC` | Find latest overall measurement |

---

## Typical Queries

**Get latest measurement for a buoy:**
```sql
SELECT * FROM data 
WHERE lower(node_id) = 'playbuoy_grinde' 
ORDER BY timestamp DESC LIMIT 1;
```

**Count records per buoy:**
```sql
SELECT node_id, COUNT(*) as record_count 
FROM data 
GROUP BY node_id 
ORDER BY record_count DESC;
```

**Get measurements from last 24 hours:**
```sql
SELECT node_id, timestamp, water_temperature, battery_voltage 
FROM data 
WHERE timestamp > (strftime('%s', 'now') - 86400) 
ORDER BY timestamp DESC;
```

**Get total database size:**
```sql
SELECT 
  COUNT(*) as total_records,
  COUNT(DISTINCT node_id) as unique_buoys,
  MIN(timestamp) as oldest_record,
  MAX(timestamp) as newest_record
FROM data;
```

---

## Data Validation Rules

When inserting new records:
- `timestamp` must be valid Unix timestamp (UTC)
- `battery_percent` must be 0-100 or NULL
- `latitude` must be -90 to +90
- `longitude` must be -180 to +180
- `water_temperature` typically -2 to 30°C (invalid if >60°C)
- All REAL columns accept NULL for missing values
- All INTEGER alert columns are 0 (false) or 1 (true) or NULL
- `node_id` is normalized to lowercase with underscores (dashes converted)

---

## Backup Procedure

**Create timestamped backup:**
```bash
cp playbuoy.db playbuoy-backup-$(date +%Y%m%d-%H%M%S).db
```

**Restore from backup:**
```bash
cp playbuoy-backup-20260420-120000.db playbuoy.db
sudo systemctl restart playbuoy-api
```

---

## References

- API Payload: See `docs/buoy.md`
- Deployment: See `docs/remote-development.md`
- Adding Fields: See `docs/how-to-add-fields.md`
- Commands: See `docs/command-cheatsheet.md`
