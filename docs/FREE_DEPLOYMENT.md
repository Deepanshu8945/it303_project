# Free deployment — exact steps

Follow this guide in order. You will get one public HTTPS link for the complete File Converter app.

| Service | Purpose |
| --- | --- |
| GitHub | Holds your source code |
| Supabase | Stores accounts, conversion history, and files |
| Brevo | Sends verification and password-reset emails |
| Render | Builds and runs the app |

Choose the free plans. **You do not need Docker Desktop running on your laptop.** Render builds the image from your repository. The Docker popup does not block this process. [Render Docker documentation](https://render.com/docs/docker)

Commands below run in **Windows Command Prompt (CMD)**. Website instructions run in your browser. Replace example values with your own values; never enter placeholders literally.

## Step 1: Open the correct folder

**Where: Command Prompt on your laptop.**

1. Open Command Prompt.
2. Run:

   ```bat
   cd /d "C:\Users\DIPANSHU KUMAR\Desktop\projects\it303_project\codebase"
   git --version
   dir Dockerfile
   dir render.yaml
   ```

3. If Git is not recognized, install [Git for Windows](https://git-scm.com/download/win), reopen Command Prompt, and repeat these commands.

**Check:** both deployment files exist inside `codebase`.

## Step 2: Create an empty GitHub repository

**Where: [GitHub → New repository](https://github.com/new).**

1. Sign in or create an account.
2. Name the repository `it303-file-converter`, or choose another name.
3. Choose **Private** if you want to keep the code private. You will authorize Render to access it later.
4. Leave the options to add a README, `.gitignore`, and license unchecked.
5. Click **Create repository**.
6. Copy the HTTPS repository URL. It looks like:

   ```text
   https://github.com/YOUR_USERNAME/it303-file-converter.git
   ```

## Step 3: Upload the source code

**Where: Command Prompt, inside `codebase`.**

These commands assume this folder is not already a Git repository. If you already use Git here, keep your existing repository/remote and push your existing branch instead.

1. Run:

   ```bat
   git init -b main
   git add .
   git status --short
   ```

2. Review the staged files. Do not commit `.env`, backup environment files, `.venv`, `.runtime`, `node_modules`, private datasets, or email messages. The supplied `.gitignore` excludes the standard local configuration/runtime paths. Remove any other private files from staging before continuing.
3. Run:

   ```bat
   git commit -m "Prepare free deployment"
   ```

4. If Git asks for your identity, run these with your own details, then repeat the commit:

   ```bat
   git config user.name "YOUR NAME"
   git config user.email "YOUR GITHUB EMAIL"
   ```

5. Replace the URL below with your repository URL, then run:

   ```bat
   git remote add origin https://github.com/YOUR_USERNAME/it303-file-converter.git
   git push -u origin main
   ```

6. Complete GitHub sign-in if prompted. Refresh the repository page.

**Check:** `Dockerfile`, `render.yaml`, `backend`, and `frontend` appear directly at the repository's top level. Upload the contents of `codebase`, rather than a ZIP of the project.

## Step 4: Create the Supabase project

**Where: [Supabase Dashboard](https://supabase.com/dashboard).**

1. Sign in and click **New project**.
2. Select or create a **Free** organization.
3. Enter the project name `it303-file-converter`.
4. Generate a strong **database password**. Save it in your password manager; you need it in Step 5.
5. Choose a nearby region and create the project.
6. Wait until provisioning finishes.

Use a new project dedicated to this app. You do not need to create tables manually; the app creates its tables on startup.

## Step 5: Prepare DATABASE_URL

**Where: your Supabase project → Connect.**

1. Click **Connect**.
2. Select the **URI** format and **Session pooler** method.
3. Copy the URI. Keep the exact host and username Supabase supplies. Session pooling provides an IPv4-compatible connection on port **5432**. [Supabase connection guide](https://supabase.com/docs/guides/database/connecting-to-postgres)
4. Replace the password placeholder with your database password from Step 4.
5. Change the beginning from `postgresql://` to `postgresql+psycopg://`.
6. Append `?sslmode=require`. If the URI already contains `?`, append `&sslmode=require` instead.

The finished value has this structure:

```text
postgresql+psycopg://postgres.PROJECT_REF:ENCODED_PASSWORD@SESSION_POOLER_HOST:5432/postgres?sslmode=require
```

If your password contains special characters, encode the **password only** before inserting it. Run this in your laptop's Command Prompt from `codebase`; it asks for the password without showing what you type:

```bat
.\.venv\Scripts\python.exe -c "from getpass import getpass; from urllib.parse import quote; print(quote(getpass('Database password: '), safe=''))"
```

Use the printed encoded password in the URI. Keep the completed connection value privately as **DATABASE_URL** for Step 9.

**Check:** the value starts with `postgresql+psycopg://`, uses the exact session-pooler host and port `5432`, and includes `sslmode=require`. Do not choose the direct connection or transaction pooler on port `6543` for this guide.

## Step 6: Create the storage bucket and copy the Supabase key

**Where: the same Supabase project.**

1. Open **Storage** in the sidebar.
2. Click **New bucket**.
3. Enter the name exactly: `converter-files`.
4. Leave **Public bucket** switched **off**.
5. Keep the default file-size allowance and create the bucket.
6. Use this bucket only for this application. Its cleanup removes expired and unreferenced app files.
7. Open **Project Settings → Data API** and copy the **Project URL**. If your dashboard places it elsewhere, copy the project URL shown in **Connect**. Save it as **SUPABASE_URL**. It looks like `https://YOUR_PROJECT_REF.supabase.co`.
8. Open **Project Settings → API Keys → Legacy anon, service_role API keys**.
9. Reveal and copy the **service_role** key. Save it as **SUPABASE_SERVICE_ROLE_KEY**. This application expects the legacy service-role JWT key. [Supabase API keys](https://supabase.com/docs/guides/getting-started/api-keys)

Keep the key private. It belongs in Render's environment settings, never in GitHub or frontend variables. Do not copy the anon/publishable key. The app handles user registration itself; Supabase Auth setup is unnecessary.

**Check:** you have DATABASE_URL, SUPABASE_URL, and SUPABASE_SERVICE_ROLE_KEY, and `converter-files` is private.

## Step 7: Set up email with Brevo

**Where: [Brevo](https://www.brevo.com/).**

1. Create a free account and complete its verification.
2. Open the account menu → **Settings → Senders, Domains, IPs → Senders**.
3. Click **Add a sender**.
4. Enter `File Converter` as the name and an email address you control.
5. Save the sender. Enter the verification code Brevo emails you, if requested. Complete any additional account/domain approval Brevo requires.
6. Save this exact verified email address as **MAIL_FROM**. [Brevo sender instructions](https://help.brevo.com/hc/en-us/articles/208836149-Create-a-new-sender-From-name-and-From-email)
7. Open the account menu → **Settings → SMTP & API → API Keys & MCP**.
8. Generate a standard API key named `file-converter`. Complete any identity check and choose an expiry covering your demonstration.
9. Copy the displayed key and save it as **BREVO_API_KEY**. Use a standard API key, rather than an SMTP password or MCP key. [Brevo API-key instructions](https://help.brevo.com/hc/en-us/articles/209467485-Create-and-manage-your-API-keys)
10. Open **Transactional → Email** and complete any activation requested before proceeding.

**Check:** the sender is verified, transactional sending is enabled, and you have the API key. The app sends through HTTPS because Render Free blocks common SMTP ports. [Render Free restrictions](https://render.com/docs/free)

## Step 8: Create the Render web service

**Where: [Render Dashboard](https://dashboard.render.com/).**

1. Sign in or create an account.
2. Click **New → Web Service**.
3. Choose the Git repository option and connect your GitHub account.
4. Grant access to the repository from Step 2 and select it.
5. Enter these settings:

   | Field | What to enter |
   | --- | --- |
   | Name | A unique name, e.g. `dipanshu-it303-converter` |
   | Region | Near your Supabase project, if available |
   | Branch | `main`, or your existing pushed branch |
   | Language / Runtime | **Docker** |
   | Root Directory | Leave blank for the layout in Step 3 |
   | Dockerfile Path | `./Dockerfile` |
   | Docker Build Context | `.` if shown |
   | Instance Type | **Free** |
   | Docker Command | Leave blank |
   | Health Check Path | `/api/v1/health` under Advanced settings |

6. Continue to the environment-variable section before creating the service.

If your GitHub repository instead has an outer `codebase` folder containing the Dockerfile, enter `codebase` as **Root Directory**. [Render service settings](https://render.com/docs/web-services)

## Step 9: Add every environment variable

**Where: Render's service creation form → Environment Variables.**

1. First generate a secret on your laptop, using Command Prompt inside `codebase`:

   ```bat
   .\.venv\Scripts\python.exe -c "import secrets; print(secrets.token_urlsafe(48))"
   ```

2. Copy the printed value. This is your **JWT_SECRET**.
3. Choose your administrator email and a new private password. The password needs at least 12 characters, uppercase and lowercase letters, and a number. It must fit within 72 UTF-8 bytes; a 16–32 character ASCII password is suitable.
4. In Render, use **Add Environment Variable** to enter every row below. Put the variable name on the left and its value on the right. Do not surround values with quotes.

   | Variable name | Value to enter |
   | --- | --- |
   | `ENVIRONMENT` | `production` |
   | `DATABASE_URL` | Completed URI from Step 5 |
   | `JWT_SECRET` | Random value generated above |
   | `FRONTEND_ORIGIN` | Expected Render URL, e.g. `https://dipanshu-it303-converter.onrender.com`, without a trailing `/`; confirm it in Step 10 |
   | `STORAGE_BACKEND` | `supabase` |
   | `SUPABASE_URL` | Project URL from Step 6 |
   | `SUPABASE_SERVICE_ROLE_KEY` | Legacy service-role key from Step 6 |
   | `SUPABASE_STORAGE_BUCKET` | `converter-files` |
   | `MAIL_MODE` | `brevo` |
   | `BREVO_API_KEY` | API key from Step 7 |
   | `MAIL_FROM` | Verified sender email from Step 7, without a display name |
   | `BOOTSTRAP_ADMIN_EMAIL` | Administrator email you chose |
   | `BOOTSTRAP_ADMIN_PASSWORD` | Administrator password you chose |
   | `MAX_UPLOAD_MB` | `5` |
   | `CLEANUP_INTERVAL_SECONDS` | `300` |

5. Check for typing errors, extra spaces, or unfilled placeholders.
6. Click **Create Web Service** / **Deploy Web Service**, whichever label Render shows.

Enter cloud values in Render. Keep your existing local `.env` for local use. Render supplies PORT; the Dockerfile includes Java, WEKA, and the built frontend. You do not need to add WEKA_JAR, FRONTEND_DIST, SMTP settings, or another frontend service.

## Step 10: Wait for deployment and confirm the URL

**Where: your Render service page.**

1. Open **Logs** or the active deployment to watch the build.
2. Wait until the service reports **Live**. The first build installs dependencies and builds the frontend.
3. Copy the public `https://...onrender.com` URL shown on the service page.
4. Open **Environment** and compare that actual URL with FRONTEND_ORIGIN.
5. If they differ, edit FRONTEND_ORIGIN to the actual HTTPS URL, without a trailing slash.
6. Save and deploy the update. If the save action does not deploy, choose **Manual Deploy → Deploy latest commit**.
7. Wait for Live again before testing registration.

The app creates its tables and your administrator automatically. You do not need to run `init-db` or `seed` on Render. Demo accounts are not created. The bootstrap password creates the administrator once; editing that variable later does not reset an existing account's password.

## Step 11: Test the public app

**Where: your browser, using your actual Render URL.**

1. Open this URL, replacing the example hostname with yours:

   ```text
   https://YOUR_SERVICE.onrender.com/api/v1/health
   ```

   Expected result:

   ```json
   {"status":"ok","database":"connected"}
   ```

2. Open the base URL. Sign in using BOOTSTRAP_ADMIN_EMAIL and BOOTSTRAP_ADMIN_PASSWORD from Step 9.
3. Register a separate test user with another email address you control. Open the verification email, follow the link, and sign in.
4. Upload this file, convert to ARFF, confirm **Verification passed**, and download the result:

   ```text
   C:\Users\DIPANSHU KUMAR\Desktop\projects\it303_project\codebase\samples\students.csv
   ```

5. Upload this file, convert to CSV, check verification, and download the result:

   ```text
   C:\Users\DIPANSHU KUMAR\Desktop\projects\it303_project\codebase\samples\weather.arff
   ```

6. Open conversion history and download a result again. Sign into another normal user account and confirm it cannot see the first user's history.
7. Sign out and use **Forgot password**. Confirm the reset email arrives and opens your Render site.
8. In Render, choose **Manual Deploy → Deploy latest commit**. After Live appears again, sign back in and download a recent result before its retention period expires. This checks that Supabase files survive redeployment.

**Done when:** health is OK, login works, emails arrive, both conversion directions pass verification, and recent files remain downloadable after redeployment.

Local regression tests and the frontend build passed during preparation. Cloud behavior was tested using mocked providers. A local Docker image build was not completed because Docker Desktop failed to start. The first Render build and the checks above still need to succeed before the public deployment is verified.

## Step 12: Deploy future code changes

**Where: Command Prompt inside `codebase`.**

1. After editing your source, run:

   ```bat
   git add .
   git status --short
   ```

2. Review the staged files, then run:

   ```bat
   git commit -m "Describe your change here"
   git push
   ```

3. Watch Render deploy. If automatic deployment is disabled, choose **Manual Deploy → Deploy latest commit**.

For future database-schema changes, back up the hosted database and plan a migration first. Startup creates missing tables; it does not migrate existing table structures.

## If something fails

| Problem | What to do |
| --- | --- |
| Git push fails | Complete GitHub sign-in. Run `git remote -v` and confirm it points to your repository. |
| Render cannot find Dockerfile | Check GitHub's folder layout. Set Root Directory to `codebase` only if an outer folder with that name contains the Dockerfile. |
| Render deployment fails | Open the failed deployment's logs and find the first error. Use the relevant row below, save the fix, and redeploy. |
| Database connection fails | Repeat Step 5: exact session-pooler host/username, port 5432, encoded password, and sslmode=require. Resume Supabase if paused. |
| Private bucket/storage error | Check that converter-files exists and Public is off. The Supabase URL and legacy service-role key must come from the same project. |
| Administrator creation fails | Check the email/password rules in Step 9. The email must not already belong to a normal user. |
| Email does not arrive | Check spam and Brevo transactional logs. Check activation, verified sender, API-key validity, quotas, and any provider security approval. |
| Email opens localhost or wrong site | Fix FRONTEND_ORIGIN in Render, redeploy, and request a fresh email link. |
| Service exits during conversion | Try the small sample files, keep MAX_UPLOAD_MB at 5, and check memory errors in Render logs. |
| First page loads slowly | Wait for the free service to wake up, then retry. |

## Before your presentation

1. Open Supabase and resume the project if paused.
2. Open your Render URL early to wake the service.
3. Check health and run a small conversion.
4. Confirm Brevo's API key is active and its email quota remains available.

Render Free sleeps after 15 minutes without incoming traffic; waking can take about a minute. Local disk files are temporary, so this setup keeps datasets in Supabase. [Render Free limits](https://render.com/docs/free)

Supabase Free can pause projects after a week of inactivity. Database, storage, email, and bandwidth quotas apply. [Supabase Free plan](https://supabase.com/docs/guides/platform/billing-on-supabase), [project pausing](https://supabase.com/docs/guides/platform/free-project-pausing)

Expired downloads are blocked immediately. Physical cleanup runs when the backend is awake, so deletion can lag while Render sleeps.
