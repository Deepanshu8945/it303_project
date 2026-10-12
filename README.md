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
- Last login sidebar tab with a list of the current user's latest 100 successful sign-ins, including time, server-observed IP address, and browser/device information.
- Login and registration pages show only the display names of the five most recently signed-in users in the left panel, replacing the promotional copy.
- Single-file CSV/ARFF uploads; extension, encoding, size, and structural validation.
- CSV delimiter, quote character, header-row flag, and relation-name configuration.
- Numeric, nominal, date, and string inference; editable attribute names and types.
- Bidirectional conversion with numeric lexemes preserved, missing-value handling, and line-level errors.
- Input grid and generated-output previews; authenticated downloads.
- Automatic verification of complete output before download: WEKA checks ARFF, Python's CSV reader checks CSV, and dataset comparison checks preservation.
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

See [requirement traceability](docs/REQUIREMENTS.md) for every FR-001–FR-021 and the DFD data-store mapping.

### Updating an existing installation for Last login

From `codebase`, run `.\.venv\Scripts\python.exe -m backend.manage init-db`, then restart the backend.
This adds the `login_activity` and `login_history` tables without changing existing account/conversion
tables, and copies any two login records retained by the previous version into the new list. Rebuild the
frontend with `npm.cmd run build` from `frontend` if you serve the built app; the Vite development
server picks up source changes. Render's Docker startup runs database initialization on deployment.

Sign out and sign in to record a login after the update, then open **Last login** in the sidebar.
The page lists up to 100 successful sign-ins, newest first. Older sign-ins that were never recorded
cannot be reconstructed. Repeated database initialization does not duplicate migrated records.
Records survive logout, password changes, and restarts, and are removed when the account is deleted.
Failed sign-ins and session refreshes do not update them. Times display in the browser's local time
zone. IP addresses come from the server connection (or its configured trusted proxy); local development
may show a loopback address. Browser/device information is the browser-supplied user-agent string.

If the names panel shows no users after a successful login, check
`http://localhost:5173/api/v1/auth/recent-users`. A 404 means the backend is running an older version:
stop and restart it from this `codebase` folder. The frontend and backend must both use the updated code.
Use `--reload` with the local uvicorn development command to pick up future source edits.

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
│   │   └── pages/{Landing,Auth,Dashboard,Converter,History,Profile,LastLogin,Admin}.jsx
│   └── tests/workflow.spec.js
├── database/{README.md,schema.sql}
├── samples/{students.csv,weather.arff,invalid.csv}
├── scripts/{local_postgres.py,backup.py,export_schema.py,benchmark.py,verify_weka.py,WekaCheck.java}
├── deploy/Caddyfile
└── docs/{REQUIREMENTS.md,TEAM.md,TESTING.md,DEPLOYMENT.md,benchmark.json,screenshots/}
```

Python package directories also contain `__init__.py`. Generated `.venv`, `.runtime`, `node_modules`,
`dist`, test output, and intermediate PDF images are ignored.

## Setup from scratch — Windows Command Prompt

Follow these steps in order for a new local demonstration installation. Commands in this section use
**Command Prompt (`cmd.exe`)**, not PowerShell. All project files, dependencies, and database data stay
in your extracted `codebase` directory. No Docker is required.

### 1. Install the prerequisites

Install Python **3.12 or 3.13**, Node.js **22+** (including npm), PostgreSQL **17 or 18**, and a
Java **JDK 11+** supporting source-file launch. Python 3.13, PostgreSQL 18, and Java 22 were tested
on this machine. Enable Python's PATH/launcher options and Java/Node PATH options in their installers.
The PostgreSQL helper detects a standard `C:\Program Files\PostgreSQL\<version>\bin` installation;
for a custom installation, add its `bin` directory to PATH. Installing WEKA's desktop GUI is unnecessary.

Open a **new Command Prompt after installation**, and check:

```bat
py -3.13 --version
node --version
npm.cmd --version
java -version
javac -version
```

If you installed Python 3.12, use `py -3.12` instead of `py -3.13` in this guide.

### 2. Extract the project and enter the right folder

Extract/copy the project to a permanent folder. Open the `codebase` directory containing `backend`,
`frontend`, `scripts`, and this README. For this checkout:

```bat
cd /d "C:\Users\DIPANSHU KUMAR\Desktop\projects\it303_project\codebase"
dir backend\requirements.txt
dir frontend\package.json
```

Replace the path with your own extracted `codebase` location. Run the backend/setup commands from
this directory, not its parent. Do not reuse a copied `.venv` or `node_modules` from another machine;
create/install them locally in the next step.

### 3. Install Python and frontend dependencies

```bat
py -3.13 -m venv .venv
.\.venv\Scripts\python.exe --version
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
.\.venv\Scripts\python.exe -m pip check
cd frontend
npm.cmd ci
cd ..
```

Wait for each command to finish successfully before continuing. Calling the environment's Python
directly means you do not need to activate it. `pip check` should report no broken requirements.

### 4. Install the required WEKA verifier

Create the runtime folder and download the official WEKA 3.8.6 JAR **before running `seed`**:

```bat
if not exist .runtime mkdir .runtime
curl.exe --fail --location "https://repo.maven.apache.org/maven2/nz/ac/waikato/cms/weka/weka-stable/3.8.6/weka-stable-3.8.6.jar" --output ".runtime\weka-3.8.6.jar"
dir .runtime\weka-3.8.6.jar
```

The file should be **9,779,141 bytes**, not empty or an HTML download page. If curl fails, download
the [official WEKA JAR](https://repo.maven.apache.org/maven2/nz/ac/waikato/cms/weka/weka-stable/3.8.6/weka-stable-3.8.6.jar)
in your browser and save it at exactly `.runtime\weka-3.8.6.jar`; check that Windows did not add another extension.
WEKA and Java are required for CSV → ARFF verification and sample seeding. CSV output uses Python's CSV reader.

### 5. Create and start the local database

For a **fresh local setup**, do not copy `.env.example` or an old `.env` to `.env` first. The helper
generates `.env` with matching database credentials and random secrets itself:

```bat
.\.venv\Scripts\python.exe scripts\local_postgres.py start
```

Wait for `Project PostgreSQL ready on 127.0.0.1:55432`. This creates a separate PostgreSQL cluster in
`.runtime\postgres`, the application and test databases, `.env`, and `.runtime\demo-credentials.txt`.
It does not change your existing PostgreSQL service. The database must be running before `init-db`,
`seed`, or the backend can connect.

If it says **"An .env already exists"**, use the troubleshooting section below. An `.env` backup
contains settings, not database contents. For an existing external database, follow the alternate
database instructions below instead of this automatic setup.

### 6. Create the tables and demo accounts

```bat
.\.venv\Scripts\python.exe -m backend.manage init-db
.\.venv\Scripts\python.exe -m backend.manage seed
type .runtime\demo-credentials.txt
```

Expected messages: `Database schema initialized.` and
`Demo accounts and sample conversion history are ready.` Both commands are safe to rerun;
seeding reuses existing accounts and does not reset their passwords.

Use `student@example.com` for the user account or `admin@example.com` for the administrator,
with the corresponding generated password in `.runtime\demo-credentials.txt`.

### 7. Start the backend — terminal 1

From `codebase`:

```bat
.\.venv\Scripts\python.exe -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
```

Keep this terminal open. Wait for `Application startup complete`, then open the
[health check](http://127.0.0.1:8000/api/v1/health). It should report `"status":"ok"` and
`"database":"connected"`. [API documentation](http://127.0.0.1:8000/docs) is also available.

### 8. Start the frontend — terminal 2

Open a second Command Prompt:

```bat
cd /d "C:\Users\DIPANSHU KUMAR\Desktop\projects\it303_project\codebase\frontend"
npm.cmd run dev -- --port 5173 --strictPort
```

Replace the path if you extracted elsewhere. Keep this terminal open and visit
[http://localhost:5173](http://localhost:5173). `--strictPort` prevents silently starting on a different port
if 5173 is already occupied.

### 9. Check a complete conversion

Sign in with the generated student credentials, open **File converter**, upload `samples\students.csv`,
review the schema, and click **Convert to ARFF**. Confirm **Verification passed** appears, then download
the ARFF file. Upload `samples\weather.arff` and convert to CSV to check the other direction.
Verification runs on the entire output before successful history and download publication.

### Starting again after closing the app or restarting Windows

Dependencies and WEKA remain installed. Do not recreate `.env` or the database. In terminal 1, enter
`codebase` and run:

```bat
.\.venv\Scripts\python.exe scripts\local_postgres.py start
.\.venv\Scripts\python.exe -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
```

In terminal 2, enter `codebase\frontend` and run:

```bat
npm.cmd run dev -- --port 5173 --strictPort
```

### Stopping the app and releasing its ports

Press **Ctrl+C** in both the backend and frontend terminals. Then, from `codebase`, stop the
project-local database:

```bat
.\.venv\Scripts\python.exe scripts\local_postgres.py stop
```

This releases frontend **5173**, backend **8000**, and database **55432**, while preserving files,
accounts, and configuration for the next run. Closing the browser alone does not stop the servers.
To inspect whether any listeners remain:

```bat
netstat -ano -p tcp | findstr LISTENING | findstr /C:":5173 " /C:":8000 " /C:":55432 "
```

No output means these ports have no TCP listeners. For a background server with no terminal, use
Task Manager to identify the project process using the reported PID and end it. Do not terminate an
unrelated service merely because it uses a port.

### Troubleshooting setup

| Symptom | Cause / action |
| --- | --- |
| `ConnectionTimeout` during `init-db` or backend startup | Start PostgreSQL with `scripts\local_postgres.py start` first. If it still fails, check `.runtime\postgres.log` and that `.env` points to the intended database. `init-db` creates tables; it does not start PostgreSQL. |
| `An .env already exists` | The database folder is absent but `.env` exists. For a new demo only, preserve it with `ren .env .env.before-local-setup`, then rerun step 5. Choose a different backup name if that name already exists. Keep the newly generated `.env` active. Recovering old data requires the original database or a database backup, not just `.env`. |
| `VerificationUnavailable: install the WEKA JAR` | Repeat step 4, confirm the file size and run from `codebase`. If `.env` specifies `WEKA_JAR`, use `.runtime/weka-3.8.6.jar` or the correct absolute JAR path. |
| Java missing or verification timeout | Check `java -version` and `javac -version`. Install a JDK 11+ and reopen the terminal. `JAVA_EXECUTABLE` in `.env` can specify the actual Java executable path. |
| `.venv\Scripts\python.exe` is empty or not a valid Windows application | Repair the local environment with `py -3.13 -m venv --upgrade .venv` (or `py -3.12` for your installed version), then rerun dependency installation in step 3 and check the environment's `python.exe --version`. |
| `py`, `node`, `npm`, or `java` not recognized | Install the prerequisite/add it to PATH, then open a new terminal. |
| Port 8000, 5173, or 55432 already in use | Inspect listeners as above and stop the old project instance before starting another. |
| Sign-in fails after restoring an old `.env` | Use the credentials belonging to the active database. A new local database gets newly generated passwords. Restoring old connection settings does not restore accounts. |

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
| `WEKA_JAR` | WEKA JAR path; default `.runtime/weka-3.8.6.jar` |
| `JAVA_EXECUTABLE` | Java executable name/path; default `java` |
| `VERIFICATION_TIMEOUT_SECONDS` | WEKA check timeout; default 30 seconds |

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
- Generated output is verified before storage and successful history publication. ARFF uses WEKA plus exact schema/value comparison; CSV checks every header and cell with Python's CSV reader. The UI displays the verification tool, counts, and any representation warnings.
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

### Required output verifier setup

Install Java 11+ (a JDK supporting source-file launch) and download the official
[WEKA 3.8.6 JAR](https://repo.maven.apache.org/maven2/nz/ac/waikato/cms/weka/weka-stable/3.8.6/weka-stable-3.8.6.jar)
to `.runtime/weka-3.8.6.jar`. No WEKA GUI or trained model is required.
`WEKA_JAR` and `JAVA_EXECUTABLE` can override the paths; `VERIFICATION_TIMEOUT_SECONDS`
defaults to 30. CSV verification requires no additional dependency. A missing verifier or timeout
returns an explicit error and withholds ARFF output; it never reports a skipped check as passed.
WEKA compares numeric values at its native floating-point precision; the additional comparison
checks exact numeric text. Values outside WEKA's finite numeric range are rejected.
CSV cannot carry ARFF type declarations and represents empty strings and missing values as empty fields;
verification checks the expected CSV representation and reports this ambiguity when empty strings occur.

Workflow: upload → review schema → convert → verify complete output → preview/download.

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

For a free hosted demonstration, follow [the complete Render + Supabase deployment guide](docs/FREE_DEPLOYMENT.md).
The repository includes `Dockerfile`, `.dockerignore`, `render.yaml`, cloud private storage, and Brevo
HTTPS email support. The Docker image serves React and the API on one origin and installs Java/WEKA.
Local setup remains the default; cloud settings are supplied through Render environment variables.

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
