# Remote Development & Deployment Guide

**Goal:** Make editing and deploying to Raspberry Pi seamless  
**Methods:** Git workflow, SCP transfer, or SSH direct execution

---

## Method 1: Git-Based Deployment (Recommended ⭐)

### Setup (One Time)

**On your local machine:**
```bash
# Configure SSH key for passwordless access (optional but recommended)
ssh-keygen -t ed25519 -f ~/.ssh/playbuoy_rsa -N ""
ssh-copy-id -i ~/.ssh/playbuoy_rsa playbuoyadmin@192.168.140.7
```

**In `~/.ssh/config` (for easy reference):**
```
Host playbuoy-pi
    HostName 192.168.140.7
    User playbuoyadmin
    IdentityFile ~/.ssh/playbuoy_rsa
```

### Workflow

1. **Make changes locally** in the repo
2. **Commit and push:**
   ```bash
   git add -A
   git commit -m "Add battery_percent field"
   git push origin main
   ```

3. **Deploy to Raspberry Pi:**
   ```bash
   # Option A: Use the deploy script
   bash tools/scripts/deploy.sh playbuoyadmin@192.168.140.7 main
   
   # Option B: Manual SSH deployment
   ssh playbuoyadmin@192.168.140.7 "cd /home/playbuoyadmin/playbuoy-server && git pull origin main && sudo systemctl restart playbuoy-api"
   ```

4. **Verify:**
   ```bash
   curl http://192.168.140.7:8000/health
   # Should return: {"ok": true}
   ```

**Advantages:**
- ✅ Changes are version controlled
- ✅ Easy to rollback
- ✅ Safe (review before deploy)
- ✅ All team members can see history

---

## Method 2: Direct SCP Transfer (For Quick Edits)

If you want to test a single file change without committing:

```bash
# 1. Edit file locally
nano main.py

# 2. Transfer to Pi
scp main.py playbuoyadmin@192.168.140.7:/home/playbuoyadmin/playbuoy-server/main.py

# 3. Restart service
ssh playbuoyadmin@192.168.140.7 "sudo systemctl restart playbuoy-api"

# 4. Check logs
ssh playbuoyadmin@192.168.140.7 "sudo journalctl -u playbuoy-api -n 20"
```

**Advantages:**
- ✅ Fast iteration
- ✅ No git commit needed
- ❌ No version history
- ⚠️ Be careful — easy to lose changes

---

## Method 3: VS Code Remote SSH (For Direct Editing)

Use Visual Studio Code to edit files directly on the Pi:

### Setup

1. **Install VS Code Remote extension:**
   - Open VS Code
   - Extensions → Search "Remote - SSH"
   - Install by Microsoft

2. **Add SSH host to config:**
   ```bash
   # Edit ~/.ssh/config
   Host playbuoy-pi
       HostName 192.168.140.7
       User playbuoyadmin
       IdentityFile ~/.ssh/playbuoy_rsa
   ```

3. **Connect:**
   - Open Command Palette (Ctrl+Shift+P)
   - Type "Remote-SSH: Connect to Host..."
   - Select "playbuoy-pi"
   - VS Code opens a window connected to the Pi

4. **Edit files directly:**
   - Open `/home/playbuoyadmin/playbuoy-server` folder
   - Edit main.py, test, commit, push — all from VS Code
   - Terminal integrated SSH access

**Advantages:**
- ✅ Full IDE experience on remote machine
- ✅ Integrated git/terminal
- ✅ No file transfer overhead
- ❌ Requires more bandwidth
- ❌ Requires VS Code

---

## Method 4: Automated Deployment Script

The **`tools/scripts/deploy.sh`** script automates the entire process:

```bash
# Simple usage
bash tools/scripts/deploy.sh

# With custom target and branch
bash tools/scripts/deploy.sh playbuoyadmin@192.168.140.7 main

# Or use SSH alias
bash tools/scripts/deploy.sh playbuoy-pi main
```

**What it does:**
1. Verifies you're in a git repo
2. Checks for uncommitted changes
3. Asks for confirmation
4. Pushes to origin
5. Backs up on Pi (timestamped)
6. Pulls changes on Pi
7. Restarts FastAPI service
8. Verifies health check
9. Shows rollback instructions if needed

**Example output:**
```
======================================
PlayBuoy Deployment Script
======================================

Target:  playbuoyadmin@192.168.140.7
Branch:  main
Path:    /home/playbuoyadmin/playbuoy-server

Ready to deploy branch 'main' to 'playbuoyadmin@192.168.140.7'
Continue? (yes/no): yes

Step 1: Pushing to origin...
✓ Pushed to origin

Step 2: Backing up on Raspberry Pi...
✓ Backup created at /home/playbuoyadmin/playbuoy-backup-20260420-143022

Step 3: Pulling changes on Raspberry Pi...
✓ Pulled changes

Step 4: Restarting FastAPI service...
✓ Service restarted

Step 5: Verifying health...
✓ Health check passed: {"ok": true}

======================================
✓ Deployment Successful
======================================
```

---

## Method 5: GitHub Actions (For Future CI/CD)

Automatically deploy when you push to main:

```yaml
# .github/workflows/deploy.yml
name: Deploy to Raspberry Pi

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Deploy to Pi
        uses: appleboy/ssh-action@master
        with:
          host: ${{ secrets.PI_HOST }}
          username: ${{ secrets.PI_USER }}
          key: ${{ secrets.PI_SSH_KEY }}
          script: |
            cd /home/playbuoyadmin/playbuoy-server
            git pull origin main
            sudo systemctl restart playbuoy-api
```

(To be implemented later)

---

## Troubleshooting

### "Permission denied (publickey)"
**Problem:** SSH key not configured

**Solution:**
```bash
# Option 1: Add SSH key
ssh-copy-id -i ~/.ssh/playbuoy_rsa playbuoyadmin@192.168.140.7

# Option 2: Use password (prompted)
ssh playbuoyadmin@192.168.140.7  # Will ask for password
```

### "Git pull fails: could not read Username"
**Problem:** Git doesn't have credentials for GitHub

**Solution:**
```bash
# On Raspberry Pi, configure git
ssh playbuoyadmin@192.168.140.7
git config --global user.email "you@example.com"
git config --global user.name "Your Name"

# If using HTTPS (not SSH):
git config --global credential.helper store
# Will prompt for credentials next push
```

### "Service failed to restart"
**Problem:** Code syntax error

**Solution:**
```bash
# Check logs
ssh playbuoyadmin@192.168.140.7 "sudo journalctl -u playbuoy-api -n 50"

# Rollback from backup
ssh playbuoyadmin@192.168.140.7 "rm -rf /home/playbuoyadmin/playbuoy-server && mv /home/playbuoyadmin/playbuoy-backup-20260420-143022 /home/playbuoyadmin/playbuoy-server && sudo systemctl restart playbuoy-api"
```

### "Port 8000 already in use"
**Problem:** Old process still running

**Solution:**
```bash
ssh playbuoyadmin@192.168.140.7 "sudo lsof -i :8000 && sudo kill -9 <PID>"
```

---

## Recommended Workflow for Claude Code

1. **Edit files locally** in the repo
2. **Test locally** if possible (run FastAPI on your machine)
3. **Commit changes** with clear messages
4. **Push to branch** (`git push origin main`)
5. **Deploy to Pi** using:
   ```bash
   bash tools/scripts/deploy.sh playbuoy-pi main
   ```
6. **Monitor logs** after deployment:
   ```bash
   ssh playbuoyadmin@192.168.140.7 "sudo journalctl -u playbuoy-api -f"
   ```

---

## Quick Commands Reference

```bash
# View Pi logs in real-time
ssh playbuoyadmin@192.168.140.7 "sudo journalctl -u playbuoy-api -f"

# Restart service
ssh playbuoyadmin@192.168.140.7 "sudo systemctl restart playbuoy-api"

# Check service status
ssh playbuoyadmin@192.168.140.7 "sudo systemctl status playbuoy-api"

# View database
ssh playbuoyadmin@192.168.140.7 "sqlite3 /home/playbuoyadmin/playbuoy-server/playbuoy.db 'SELECT COUNT(*) FROM data;'"

# Run health check
curl http://192.168.140.7:8000/health

# Deploy using script
bash tools/scripts/deploy.sh playbuoy-pi main
```

---

## References

- SSH config guide: https://linux.die.net/man/5/ssh_config
- VS Code Remote SSH: https://code.visualstudio.com/docs/remote/ssh
- Git over SSH: https://docs.github.com/en/authentication/connecting-to-github-with-ssh
