# PlayBuoy System Summary

**Version:** 1.0  
**Created:** 2026-04-20  
**Purpose:** Solar-powered IoT buoy for water monitoring (lakes, beaches)  
**Deployment:** Permanently sealed (no field service) — Norwegian lakes, 59.4°N latitude

## What is PlayBuoy?

PlayBuoy is a permanently sealed, solar-powered IoT buoy that measures water conditions and transmits telemetry via 4G cellular (LTE-M/NB-IoT). The device is designed to operate autonomously for years without maintenance, surviving long dark winters in Norway on minimal solar power.

**Key characteristics:**
- **Hardware:** ESP32 microcontroller + SIM7000G modem + DS18B20 temperature sensor + ICM-20948 IMU
- **Power:** Solar panel + Samsung INR18650-35E 18650 cell (3.7V, 3500mAh)
- **Deployment:** Permanently sealed enclosure (no access once deployed)
- **Operating mode:** Deep sleep 2 hours to 3 months; wake cycles 3–20 minutes
- **Data upload:** HTTP POST to playbuoyapi.no with X-API-Key header
- **Update method:** Over-the-air firmware updates (HTTP, no HTTPS due to SIM7000G limitation)

## Boot Cycle (Every 2 hours to 3 months, depending on season and battery)

1. **Power up** → Initialize ESP32, check voltage
2. **Battery gate** — If ≤3.70V or ≤25% SoC → deep sleep immediately
3. **Measure temperature** — DS18B20 sensor, 750ms conversion, validate range (-30 to +60°C)
4. **Collect wave data** — IMU sampling at 10Hz for ~100 seconds → 1024-point FFT → spectral analysis
5. **Get GPS fix** — NTP sync → XTRA ephemeris download → 60s GNSS warm-up → position polling
6. **Check for OTA update** — Compare firmware version, download if newer (battery gates: 3.85V + 50% SoC)
7. **Build JSON payload** — ~40 fields with telemetry, diagnostics, alerts
8. **Upload to API** — HTTP POST with X-API-Key header, 512-byte RTC buffer for failed uploads
9. **Calculate next sleep** — Season-aware: winter 90 days, summer 30 min (modulated by battery %)
10. **Deep sleep** — GPIO 25 held LOW to prevent 3.3V rail leakage

## JSON Payload Structure

The buoy sends a structured JSON payload (~500–800 bytes typical) with the following sections:

### Root-Level Fields
- **Device Identity:** `nodeId`, `name`, `version`
- **Timing & State:** `timestamp`, `uptime`, `boot_count`, `reset_reason`
- **Location:** `lat`, `lon`
- **Temperature:** `temp`, `temp_valid`, `temp_trend`
- **Battery:** `battery`, `battery_percent`, `battery_change_since_last`
- **Sleep Schedule:** `minutes_to_sleep`, `next_wake_utc`

### Nested Objects
- **`wave`** — Wave spectral analysis (height, period, direction, power)
- **`buoy`** — Physical diagnostics (tilt, accel_rms)
- **`rtc`** — RTC snapshot (cached water temperature)
- **`gps`** — GPS diagnostics (hdop, ttf)
- **`net`** — Network diagnostics (operator, apn, ip, signal)
- **`alerts`** — Boolean flags (anchorDrift, chargingIssue, tempSpike, overTemp, uploadFailed)

## Data Flow

```
[Buoy Boot]
   ↓
[Measure sensors: battery, temperature, waves, GPS, network]
   ↓
[Build JSON payload with ~40 fields]
   ↓
[Upload via HTTP POST with X-API-Key header]
   ├─ Success → Clear buffer, increment boot counter
   └─ Failure → Store JSON in RTC buffer for next attempt
   ↓
[Calculate next sleep duration: season-aware + battery modulated]
   ↓
[Deep sleep for 2 hours to 90 days]
   ↓
[RTC wakeup → Repeat]
```

## API Specification

**Endpoint:** `POST https://playbuoyapi.no/upload`  
**Authentication:** `X-API-Key: super-secret-key-123` (header)  
**Content-Type:** `application/json`  
**Max payload:** 2048 bytes

### Success Response (201 Created)
```json
{
  "status": "success",
  "timestamp": "2026-04-20T15:30:45Z"
}
```

### Error Response (400 Bad Request)
```json
{
  "error": "Invalid field: battery_percent must be 0-100",
  "field": "battery_percent",
  "value": 105
}
```

## Data Characteristics

- **Frequency:** Every 2 hours to 3 months (seasonal)
- **Volume:** ~12 messages/day in summer (30-min cycles), ~8 messages/day in winter (90-day hibernation)
- **Retention:** 10 years (time-series archive)
- **Busiest period:** April–September (spring/summer)
- **Slowest period:** October–March (winter hibernation)

## Validation Rules

- **lat/lon:** -90 to +90 / -180 to +180 (reject 0,0 "Null Island")
- **temperature:** -30 to +60°C (reject -127 = disconnected, 85 = error)
- **battery_percent:** 0–100% (reject >100 or <0)
- **wave height:** 0–2.0m for lakes (reject >2.0 as noise)
- **timestamp:** Unix epoch, within ±24h of current time
- **float sanitization:** Replace NaN/Inf with 0

## Persistent RTC State

Stored in RTC slow memory (survives deep sleep, cleared only on power-on reset):
- Boot counter
- GPS anchor (lat/lon from last fix)
- Temperature history (last 5 readings)
- Last upload time
- XTRA ephemeris timestamp
- Charge state
- Alert flags

## Alert Processing Rules

- **anchorDrift:** Haversine distance >50m from anchor
- **chargingIssue:** Battery % not increasing over N cycles (solar failure)
- **tempSpike:** Current temp differs >5°C from 5-cycle mean
- **overTemp:** Temp >60°C (sensor error)
- **uploadFailed:** Sticky flag, cleared only on successful upload

## Hardware Architecture

```
ESP32 (main controller)
├── Power Management
│   ├── Solar panel → charging circuit
│   ├── Samsung INR18650-35E (3.7V, 3500mAh)
│   └── AMS1117 3.3V regulator (GPIO 25 control)
├── Sensors
│   ├── DS18B20 water temperature (1-Wire, GPIO 13)
│   ├── ICM-20948 IMU (I2C, 10Hz sampling)
│   └── NEO-M9N GNSS receiver (UART via SIM7000G)
├── Modem
│   └── SIM7000G LTE-M/NB-IoT (UART1, GPIO 4 PWRKEY)
└── Storage
    ├── RTC slow memory (512 bytes, survives sleep)
    └── NVS (non-volatile storage)
```

## Deployment Details

**Buoy Models:**
- `playbuoy_grinde` — Litla Grindevatnet (test lake)
- `playbuoy_vatna` — Vatnakvamsvatnet (production)

**Location:** Haugesund, Norway (59.4°N)  
**Season Detection:**
- Winter (Oct–Mar): 90-day hibernation
- Shoulder (Apr, May, Sep): 2-hour cycles
- Summer (Jun–Aug): 30-minute cycles

**Critical Thresholds:**
- **Critical voltage:** ≤3.70V → immediate deep sleep
- **Critical SoC:** ≤25% → skip cycle, return to sleep
- **Brownout:** <3.55V during upload → skip cycle
