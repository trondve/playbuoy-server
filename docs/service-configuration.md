# PlayBuoy API Service Configuration

**Service Name:** playbuoy-api  
**Runtime:** Python 3 + Uvicorn (FastAPI ASGI server)  
**Location:** Raspberry Pi (192.168.140.7:8000)  
**Status:** Production

---

## Systemd Service File

**Location:** `/etc/systemd/system/playbuoy-api.service`

```ini
[Unit]
Description=PlayBuoy FastAPI backend
After=network.target

[Service]
User=playbuoyadmin
Group=playbuoyadmin
WorkingDirectory=/home/playbuoyadmin/playbuoy-server
ExecStart=/home/playbuoyadmin/playbuoy-server/venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000
Restart=on-failure
RestartSec=5
StartLimitInterval=60
StartLimitBurst=3
MemoryMax=256M
StandardOutput=journal
StandardError=journal
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
```

---

## Service Configuration Details

### Unit Section
| Setting | Value | Description |
|---------|-------|-------------|
| **Description** | PlayBuoy FastAPI backend | Service display name |
| **After** | network.target | Start after network is ready |

### Service Section
| Setting | Value | Description |
|---------|-------|-------------|
| **User** | playbuoyadmin | Service runs as this user |
| **Group** | playbuoyadmin | Service runs with this group |
| **WorkingDirectory** | /home/playbuoyadmin/playbuoy-server | App root directory |
| **ExecStart** | uvicorn main:app --host 0.0.0.0 --port 8000 | Start command |
| **Restart** | on-failure | Restart only on exit code != 0 |
| **RestartSec** | 5 | Wait 5 seconds before restart |
| **StartLimitInterval** | 60 | Time window for rate limiting (seconds) |
| **StartLimitBurst** | 3 | Max 3 restarts per interval |
| **MemoryMax** | 256M | Kill service if memory exceeds 256MB |
| **StandardOutput** | journal | Send stdout to systemd journal |
| **StandardError** | journal | Send stderr to systemd journal |
| **Environment** | PYTHONUNBUFFERED=1 | Don't buffer Python output |

### Install Section
| Setting | Value | Description |
|---------|-------|-------------|
| **WantedBy** | multi-user.target | Auto-start when system boots |

---

## Restart Behavior

**Restart Policy: on-failure with crash loop protection**

| Condition | Behavior |
|-----------|----------|
| Normal shutdown | No restart |
| Exit code 0 | No restart |
| Exit code ≠ 0 | Restart after 5 seconds |
| 3 failures in 60 seconds | Stop restarting (protection against crash loops) |
| Manual `systemctl stop` | Stays stopped |
| Manual `systemctl start` | Starts immediately |
| System reboot | Auto-starts (via WantedBy=multi-user.target) |

**Protection:**
- Max 3 restart attempts within 60 seconds
- After 3 failures, service enters failed state
- Prevents hammering resources on misconfigured app
- Allows manual recovery time before retry

---

## Memory Safety

**Limit: 256MB**

If the uvicorn process exceeds 256MB of memory:
1. systemd receives OOM notification
2. Service is killed immediately
3. Systemd attempts restart (per Restart policy)
4. Prevents Pi from running out of memory

**Monitoring:**
```bash
ps aux | grep uvicorn  # Check current memory usage
```

---

## Logging

**Output:** systemd journal (journalctl)

Both stdout and stderr captured and indexed by systemd.

**View logs:**
```bash
sudo journalctl -u playbuoy-api -f          # Real-time
sudo journalctl -u playbuoy-api -n 50       # Last 50 lines
sudo journalctl -u playbuoy-api --since "1 hour ago"  # Last hour
```

**Log retention:**
- Default: ~7 days (system-dependent)
- Persistent storage on Raspberry Pi
- Can query by timestamp, priority, unit name

---

## API Details

### Service Binding
- **Host:** 0.0.0.0 (listen on all interfaces)
- **Port:** 8000 (TCP)
- **Workers:** 1 (Raspberry Pi is single-core, Uvicorn is async)

### FastAPI App (main:app)
- **Framework:** FastAPI 0.115.14
- **Server:** Uvicorn 0.35.0
- **ASGI:** Full async support
- **Endpoints:** See main.py

### Available Routes
- `GET /` — API status
- `GET /health` — Database connectivity check
- `POST /upload` — Accept buoy telemetry
- `GET /latest` — Latest measurement for node_id
- `GET /latest_all` — Latest for all buoys

### Authentication
- **Header:** X-API-Key
- **Default:** super-secret-key-123
- **Required:** For /upload, /latest, /latest_all

---

## Environment Variables

**PYTHONUNBUFFERED=1**
- Disables Python stdout buffering
- Logs appear immediately in journalctl
- Essential for real-time monitoring

**Optional (can be added):**
```bash
PLAYBUOY_API_KEY=your-secret-key  # Override default API key
```

---

## System Requirements

- **CPU:** ARM (Raspberry Pi, single-core sufficient)
- **Memory:** 512MB minimum, 256MB service limit
- **Storage:** SQLite database (currently ~1MB, grows ~1MB per year)
- **Network:** Ethernet or WiFi with internet connectivity
- **Python:** 3.9+
- **Systemd:** 230+ (standard on Bookworm)

---

## Management Commands

**Check status:**
```bash
sudo systemctl status playbuoy-api
```

**Restart:**
```bash
sudo systemctl restart playbuoy-api
```

**View logs:**
```bash
sudo journalctl -u playbuoy-api -f
```

**Reload configuration:**
```bash
sudo systemctl daemon-reload
```

**Check syntax:**
```bash
sudo systemd-analyze verify /etc/systemd/system/playbuoy-api.service
```

---

## Maintenance

### Weekly
- [ ] Check logs for errors: `sudo journalctl -u playbuoy-api -n 100`
- [ ] Verify health: `curl http://localhost:8000/health`

### Monthly
- [ ] Backup database: `cp playbuoy.db playbuoy-backup-$(date +%Y%m%d).db`
- [ ] Check disk usage: `df -h`
- [ ] Review service restarts: `sudo journalctl -u playbuoy-api | grep "Main process exited"`

### Quarterly
- [ ] Update system packages: `sudo apt-get update && sudo apt-get upgrade`
- [ ] Update Python packages: See `docs/command-cheatsheet.md`
- [ ] Test failover: Stop and restart service, verify auto-restart

---

## Troubleshooting

**Service won't start:**
```bash
sudo systemctl status playbuoy-api
sudo journalctl -u playbuoy-api -n 50
```

**Port 8000 in use:**
```bash
sudo lsof -i :8000
sudo kill -9 <PID>
sudo systemctl restart playbuoy-api
```

**Memory limit exceeded:**
Check for memory leaks in FastAPI/Uvicorn. See logs:
```bash
ps aux | grep uvicorn
sudo journalctl -u playbuoy-api | grep "Killed"
```

**Service repeatedly restarting:**
Indicates code issue or startup failure. Check:
```bash
sudo journalctl -u playbuoy-api -n 100  # Find actual error
```

---

## Upgrade Procedure

When updating service configuration:

1. **Edit service file:**
   ```bash
   sudo nano /etc/systemd/system/playbuoy-api.service
   ```

2. **Reload systemd:**
   ```bash
   sudo systemctl daemon-reload
   ```

3. **Restart service (if running):**
   ```bash
   sudo systemctl restart playbuoy-api
   ```

4. **Verify:**
   ```bash
   sudo systemctl status playbuoy-api
   ```

---

## References

- FastAPI Docs: https://fastapi.tiangolo.com/
- Uvicorn Docs: https://www.uvicorn.org/
- Systemd Docs: https://www.freedesktop.org/software/systemd/man/systemd.service.html
- PlayBuoy API: See `main.py` in this repo
- Commands: See `docs/command-cheatsheet.md`
- Database: See `docs/database-schema.md`
