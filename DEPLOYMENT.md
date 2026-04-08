# StockPilot Deployment Guide — Vercel

## Table of Contents

- [Prerequisites](#prerequisites)
- [Environment Variables](#environment-variables)
- [Understanding vercel.json](#understanding-verceljson)
- [Deployment via Vercel CLI](#deployment-via-vercel-cli)
- [Deployment via Vercel Dashboard](#deployment-via-vercel-dashboard)
- [Post-Deployment Verification](#post-deployment-verification)
- [Troubleshooting Common Issues](#troubleshooting-common-issues)
- [Production Security Checklist](#production-security-checklist)

---

## Prerequisites

Before deploying StockPilot to Vercel, ensure you have the following:

1. **Node.js 18+** installed locally (required for Vercel CLI)
2. **Python 3.12** installed locally for testing before deployment
3. **Vercel Account** — sign up at [vercel.com](https://vercel.com) if you don't have one
4. **Vercel CLI** installed globally:
   ```bash
   npm install -g vercel
   ```
5. **Git** — your project should be committed to a Git repository (GitHub, GitLab, or Bitbucket)
6. **A PostgreSQL database** provisioned and accessible from the internet (e.g., Vercel Postgres, Supabase, Neon, Railway, or AWS RDS)
7. **All dependencies** listed in `requirements.txt` are up to date:
   ```bash
   pip install -r requirements.txt
   ```

---

## Environment Variables

StockPilot requires the following environment variables to be configured in your Vercel project. **Never commit these values to version control.**

| Variable | Required | Description | Example |
|---|---|---|---|
| `SECRET_KEY` | ✅ Yes | Secret key used for JWT token signing and cryptographic operations. Must be a long, random string. | `a3f8b2c1d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9` |
| `DEFAULT_ADMIN_USERNAME` | ✅ Yes | Username for the initial admin account created on first startup. | `admin` |
| `DEFAULT_ADMIN_PASSWORD` | ✅ Yes | Password for the initial admin account. Must meet complexity requirements (min 12 characters, mixed case, numbers, symbols). | `S3cur3P@ssw0rd!2024` |
| `DATABASE_URL` | ✅ Yes | PostgreSQL connection string. Must use the `postgresql+asyncpg://` scheme for async support. | `postgresql+asyncpg://user:pass@host:5432/stockpilot` |
| `ENVIRONMENT` | ❌ No | Deployment environment identifier. Defaults to `production`. | `production` |
| `CORS_ORIGINS` | ❌ No | Comma-separated list of allowed CORS origins. Defaults to the Vercel deployment URL. | `https://stockpilot.vercel.app,https://custom-domain.com` |
| `LOG_LEVEL` | ❌ No | Logging verbosity. Defaults to `INFO`. | `INFO`, `DEBUG`, `WARNING`, `ERROR` |

### Generating a Secure SECRET_KEY

Use one of the following methods to generate a cryptographically secure secret key:

**Python:**
```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

**OpenSSL:**
```bash
openssl rand -hex 32
```

### DATABASE_URL Format

The `DATABASE_URL` must follow this format for async SQLAlchemy compatibility:

```
postgresql+asyncpg://<username>:<password>@<host>:<port>/<database_name>?sslmode=require
```

> **Important:** Always append `?sslmode=require` when connecting to cloud-hosted PostgreSQL instances to enforce encrypted connections.

If your provider gives you a `postgres://` URL, replace the scheme:
- ❌ `postgres://user:pass@host:5432/db`
- ✅ `postgresql+asyncpg://user:pass@host:5432/db`

---

## Understanding vercel.json

The `vercel.json` file configures how Vercel builds and serves the StockPilot FastAPI application. Here is a breakdown of each section:

```json
{
  "version": 2,
  "builds": [
    {
      "src": "main.py",
      "use": "@vercel/python"
    }
  ],
  "routes": [
    {
      "src": "/(.*)",
      "dest": "main.py"
    }
  ]
}
```

| Key | Purpose |
|---|---|
| `version` | Vercel platform version. Always use `2`. |
| `builds[].src` | Entry point of the application. Points to `main.py` where the FastAPI `app` instance is defined. |
| `builds[].use` | Specifies the Vercel builder runtime. `@vercel/python` handles Python applications. |
| `routes[].src` | Regex pattern matching all incoming requests. `/(.*)`catches every path. |
| `routes[].dest` | Routes all matched requests to `main.py` for FastAPI to handle routing internally. |

> **Note:** Vercel serverless functions have a default timeout of 10 seconds (Hobby) or 60 seconds (Pro). Long-running operations like bulk data imports should use background tasks or be handled outside the request cycle.

---

## Deployment via Vercel CLI

### Step 1: Authenticate

```bash
vercel login
```

Follow the prompts to authenticate with your Vercel account via browser or email.

### Step 2: Link Your Project

From the project root directory:

```bash
vercel link
```

Select your Vercel team/account and either link to an existing project or create a new one.

### Step 3: Set Environment Variables

Set each required environment variable for the production environment:

```bash
vercel env add SECRET_KEY production
# Paste your secret key when prompted

vercel env add DEFAULT_ADMIN_USERNAME production
# Enter the admin username when prompted

vercel env add DEFAULT_ADMIN_PASSWORD production
# Enter the admin password when prompted

vercel env add DATABASE_URL production
# Paste your database connection string when prompted
```

To set optional variables:

```bash
vercel env add CORS_ORIGINS production
vercel env add LOG_LEVEL production
vercel env add ENVIRONMENT production
```

You can verify your environment variables are set:

```bash
vercel env ls
```

### Step 4: Deploy to Preview

Run a preview deployment to validate everything works:

```bash
vercel
```

This creates a preview deployment with a unique URL. Test this URL before promoting to production.

### Step 5: Deploy to Production

Once the preview deployment is verified:

```bash
vercel --prod
```

Your application is now live at your production URL.

### Step 6: Verify the Deployment

```bash
curl https://your-project.vercel.app/docs
```

You should see the FastAPI Swagger UI documentation page.

---

## Deployment via Vercel Dashboard

### Step 1: Import Your Repository

1. Go to [vercel.com/new](https://vercel.com/new)
2. Click **"Import Git Repository"**
3. Select your Git provider (GitHub, GitLab, or Bitbucket)
4. Authorize Vercel to access your repositories if prompted
5. Select the **stockpilot** repository

### Step 2: Configure Project Settings

1. **Framework Preset:** Select **"Other"** (Vercel will detect the Python runtime from `vercel.json`)
2. **Root Directory:** Leave as `.` (project root) unless your code is in a subdirectory
3. **Build & Output Settings:** Leave defaults — `vercel.json` handles the configuration

### Step 3: Add Environment Variables

In the **"Environment Variables"** section of the project setup:

1. Add `SECRET_KEY` → paste your generated secret key
2. Add `DEFAULT_ADMIN_USERNAME` → enter the admin username
3. Add `DEFAULT_ADMIN_PASSWORD` → enter the admin password
4. Add `DATABASE_URL` → paste your PostgreSQL connection string
5. (Optional) Add `CORS_ORIGINS`, `LOG_LEVEL`, `ENVIRONMENT`

> **Tip:** Select which environments each variable applies to (Production, Preview, Development). For sensitive values like `SECRET_KEY` and `DATABASE_URL`, use different values for each environment.

### Step 4: Deploy

Click **"Deploy"**. Vercel will:

1. Clone your repository
2. Install Python dependencies from `requirements.txt`
3. Build the serverless function from `main.py`
4. Deploy to the Vercel edge network

### Step 5: Configure Custom Domain (Optional)

1. Go to **Project Settings → Domains**
2. Add your custom domain (e.g., `api.stockpilot.com`)
3. Update your DNS records as instructed by Vercel
4. Vercel automatically provisions an SSL certificate

---

## Post-Deployment Verification

After deploying, run through these checks to confirm everything is working correctly.

### 1. Health Check

```bash
curl -s https://your-project.vercel.app/health | python -m json.tool
```

Expected response:
```json
{
  "status": "healthy"
}
```

### 2. API Documentation

Open in your browser:
```
https://your-project.vercel.app/docs
```

The Swagger UI should load with all available endpoints listed.

### 3. Authentication Flow

Test the login endpoint:

```bash
curl -s -X POST https://your-project.vercel.app/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "admin",
    "password": "YOUR_DEFAULT_ADMIN_PASSWORD"
  }' | python -m json.tool
```

You should receive a JSON response containing an `access_token`.

### 4. Database Connectivity

If the health check and authentication work, the database connection is confirmed. If they fail, check:

- The `DATABASE_URL` is correctly formatted with `postgresql+asyncpg://`
- The database is accessible from Vercel's IP ranges
- SSL mode is enabled (`?sslmode=require`)

### 5. Response Headers

Verify security headers are present:

```bash
curl -I https://your-project.vercel.app/health
```

Check for:
- `x-content-type-options: nosniff`
- `x-frame-options: DENY`
- Appropriate `access-control-allow-origin` header

---

## Troubleshooting Common Issues

### Build Fails: "No module named 'xyz'"

**Cause:** A dependency is missing from `requirements.txt`.

**Fix:** Ensure all dependencies are listed in `requirements.txt` with pinned versions:
```bash
pip freeze > requirements.txt
```
Commit and redeploy.

### Runtime Error: "Connection refused" or Database Timeout

**Cause:** The database is not accessible from Vercel's serverless functions.

**Fix:**
1. Ensure your database allows connections from all IPs (`0.0.0.0/0`) or Vercel's IP ranges
2. Verify the `DATABASE_URL` uses the correct host, port, username, and password
3. Confirm SSL is enabled: append `?sslmode=require` to the connection string
4. Check that the database is in a region close to your Vercel deployment region for lower latency

### 500 Internal Server Error on All Routes

**Cause:** Application fails to start, usually due to missing or malformed environment variables.

**Fix:**
1. Check Vercel function logs: **Project → Deployments → [latest] → Functions → View Logs**
2. Verify all required environment variables are set: `SECRET_KEY`, `DEFAULT_ADMIN_USERNAME`, `DEFAULT_ADMIN_PASSWORD`, `DATABASE_URL`
3. Ensure `SECRET_KEY` is a valid string (no special characters that might break shell escaping)
4. Ensure `DATABASE_URL` uses the `postgresql+asyncpg://` scheme, not `postgres://`

### 504 Gateway Timeout

**Cause:** The serverless function exceeds the execution time limit.

**Fix:**
1. Hobby plans have a 10-second limit; Pro plans have 60 seconds
2. Optimize slow database queries — add indexes, reduce result sets
3. Move long-running operations to background tasks
4. Consider upgrading to Vercel Pro for longer timeouts

### CORS Errors in Browser

**Cause:** The frontend origin is not in the allowed CORS origins list.

**Fix:**
1. Set the `CORS_ORIGINS` environment variable to include your frontend URL:
   ```
   https://your-frontend.vercel.app,https://your-custom-domain.com
   ```
2. Redeploy after updating environment variables
3. Never use `*` as the allowed origin in production

### "Serverless Function Crashed" in Logs

**Cause:** Unhandled exception during application startup or request handling.

**Fix:**
1. Check the full stack trace in Vercel function logs
2. Common causes:
   - Invalid `DATABASE_URL` format
   - Python version mismatch (ensure `runtime.txt` specifies `python-3.12` if needed)
   - Import errors from incompatible package versions
3. Test locally with production environment variables before deploying:
   ```bash
   ENVIRONMENT=production uvicorn main:app --host 0.0.0.0 --port 8000
   ```

### Environment Variables Not Taking Effect

**Cause:** Variables were added after the last deployment, or they are scoped to the wrong environment.

**Fix:**
1. After adding or changing environment variables, you **must redeploy**:
   ```bash
   vercel --prod
   ```
2. Verify variable scope — ensure they are set for the **Production** environment
3. Check for typos in variable names (they are case-sensitive)

---

## Production Security Checklist

Before going live, verify every item on this checklist:

### Authentication & Secrets

- [ ] `SECRET_KEY` is a unique, randomly generated string of at least 32 characters
- [ ] `SECRET_KEY` is different across all environments (development, preview, production)
- [ ] `DEFAULT_ADMIN_PASSWORD` meets complexity requirements (min 12 chars, mixed case, numbers, symbols)
- [ ] Default admin credentials are changed after first login
- [ ] No secrets are committed to version control (check `.gitignore` includes `.env`)
- [ ] JWT token expiration is set to a reasonable duration (e.g., 30 minutes for access tokens)

### Database

- [ ] `DATABASE_URL` uses SSL (`?sslmode=require`)
- [ ] Database user has minimal required permissions (no superuser access)
- [ ] Database password is strong and unique
- [ ] Database backups are configured and tested
- [ ] Connection pooling is configured appropriately for serverless (consider PgBouncer or Supabase pooler)

### Network & CORS

- [ ] `CORS_ORIGINS` is set to specific allowed origins — never `["*"]` in production
- [ ] HTTPS is enforced on all endpoints (Vercel handles this automatically)
- [ ] Rate limiting is configured to prevent abuse
- [ ] Security headers are present (`X-Content-Type-Options`, `X-Frame-Options`, `Strict-Transport-Security`)

### Application

- [ ] `ENVIRONMENT` is set to `production`
- [ ] `LOG_LEVEL` is set to `INFO` or `WARNING` (not `DEBUG` in production)
- [ ] Debug mode / Swagger UI is disabled or restricted in production if the API is not public
- [ ] All API endpoints require authentication except explicitly public routes
- [ ] Input validation is enforced via Pydantic models on all endpoints
- [ ] Error responses do not leak internal details (stack traces, database schemas)

### Monitoring & Observability

- [ ] Vercel function logs are accessible and monitored
- [ ] Error alerting is configured (Vercel integrations, Sentry, or similar)
- [ ] Application health check endpoint (`/health`) is monitored with an uptime service
- [ ] Database connection health is included in the health check

### Deployment Process

- [ ] Preview deployments are tested before promoting to production
- [ ] Rollback plan is documented — Vercel supports instant rollback to previous deployments
- [ ] Environment variables are documented (this guide) and securely shared with the team
- [ ] CI/CD pipeline runs tests before deployment (GitHub Actions, etc.)

---

## Quick Reference Commands

```bash
# Deploy to preview
vercel

# Deploy to production
vercel --prod

# View environment variables
vercel env ls

# Add an environment variable
vercel env add VARIABLE_NAME production

# Remove an environment variable
vercel env rm VARIABLE_NAME production

# View deployment logs
vercel logs https://your-deployment-url.vercel.app

# Roll back to a previous deployment
vercel rollback

# List all deployments
vercel ls
```

---

## Support

If you encounter issues not covered in this guide:

1. Check the [Vercel Documentation](https://vercel.com/docs)
2. Review [FastAPI Deployment Docs](https://fastapi.tiangolo.com/deployment/)
3. Check the Vercel function logs for detailed error messages
4. Open an issue in the StockPilot repository with the error details and steps to reproduce