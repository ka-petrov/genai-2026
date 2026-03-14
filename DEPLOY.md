# Deploying GenGeo to gengeo.constp.dev

## Prerequisites

- A DigitalOcean droplet (or any VM) with Docker and Docker Compose installed.
- An A record pointing `gengeo.constp.dev` to the droplet's IP address.

## 1. Open firewall ports

Ports 80 and 443 must be reachable **before** requesting a certificate.

```bash
sudo ufw allow 22/tcp    # SSH
sudo ufw allow 80/tcp    # HTTP (certbot + redirect)
sudo ufw allow 443/tcp   # HTTPS
sudo ufw enable
```

If the droplet has a DigitalOcean cloud firewall, also add inbound rules for
TCP 80 and 443 in the control panel (Networking > Firewalls).

## 2. Install certbot

```bash
sudo apt update && sudo apt install -y certbot
```

## 3. Obtain the initial TLS certificate

Port 80 must be free (no nginx running yet).

```bash
sudo certbot certonly --standalone -d gengeo.constp.dev
```

This writes certs to `/etc/letsencrypt/live/gengeo.constp.dev/`.

Create the ACME webroot directory for future renewals:

```bash
sudo mkdir -p /var/www/certbot
```

## 4. Clone the repo and configure

```bash
git clone <repo-url> /opt/gengeo
cd /opt/gengeo
```

Create the `.env` file:

```bash
cat > .env << 'EOF'
OPENROUTER_API_KEY=sk-or-v1-...
LLM_MODEL_ID=openai/gpt-5-mini
MAP_STYLE_URL=https://tiles.openfreemap.org/styles/liberty
REDIS_URL=redis://redis:6379/0
REDIS_CONTEXT_TTL_SECONDS=3600
REDIS_REGION_TTL_SECONDS=900
LOG_LEVEL=info
EOF
```

## 5. Build and start all services

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
```

Verify:

```bash
curl -s https://gengeo.constp.dev/api/health | python3 -m json.tool
```

## 6. Set up automatic certificate renewal

Certbot installs a systemd timer that runs `certbot renew` twice daily. We need
a deploy hook to reload the nginx container after a successful renewal.

```bash
sudo tee /etc/letsencrypt/renewal-hooks/deploy/restart-nginx.sh > /dev/null << 'HOOK'
#!/bin/bash
docker compose -f /opt/gengeo/docker-compose.yml \
               -f /opt/gengeo/docker-compose.prod.yml \
               restart nginx
HOOK
sudo chmod +x /etc/letsencrypt/renewal-hooks/deploy/restart-nginx.sh
```

Test that renewal would work (dry run):

```bash
sudo certbot renew --dry-run
```

## 7. Updating the application

```bash
cd /opt/gengeo
git pull
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
```

## 8. Viewing logs

```bash
# All services
docker compose -f docker-compose.yml -f docker-compose.prod.yml logs -f

# Single service
docker compose -f docker-compose.yml -f docker-compose.prod.yml logs -f backend
```

## Local development

Locally, `docker compose up` auto-loads `docker-compose.override.yml` which
exposes `backend:8000` and `redis:6380` on the host and uses the dev nginx
config (no TLS). No production files are involved.
