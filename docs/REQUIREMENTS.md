# Requirement traceability

## Source review

Reviewed the complete 28-page `FINAL_IT303.pdf`: SRS pages 1–14, DFD design pages 15–23,
structure chart pages 24–25, and data dictionary pages 26–28. DFD and structure-chart pages were
rendered and visually inspected because their labels were embedded in images.

The system is a private web-based CSV/ARFF data-preparation application for students, researchers,
and data analysts. Administrators manage accounts and limits. Email is an external service.
The project explicitly excludes model training, statistical analysis, other formats, and sparse ARFF.

## Functional requirements → implementation

All backend paths below are prefixed by `/api/v1`.

| Requirement / source page | Module / DFD | UI | Backend/API | Database / storage |
| --- | --- | --- | --- | --- |
| FR-001 Registration, verification, duplicate email/password rules — p7 | 0.1.1–0.1.2 | `/register`, `/verify`, `/resend` | POST `/auth/register`, `/auth/verify`, `/auth/resend-verification` | users, action_tokens, email events, SMTP/local outbox |
| FR-002 Login, signed tokens, recovery, lockout — p7 | 0.1.3–0.1.5 | `/login`, `/forgot`, `/reset` | POST `/auth/login`, `/auth/forgot-password`, `/auth/reset-password` | users, sessions, action_tokens |
| FR-003 Inactivity, logout, route protection — p8 | 0.1.4 / Level-3 JWT | AuthProvider, Protected, sign-out | bearer dependency, POST `/auth/refresh`, `/auth/logout` | sessions with refresh hashes and last_seen |
| FR-004 Profile, password change, account removal — p8 | 0.1.6 | `/profile` | PATCH/DELETE `/profile`, POST `/profile/password` | users; cascaded sessions/history/uploads/tokens; file cleanup |
| FR-005 File upload, extension/size/encoding — p8 | 0.2.1 | file selector, drag/drop, limit label | POST `/uploads`; bounded read, UTF-8 decoding | uploads, system_config, temporary input |
| FR-006 Source detection and direction banner — p8 | 0.2.2–0.2.3 | schema direction badge | `engine.detect` | uploads.source_format |
| FR-007 Parsing options and defaults — p8 | 0.3.1 | delimiter, quote, header, relation form | ParsingOptions schema | uploads.options |
| FR-008 CSV parsing, quoting/newlines, missing values — p8 | 0.3.1 | input grid | `readers.csv_reader` | in-memory Dataset; private input only |
| FR-009 Numeric/nominal/date/string inference — p8 | 0.3.3 / Level-3 | schema table and nominal sets | `inference.infer` | system_config.nominal_threshold |
| FR-010 Editable names/types; inconsistent override rejection — p8 | 0.3.4 | schema table and errors | POST `/conversions`; `engine.override` | full dataset revalidated; validation events on failure |
| FR-011 CSV → ARFF — p8 | 0.4.2 / Level-3 | Convert to ARFF | `writers.arff_writer` | complete temporary output |
| FR-012 Dense ARFF parser/types/comments — p8–9 | 0.3.2 / 0.4.1 | upload and input grid | `readers.arff_reader`, liac-arff header integration | Dataset; original numeric text preserved |
| FR-013 ARFF → CSV — p9 | 0.4.3 | Convert to CSV | `writers.csv_writer`; RFC 4180 output | complete temporary output |
| FR-014 Fatal input/type validation, line context — p9 | 0.5.1–0.5.4 / Level-3 | dedicated error notification | `validation.validate`, ConversionError, 400 handler | events (no partial conversion history/output) |
| FR-015 Output preview, row/column counts — p9 | 0.6.1 | generated text + counts | POST `/conversions` response | in-memory preview; metadata in conversions |
| FR-016 Named authenticated download — p9 | 0.6.2 | Download buttons | GET `/conversions/{id}/download` | owner-checked conversion and file expiry |
| FR-017 Metadata/history/reverse order/deletion — p9 | 0.6.3–0.6.5 | `/history`, `/dashboard` | GET `/history`, GET `/dashboard`, DELETE `/history/{id}` | conversions + output deletion |
| FR-018 Accounts, aggregate activity, limits, role restriction — p9 | 0.7.1–0.7.3 | `/admin` | GET `/admin`, PATCH/DELETE `/admin/users/{id}`, PUT `/admin/config` | users, sessions, conversions, events, system_config |

## Data stores and flows

| DFD store | Implementation | Contents / movement |
| --- | --- | --- |
| D1 User DB | users | registration/profile writes; login/status reads; administrative actions |
| D2 Session Store | sessions, action_tokens | signed JWT references persisted session; rotating refresh hash; one-use action tokens |
| D3 Temp File Storage | STORAGE_DIR + uploads metadata | multipart bytes → parsed Dataset → fully validated output → authenticated download → expiry cleanup |
| D4 Conversion History DB | conversions | completed conversion metadata → dashboard/history/admin activity; per-user delete |
| D5 Validation Logs | events with kind=validation | fatal defect, physical source line, attribute, description; no dataset rows stored |
| D6 System Config | system_config | admin limits → upload validator, inference engine, file retention |

User forms send JSON except uploads (multipart). APIs return JSON metadata/errors and download responses
return file bytes. React never performs parsing/inference/conversion. Original numeric strings remain in
the shared representation, avoiding binary floating-point rounding during conversion.

## Structure chart and Level-3 details

The root transaction-control module is FastAPI routing plus the React application shell. The seven
branches map to the README module table. The reader/inference/validation/writer separation mirrors
the chart's children without inventing a separate service for each box.

- JWT: payload assembly → HS256 signing → random refresh generation → hashed metadata storage → response.
- Inference: numeric parse check → ordered distinct count → classification → nominal value enumeration.
- ARFF writer: relation → ordered attributes → data → quote/escape and missing-value encoding.
- Error reporting: parser/type defect → line/attribute annotation → fatal classification → logged error and abort.

## Conflicts and implementation decisions

1. **Date inference:** Level-3 DFD lists numeric/nominal/string; SRS FR-009 also requires date. Date is included.
2. **Session storage:** the appendix calls JWT stateless, but logout revocation/inactivity and DFD D2 require
   persisted metadata. Short-lived signed JWTs reference database sessions; refresh tokens rotate and
   are stored only as hashes. This supports real revocation rather than client-only logout.
3. **User management chart:** its shortened branch shows registration/login/JWT; SRS profile, recovery,
   verification, and DFD Level-2 requirements are also implemented.
4. **History status:** successful conversions create completed history; fatal attempts write validation
   events. This follows the appendix's successful-conversion ACID rule without publishing partial records.
5. **CSV output:** RFC 4180 wins over input delimiter/quote preferences (C-003); all generated CSV uses
   comma, double quote escaping, and CRLF. Those options apply only when reading CSV.
6. **Empty values:** CSV empty fields are missing by FR-008. Empty ARFF strings consequently lose that
   distinction through CSV, which is documented instead of claiming a mathematically impossible guarantee.
7. **Names/course:** PDF names take precedence over fallback spelling; the course comes from the pasted prompt.
8. **Email activation:** verification and administrative active status are separate. Reactivation never
   bypasses email verification. Admins cannot delete/suspend administrator accounts through this demo UI.
9. **Threshold/defaults:** nominal distinct count ≤ configured threshold; numeric before date before nominal
   before string; missing values excluded. CSV header required by default; generated names if disabled.

## Non-functional verification and deployment dependencies

| Requirement | Implementation / evidence | Qualification |
| --- | --- | --- |
| NF-001 performance | 100,000-row / 12.3 MB core benchmark in benchmark.json | Upload network latency and concurrent load not certified |
| NF-002 capacity | Configurable cap up to 50 MB; synchronous conversion on worker threads | 200 concurrent users and daily throughput need load testing |
| NF-003 reliability | validated output, atomic rename, DB transactions, rollback cleanup, error handlers | No availability/recovery SLA established by local testing |
| NF-004 availability | health endpoint and deployment monitoring instructions | Hosting/supervision/maintenance scheduling is an operator responsibility |
| NF-005 authentication | salted bcrypt; 24h idle expiry; logged admin access | Verified by API tests |
| NF-006 data protection | ownership, private storage, expiry, restricted CORS, ORM queries, escaped React rendering | HTTPS configured by deployment proxy; loopback demo uses HTTP |
| NF-007 maintainability | seven modules, separate readers/writers, unit + API + browser tests | Python source formatted and linted; React formatted |
| NF-008 portability | cross-platform Python/Node; environment database URL | Tested on Windows/Python 3.12/Chrome; targets Python 3.11+ |
| NF-009 integrity | string numeric representation, ordered attributes, round-trip tests | WEKA's own floating-point display can round; CSV empty-string ambiguity remains |
| SI-001 libraries | pandas inference, stdlib csv, liac-arff headers, custom precision-preserving row codec | Explicit supported date-pattern set |
| SI-003 email | background SMTP, local outbox, accepted/failed delivery events | Real provider delivery not tested; queue not crash-durable |
| CI-001/API | `/api/v1`, 400/401/403/404/410/413/429 statuses, bearer protection | OpenAPI at `/docs` |
| Operations | backup script, health endpoint, 30-second cleanup sweep, deployment guide | Daily scheduler/HTTPS not installed on this user's machine |
