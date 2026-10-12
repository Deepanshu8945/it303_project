# Deploy the File Converter for free

This guide deploys one Render Docker web service (React + FastAPI + Java/WEKA), a Supabase PostgreSQL
database, and a private Supabase Storage bucket. Brevo delivers verification and password-reset emails
over HTTPS. Your existing local installation remains separate and unchanged.

## 1. Put the source on GitHub

Create an empty GitHub repository. **Use the contents of `codebase` as the repository root**:
`Dockerfile`, `render.yaml`, `backend`, and `frontend` must appear at its top level.
From Command Prompt in your `codebase` folder:

```bat
git init -b main
git add .
git status --short
git commit -m "Prepare file converter deployment"
git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPOSITORY.git
git push -u origin main
```

Replace the GitHub URL with your repository. If this is already a Git repository, use its existing
branch/remote rather than running `git init` again. GitHub may ask you to sign in.
Review `git status` before committing: `.env`, `.env` backups, `.venv`, `.runtime`, `node_modules`,
private datasets, and email messages must not be included. `.gitignore` and `.dockerignore` exclude
the standard local runtime/configuration paths. Do not upload the old project ZIP as the deployment source.

## 2. Create a Supabase Free project

Sign in at [Supabase](https://supabase.com/dashboard) and create a **new dedicated project** on its Free plan.
Choose a strong database password and save it securely. Pick a nearby region and wait until provisioning finishes.

Click **Connect**, select the **Session pooler** connection (IPv4, port **5432**), and copy its URI.
Use the exact username/host shown by Supabase, including the project reference in the username.
Replace the URI's `postgresql://` prefix with `postgresql+psycopg://`, supply the password, and append
`?sslmode=require` (or `&sslmode=require` if the URI already contains a query). Example structure:

```text
postgresql+psycopg://postgres.PROJECT_REF:URL_ENCODED_PASSWORD@POOLER_HOST:5432/postgres?sslmode=require
```

URL-encode special characters in the password (`@`, `:`, `/`, `#`, `%`, etc.). Do not use the direct IPv6
connection or the transaction pooler on port 6543 for this guide. Do not reuse your local `127.0.0.1` URL.
See [Supabase connection guidance](https://supabase.com/docs/guides/database/connecting-to-postgres).

Under **Storage**, create a bucket named **`converter-files`**. Leave **Public bucket disabled**.
Use a bucket dedicated to this app: its orphan cleanup deletes files that have no corresponding app record.
Leave the bucket's size limit at its supported default rather than making it smaller than the app's output.

From the project settings, collect:

- The project URL, such as `https://PROJECT_REF.supabase.co`.
- The **legacy `service_role` API key** (a server-only JWT key), not the `anon`/publishable key.

The backend uses this key for private object access; never put it in a frontend `VITE_` variable.
You do not need Supabase Auth or browser storage policies: the app keeps its own account system and
checks ownership before proxying downloads. Startup enables RLS on its PostgreSQL tables without
adding public access policies, while the database owner connection can access them.

## 3. Set up HTTPS email with Brevo

Create a [Brevo](https://www.brevo.com/) account and enable transactional email. In **Senders**, add
and verify the email address you will send from; complete any sender/domain/account approval the
provider requests. Under **SMTP & API → API Keys**, create an **API key**, not an SMTP password.

Keep the verified sender email and API key for the next step. The app sends real registration and reset
links through Brevo's HTTPS API. Render's Free service blocks common SMTP ports, so the local SMTP
configuration will not work there. Provider quotas and sender approval apply. See
[Brevo transactional email](https://developers.brevo.com/docs/send-a-transactional-email).

## 4. Create the Render Free web service

Sign in at [Render](https://dashboard.render.com/) and connect your GitHub account/repository.
Choose **New → Web Service**, select the repository, choose **Docker**, and select the **Free** instance.

Use these settings:

| Setting | Value |
| --- | --- |
| Name | A unique name you choose, e.g. `your-team-file-converter` |
| Branch | The branch you pushed |
| Root directory | Leave blank when `codebase` contents are the repository root |
| Dockerfile path | `./Dockerfile` |
| Docker build context | `.` |
| Health check | `/api/v1/health` |
| Docker command | Leave blank; the image's startup command handles it |
| Persistent disk | None; datasets persist in Supabase Storage |

If your repository instead contains an outer `codebase` folder, set **Root directory** to `codebase`
and ensure the Dockerfile/build context are resolved within that directory. The supplied `render.yaml`
assumes the recommended repository-root layout.

Add these environment variables in Render's dashboard before deploying. They are **cloud secrets**;
do not commit them or copy the local `.env` into the repository.

| Variable | Value you supply |
| --- | --- |
| `ENVIRONMENT` | `production` |
| `DATABASE_URL` | Supabase session-pooler URI from step 2, with `postgresql+psycopg://` and TLS |
| `JWT_SECRET` | New random secret, at least 32 characters |
| `FRONTEND_ORIGIN` | Exact public HTTPS Render URL, without a trailing slash |
| `STORAGE_BACKEND` | `supabase` |
| `SUPABASE_URL` | Supabase project URL |
| `SUPABASE_SERVICE_ROLE_KEY` | Legacy service-role key from step 2 |
| `SUPABASE_STORAGE_BUCKET` | `converter-files` |
| `MAIL_MODE` | `brevo` |
| `BREVO_API_KEY` | Brevo API key from step 3 |
| `MAIL_FROM` | Bare verified sender email, e.g. `your-verified-email@example.com` |
| `BOOTSTRAP_ADMIN_EMAIL` | Your administrator login email |
| `BOOTSTRAP_ADMIN_PASSWORD` | New private password: at least 12 characters, at most 72 UTF-8 bytes, including uppercase, lowercase, and a number |
| `MAX_UPLOAD_MB` | `5` for an initial small free-tier demonstration |
| `CLEANUP_INTERVAL_SECONDS` | `300` |

Generate `JWT_SECRET` locally using:

```bat
.\.venv\Scripts\python.exe -c "import secrets; print(secrets.token_urlsafe(48))"
```

Render supplies `PORT`. The Dockerfile supplies `FRONTEND_DIST`, `WEKA_JAR`, and a bounded Java heap;
you do not need to download WEKA on Render or specify a separate frontend URL.
Confirm the assigned public URL in Render's dashboard after service creation. If it differs from
`FRONTEND_ORIGIN`, update that variable and redeploy **before testing registration**, so emailed links
lead to the correct site. Do not use `localhost` in cloud settings.

Click **Create Web Service**. Render builds the image, including the frontend and checksum-verified
WEKA JAR, checks that the storage bucket is private, initializes the tables/RLS, creates your private
administrator once, and launches the app. No demo accounts or sample history are automatically seeded.
Redeploying does not reset an existing administrator's password. Change passwords through the app;
changing `BOOTSTRAP_ADMIN_PASSWORD` does not change a previously created account.

**Blueprint alternative:** rename the service in `render.yaml` if desired, then choose **New → Blueprint**
with this repository. It defines the same Free service and prompts for the secret variables; Render
generates `JWT_SECRET`. Confirm `FRONTEND_ORIGIN` against the final assigned URL as above.

## 5. Verify the public deployment

1. Wait until Render marks the service live. Inspect deploy logs if startup fails.
2. Open `https://YOUR_SERVICE.onrender.com/api/v1/health`; expect `status: ok` and `database: connected`.
3. Open the app's base URL and sign in with your private administrator credentials.
4. Register a separate user with an email you control. Open the actual verification email and sign in.
5. Upload `samples/students.csv`, convert to ARFF, confirm **Verification passed**, and download it.
6. Upload `samples/weather.arff`, convert to CSV, and download it.
7. Confirm history and cross-account isolation. Exercise a password-reset email.
8. Redeploy/restart the service, sign in again, and download a file whose retention period has not expired.
   This checks that the file comes from Supabase rather than the ephemeral Render filesystem.

The local tests exercise cloud behavior using a mocked provider. Your actual Supabase permissions,
Brevo delivery, and Render URL must be verified after you create the accounts and provide credentials.
The frontend build, same-origin server, and regression tests passed locally. A local Docker image build
was not completed because Docker Desktop's engine did not respond; check the first Render image build
and startup logs before treating the public deployment as verified.

## Updates and free-tier limits

Push future source changes to the connected branch; Render can automatically build and deploy them.
Secrets and datasets remain in the hosting providers. Database initialization creates missing tables;
it is not a migration system for future schema changes. Back up the hosted database before such changes.

Render Free sleeps after 15 minutes without inbound traffic and loses local writable files on restarts.
The initial page after a cold start can take about a minute. Supabase Free may pause a low-activity
project after seven days; resume it in the dashboard before a presentation. Free quotas/terms can change.
Use a separate demonstration environment for browser tests, as they create conversions and change settings.

Expiration checks still block downloads immediately. Physical file cleanup runs while the backend is
awake; it resumes on startup, so deletion can lag while a Free service sleeps. Supabase capacity and
email/bandwidth quotas limit usage. Start with small datasets; the free instance is not a guarantee
that 50 MB uploads or many simultaneous WEKA processes will fit in memory.

References: [Render Free limits](https://render.com/docs/free),
[Render Docker](https://render.com/docs/docker),
[Supabase Free quotas](https://supabase.com/docs/guides/platform/billing-on-supabase),
[Supabase pausing](https://supabase.com/docs/guides/platform/free-project-pausing).

## Common deployment errors

| Symptom | Check |
| --- | --- |
| Database cannot connect | Use the exact session-pooler host, `postgres.PROJECT_REF` username, URL-encoded password, port 5432, and `sslmode=require`. Resume a paused Supabase project. |
| Private bucket startup check fails | Bucket must exist, be named `converter-files`, and have Public disabled. Use the service-role JWT key from the same project. |
| Administrator bootstrap fails | Supply a valid email and a password within the stated limits. The email must not belong to an existing non-admin account. |
| Registration email does not arrive | Confirm Brevo transactional activation, API key, verified sender/approval, quota, and spam folder. Inspect app email events/Render logs. |
| Email links point to localhost or the wrong host | Fix `FRONTEND_ORIGIN` to the actual HTTPS service URL, redeploy, and request a fresh link. |
| 404 on a frontend page | Confirm Docker build includes `frontend/dist/index.html` and `FRONTEND_DIST` is not overridden incorrectly. |
| Service exits on large conversions | Reduce dataset size/upload limit and inspect memory logs; free resources are limited. |
