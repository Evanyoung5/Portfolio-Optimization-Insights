# Public Deployment Checklist

This project is close to public-hosting shape, but there are still a few launch disciplines that matter if real users will trust it with account and portfolio data.

## 1. Required environment and secrets

Use `APP_ENV=production` and fill every value from `.env.production.example`.

At minimum:

- `AUTH_SECRET_KEY`: long random secret, at least 32 characters
- `DATA_ENCRYPTION_KEY`: separate long random secret, at least 32 characters
- `POSTGRES_PASSWORD`
- `PUBLIC_APP_URL`
- `FRONTEND_ORIGINS`
- `APP_HOSTS`
- `SMTP_HOST`
- `SMTP_USERNAME`
- `SMTP_PASSWORD`
- `SMTP_FROM_EMAIL`

Public mode now refuses to start if those basics are misconfigured.

Before the first real deploy, run:

```bash
./scripts/prod_preflight.sh .env.production
```

## 2. Deployment topology

Recommended production shape:

1. Reverse proxy / TLS terminator
   - Caddy is already wired in `docker-compose.prod.yml`
2. API container
   - FastAPI + static frontend
3. Worker container
   - background market-data and history jobs
4. Postgres
   - persistent volume and automated backups
5. Redis
   - queue + rate limiting + market-data cache

Do not expose the API container directly to the internet. Only the reverse proxy should publish ports.

## 3. Data protection

Already present:

- per-user portfolio ownership checks
- encrypted database payloads for private portfolio data
- hashed lookup fields for user email and ticker joins
- password hashing
- refresh-token rotation and revocation
- same-origin `HttpOnly` auth cookies on register, login, and refresh

Still recommended before broad public launch:

- add secret rotation procedures for `AUTH_SECRET_KEY` and `DATA_ENCRYPTION_KEY`
- enable encrypted off-site Postgres backups
- add audit logging for login, password reset, email verification, and portfolio deletion events

## 4. Network and browser hardening

Already present:

- trusted host enforcement
- CORS allowlist
- HSTS support
- CSP
- frame denial
- referrer and permissions policies

Operational next steps:

- point DNS for the public domain at the reverse proxy host
- verify TLS issuance succeeds in Caddy
- test the site only over `https://`
- keep `AUTH_DEV_EXPOSE_TOKENS=false`

## 5. Abuse controls

Already present:

- Redis-backed market-data rate limiting
- provider budget caps for history, quotes, and options requests
- auth endpoint rate limiting

Operational next steps:

- monitor 429 rates
- add IP-based edge throttling at the reverse proxy or hosting provider
- add bot protection or CAPTCHA only if registration abuse becomes real

## 6. Persistence and recovery

Before launch:

1. run `scripts/prod_backup.sh` on a schedule and ship Postgres dumps off-host
2. document restore steps with `scripts/prod_restore.sh`
3. test an actual restore into a fresh environment
4. keep Redis persistence enabled for queue durability, while treating Redis as cache and queue state rather than the primary system of record
5. add alerts for worker failures and queue backlog

Suggested restore drill:

1. `docker compose -f docker-compose.prod.yml up -d`
2. `scripts/prod_backup.sh backups`
3. create a throwaway staging copy of the stack
4. `ALLOW_DROP=true scripts/prod_restore.sh backups/postgres_<timestamp>.dump`
5. `python3 scripts/prod_smoke_test.py --base-url http://localhost`
6. verify login and portfolio counts on the restored environment

For local rehearsals on one machine, use `.env.prod.local` plus the `local-drill` Mailpit profile, and prefer restoring into an isolated verification database first:

1. `docker compose --env-file .env.prod.local -f docker-compose.prod.yml --profile local-drill up -d`
2. `ENV_FILE=.env.prod.local scripts/prod_backup.sh backups`
3. mutate the live drill data after backup so the restore has something to prove
4. `ENV_FILE=.env.prod.local TARGET_DATABASE=portfolio_restore_check scripts/prod_restore.sh backups/postgres_<timestamp>.dump`
5. compare live counts with restored counts before attempting any destructive primary restore

Each Postgres dump gets a SHA-256 checksum next to it so off-site storage can verify integrity before restore.

## 7. Observability

Before launch:

- centralize API and worker logs
- alert on repeated background-job failures
- alert on failed SMTP delivery
- track login failures, password reset volume, and quote refresh failures
- monitor disk growth for Postgres and Redis volumes

## 8. Public launch smoke test

Run this before DNS cutover:

1. `docker compose -f docker-compose.prod.yml up --build -d`
2. `python3 scripts/prod_smoke_test.py --base-url http://localhost`
3. `docker compose -f docker-compose.prod.yml exec api python -m app.ops.smtp_check`
4. create an account
5. verify email verification flow
6. verify password reset flow
7. create a portfolio
8. confirm worker picks up quote refresh jobs
9. confirm rate limiter blocks abusive refresh loops
10. verify the site in light and dark mode on desktop and mobile
11. `scripts/prod_backup.sh backups`
12. perform at least one restore drill before public launch

## 9. Current honest status

After the latest hardening pass, the repo is in better shape for public hosting:

- startup validation blocks unsafe production config
- auth routes are rate limited
- public runtime metadata is redacted
- stricter browser security headers are in place
- the container runs as a non-root user
- the production compose stack includes container health checks and deployment scripts for SMTP verification, backups, restores, and smoke testing

## 10. Hostinger VPS note

If the site is going to a Hostinger VPS, use [docs/HOSTINGER_VPS_DEPLOYMENT.md](docs/HOSTINGER_VPS_DEPLOYMENT.md)
as the concrete runbook. It covers DNS, VPS prep, `.env.production`, deploy commands, smoke tests,
and backup drills.
