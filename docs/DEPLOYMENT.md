# Deployment and operations

## HTTPS deployment

Local development binds only to loopback over HTTP. For a public deployment, use an actual hostname,
DNS pointing to the server, inbound ports 80/443, and Caddy with the supplied `deploy/Caddyfile`.
Set `SITE_DOMAIN` to that hostname and `FRONTEND_DIST` to the absolute `frontend/dist` directory.
Set `FRONTEND_ORIGIN=https://your-hostname` in `.env`. Caddy obtains/renews TLS certificates and serves
the React build while proxying `/api/*` to a private FastAPI listener on `127.0.0.1:8000`.

```text
cd frontend
npm ci
npm run build
cd ..
python -m backend.manage init-db
python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
caddy run --config deploy/Caddyfile
```

Run backend/Caddy under your platform's service manager with automatic restart. Use a dedicated OS
account and a PostgreSQL role restricted to the application database. Keep `.env` and `.runtime` outside
the web root with access limited to that account. Do not seed demo accounts on a public service.
The included helper's cluster is for local development, not a production database provisioning policy.

The proxy caps requests at 52 MB including multipart overhead; the application caps dataset bytes at
the administrator-selected limit up to 50 MB. Proxy response timeout is 60 seconds. Restrict direct
backend access, and retain the default CORS origin restriction. Use same-origin HTTPS rather than
loosening CORS. The provided CSP permits only local scripts and the optional Google Fonts styles/fonts.

## SMTP

Set `MAIL_MODE=smtp` and the SMTP host/port/sender credentials. Set `SMTP_STARTTLS=true` for a provider
using STARTTLS (typically port 587). This implementation supports SMTP plus STARTTLS, not implicit SMTPS
port 465. Use the provider's app password/token, not a personal account password. Email sending runs as
a background task with a 10-second socket timeout; status is visible in admin logs. A resend-verification
form and repeatable reset request recover from failed delivery. For higher reliability, replace in-process
delivery with a durable queue; no durable-queue guarantee is claimed here.

## Backup and restore

`scripts/backup.py` invokes PostgreSQL's `pg_dump -Fc`; credentials are passed through the subprocess
environment, never embedded in shell command text. The backup includes accounts, token hashes, configuration,
and history metadata; temporary dataset files are deliberately not backed up.

```powershell
.\.venv\Scripts\python.exe scripts\backup.py
```

Schedule this command daily with Task Scheduler (Windows) or cron/systemd timers (Linux). For Windows,
create a daily task at 02:00 with program `C:\absolute\project\.venv\Scripts\python.exe`, arguments
`scripts\backup.py`, and **Start in** `C:\absolute\project`. Run it under the service account and check
its exit code. For Linux, schedule an equivalent command that first changes to the project directory.
Scheduling is an explicit deployment step; no recurring OS task was installed by project generation.

Store encrypted backup copies off-host according to institutional policy and prune old backups.
Restore into a newly created database rather than overwriting a working database:

```text
createdb -h HOST -U ADMIN converter_restore
pg_restore -h HOST -U ADMIN -d converter_restore --no-owner .runtime/backups/TIMESTAMP.dump
```

Validate `/api/v1/health`, account login, and history in the restored database before switching
`DATABASE_URL`. Rotate JWT_SECRET after a recovery incident to invalidate prior signed access tokens.
Do not promise a two-hour recovery objective without rehearsing the procedure on your host.

## Retention and health

The backend sweeps expired uploads/outputs every 30 seconds. Requests reject expired downloads immediately;
physical removal follows in the next sweep. An expired output's history metadata remains until explicitly
deleted. Lowering the retention setting shortens outstanding deadlines; increasing it does not resurrect
expired files. Account and history deletion remove their applicable files.

```text
python -m backend.manage cleanup
```

Schedule cleanup independently if the backend may be stopped during retention deadlines. Health monitoring
should request `/api/v1/health` at a reasonable interval and alert on failed status/database connectivity.
Check disk space, database connections, application logs, backup freshness, and SMTP failures. Apply security
updates regularly and rerun the automated tests before deployment.

## Capacity scope

The demonstrated runtime uses one FastAPI process and a SQLAlchemy connection pool. The HTTP rate limiter
is per-process/IP (40 auth requests or 240 other requests/minute), with per-account lockout in PostgreSQL.
Large institutional shared-IP deployments may need different limits and a shared limiter. Before scaling
to multiple workers or asserting 200 concurrent users, measure memory for your actual datasets, pool sizes,
upload latency, concurrency, rate-limit behavior, and 2,000 conversions/day. The core timing measurement
is evidence of conversion speed only, not an availability or concurrency SLA.
