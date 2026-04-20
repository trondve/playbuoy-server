# PlayBuoy API Server — Command Cheatsheet

Quick reference for common operations on the Raspberry Pi running the PlayBuoy FastAPI server.

---

## Service Management

**Check service status:**
```bash
sudo systemctl status playbuoy-api
```

**Start the service:**
```bash
sudo systemctl start playbuoy-api
```

**Stop the service:**
```bash
sudo systemctl stop playbuoy-api
```

**Restart the service:**
```bash
sudo systemctl restart playbuoy-api
```

**Enable service to auto-start on boot:**
```bash
sudo systemctl enable playbuoy-api
```

**Disable auto-start on boot:**
```bash
sudo systemctl disable playbuoy-api
```

---

## Logs & Monitoring

**View recent logs (last 20 lines):**
```bash
sudo journalctl -u playbuoy-api -n 20
```

**View logs in real-time (follow mode):**
```bash
sudo journalctl -u playbuoy-api -f
```

**View logs from last 1 hour:**
```bash
sudo journalctl -u playbuoy-api --since "1 hour ago"
```

**View logs with timestamps:**
```bash
sudo journalctl -u playbuoy-api -o short-iso
```

**Check service is using memory correctly:**
```bash
ps aux | grep uvicorn
```

---

## Health & API Checks

**Check API health endpoint:**
```bash
curl http://localhost:8000/health
```

**Check API health from another machine:**
```bash
curl http://192.168.140.7:8000/health
```

**Get latest measurement for a buoy:**
```bash
curl -H "X-API-Key: super-secret-key-123" http://localhost:8000/latest?node_id=playbuoy_grinde
```

**Get all latest measurements:**
```bash
curl -H "X-API-Key: super-secret-key-123" http://localhost:8000/latest_all
```

---

## Database Operations

**Check total number of records:**
```bash
sqlite3 playbuoy.db "SELECT COUNT(*) FROM data;"
```

**List all buoys (distinct node_ids):**
```bash
sqlite3 playbuoy.db "SELECT DISTINCT node_id FROM data ORDER BY node_id;"
```

**Get latest measurement for a buoy:**
```bash
sqlite3 playbuoy.db "SELECT * FROM data WHERE node_id='playbuoy_grinde' ORDER BY timestamp DESC LIMIT 1;"
```

**Get measurements from last 24 hours:**
```bash
sqlite3 playbuoy.db "SELECT node_id, timestamp, water_temperature, battery_voltage FROM data WHERE timestamp > (strftime('%s', 'now') - 86400) ORDER BY timestamp DESC;"
```

**Get measurements from last 7 days:**
```bash
sqlite3 playbuoy.db "SELECT node_id, timestamp, water_temperature FROM data WHERE timestamp > (strftime('%s', 'now') - 604800) ORDER BY timestamp DESC LIMIT 100;"
```

**Check database file size:**
```bash
ls -lh playbuoy.db
```

**Backup the database:**
```bash
cp playbuoy.db playbuoy-backup-$(date +%Y%m%d-%H%M%S).db
```

**View database schema:**
```bash
sqlite3 playbuoy.db ".schema data"
```

**Count records per buoy:**
```bash
sqlite3 playbuoy.db "SELECT node_id, COUNT(*) as record_count FROM data GROUP BY node_id ORDER BY record_count DESC;"
```

---

## Testing Upload

**Test upload with full payload:**
```bash
curl -X POST http://localhost:8000/upload \
  -H "X-API-Key: super-secret-key-123" \
  -H "Content-Type: application/json" \
  -d '{
    "nodeId": "playbuoy_test",
    "version": "2.5.3",
    "timestamp": '$(date +%s)',
    "lat": 59.4123,
    "lon": 5.2456,
    "temp": 12.5,
    "battery": 3.92,
    "battery_percent": 75,
    "temp_trend": 0.3,
    "wave": {"height": 0.45, "period": 4.2, "direction": "N/A", "power": 2.1},
    "alerts": {"anchorDrift": false, "chargingIssue": false, "tempSpike": false, "overTemp": false, "uploadFailed": false},
    "buoy": {"tilt": 8.5, "accel_rms": 0.2},
    "gps": {"hdop": 1.2, "ttf": 45}
  }'
```

**Test with minimal payload:**
```bash
curl -X POST http://localhost:8000/upload \
  -H "X-API-Key: super-secret-key-123" \
  -H "Content-Type: application/json" \
  -d '{
    "nodeId": "playbuoy_test",
    "version": "2.5.3",
    "timestamp": '$(date +%s)',
    "lat": 59.4123,
    "lon": 5.2456,
    "temp": 12.5,
    "battery": 3.92,
    "wave": {"height": 0.0, "period": 0.0, "direction": "N/A", "power": 0.0},
    "alerts": {"anchorDrift": false, "chargingIssue": false, "tempSpike": false, "overTemp": false, "uploadFailed": false}
  }'
```

---

## System Information

**Check Raspberry Pi uptime:**
```bash
uptime
```

**Check CPU temperature:**
```bash
vcgencmd measure_temp
```

**Check available disk space:**
```bash
df -h
```

**Check memory usage:**
```bash
free -h
```

**Check Python version:**
```bash
python3 --version
```

**Check venv activation:**
```bash
which python3
```

**Check installed Python packages:**
```bash
pip list
```

---

## Deployment

**Deploy using git workflow (recommended):**
```bash
bash tools/scripts/deploy.sh playbuoy-pi main
```

**Deploy to specific branch:**
```bash
bash tools/scripts/deploy.sh playbuoyadmin@192.168.140.7 feature-branch
```

**Manually pull and restart:**
```bash
cd /home/playbuoyadmin/playbuoy-server && git pull origin main && sudo systemctl restart playbuoy-api
```

**Quick SCP transfer (single file):**
```bash
scp /path/to/main.py playbuoyadmin@192.168.140.7:/home/playbuoyadmin/playbuoy-server/main.py
```

---

## System Updates

**Update system packages:**
```bash
sudo apt-get update && sudo apt-get upgrade
```

**Update Python packages:**
```bash
source /home/playbuoyadmin/playbuoy-server/venv/bin/activate
pip install --upgrade pip
pip list --outdated
```

**Reboot Raspberry Pi:**
```bash
sudo reboot
```

---

## Troubleshooting

**If service won't start, check for port conflicts:**
```bash
sudo lsof -i :8000
```

**Kill process using port 8000:**
```bash
sudo kill -9 <PID>
```

**Check service file for errors:**
```bash
sudo systemctl status playbuoy-api
sudo journalctl -u playbuoy-api -n 50
```

**Verify service file syntax:**
```bash
sudo systemd-analyze verify /etc/systemd/system/playbuoy-api.service
```

**Restart systemd and reload service:**
```bash
sudo systemctl daemon-reload
sudo systemctl restart playbuoy-api
```

**Check if API is responding:**
```bash
curl -v http://localhost:8000/health
```

**View current service configuration:**
```bash
sudo cat /etc/systemd/system/playbuoy-api.service
```

---

## Quick Diagnostics

**Run full diagnostic:**
```bash
echo "=== Service Status ===" && \
sudo systemctl status playbuoy-api && \
echo -e "\n=== Recent Logs ===" && \
sudo journalctl -u playbuoy-api -n 10 && \
echo -e "\n=== Health Check ===" && \
curl http://localhost:8000/health && \
echo -e "\n=== Database Records ===" && \
sqlite3 playbuoy.db "SELECT COUNT(*) as total_records FROM data;" && \
echo -e "\n=== System Status ===" && \
uptime
```

---

## Useful SSH Aliases

Add these to `~/.bashrc` for quick access:

```bash
alias playbuoy-status='sudo systemctl status playbuoy-api'
alias playbuoy-logs='sudo journalctl -u playbuoy-api -f'
alias playbuoy-restart='sudo systemctl restart playbuoy-api'
alias playbuoy-health='curl http://localhost:8000/health'
alias playbuoy-db='sqlite3 /home/playbuoyadmin/playbuoy-server/playbuoy.db'
```

Then reload:
```bash
source ~/.bashrc
```

---

## References

- API Documentation: See `docs/buoy.md` for payload specification
- Deployment Guide: See `docs/remote-development.md`
- Field Addition Guide: See `docs/how-to-add-fields.md`
- Service Configuration: See `/etc/systemd/system/playbuoy-api.service`
