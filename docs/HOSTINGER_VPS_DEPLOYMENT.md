# Hostinger VPS Deployment

This runbook assumes:

- the canonical repo is `/Users/evanyoung/Documents/Portfolio_Optimization`
- the public site will live on a real domain such as `example.com`
- Docker will run the full stack: Caddy, API, worker, Postgres, and Redis

## 1. Prepare the domain

In Hostinger DNS:

1. Create an `A` record for the apex domain pointing to the VPS IPv4 address.
2. Create a `CNAME` or `A` record for `www` pointing to the same site.
3. Wait for DNS propagation before expecting TLS to finish cleanly.

Use one public origin for the app:

- `https://example.com`
- optionally redirect `https://www.example.com`

## 2. Prepare the VPS

Example for a fresh Ubuntu VPS:

```bash
sudo apt update
sudo apt install -y ca-certificates curl git
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker "$USER"
newgrp docker
docker version
docker compose version
```

Open inbound ports:

- `22` for SSH
- `80` for HTTP
- `443` for HTTPS

Do not expose Postgres or Redis publicly.

## 3. Clone the repo

```bash
git clone https://github.com/<your-user>/<your-repo>.git
cd <your-repo>
```

## 4. Create production secrets

Start from the checked-in template:

```bash
cp .env.production.example .env.production
```

Edit `.env.production` with:

- `APP_DOMAIN=yourdomain.com`
- `FRONTEND_ORIGINS=https://yourdomain.com,https://www.yourdomain.com`
- `APP_HOSTS=yourdomain.com,www.yourdomain.com`
- `PUBLIC_APP_URL=https://yourdomain.com`
- strong `POSTGRES_PASSWORD`
- strong `AUTH_SECRET_KEY`
- strong `DATA_ENCRYPTION_KEY`
- real SMTP credentials

Important:

- keep `PORTFOLIO_REPOSITORY=postgres`
- keep `AUTH_DEV_EXPOSE_TOKENS=false`
- keep `MARKET_DATA_REQUIRE_REDIS_LIMITER=true`
- keep `AUTH_REQUIRE_REDIS_LIMITER=true`
- never commit `.env.production`
- never rotate `DATA_ENCRYPTION_KEY` casually after users have live data

## 5. Run the preflight check

```bash
chmod +x scripts/prod_preflight.sh
./scripts/prod_preflight.sh .env.production
```

The preflight checks the basic public-safety requirements before you cut over.

## 6. Launch the stack

```bash
docker compose --env-file .env.production -f docker-compose.prod.yml up --build -d
```

Then verify:

```bash
docker compose --env-file .env.production -f docker-compose.prod.yml ps
python3 scripts/prod_smoke_test.py --base-url https://yourdomain.com
docker compose --env-file .env.production -f docker-compose.prod.yml exec api python -m app.ops.smtp_check
```

## 7. Validate the public site

Before sharing the domain:

1. Register a real account.
2. Verify email verification works.
3. Verify password reset works.
4. Create a portfolio.
5. Refresh quotes and confirm the worker processes jobs.
6. Confirm rate limiting blocks abusive refresh loops.
7. Check light and dark mode on desktop and mobile.
8. Confirm the demo path works from the homepage.

## 8. Backups and restore drills

Create a backup:

```bash
ENV_FILE=.env.production scripts/prod_backup.sh backups
```

Test a restore before public launch:

```bash
ENV_FILE=.env.production TARGET_DATABASE=portfolio_restore_check scripts/prod_restore.sh backups/postgres_<timestamp>.dump
```

Back up the Postgres dump files off-host. Redis should not be your only recovery plan.

## 9. Updating the live site

```bash
git pull
./scripts/prod_preflight.sh .env.production
docker compose --env-file .env.production -f docker-compose.prod.yml up --build -d
python3 scripts/prod_smoke_test.py --base-url https://yourdomain.com
```

## 10. Recommended first public-launch routine

1. Push the repo to GitHub from the canonical local path.
2. Deploy to the VPS with `.env.production`.
3. Verify the site privately at the real domain.
4. Run one full backup.
5. Test one password reset email.
6. Test one quote refresh and one options refresh.
7. Only then announce the site publicly.
