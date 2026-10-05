# Verification results

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

For actual WEKA verification, install Java 11+ and obtain the official
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
