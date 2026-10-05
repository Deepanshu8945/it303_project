# File Converter System

Bidirectional CSV ↔ ARFF conversion for preparing datasets for the WEKA workbench.
Built from the SRS, DFDs, structure chart, and data dictionary in **FINAL_IT303.pdf**.

## Course

Software Engineering - IT303, Department of Information Technology, NITK Surathkal.

## Participants

| Participant | Roll number |
| --- | --- |
| Aayush Sarraf | 241IT001 |
| Aditya Raj | 241IT006 |
| Deepanshu Kumar | 241IT020 |
| Dhruv Agarwal | 241IT026 |

Names follow the source PDF. In particular, the PDF spells the fourth participant's surname **Agarwal**.

## Project description and problem statement

General-purpose tools export CSV, while WEKA uses ARFF with an explicit relation and typed attributes.
Manually preparing headers, missing values, quotes, and column types is error-prone. This application lets
authenticated users upload a dataset, inspect and correct its schema, convert it, preview the result,
and download it. PostgreSQL stores account and history metadata; private files expire automatically.

## Features

- Registration with email verification; sign in, rotating refresh tokens, inactivity expiry, and logout.
- Temporary lockout after five failed login attempts; one-hour email password reset links.
- Profile and email editing, current-password confirmation, password changes, and account deletion.
- Single-file CSV/ARFF uploads; extension, encoding, size, and structural validation.
- CSV delimiter, quote character, header-row flag, and relation-name configuration.
- Numeric, nominal, date, and string inference; editable attribute names and types.
- Bidirectional conversion with numeric lexemes preserved, missing-value handling, and line-level errors.
- Input grid and generated-output previews; authenticated downloads.
- Personal conversion history with file-name search, format filters, and confirmed deletion.
- Dashboard with real conversion totals, processed instance counts, recent activity, and retained downloads.
- Administrator account activation/suspension/deletion, aggregate counts, validation/email/access logs,
  and upload/inference/retention configuration.
- Responsive public landing page with course, team, workflow, and copyright footer.

## Actors and user roles

**Registered user:** students, researchers, and data analysts share this role; they manage only their own
profile, uploads, conversions, and history. **Administrator:** manages accounts, activity, and settings;
administrators cannot download another user's dataset. **Email service:** delivers verification/reset
links. PostgreSQL, temporary storage, and WEKA are supporting systems, not extra application roles.

## Technology stack

The stack is mandated by SRS C-001: **React**, **Python/FastAPI**, and **PostgreSQL**.
Vite builds the frontend; React Router handles navigation. SQLAlchemy provides the ORM. Python `csv`,
pandas, and liac-arff support parsing and inference. bcrypt hashes passwords, and PyJWT signs access tokens.
The code uses Python 3.11+ (tested on 3.12), Node 22+, and PostgreSQL 17+ (tested on 18).
Exact direct dependency versions are in `backend/requirements.txt`; the frontend lockfile is committed.

## Architecture and modules

The browser calls `/api/v1` REST endpoints through the frontend's same-origin proxy. All conversion logic
lives on the backend. Readers build one format-independent `Dataset` containing relation, ordered
attributes, original string values, and source line numbers. Validation and inference operate on that
representation; writers emit complete output before it is published to storage.

| Structure chart branch | Implementation |
| --- | --- |
| 0.1 Manage User Account | `routes/auth.py`, `routes/profile.py`, `security.py`, `mail.py` |
| 0.2 Upload & Detect Format | `routes/conversions.py`, `conversion/engine.py` |
| 0.3 Parse & Extract Schema | `conversion/readers.py`, `inference.py`, schema-review UI |
| 0.4 Convert Dataset | `conversion/types.py`, `engine.py`, `writers.py`, `storage.py` |
| 0.5 Validate & Report Errors | `conversion/validation.py`, structured errors, validation events |
| 0.6 Deliver Output & History | preview/download/history endpoints and pages |
| 0.7 Administer System | `routes/admin.py`, administration page |

See [requirement traceability](docs/REQUIREMENTS.md) for every FR-001–FR-018 and the DFD data-store mapping.

## Database

| Table | Purpose and relationships |
| --- | --- |
| `users` | Unique email, bcrypt hash, profile, role, verification/status, lockout, timestamps |
| `sessions` | User FK; refresh-token hash, last activity, session identity used by signed JWT |
| `action_tokens` | User FK; hashed single-use verification/reset token and expiry |
| `uploads` | User FK; file name/size, format, parsing options, temporary-file identity and expiry |
| `conversions` | User FK; formats, file metadata, row/column counts, status, timestamps and expiry |
| `events` | Nullable actor FK; validation, administrative-access and mail-delivery metadata |
| `system_config` | Single configuration row for upload size, nominal threshold, retention |

User-owned rows cascade on account deletion; event actors become null. Dataset content is kept outside
the public web root and is never stored in database rows. See [PostgreSQL schema](database/schema.sql).

## Folder structure

```text
it303_project/
├── FINAL_IT303.pdf
├── README.md
├── .env.example
├── .gitignore
├── pytest.ini
├── ruff.toml
├── backend/
│   ├── requirements.txt
│   ├── manage.py
│   ├── app/
│   │   ├── main.py
│   │   ├── config.py
│   │   ├── database.py
│   │   ├── models.py
│   │   ├── security.py
│   │   ├── mail.py
│   │   ├── storage.py
│   │   ├── middleware.py
│   │   ├── conversion/
│   │   │   ├── types.py
│   │   │   ├── readers.py
│   │   │   ├── inference.py
│   │   │   ├── validation.py
│   │   │   ├── writers.py
│   │   │   └── engine.py
│   │   └── routes/{auth,profile,conversions,admin}.py
│   └── tests/{conftest,test_conversion,test_api,test_body_limit}.py
├── frontend/
│   ├── package.json
│   ├── package-lock.json
│   ├── index.html
│   ├── vite.config.js
│   ├── playwright.config.js
│   ├── src/
│   │   ├── main.jsx
│   │   ├── api.js
│   │   ├── components.jsx
│   │   ├── styles.css
│   │   └── pages/{Landing,Auth,Dashboard,Converter,History,Profile,Admin}.jsx
│   └── tests/workflow.spec.js
├── database/{README.md,schema.sql}
├── samples/{students.csv,weather.arff,invalid.csv}
├── scripts/{local_postgres.py,backup.py,export_schema.py,benchmark.py,verify_weka.py,WekaCheck.java}
├── deploy/Caddyfile
└── docs/{REQUIREMENTS.md,TEAM.md,TESTING.md,DEPLOYMENT.md,benchmark.json,screenshots/}
```

Python package directories also contain `__init__.py`. Generated `.venv`, `.runtime`, `node_modules`,
`dist`, test output, and intermediate PDF images are ignored.

## Installation — Windows PowerShell

Install Python 3.11 or 3.12, Node 22+, and PostgreSQL 17 or 18. Include PostgreSQL `bin` in PATH;
the local database helper also detects a standard Windows PostgreSQL installation.
Run the commands below from this project directory. No Docker is required.

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
cd frontend
npm.cmd ci
cd ..
```

### Database setup and configuration

For a fresh demonstration setup, the helper creates a **separate project-local PostgreSQL cluster**,
binds it only to `127.0.0.1:55432`, creates application/test databases, generates `.env` secrets,
and creates random demonstration passwords. It does not change your existing PostgreSQL service.

```powershell
.\.venv\Scripts\python.exe scripts\local_postgres.py start
.\.venv\Scripts\python.exe -m backend.manage init-db
.\.venv\Scripts\python.exe -m backend.manage seed
Get-Content .runtime\demo-credentials.txt
```

The helper intentionally refuses to overwrite an existing `.env` when initializing a new cluster.
If you already have a configured database, use the existing-database instructions below instead.

### Running the project

Terminal 1, project root:

```powershell
.\.venv\Scripts\python.exe -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
```

Terminal 2:

```powershell
cd frontend
npm.cmd run dev -- --port 5173
```

Open **http://localhost:5173**. API documentation is at http://127.0.0.1:8000/docs and the health check is
http://127.0.0.1:8000/api/v1/health. On later runs, start the local database before the servers with the
same `local_postgres.py start` command. Stop the servers with Ctrl+C. Stop only this project's database:

```powershell
.\.venv\Scripts\python.exe scripts\local_postgres.py stop
```

### Existing PostgreSQL database / Linux / macOS

Create a dedicated `converter` login and `file_converter` database using your PostgreSQL administrator.
For example, in `psql`, run `CREATE USER converter WITH PASSWORD 'your-generated-password';` then
`CREATE DATABASE file_converter OWNER converter;`. Create a separate `file_converter_test` database
with the same owner for automated tests. Never use production data for testing.

Copy `.env.example` to `.env`, set `DATABASE_URL` to the dedicated database, and generate a JWT secret
with `python -c "import secrets; print(secrets.token_urlsafe(48))"`. Set the two demo password variables
to strong passwords of your choosing. Run `python -m backend.manage init-db`, then `python -m backend.manage seed`.
On Linux/macOS, create the environment with `python3 -m venv .venv`, activate it with
`source .venv/bin/activate`, and use `python`, `pip`, and `npm` in place of the Windows executable paths.
The local cluster helper also works when `initdb` and `pg_ctl` are on PATH and it is run by a non-root user.

## Demo login credentials — demo only

| Role | Email | Password |
| --- | --- | --- |
| Registered user | `student@example.com` | Generated value of `DEMO_USER_PASSWORD` in `.env` |
| Administrator | `admin@example.com` | Generated value of `DEMO_ADMIN_PASSWORD` in `.env` |

For the automatic setup, **both exact passwords are in `.runtime/demo-credentials.txt`**. Read them with
the command above. This avoids embedding reusable passwords in application source. Both accounts are
verified and immediately usable. Seeding is idempotent and does not reset existing passwords.
Do not use these demonstration accounts for a public deployment.

## Configuration and email

| Variable | Purpose |
| --- | --- |
| `DATABASE_URL` | SQLAlchemy PostgreSQL URL, using `postgresql+psycopg://` |
| `JWT_SECRET` | Required random signing secret, at least 32 characters |
| `FRONTEND_ORIGIN` | Exact permitted frontend origin and email-link base URL |
| `STORAGE_DIR` | Private filesystem storage; defaults to `.runtime/storage` |
| `SESSION_HOURS` | Inactivity limit; default 24 hours |
| `MAX_UPLOAD_MB`, `NOMINAL_THRESHOLD`, `RETENTION_HOURS` | Initial database configuration; default 50, 20, 24 |
| `MAIL_MODE` | `local` writes development `.eml` messages; `smtp` sends real email |
| `SMTP_HOST`, `SMTP_PORT`, `SMTP_USERNAME`, `SMTP_PASSWORD`, `SMTP_STARTTLS` | Email-provider configuration |
| `MAIL_FROM` | Sender address |
| `DEMO_USER_PASSWORD`, `DEMO_ADMIN_PASSWORD` | Used only by the explicit seed command |

After initialization, administrators change upload, inference, and retention limits in the UI; changing
their initial environment defaults does not overwrite database settings.

In local mail mode, registration and recovery generate real expiring links in `.runtime/outbox/*.eml`.
Open the newest message locally in an email viewer or text editor, and follow its plain-text link.
The outbox is not exposed through an HTTP endpoint. SMTP mode queues sending as a FastAPI background
task, records accepted/failed delivery, and supports requesting another link. SMTP acceptance is not
a guarantee that a provider delivered to the recipient's inbox. Local emails are cleaned after one hour.

## Conversion rules

- CSV defaults: comma, double quote, first row is header, relation derived from file name.
- Empty CSV fields are missing. A literal CSV `?` remains a literal string/nominal value in ARFF.
- Inference checks numeric, then supported date patterns, then nominal distinct count ≤ threshold,
  then string. An entirely missing column is string. The inference runs over all rows.
- Numeric values remain their original strings; no intermediate floating-point conversion occurs.
- CSV output always uses comma, double quote escaping, and CRLF (SRS C-003 takes precedence over parsing options).
- ARFF output includes its full header and correctly escaped values. Only dense ARFF is in scope.
- Supported date patterns are listed in the schema date selector and `conversion/validation.py`.
  Other patterns are rejected explicitly, never silently reinterpreted.
- Fatal validation prevents output and successful-history creation. Failure details go to validation logs.
- Preview shows the full ARFF header and at most 20 data rows; the download contains the full dataset.
- Downloads require ownership, a live session, and unexpired retention. History metadata outlives files.

## Four-person work distribution

See [TEAM WORK DISTRIBUTION and viva responsibilities](docs/TEAM.md). The split assigns complete
functional areas, including frontend, backend, database, and tests, to all four participants.

## DFD / structure chart relationship

The seven branches above implement DFD processes 0.1–0.7. PostgreSQL represents D1, D2, D4, D5, and D6;
private temporary files represent D3. The Level-3 JWT process includes signed access tokens, rotating
refresh tokens, and persisted token hashes. The Level-3 writer includes relation, ordered attributes,
data, quoting, and missing-value encoding. [REQUIREMENTS.md](docs/REQUIREMENTS.md) records diagram
differences and the SRS-first decisions.

## Testing

Start the project-local database, then run from the project root:

```powershell
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe -m scripts.benchmark
cd frontend
npm.cmd run build
.\node_modules\.bin\playwright.cmd test
```

Browser tests require both servers, seeded demo accounts, and Google Chrome. Set Playwright's `channel`
to `msedge` if only Edge is installed, or install Chromium and remove `channel` from its configuration.
Backend integration tests reset **only** the database whose name ends in `_test`. Set `TEST_DATABASE_URL`
to override its connection. Browser tests use the demo application database, create sample conversions,
and test administrator controls; use a demonstration environment.

See [test evidence and limits](docs/TESTING.md). Screenshots are in `docs/screenshots`.

## Deployment and operations

The local demo uses loopback HTTP. Public deployment must use HTTPS; a Caddy reverse-proxy configuration
is included. [DEPLOYMENT.md](docs/DEPLOYMENT.md) covers HTTPS, SMTP, process supervision, daily backups,
health checks, retention, and restore. Build frontend assets with `npm ci` followed by `npm run build`.

## Known limitations

- Sparse/relational ARFF, non-UTF-8 encoding, other file formats, statistics, and model building are outside scope.
- The date parser supports the explicit patterns offered by the UI, not every Java SimpleDateFormat pattern.
- A single application process is the demonstrated deployment. Rate limiting is per-process; multi-worker
  deployments need a shared rate limiter. SMTP background jobs are not durable across process crashes.
- Automatic cleanup runs every 30 seconds while the backend runs. Downloads expire at the exact deadline;
  physical deletion can lag by one sweep. Run the cleanup command under a scheduler if the server is stopped.
- The 200-concurrent-user, 2,000-conversions/day, upload-latency, availability, and recovery targets are not
  certified by the local tests. Production hosting, monitoring, and backup scheduling remain deployment tasks.
- CSV empty strings and missing values share an empty-field representation by SRS FR-008/FR-013; an ARFF
  empty string cannot be distinguished from missing after a CSV round trip. Numeric lexemes are preserved,
  but WEKA itself uses floating-point numbers and may display them at lower precision.
- History and account search return up to 500 results, activity 50, and logs 100. Date values and numeric
  spellings are not normalized. Only the first fatal defect is returned, with line and attribute context.
- Browser verification was performed in Chrome, including mobile viewport tests. Firefox/Safari/Edge
  compatibility and live SMTP delivery require separate environment testing.

## References

- Primary project specification: `FINAL_IT303.pdf`, all 28 pages.
- [WEKA ARFF format](https://ml.cms.waikato.ac.nz/weka/arff.html)
- [RFC 4180](https://www.rfc-editor.org/rfc/rfc4180)
- [FastAPI bearer/JWT authentication](https://fastapi.tiangolo.com/tutorial/security/oauth2-jwt/)
