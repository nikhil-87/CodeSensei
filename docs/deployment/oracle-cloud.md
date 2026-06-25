# Oracle Cloud Free Tier Deployment (from zero)

Deploy CodeSensei to an always-free Oracle Cloud VM, fronted by nginx with HTTPS. This is
the recommended "real, public, $0" deployment.

## 0. Why Oracle Free Tier
The Ampere A1 (Arm) always-free shape gives up to 4 OCPUs / 24 GB RAM — plenty for the
backend, worker, and Chroma, while Postgres (Neon) and Redis (Upstash) are managed and free.

## 1. Create the account & VM
1. Sign up at oracle.com/cloud/free.
2. **Compute → Instances → Create instance.**
   - Shape: **VM.Standard.A1.Flex** (Ampere) — e.g. 2 OCPU / 12 GB (free-tier eligible).
   - Image: Ubuntu 22.04 LTS.
   - Add your SSH public key.
3. Note the public IP.

## 2. Networking / firewall
Two layers must both allow traffic:
- **OCI Security List / NSG** (in the VCN): ingress rules for **22** (SSH), **80** (HTTP),
  **443** (HTTPS).
- **OS firewall** on the VM:
  ```bash
  sudo iptables -I INPUT -p tcp --dport 80 -j ACCEPT
  sudo iptables -I INPUT -p tcp --dport 443 -j ACCEPT
  sudo netfilter-persistent save   # persist (Ubuntu)
  ```
  (Oracle Ubuntu images ship restrictive iptables — this step is commonly missed.)

## 3. Server setup
```bash
ssh ubuntu@<public-ip>
sudo apt update && sudo apt -y upgrade
# Docker + Compose plugin
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker $USER && newgrp docker
docker compose version
```

## 4. Get the code & configure
```bash
git clone <repo-url> codesensei && cd codesensei
cp .env.free-tier .env
nano .env
```
Set in `.env`:
```dotenv
APP_ENV=production
APP_SECRET_KEY=<openssl rand -hex 32>
APP_CORS_ORIGINS=https://your-domain
GITHUB_OAUTH_CLIENT_ID=...           # OAuth app for https://your-domain
GITHUB_OAUTH_CLIENT_SECRET=...
GITHUB_OAUTH_CALLBACK_URL=https://your-domain/api/v1/auth/github/callback
FRONTEND_BASE_URL=https://your-domain
# Managed data services
POSTGRES_HOST=<neon-host>  POSTGRES_SSLMODE=require  POSTGRES_USER=...  POSTGRES_PASSWORD=...
REDIS_HOST=<upstash-host>  REDIS_TLS=true  REDIS_PASSWORD=...
# AI providers
LLM_PROVIDER=groq          GROQ_API_KEY=gsk_...
EMBEDDING_PROVIDER=huggingface  HUGGINGFACE_API_KEY=hf_...
API_WORKERS=2  WORKER_CONCURRENCY=1
```
Provider sign-ups: [providers.md](providers.md). Full var reference:
[environment-variables.md](environment-variables.md).

## 5. Deploy
```bash
docker compose -f docker/docker-compose.free-tier.yml --env-file .env up -d --build
docker exec codesensei-backend alembic upgrade head
docker ps --filter "name=codesensei"
```

## 6. Domain + reverse proxy + TLS
1. Point an A record for `your-domain` at the VM's public IP.
2. Use the `infrastructure/` nginx config (or install nginx on the host) to reverse-proxy
   `/` → frontend `:3000` and `/api` → backend `:8000`.
3. TLS with Let's Encrypt:
   ```bash
   sudo apt -y install certbot python3-certbot-nginx
   sudo certbot --nginx -d your-domain
   ```
   Certbot installs the cert and a renewal timer.

## 7. Monitoring & operations
- Logs: `docker compose -f docker/docker-compose.free-tier.yml logs -f backend worker`.
- Restart a service: `docker compose ... up -d --build <service>`.
- Health: `curl https://your-domain/api/v1/healthz`.
- Optional: `docker/docker-compose.observability.yml` adds Prometheus + Grafana.
- Runbooks: [../operations/runbooks.md](../operations/runbooks.md).

## Troubleshooting
- **Site unreachable** → check *both* OCI security list **and** host iptables.
- **OAuth mismatch** → callback URL must equal `GITHUB_OAUTH_CALLBACK_URL`.
- **DB/Redis connection errors** → Neon needs `sslmode=require`; Upstash needs `REDIS_TLS=true`.
- **OOM during analysis** → lower `WORKER_CONCURRENCY`, raise the shape's RAM.
- Full catalogue: [../troubleshooting/README.md](../troubleshooting/README.md).
