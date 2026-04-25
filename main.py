from fastapi import FastAPI, Request, HTTPException, Security, Response
from fastapi.openapi.utils import get_openapi
from fastapi.security.api_key import APIKeyHeader
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from pydantic import BaseModel
from typing import Optional, List, Tuple, Dict, Any
import sqlite3
import os
import time

app = FastAPI()

# --- CORS (Allow Wix frontend access) ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://www.playbuoy.no",
        "https://editor.wix.com",
        "https://www.wix.com",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- API Key Security ---
API_KEY_NAME = "X-API-Key"
API_KEY = os.getenv("PLAYBUOY_API_KEY", "super-secret-key-123")
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)

# --- Security Headers ---
class SecureHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response: Response = await call_next(request)
        response.headers["Strict-Transport-Security"] = "max-age=15768000; includeSubDomains"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Cache-Control"] = "no-store"
        return response

app.add_middleware(SecureHeadersMiddleware)

# --- OpenAPI Auth Integration ---
def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema

    openapi_schema = get_openapi(
        title="PlayBuoy API",
        version="1.0.0",
        description="REST API for PlayBuoy data collection and monitoring.",
        routes=app.routes,
    )
    openapi_schema["components"]["securitySchemes"] = {
        "APIKeyHeader": {"type": "apiKey", "in": "header", "name": API_KEY_NAME}
    }
    for path in openapi_schema["paths"].values():
        for method in path.values():
            method.setdefault("security", []).append({"APIKeyHeader": []})
    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi

# --- Auth Check ---
def verify_api_key(key: str = Security(api_key_header)):
    if key != API_KEY:
        raise HTTPException(status_code=401, detail="Unauthorized: Invalid API Key")

# --- Pydantic Models matching payload ---
class WaveModel(BaseModel):
    height: Optional[float] = 0
    period: Optional[float] = 0
    direction: Optional[str] = "N/A"
    power: Optional[float] = 0

class TideModel(BaseModel):
    current_height: Optional[float] = None

class RTCModel(BaseModel):
    waterTemp: Optional[float] = None

class NetModel(BaseModel):
    operator: Optional[str] = None
    apn: Optional[str] = None
    ip: Optional[str] = None
    signal: Optional[int] = 0

class BuoyModel(BaseModel):
    tilt: Optional[float] = None
    accel_rms: Optional[float] = None

class GpsModel(BaseModel):
    hdop: Optional[float] = None
    ttf: Optional[int] = None

class AlertsModel(BaseModel):
    anchorDrift: Optional[bool] = False
    chargingIssue: Optional[bool] = False
    tempSpike: Optional[bool] = False
    overTemp: Optional[bool] = False
    uploadFailed: Optional[bool] = False

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
    name: Optional[str] = None
    tide: Optional[TideModel] = None

    # Extra optional fields
    battery_precal: Optional[float] = None
    battery_cal_factor: Optional[float] = None
    temp_valid: Optional[bool] = None
    temp_trend: Optional[float] = None
    uptime: Optional[int] = None
    reset_reason: Optional[str] = None
    rtc: Optional[RTCModel] = None
    net: Optional[NetModel] = None
    buoy: Optional[BuoyModel] = None
    gps: Optional[GpsModel] = None
    boot_count: Optional[int] = None
    altitude_gps: Optional[float] = None
    accuracy_gps: Optional[float] = None

    # Sleep schedule fields
    hours_to_sleep: Optional[int] = None
    next_wake_utc: Optional[int] = None
    battery_change_since_last: Optional[float] = None
    battery_percent: Optional[int] = None

# --- Helpers ---
DB_PATH = "playbuoy.db"

def b2i(v: Optional[bool]) -> Optional[int]:
    if v is None:
        return None
    return 1 if v else 0

def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def map_row_full(row: sqlite3.Row) -> Dict[str, Any]:
    """Return all DB columns plus legacy aliases and ISO timestamp."""
    d: Dict[str, Any] = dict(row)
    ts_unix = d.get("timestamp")
    try:
        iso = time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime(int(ts_unix))) if ts_unix is not None else None
    except Exception:
        iso = None
    d["timestamp_unix"] = ts_unix
    d["timestamp"] = iso

    d["temperature_c"] = d.get("water_temperature")
    d["wave_height_m"] = d.get("wave_height")
    d["wave_period_s"] = d.get("wave_period")

    node = d.get("node_id") or ""
    d["_id"] = f"{node}__{ts_unix}" if ts_unix is not None else node
    return d

def normalize_to_store(node_id: str) -> str:
    return (node_id or "").strip().lower().replace("-", "_")

def normalize_for_query(node_id: str) -> str:
    return (node_id or "").strip().lower().replace("-", "_")

@app.on_event("startup")
def ensure_indexes():
    try:
        with get_conn() as conn:
            cur = conn.cursor()
            cur.execute("CREATE INDEX IF NOT EXISTS idx_data_node_ts ON data(lower(node_id), timestamp)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_data_ts ON data(timestamp)")
            conn.commit()
    except Exception:
        pass

# --- Routes ---
@app.get("/")
def root():
    return {"message": "PlayBuoy API is live"}

@app.get("/robots.txt", include_in_schema=False)
def robots_txt():
    return Response(content="User-agent: *\nDisallow: /", media_type="text/plain")

@app.get("/health", include_in_schema=False)
def health():
    try:
        with get_conn() as conn:
            cur = conn.cursor()
            cur.execute("SELECT 1")
            cur.fetchone()
        return {"ok": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"DB error: {e}")

@app.post("/upload")
def upload_data(data: UploadModel, _: str = Security(verify_api_key)):
    normalized_node = normalize_to_store(data.nodeId)

    wave = data.wave or WaveModel()
    tide = data.tide or TideModel()
    rtc  = data.rtc  or RTCModel()
    net  = data.net  or NetModel()
    buoy = data.buoy or BuoyModel()
    gps  = data.gps  or GpsModel()
    alerts = data.alerts or AlertsModel()

    # Column list (ALL except auto-increment id)
    cols: List[str] = [
        "node_id", "firmware_version", "timestamp",
        "latitude", "longitude",
        "wave_height", "wave_period", "wave_direction", "wave_power",
        "water_temperature", "battery_voltage",
        "name", "tide_current_height",
        "battery_precal", "battery_cal_factor", "temp_valid", "temp_trend",
        "uptime", "reset_reason",
        "rtc_water_temp",
        "net_operator", "net_apn", "net_ip", "net_signal",
        "alert_anchor_drift", "alert_charging_issue", "alert_temp_spike", "alert_over_temp", "alert_upload_failed",
        "hours_to_sleep", "next_wake_utc", "battery_change_since_last",
        "battery_percent", "buoy_tilt", "buoy_accel_rms",
        "gps_hdop", "gps_ttf", "boot_count", "altitude_gps", "accuracy_gps",
    ]

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
        None if data.temp_trend is None else float(data.temp_trend),

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

        None if data.battery_percent is None else int(data.battery_percent),
        None if buoy.tilt is None else float(buoy.tilt),
        None if buoy.accel_rms is None else float(buoy.accel_rms),

        None if gps.hdop is None else float(gps.hdop),
        None if gps.ttf is None else int(gps.ttf),
        None if data.boot_count is None else int(data.boot_count),
        None if data.altitude_gps is None else float(data.altitude_gps),
        None if data.accuracy_gps is None else float(data.accuracy_gps),
    )

    placeholders = ", ".join(["?"] * len(cols))
    sql = f"INSERT INTO data ({', '.join(cols)}) VALUES ({placeholders})"

    conn = None
    try:
        conn = get_conn()
        cur = conn.cursor()
        cur.execute(sql, values)
        conn.commit()
        return {"status": "ok"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"DB error: {e}")
    finally:
        if conn:
            conn.close()

@app.get("/latest")
def latest_data(node_id: str, _: str = Security(verify_api_key)):
    normalized = normalize_for_query(node_id)
    conn = None
    try:
        conn = get_conn()
        cur = conn.cursor()
        cur.execute(
            """
            SELECT *
            FROM data
            WHERE lower(node_id) = ?
            ORDER BY timestamp DESC
            LIMIT 1
            """,
            (normalized,),
        )
        row = cur.fetchone()
        if not row:
            return []
        return [map_row_full(row)]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Query error: {e}")
    finally:
        if conn:
            conn.close()

@app.get("/latest_all")
def latest_all(_: str = Security(verify_api_key)):
    conn = None
    try:
        conn = get_conn()
        cur = conn.cursor()
        cur.execute(
            """
            SELECT d.*
            FROM data d
            INNER JOIN (
                SELECT lower(node_id) AS node_id, MAX(timestamp) AS max_ts
                FROM data
                GROUP BY lower(node_id)
            ) latest
            ON lower(d.node_id) = latest.node_id AND d.timestamp = latest.max_ts
            """
        )
        rows = cur.fetchall()
        result = [map_row_full(r) for r in rows]

        def temp_key(rec: Dict[str, Any]) -> float:
            t = rec.get("water_temperature")
            try:
                return float(t) if t is not None else -999.0
            except Exception:
                return -999.0

        result.sort(key=temp_key, reverse=True)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Query error: {e}")
    finally:
        if conn:
            conn.close()

@app.get("/history")
def history_data(node_id: str, days: int = 365, limit: int = 10000, _: str = Security(verify_api_key)):
    normalized = normalize_for_query(node_id)
    conn = None
    try:
        conn = get_conn()
        cur = conn.cursor()
        cutoff_ts = int(time.time()) - (days * 86400)
        cur.execute(
            """
            SELECT *
            FROM data
            WHERE lower(node_id) = ? AND timestamp >= ?
            ORDER BY timestamp DESC
            LIMIT ?
            """,
            (normalized, cutoff_ts, limit),
        )
        rows = cur.fetchall()
        result = [map_row_full(r) for r in rows]
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Query error: {e}")
    finally:
        if conn:
            conn.close()
