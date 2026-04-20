# PlayBuoy Database Server — Architecture Design

**Document Status:** Draft  
**Created:** 2026-04-20  
**Purpose:** Design decisions, schema rationale, scaling strategy

## Database Design

### Time-Series Partitioning Strategy

The `measurements` table is partitioned by month to:
- **Improve query performance** — Range queries (last N days) scan only relevant partitions
- **Simplify retention** — Drop entire month partitions older than 10 years
- **Enable parallel inserts** — Multiple concurrent uploads target different partitions
- **Reduce index size** — Smaller indexes per partition, faster lookups

### Indexing Strategy

#### Primary Index: `(node_id, timestamp DESC)`

Used by queries like: "Get latest 100 measurements from buoy X"

```sql
CREATE INDEX measurements_nodeid_timestamp 
ON measurements (node_id, timestamp DESC);
```

**Why composite?**
- B-tree traversal starts at (node_id), then filtered by (timestamp)
- DESC ensures most recent data is at index start
- Covers full query without table lookups (covering index)

#### Secondary Index: `(timestamp DESC)`

Used by global queries: "Get latest measurements from all buoys"

```sql
CREATE INDEX measurements_timestamp 
ON measurements (timestamp DESC);
```

#### Cleanup Index: `timestamp`

Used by retention job: "Delete measurements older than 10 years"

```sql
CREATE INDEX measurements_timestamp_cleanup 
ON measurements (timestamp);
```

### Data Types & Precision

| Field | Type | Rationale |
|-------|------|-----------|
| `timestamp` | TIMESTAMP (UTC) | Second precision (buoy uploads every 2+ hours) |
| `temperature` | FLOAT | ±0.1°C typical sensor precision |
| `battery_voltage` | FLOAT | ±0.01V ADC resolution (10-bit) |
| `battery_percent` | SMALLINT | Discrete 0–100% SoC values |
| `gps_lat`, `lon` | FLOAT | ±0.0001° = ~11m accuracy at 59°N |
| `wave_height` | FLOAT | ±0.01m FFT spectral resolution |
| `gps_hdop` | FLOAT | Dimensionless (0.5–100, smaller = better) |
| `alerts` | JSONB | Flexible boolean flags, queryable |

## API Design

### Request Validation Pipeline

```
[HTTP Request]
  ↓
[Parse JSON] → Reject if malformed
  ↓
[Verify X-API-Key header] → Return 401 if invalid
  ↓
[Validate schema] → Check required fields present
  ↓
[Validate ranges] → Check battery % ∈ [0, 100], temp ∈ [-30, 60], etc.
  ↓
[Sanitize floats] → Replace NaN/Inf with 0
  ↓
[Timestamp validation] → Reject if >24h away from UTC now
  ↓
[Insert into database] → Return 201 on success, 400 on DB error
```

### Error Response Format

All errors return HTTP 400 with:
```json
{
  "error": "Human-readable error message",
  "field": "field_name",  // if applicable
  "value": actual_value   // for debugging
}
```

### Success Response

HTTP 201 Created:
```json
{
  "status": "success",
  "timestamp": "2026-04-20T15:30:45Z"
}
```

## Alert Processing

### Detection Rules

**1. Anchor Drift (every cycle)**
```
IF Haversine(current_gps, anchor_gps) > 50m THEN
  SET alerts.anchorDrift = true
END
```
Anchor is set on first successful GPS fix, reset if manually repositioned.

**2. Charging Issue (every 5 cycles)**
```
IF battery_percent[n] ≤ battery_percent[n-5] THEN
  SET alerts.chargingIssue = true  // solar failure
ELSE
  CLEAR alerts.chargingIssue
END
```
5-cycle window detects gradual discharge over ~10 hours (summer) or ~5 days (winter).

**3. Temperature Spike (every cycle)**
```
mean_temp = AVG(temp[n-4:n])
IF |temp[n] - mean_temp| > 5°C THEN
  SET alerts.tempSpike = true
END
```
5-cycle moving average detects anomalies; resets next cycle if temp normalizes.

**4. Over-Temperature (every cycle)**
```
IF temp[n] > 60°C THEN
  SET alerts.overTemp = true  // impossible for Norwegian water
  MARK measurement as invalid
END
```
Indicates sensor error (water temp max ~20°C in summer, 0°C in winter).

**5. Upload Failed (sticky)**
```
IF previous_upload_failed AND current_upload_succeeds THEN
  CLEAR alerts.uploadFailed
ELSE IF upload_fails THEN
  SET alerts.uploadFailed = true  // persists until next success
END
```
Buoy holds JSON in RTC buffer until successful upload; sticky flag indicates backlog.

## Scaling Considerations

### Expected Data Volume

**Per buoy, per year:**
- Summer (4 months @ 30-min cycles): 5,760 messages
- Winter (2 months hibernation): 0 messages
- Shoulder (6 months @ 2-hour cycles): 2,190 messages
- **Total:** ~7,950 messages/year per buoy

**Fleet size:** 2–10 buoys (initial), up to 100 buoys (future)

**Disk usage:**
- Per measurement: ~200 bytes (JSON serialized + indices)
- Per buoy, per year: ~1.6 MB
- Per buoy, 10 years: ~16 MB
- Fleet (10 buoys, 10 years): ~160 MB

### Partitioning

Monthly partitions mean:
- 120 partitions for 10-year retention
- Easy cleanup: `DROP PARTITION` for months older than 10 years
- Parallelizable queries across partitions

### Connection Pooling

- **Pool size:** 10–20 connections (small fleet)
- **Timeout:** 30s idle before release
- **Growth:** Add connections if fleet >50 buoys

### Query Performance

| Query | Expected Time | Approach |
|-------|----------------|----------|
| Get latest 100 from buoy X | <10ms | Index (node_id, timestamp DESC) |
| Get global latest | <20ms | Index (timestamp DESC) + LIMIT 1 per buoy |
| Historical range (30 days) | <100ms | Partition pruning + index scan |
| Purge old data (10 years) | <5s | Bulk DROP PARTITION once per month |

## Security

### Authentication

- **Method:** Shared API key in `X-API-Key` header
- **Rotation:** Change key if exposed; old messages still accepted for 30 days
- **Future:** Consider JWT tokens per buoy for fine-grained control

### Input Validation

- **SQL injection:** Use parameterized queries (prepared statements)
- **Float overflow:** Sanitize NaN/Inf before JSON storage
- **Timestamp skew:** Reject if >24h away from server time (detect device clock issues)
- **GPS bounds:** Reject if outside valid ranges, reject Null Island (0, 0)

### Rate Limiting

Per-buoy limits (by `node_id`):
- **1 upload per 60 seconds** (burst allowed, but max 1 per minute average)
- **100 uploads per day** (summer 30-min cycles = ~48/day, plenty of buffer)
- **1000 uploads per month**

Respond with HTTP 429 (Too Many Requests) if exceeded.

## Monitoring & Observability

### Metrics to Track

- **Buoy uptime:** Days since last heartbeat per buoy
- **Alert frequency:** Count of each alert type per buoy
- **API latency:** Percentiles (p50, p99) for `/upload` endpoint
- **Database query time:** Slow query log (>100ms)
- **Disk usage growth:** Monthly trend, forecast 10-year horizon

### Alerting Rules

- **Buoy silence:** No upload for >3 days (summer) or >10 days (winter) → alert ops
- **API errors:** >5% of requests failing → page on-call
- **Database disk:** >80% capacity → trigger cleanup or expand
- **Slow queries:** >500ms latency → investigate, add index if needed

### Logging

Structure logs as JSON for parsability:
```json
{
  "timestamp": "2026-04-20T15:30:45.123Z",
  "level": "info",
  "message": "Measurement stored",
  "node_id": "playbuoy_grinde",
  "timestamp_received": 1713607200,
  "latency_ms": 8
}
```

## Future Enhancements

### 1. Dashboard API

Add REST endpoints for dashboards:
```
GET /api/buoys                    # List all buoys
GET /api/buoys/:id                # Get buoy metadata
GET /api/buoys/:id/latest         # Latest measurement
GET /api/buoys/:id/history?range=30d  # Historical data
GET /api/buoys/:id/alerts         # Recent alerts
```

### 2. Real-Time WebSocket

Stream latest measurements to connected dashboards:
```
WS /ws/live
→ {nodeId, temperature, battery, ...} every new upload
```

### 3. Data Export

Add CSV/Parquet export for scientific analysis:
```
GET /api/export?buoy=X&from=2025-01-01&to=2025-12-31&format=csv
```

### 4. Machine Learning

Detect anomalies using models trained on historical data:
- Temperature trend forecasting
- Charging failure early warning
- Buoy health scoring

## References

- [PlayBuoy Specification](buoy.md)
- [CLAUDE.md](../CLAUDE.md) — Project context
