# TEAM WORK DISTRIBUTION

The source PDF names four participants but does not assign implementation ownership. This is a proposed
functional distribution for development, demonstration, and viva preparation, not a claim of past contributions.

## Participant 1 — Aayush Sarraf (241IT001)

**Primary responsibility:** user management and secure account lifecycle.

- **Modules:** 0.1 registration, verification, login, JWT/refresh sessions, recovery, profile management.
- **Frontend responsibility:** Auth pages and forms, route guards, session state, profile/security page.
- **Backend responsibility:** auth/profile routes, password hashing, lockout, expiry, refresh rotation, email links.
- **Database responsibility:** users, sessions, action_tokens; unique email and account-deletion relationships.
- **Testing responsibility:** invalid login, lockout, verification/reset expiry and reuse, logout revocation,
  password/email changes, profile deletion, user/admin authorization boundaries.
- **Integration:** supplies current-user dependencies and session handling to every protected module.

## Participant 2 — Aditya Raj (241IT006)

**Primary responsibility:** file upload, source detection, parsing, and attribute inference.

- **Modules:** 0.2 upload/format detection; 0.3 CSV/ARFF readers, inference, schema extraction/review.
- **Frontend responsibility:** drag/drop upload, file selector, parsing controls, detected-format banner, input grid.
- **Backend responsibility:** UTF-8 decoding, bounded upload, CSV options, ARFF headers/data, ordered Dataset,
  numeric/date/nominal/string classification.
- **Database responsibility:** uploads metadata and parsing configuration; read system limits.
- **Testing responsibility:** size/extension/encoding rejection, quoted commas/newlines, header/no-header parsing,
  comments, sparse rejection, date and nominal inference, source detection.
- **Integration:** produces the format-independent Dataset consumed by the conversion and validation modules.

## Participant 3 — Deepanshu Kumar (241IT020)

**Primary responsibility:** conversion correctness, schema overrides, and validation/error reporting.

- **Modules:** 0.4 conversion engine and writers; 0.5 structural/type validation, fatal reports, abort handling.
- **Frontend responsibility:** editable schema table, nominal/date metadata, conversion controls, error notifications.
- **Backend responsibility:** override validation, ARFF relation/attribute/data writing, RFC 4180 CSV writing,
  missing-value/escaping rules, numeric lexical preservation, atomic output staging.
- **Database responsibility:** validation events and conversion transaction boundaries, coordinated with participant 4.
- **Testing responsibility:** CSV–ARFF–CSV round trips, precision, quoted question marks, duplicates,
  invalid overrides, no partial output, WEKA compatibility, core performance benchmark.
- **Integration:** returns validated output and metadata to history/preview/download; receives schemas from participant 2.

## Participant 4 — Dhruv Agarwal (241IT026)

**Primary responsibility:** delivery, history, administration, and operations.

- **Modules:** 0.6 preview/download/history; 0.7 accounts/activity/configuration; shared application shell and setup.
- **Frontend responsibility:** landing/course/team/footer, dashboards, history/filter/delete, download controls,
  admin accounts/limits/logs, responsive navigation.
- **Backend responsibility:** owner-only download, history queries/deletion, admin account actions, aggregates,
  configuration changes, retention cleanup, health endpoint.
- **Database responsibility:** conversions and system_config; schema initialization/export and backup procedures.
- **Testing responsibility:** download authorization/expiry, history search/deletion, role restrictions,
  admin configuration, browser end-to-end workflow, desktop/mobile layout, reproducible setup.
- **Integration:** coordinates final frontend/backend wiring and release documentation with all three members.

## Viva responsibility summary

| Participant | Be prepared to explain and demonstrate |
| --- | --- |
| Aayush | Why JWT still needs revocation metadata; bcrypt versus plaintext; email verification; reset/refresh token hashing and rotation; RBAC |
| Aditya | CSV versus ARFF; upload checks; readers and internal representation; full-column inference; parsing configuration and missing values |
| Deepanshu | Lossless numeric text; ARFF header/data syntax; quoting/newline escapes; schema override rejection; atomic conversion; WEKA and round-trip evidence |
| Dhruv | D1–D6 stores; history ownership; authenticated file delivery; administrative limits; retention/backup/HTTPS; dashboards and end-to-end demonstration |

All members should explain the seven-module structure, React → REST → FastAPI → PostgreSQL/temp storage
architecture, all 18 functional requirements, and the documented exclusions and verification limits.
