# 🚀 Deployment Guide - FIDIT AI Assistant

Ovaj vodič pokriva deployment aplikacije u različite okoline.

## 📋 Sadržaj

1. [Development Setup](#development-setup)
2. [Production Deployment](#production-deployment)
3. [Docker Deployment](#docker-deployment)
4. [Cloud Deployment](#cloud-deployment)
5. [Monitoring & Maintenance](#monitoring--maintenance)

---

## 🛠️ Development Setup

### Lokalni development

```bash
# 1. Clone repository
git clone <repository-url>
cd fidit-ai-assistant

# 2. Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate  # Windows

# 3. Install dependencies
pip install -r requirements.txt

# 4. Setup environment
cp .env.example .env
# Edit .env with your settings

# 5. Initialize database
python src/database/database.py
python src/utils/create_demo_data.py

# 6. Run services
python src/api/main.py &
streamlit run frontend/app.py
```

---

## 🏭 Production Deployment

### Opcija 1: VPS/Dedicated Server

#### 1. Priprema servera

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Python 3.11
sudo apt install python3.11 python3.11-venv python3-pip -y

# Install PostgreSQL
sudo apt install postgresql postgresql-contrib -y

# Install Nginx
sudo apt install nginx -y

# Install supervisor (za process management)
sudo apt install supervisor -y
```

#### 2. Setup PostgreSQL

```bash
# Create database and user
sudo -u postgres psql

CREATE DATABASE fidit_db;
CREATE USER fidit WITH PASSWORD 'your_secure_password';
GRANT ALL PRIVILEGES ON DATABASE fidit_db TO fidit;
\q
```

#### 3. Deploy aplikacije

```bash
# Create app directory
sudo mkdir -p /opt/fidit-ai-assistant
cd /opt/fidit-ai-assistant

# Clone code
git clone <repository-url> .

# Setup virtual environment
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Configure environment
cat > .env << EOF
DATABASE_URL=postgresql://fidit:your_secure_password@localhost:5432/fidit_db
OPENAI_API_KEY=your_openai_key
DEBUG=False
LOG_LEVEL=INFO
EOF

# Initialize database
python src/database/database.py
```

#### 4. Supervisor konfiguracija

```bash
# Backend service
sudo nano /etc/supervisor/conf.d/fidit-backend.conf
```

```ini
[program:fidit-backend]
command=/opt/fidit-ai-assistant/venv/bin/uvicorn src.api.main:app --host 0.0.0.0 --port 8000
directory=/opt/fidit-ai-assistant
user=www-data
autostart=true
autorestart=true
stderr_logfile=/var/log/fidit-backend.err.log
stdout_logfile=/var/log/fidit-backend.out.log
```

```bash
# Frontend service
sudo nano /etc/supervisor/conf.d/fidit-frontend.conf
```

```ini
[program:fidit-frontend]
command=/opt/fidit-ai-assistant/venv/bin/streamlit run frontend/app.py --server.port 8501 --server.address 0.0.0.0
directory=/opt/fidit-ai-assistant
user=www-data
autostart=true
autorestart=true
stderr_logfile=/var/log/fidit-frontend.err.log
stdout_logfile=/var/log/fidit-frontend.out.log
```

```bash
# Start services
sudo supervisorctl reread
sudo supervisorctl update
sudo supervisorctl start all
```

#### 5. Nginx reverse proxy

```bash
sudo nano /etc/nginx/sites-available/fidit
```

```nginx
# Backend API
server {
    listen 80;
    server_name api.fidit.example.com;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}

# Frontend Dashboard
server {
    listen 80;
    server_name dashboard.fidit.example.com;

    location / {
        proxy_pass http://localhost:8501;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

```bash
# Enable site
sudo ln -s /etc/nginx/sites-available/fidit /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

#### 6. SSL certifikat (Let's Encrypt)

```bash
# Install certbot
sudo apt install certbot python3-certbot-nginx -y

# Get certificates
sudo certbot --nginx -d api.fidit.example.com
sudo certbot --nginx -d dashboard.fidit.example.com
```

#### 7. Scheduled scraping (Cron)

```bash
# Edit crontab
crontab -e

# Add daily scraping at 2 AM
0 2 * * * cd /opt/fidit-ai-assistant && /opt/fidit-ai-assistant/venv/bin/python src/scrapers/scraper_manager.py >> /var/log/fidit-scraper.log 2>&1
```

---

## 🐳 Docker Deployment

### Production Docker Compose

```yaml
version: '3.8'

services:
  postgres:
    image: postgres:15
    container_name: fidit_postgres
    restart: always
    environment:
      POSTGRES_USER: fidit
      POSTGRES_PASSWORD: ${DB_PASSWORD}
      POSTGRES_DB: fidit_db
    volumes:
      - postgres_data:/var/lib/postgresql/data
    networks:
      - fidit_network

  api:
    build: .
    container_name: fidit_api
    restart: always
    command: uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --workers 4
    environment:
      - DATABASE_URL=postgresql://fidit:${DB_PASSWORD}@postgres:5432/fidit_db
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - DEBUG=False
    depends_on:
      - postgres
    networks:
      - fidit_network
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.api.rule=Host(`api.fidit.example.com`)"

  frontend:
    build: .
    container_name: fidit_frontend
    restart: always
    command: streamlit run frontend/app.py --server.port 8501 --server.address 0.0.0.0
    depends_on:
      - api
    networks:
      - fidit_network
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.frontend.rule=Host(`dashboard.fidit.example.com`)"

  # Scheduled scraping
  scraper:
    build: .
    container_name: fidit_scraper
    restart: always
    command: >
      bash -c "while true; do
        python src/scrapers/scraper_manager.py;
        sleep 86400;
      done"
    environment:
      - DATABASE_URL=postgresql://fidit:${DB_PASSWORD}@postgres:5432/fidit_db
    depends_on:
      - postgres
    networks:
      - fidit_network

  # Reverse proxy (optional)
  traefik:
    image: traefik:v2.10
    container_name: traefik
    restart: always
    command:
      - "--providers.docker=true"
      - "--entrypoints.web.address=:80"
      - "--entrypoints.websecure.address=:443"
      - "--certificatesresolvers.letsencrypt.acme.email=admin@example.com"
      - "--certificatesresolvers.letsencrypt.acme.storage=/letsencrypt/acme.json"
      - "--certificatesresolvers.letsencrypt.acme.httpchallenge.entrypoint=web"
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
      - ./letsencrypt:/letsencrypt
    networks:
      - fidit_network

volumes:
  postgres_data:

networks:
  fidit_network:
    driver: bridge
```

### Deployment s Docker

```bash
# 1. Setup environment
cat > .env << EOF
DB_PASSWORD=your_secure_password
OPENAI_API_KEY=your_openai_key
EOF

# 2. Build and start
docker-compose -f docker-compose.prod.yml up -d --build

# 3. Initialize database
docker-compose exec api python src/database/database.py

# 4. Check logs
docker-compose logs -f
```

---

## ☁️ Cloud Deployment

### AWS Deployment

#### 1. EC2 Instance

```bash
# Launch EC2 instance (t3.medium or larger)
# Ubuntu 22.04 LTS
# Security groups: 22, 80, 443, 8000, 8501

# SSH to instance
ssh -i your-key.pem ubuntu@your-instance-ip

# Follow VPS deployment steps above
```

#### 2. RDS PostgreSQL

```bash
# Create RDS PostgreSQL instance
# Update DATABASE_URL in .env
DATABASE_URL=postgresql://fidit:password@your-rds-endpoint:5432/fidit_db
```

#### 3. S3 za backup

```bash
# Install AWS CLI
sudo apt install awscli -y

# Configure
aws configure

# Backup script
cat > backup.sh << EOF
#!/bin/bash
BACKUP_FILE="/tmp/fidit_backup_$(date +%Y%m%d).sql"
pg_dump -h your-rds-endpoint -U fidit fidit_db > $BACKUP_FILE
aws s3 cp $BACKUP_FILE s3://your-backup-bucket/
rm $BACKUP_FILE
EOF

chmod +x backup.sh

# Cron za daily backup
0 3 * * * /opt/fidit-ai-assistant/backup.sh
```

### Google Cloud Platform

```bash
# Use Cloud Run or Compute Engine
# Similar setup as AWS
```

### Heroku

```bash
# Install Heroku CLI
# heroku login

# Create app
heroku create fidit-ai-assistant

# Add PostgreSQL
heroku addons:create heroku-postgresql:hobby-dev

# Deploy
git push heroku main

# Set env vars
heroku config:set OPENAI_API_KEY=your_key
```

---

## 📊 Monitoring & Maintenance

### Logging

```bash
# Application logs
tail -f /var/log/fidit-backend.out.log
tail -f /var/log/fidit-frontend.out.log
tail -f /var/log/fidit-scraper.log

# Nginx logs
tail -f /var/log/nginx/access.log
tail -f /var/log/nginx/error.log

# Docker logs
docker-compose logs -f api
docker-compose logs -f frontend
```

### Backup stratergija

```bash
# Daily database backup
0 3 * * * pg_dump -U fidit fidit_db > /backups/fidit_$(date +\%Y\%m\%d).sql

# Retention (keep 30 days)
find /backups -name "fidit_*.sql" -mtime +30 -delete
```

### Update procedure

```bash
# 1. Backup
pg_dump fidit_db > backup_before_update.sql

# 2. Pull latest code
git pull origin main

# 3. Update dependencies
pip install -r requirements.txt

# 4. Run migrations (if any)
# alembic upgrade head

# 5. Restart services
sudo supervisorctl restart all
# Or with Docker:
docker-compose restart
```

### Health monitoring

```bash
# Setup healthcheck endpoint monitoring
# Use tools like:
# - UptimeRobot
# - Pingdom
# - StatusCake

# Endpoint to monitor:
# https://api.fidit.example.com/health
```

### Performance tuning

```bash
# PostgreSQL optimization
sudo nano /etc/postgresql/15/main/postgresql.conf

# Increase connections
max_connections = 100

# Memory settings
shared_buffers = 256MB
effective_cache_size = 1GB

# Restart PostgreSQL
sudo systemctl restart postgresql
```

---

## 🔒 Security Checklist

- [ ] Change default passwords
- [ ] Use strong API keys
- [ ] Enable SSL/TLS (HTTPS)
- [ ] Setup firewall (UFW)
- [ ] Regular security updates
- [ ] Backup encryption
- [ ] Rate limiting
- [ ] CORS configuration
- [ ] Environment variables (never commit .env)
- [ ] Database backup schedule

---

## 📞 Support

Za probleme pri deploymentu:
- Provjeri logove
- Testiraj health endpoint
- Provjeri firewall/security groups
- Verifi ciraj environment varijable

---

**Good luck with deployment! 🚀**
