# Verification results

## Local recent-users fix and login-history list — 12 October 2026

- Diagnosed the actual localhost app: GET `/auth/recent-users` returned **404** through both
  port 8000 and the Vite proxy on 5173. The running backend had not loaded the new routes.
  Started the updated backend with source reload and the frontend from the real project directory.
- Initialized `login_history` in the configured Supabase database with RLS enabled, preserving
  the latest/previous records available in `login_activity`. Repeated initialization is idempotent.
- **88 backend tests passed.** New coverage includes multiple logins surviving logout, newest-first
  ordering, exclusion of failed attempts and token refreshes, 100-record retention, owner isolation,
  deletion cascade, safe backfill, and history privacy.
- **Two affected Chrome workflows passed** against isolated test databases: public names after
  login/logout, and the private history list retaining three successive logins. Reload, token renewal,
  empty/error states, and mobile overflow were checked. Desktop/mobile screenshots were inspected.
  The names panel also passed a focus-recovery check after a simulated backend error.
- Verified the **regular localhost app through port 5173 using its actual configured Supabase database**:
  recent-users returned HTTP 200, an existing account signed in, authenticated history returned rows,
  logout succeeded, and the user's name remained in the public list. No account or password was created
  or changed for that smoke check. Production build, lint, and formatting passed.

## Names-only sign-in panel — 12 October 2026

- **84 backend tests passed.** The public endpoint returns only display names, sorted by each
  user's latest successful sign-in, limited to five users, without repeating a user. Unverified,
  suspended, and never-signed-in accounts are excluded. Empty results are supported.
- **All eight Chrome workflows passed across isolated batches.** The new workflow checks both
  login/registration panels, removal of promotional text, names-only output, desktop/mobile layout,
  long-name wrapping, HTML escaping, and empty/unavailable states without disabling the forms.
  Existing conversion, administration, private login details, and recovery workflows also passed.
  One initial navigation started before the restarted server was ready; it passed on rerun, and
  subsequent batches waited for the health check before launching Chrome.
- Production build, Python lint, and formatting checks passed. Login/registration screenshots were
  captured, and desktop login plus mobile registration screenshots were visually inspected.
- Verification used the dedicated local cluster and databases described below. No Supabase schema
  or credentials changed for this addition; the existing `login_activity` table supplies the ordering.

## Last-login requirement — 12 October 2026

- **81 backend tests passed**, including seven new integration tests for first-login timestamps,
  previous-login rotation, authentication and account isolation, logout persistence, account-deletion
  cascade, unavailable/long browser metadata, and exclusion of failed/unverified/suspended sign-ins
  and token refreshes. The upgrade test checks repeated initialization, preserved accounts, and RLS
  protection in local mode. Client-supplied forwarded headers do not override the direct test-client address.
- **All seven Chrome workflows passed across two runs.** The new workflow verifies the sidebar,
  protected route, account email, recorded browser/time details, previous-login rotation, page reload,
  refresh, access-token renewal, empty/error/retry states, and mobile overflow. The initial complete
  run hit the existing 40-auth-requests/minute limit during password recovery; recovery and the
  expanded last-login workflow passed in a later isolated batch after the window reset.
- Production frontend build, Python lint, and formatting checks passed. Desktop/mobile screenshots
  were visually inspected: `screenshots/last-login.png` and `screenshots/last-login-mobile.png`.
- Checks ran on this Windows laptop from the actual project directory. A dedicated PostgreSQL
  cluster under `.runtime/login-postgres`, port 55433, kept tests separate from existing databases.
  Backend tests used `file_converter_test`; browser checks used `file_converter_login_ui_test`.
  The existing `.env` and Supabase credentials were not changed by these tests.
- Applied database initialization to the configured Supabase project and confirmed the new
  `login_activity` table exists with RLS enabled. Existing accounts and history were retained.
- Existing installations need `python -m backend.manage init-db` before restarting the backend.
  Render's existing startup runs this automatically. Prior login details cannot be reconstructed;
  recording starts at the next successful sign-in after installing the update.

## Free deployment preparation — 12 October 2026

- Backend regression suite: **74 passed**. Deployment-specific rerun: **10 passed**, including
  private cloud upload/verification/download/delete/expiry, paginated orphan cleanup, provider errors,
  Brevo HTTPS mail, administrator bootstrap/idempotence, PostgreSQL RLS, startup port handling,
  SPA routing, traversal/hidden-file rejection, and configuration validation.
- Frontend production build and Python lint passed. **Six Chrome workflows passed** on isolated
  ports 18000/15173 with local-only email. The initial email workflow failed against an existing
  SMTP-configured server; the isolated rerun passed without changing that server's settings.
- Same-origin smoke check: FastAPI served the built homepage and `/register`, with healthy database/API.
- Cloud provider HTTP responses were mocked. Actual Supabase permissions, Brevo delivery, and the
  public Render deployment must be checked after the owner configures those accounts.
- **Docker image build was not validated locally**: Docker Desktop's engine did not respond to
  bounded readiness checks. Render can build the supplied Dockerfile; its first build/startup is
  an outstanding deployment validation step, not a completed check.

See [FREE_DEPLOYMENT.md](FREE_DEPLOYMENT.md) for account setup, secrets, and public smoke tests.

## Converted-output verification — 11 October 2026

Reverified on Windows with Python 3.13, Java 22, PostgreSQL 18, and Chrome.

| Check | Result |
| --- | --- |
| Complete backend unit and PostgreSQL integration suite | **64 passed** |
| Chrome browser workflows | **6 passed**, including verified ARFF/CSV output and rejected output with no preview/download |
| Frontend production build | Passed |
| Python lint (`ruff check backend scripts`) | Passed |
| Real WEKA compatibility helper | Passed: adversarial ARFF 4 × 3, weather ARFF 3 × 5 |
| 100,000-row benchmark | Verification passed; parse/convert 1.267 s, verification 6.767 s, combined 8.034 s |
| Converter screenshot | Verification message, checked counts, and download button visually inspected |

The automatic gate runs after writing the full output in memory and before publishing a file or
successful history record. WEKA independently loads ARFF and compares relation, ordered schema,
nominal values, dates, cells, missing values, and counts with a source-data manifest. An additional
comparison preserves exact numeric spelling. CSV is reparsed and every header/cell is compared with
the expected representation. Empty ARFF strings generate a CSV representation warning.

Tests cover all seven date patterns, Unicode, escaping, embedded CRLF, literal question marks,
empty strings, missing values, high precision, header-only output, rows beyond the preview,
changed/dropped/reordered data, numeric overflow, missing JAR/Java, timeouts, and bad WEKA reports.
API tests confirm failure/unavailability logs errors and creates no output or history; browser tests
confirm a genuine WEKA rejection displays an error and withholds preview/download.

Install the required WEKA JAR as described in README before reproducing tests. The benchmark includes
verification, but excludes HTTP/database/UI overhead. One existing TestClient deprecation warning
remains; all tests pass with the pinned dependencies.

## Earlier baseline

Verified on **5 October 2026**, Windows, Python 3.12, Node 22.12, PostgreSQL 18, and Google Chrome.

| Check | Result / evidence |
| --- | --- |
| Backend unit and PostgreSQL integration tests | **33 passed** (`python -m pytest`) |
| Browser workflow scenarios | **5 passed**; first four passed in the full run, repaired account-notification scenario passed on targeted rerun |
| Frontend production build | Passed; Vite output generated in `frontend/dist` |
| Python lint | `ruff check backend scripts` passed |
| Frontend formatting | Prettier applied to React, CSS, configuration and browser tests |
| npm dependency audit | 0 reported vulnerabilities after patched dependency installation |
| Python dependency audit | No known vulnerabilities reported after updates |
| WEKA 3.8.6 | Loaded generated sample and adversarial ARFF plus sample weather ARFF |
| Core performance | 100,000 rows, 12,327,812 input bytes, 1.011 seconds for parse + conversion |
| PostgreSQL backup | `scripts/backup.py` successfully produced a custom-format pg_dump archive |
| Visual inspection | Desktop landing and converter plus mobile converter screenshots inspected; no horizontal viewport overflow in browser assertions |

## Backend coverage

- CSV and ARFF readers, writers, inference, name/type overrides, and CSV–ARFF–CSV round trips.
- High-precision numbers, exponent spelling, literal question marks versus missing values, Unicode,
  embedded delimiters, quotes, backslashes, newlines, and preserved embedded CRLF bytes.
- Missing-only single-column rows, no-header CSV, configurable delimiters/quotes, RFC 4180 output.
- Malformed rows/headers, duplicate names, invalid dates/types/nominal values, sparse ARFF rejection,
  unsupported extensions, non-UTF-8 and binary content, oversized uploads and streamed bodies.
- Database health, valid/invalid login, role guards, lockout, signed token validation, refresh rotation,
  inactivity expiry, logout revocation, verification/recovery, profile updates and deletion.
- Full upload → schema → conversion → download → history → filter → deletion workflow.
- Cross-user and administrator dataset isolation, system settings, account suspension/reactivation/deletion,
  validation logs, retention expiry, and history surviving file expiry.

The test database is recreated between integration tests. Its name must end in `_test`; application
database records are not used for those tests. Browser tests use seeded demo accounts and create real
sample conversions. The registration browser test follows actual local `.eml` links and deletes its
temporary account at the end.

## Browser scenarios

1. Landing/team, protected-route redirect, invalid/valid sign-in, dashboard, upload, schema rename/type
   override, ARFF conversion, download, history search/deletion, logout, no uncaught page errors.
2. Malformed-file line-number feedback, ARFF upload, CSV conversion and output preview.
3. Administrator account list, limits save, success message, activity and logs rendering.
4. 390-pixel mobile viewport, no horizontal document overflow, role redirect, converter, mobile sign-out.
5. Registration, actual emailed verification link, actual reset link, new-password sign-in, confirmed
   account deletion, and success message surviving the sign-in redirect.

The fifth scenario initially exposed a confirmation-message routing race; a one-time session message
fixed it and the targeted rerun passed. One test-client deprecation warning recommends `httpx2` in a future
dependency update; the current `httpx` adapter still passes all tests.

Screenshots: `docs/screenshots/landing.png`, `dashboard.png`, `converter.png`, `admin.png`,
`landing-mobile.png`, and `converter-mobile.png`.

## Reproduction

Follow README setup first. With the database running:

```powershell
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe -m scripts.benchmark
```

With both app servers running and Chrome installed:

```powershell
cd frontend
npm.cmd run build
.\node_modules\.bin\playwright.cmd test
```

Optional development checks:

```powershell
.\.venv\Scripts\python.exe -m pip install ruff pip-audit
.\.venv\Scripts\python.exe -m ruff check backend scripts
.\.venv\Scripts\python.exe -m pip_audit --local
cd frontend
npm.cmd audit
.\node_modules\.bin\prettier.cmd --check src tests
```

For actual WEKA verification (now required for CSV → ARFF conversion), install Java 11+ and obtain the official
[weka-stable 3.8.6 JAR](https://repo.maven.apache.org/maven2/nz/ac/waikato/cms/weka/weka-stable/3.8.6/weka-stable-3.8.6.jar),
placing it at `.runtime/weka-3.8.6.jar`. Run:

```powershell
.\.venv\Scripts\python.exe -m scripts.verify_weka
```

The generated adversarial file contains high-precision numeric text, commas, quotes, apostrophes,
backslashes, literal question marks, Unicode, leading/trailing spaces, percent signs, missing values,
dates, and embedded CRLF. Java's WEKA `Instances` parser loaded it as 4 instances × 3 attributes;
the weather sample loaded as 3 × 5. This checks acceptance, while Python round-trip tests check lexical fidelity.

## Limits of this verification

No claim is made that local testing certifies 200 concurrent users, 2,000 daily conversions, 99% uptime,
two-hour recovery, the network upload target, Firefox/Safari/Edge behavior, SMTP inbox delivery, or a
production HTTPS deployment. Backup creation was exercised; a full disaster-recovery rehearsal was not.
The benchmark measures the in-process conversion core on this host and excludes network, database,
and UI latency. Core processing completed below the SRS's 10-second target for the measured dataset.
