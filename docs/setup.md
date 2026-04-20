# PlayBuoy Server — Infrastructure Setup Guide

**Status:** Connected to existing Raspberry Pi deployment  
**Created:** 2026-04-20

## Existing Infrastructure

Your PlayBuoy stack is running on a **Raspberry Pi** with the following configuration:

| Component | Details |
|-----------|---------|
| **Database Server** | PostgreSQL on Raspberry Pi |
| **IP Address** | `192.168.140.7` |
| **SSH Access** | `playbuoyadmin@192.168.140.7` |
| **DNS Provider** | Cloudflare (API managed) |
| **API Key** | Configured for `/upload` endpoint |

## Getting Started (Local Development)

### 1. Set Up Environment Variables

Create a local `.env` file (git-ignored for security):

```bash
cp .env.example .env
```

Edit `.env` and fill in your credentials:
```bash
# From your Raspberry Pi setup:
DB_HOST=192.168.140.7
DB_USER=playbuoyadmin
DB_PASSWORD=<your_postgres_password>
API_KEY=super-secret-key-123
CLOUDFLARE_API_KEY=<your_cloudflare_key>
SSH_USER=playbuoyadmin
```

**⚠️ NEVER commit `.env` to git — it's in `.gitignore` for your protection.**

### 2. Test Database Connection

```bash
npm install  # Install dependencies first

# Test connection to Raspberry Pi PostgreSQL
psql -h 192.168.140.7 -U playbuoyadmin -d playbuoy
```

### 3. Verify Existing Schema

Check what tables/data exist on the Raspberry Pi:

```bash
psql -h 192.168.140.7 -U playbuoyadmin -d playbuoy -c "\dt"
psql -h 192.168.140.7 -U playbuoyadmin -d playbuoy -c "SELECT COUNT(*) FROM measurements LIMIT 5;"
```

### 4. Run Migrations (if needed)

```bash
npm run migrate
```

### 5. Start Development Server

```bash
npm run dev
```

Server will connect to your Raspberry Pi database at `192.168.140.7:5432`.

## Remote Access (SSH Tunneling)

If developing remotely, create an SSH tunnel to the Raspberry Pi:

```bash
ssh -L 5432:localhost:5432 playbuoyadmin@192.168.140.7
```

Then set `DB_HOST=localhost` in `.env` and connect through the tunnel.

## Credentials Reference

Your setup uses the following (stored securely in `.env`):

| Credential | Usage | Security |
|-----------|-------|----------|
| PostgreSQL password | Database authentication | In `.env` (git-ignored) |
| API Key (`super-secret-key-123`) | Buoy `X-API-Key` header validation | In `.env` + environment variable |
| Cloudflare API key | DNS management & certificate renewal | In `.env` (git-ignored) |
| SSH key/password | Raspberry Pi remote management | Local SSH config, never in code |

### Managing Secrets Safely

1. **Never hardcode credentials** in code files
2. **Always use `.env`** for local secrets
3. **Add `.env` to `.gitignore`** (already done ✓)
4. **For CI/CD deployment**, use GitHub Secrets or your deployment platform's credential management
5. **Rotate credentials periodically** and update `.env` locally

## Raspberry Pi Maintenance

### SSH Into Raspberry Pi

```bash
ssh playbuoyadmin@192.168.140.7
```

### Check Database Status

```bash
# On Raspberry Pi:
sudo systemctl status postgresql
sudo systemctl restart postgresql  # if needed
```

### View Logs

```bash
# On Raspberry Pi, PostgreSQL logs:
sudo tail -f /var/log/postgresql/postgresql-*.log

# Application logs (if running):
pm2 logs
```

## Deployment

When deploying to production:

1. **GitHub Secrets** — Store credentials in your GitHub repo's Settings → Secrets → New secret
2. **Docker** — Pass secrets via `docker run -e DB_PASSWORD=$SECRET_PASSWORD ...`
3. **Kubernetes** — Use ConfigMaps/Secrets for credential injection
4. **Environment Variables** — Cloudflare, API keys, database passwords

Example GitHub Actions deployment:

```yaml
env:
  DB_HOST: ${{ secrets.DB_HOST }}
  DB_PASSWORD: ${{ secrets.DB_PASSWORD }}
  API_KEY: ${{ secrets.API_KEY }}
  CLOUDFLARE_API_KEY: ${{ secrets.CLOUDFLARE_API_KEY }}
```

## Troubleshooting

### Database Connection Failed

```bash
# Test network connectivity to Raspberry Pi
ping 192.168.140.7

# Test PostgreSQL port
nc -zv 192.168.140.7 5432

# Check .env file has correct credentials
cat .env | grep DB_
```

### Permission Denied (SSH)

```bash
# Verify SSH key permissions
ls -la ~/.ssh/
chmod 600 ~/.ssh/id_rsa  # if needed
```

### PostgreSQL "peer authentication failed"

Ensure your `.env` has the correct username and password. PostgreSQL on Raspberry Pi may use password-based auth instead of peer.

## References

- [CLAUDE.md](../CLAUDE.md) — Project context
- [README.md](../README.md) — API documentation
- [docs/buoy.md](buoy.md) — PlayBuoy specification
