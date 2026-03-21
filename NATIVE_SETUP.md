# Swaya.me Native Setup on Ubuntu 22.04 (No Docker)

## Prerequisites Check

```bash
# Check current installations
python3 --version    # Should be 3.10+
node --version       # Check if installed
mysql --version      # Check if aaPanel MySQL exists
redis-cli --version  # Check if Redis installed
```

---

## Step 1: Install Required Packages

```bash
# Update system
sudo apt update

# Install Python and tools
sudo apt install -y python3.10 python3.10-venv python3-pip python3.10-dev

# Install build essentials for Python packages
sudo apt install -y build-essential libmysqlclient-dev pkg-config

# Install Node.js 18 (if not already installed)
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt install -y nodejs

# Install Redis
sudo apt install -y redis-server

# Start Redis
sudo systemctl start redis-server
sudo systemctl enable redis-server
```

---

## Step 2: Configure MySQL (Using aaPanel MySQL)

### Create Database and User

```bash
# Access MySQL (use aaPanel MySQL credentials)
mysql -u root -p

# Or if aaPanel has a specific MySQL user:
# mysql -u aapanel_user -p
```

In MySQL console:

```sql
-- Create database
CREATE DATABASE swaya_production CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- Create user
CREATE USER 'swaya'@'localhost' IDENTIFIED BY 'YourSecurePassword123!';

-- Grant privileges
GRANT ALL PRIVILEGES ON swaya_production.* TO 'swaya'@'localhost';

-- Flush privileges
FLUSH PRIVILEGES;

-- Exit
EXIT;
```

---

## Step 3: Setup Backend

```bash
# Navigate to backend directory
cd /home/vinay/Swaya.me/backend

# Create virtual environment
python3 -m venv .venv

# Activate virtual environment
source .venv/bin/activate

# Upgrade pip
pip install --upgrade pip

# Install dependencies
pip install -r requirements.txt

# Create production .env file
cat > .env << 'EOF'
# Database Configuration (Native MySQL)
DB_HOST=localhost
DB_PORT=3306
DB_NAME=swaya_production
DB_USER=swaya
DB_PASSWORD=YourSecurePassword123!
DB_POOL_SIZE=10
DB_MAX_OVERFLOW=20

# Redis Configuration (Native Redis)
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=
REDIS_DB=0
REDIS_POOL_SIZE=10

# JWT Configuration
JWT_SECRET=$(openssl rand -base64 32)
JWT_ALGORITHM=HS256
JWT_EXPIRATION_HOURS=24

# Application Configuration
HOST=0.0.0.0
PORT=8000
DEBUG=false
RELOAD=false
LOG_LEVEL=INFO
ENVIRONMENT=production

# CORS Configuration
ALLOWED_ORIGINS=http://your-domain.com,https://your-domain.com

# Rate Limiting
RATE_LIMIT_ENABLED=true
RATE_LIMIT_LOGIN=5/minute
RATE_LIMIT_JOIN=10/minute
RATE_LIMIT_SUBMIT=100/minute
RATE_LIMIT_QUIZ_CREATE=20/hour

# Profanity Filter
PROFANITY_FILTER_ENABLED=true
PROFANITY_FILTER_MODE=mask

# Multi-Tenant Configuration
DEFAULT_TIER=free
TIER_FREE_MAX_PARTICIPANTS=50
TIER_FREE_MAX_QUESTIONS=10
TIER_FREE_MAX_CONCURRENT_EVENTS=1
TIER_PRO_MAX_PARTICIPANTS=1000
TIER_PRO_MAX_QUESTIONS=100
TIER_PRO_MAX_CONCURRENT_EVENTS=5
EOF

# Run database migrations
alembic upgrade head

# Seed initial data
python scripts/seed_data.py
```

---

## Step 4: Setup Frontend

```bash
# Navigate to frontend directory
cd /home/vinay/Swaya.me/frontend

# Install dependencies
npm install

# Build for production
npm run build

# The build will be in frontend/dist directory
```

---

## Step 5: Create Systemd Service for Backend

```bash
# Create systemd service file
sudo nano /etc/systemd/system/swaya-backend.service
```

Add this content:

```ini
[Unit]
Description=Swaya.me Backend API
After=network.target mysql.service redis.service

[Service]
Type=simple
User=vinay
Group=vinay
WorkingDirectory=/home/vinay/Swaya.me/backend
Environment="PATH=/home/vinay/Swaya.me/backend/.venv/bin"
ExecStart=/home/vinay/Swaya.me/backend/.venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start the service:

```bash
# Reload systemd
sudo systemctl daemon-reload

# Enable service to start on boot
sudo systemctl enable swaya-backend

# Start the service
sudo systemctl start swaya-backend

# Check status
sudo systemctl status swaya-backend

# View logs
sudo journalctl -u swaya-backend -f
```

---

## Step 6: Configure Nginx (via aaPanel or Manual)

### Option A: Using aaPanel

1. Open aaPanel dashboard
2. Go to Website → Add Site
3. Domain: your-domain.com
4. Configure as reverse proxy to `http://localhost:8000`

### Option B: Manual Nginx Configuration

```bash
# Create Nginx configuration
sudo nano /etc/nginx/sites-available/swaya.me
```

Add this content:

```nginx
# Backend API
upstream backend {
    server localhost:8000;
}

# Main server block
server {
    listen 80;
    server_name your-domain.com www.your-domain.com;

    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;

    # Rate limiting
    limit_req_zone $binary_remote_addr zone=api_limit:10m rate=100r/m;
    limit_req_zone $binary_remote_addr zone=login_limit:10m rate=5r/m;

    # API Backend
    location /api/ {
        limit_req zone=api_limit burst=20 nodelay;
        
        proxy_pass http://backend;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_cache_bypass $http_upgrade;
    }

    # API Docs
    location /health {
        proxy_pass http://backend;
    }

    # Frontend Static Files
    location / {
        root /home/vinay/Swaya.me/frontend/dist;
        try_files $uri $uri/ /index.html;
        
        # Cache static assets
        location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg)$ {
            expires 1y;
            add_header Cache-Control "public, immutable";
        }
    }

    # WebSocket support (future)
    location /ws/ {
        proxy_pass http://backend;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_read_timeout 86400;
    }
}
```

Enable the site:

```bash
# Enable site
sudo ln -s /etc/nginx/sites-available/swaya.me /etc/nginx/sites-enabled/

# Test configuration
sudo nginx -t

# Reload Nginx
sudo systemctl reload nginx
```

---

## Step 7: Configure SSL with Let's Encrypt

```bash
# Install Certbot
sudo apt install -y certbot python3-certbot-nginx

# Get SSL certificate
sudo certbot --nginx -d your-domain.com -d www.your-domain.com

# Auto-renewal is configured automatically
```

---

## Step 8: Verify Installation

```bash
# Check backend service
sudo systemctl status swaya-backend

# Check if backend is responding
curl http://localhost:8000/health

# Check Redis
redis-cli ping

# Check MySQL
mysql -u swaya -p swaya_production -e "SHOW TABLES;"

# Check Nginx
sudo systemctl status nginx

# Test API endpoint
curl http://localhost:8000/api/v1/

# Access from browser
# http://your-domain.com
# http://your-domain.com/api/docs
```

---

## Step 9: Create Admin User

```bash
cd /home/vinay/Swaya.me/backend
source .venv/bin/activate

# Use API to register
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@yourdomain.com",
    "password": "SecurePassword123!",
    "full_name": "Admin User",
    "tenant_name": "Your Organization"
  }'
```

---

## Monitoring & Maintenance

### View Logs

```bash
# Backend logs
sudo journalctl -u swaya-backend -f

# Nginx access logs
sudo tail -f /var/log/nginx/access.log

# Nginx error logs
sudo tail -f /var/log/nginx/error.log

# MySQL logs (if needed)
sudo tail -f /var/log/mysql/error.log
```

### Restart Services

```bash
# Restart backend
sudo systemctl restart swaya-backend

# Restart Nginx
sudo systemctl restart nginx

# Restart Redis
sudo systemctl restart redis-server

# Restart MySQL (if needed)
sudo systemctl restart mysql
```

### Update Application

```bash
# Pull latest changes
cd /home/vinay/Swaya.me
git pull origin main

# Update backend
cd backend
source .venv/bin/activate
pip install -r requirements.txt
alembic upgrade head
sudo systemctl restart swaya-backend

# Update frontend
cd ../frontend
npm install
npm run build
```

---

## Troubleshooting

### Backend won't start

```bash
# Check logs
sudo journalctl -u swaya-backend -n 100

# Test manually
cd /home/vinay/Swaya.me/backend
source .venv/bin/activate
uvicorn main:app --host 0.0.0.0 --port 8000

# Check port
sudo lsof -i :8000
```

### Database connection issues

```bash
# Test MySQL connection
mysql -u swaya -p swaya_production

# Check MySQL is running
sudo systemctl status mysql

# Check credentials in .env file
cat /home/vinay/Swaya.me/backend/.env | grep DB_
```

### Frontend not loading

```bash
# Check Nginx configuration
sudo nginx -t

# Check if dist folder exists
ls -la /home/vinay/Swaya.me/frontend/dist

# Rebuild frontend
cd /home/vinay/Swaya.me/frontend
npm run build
```

---

## Performance Tuning

### MySQL Optimization

```bash
# Edit MySQL config
sudo nano /etc/mysql/mysql.conf.d/mysqld.cnf

# Add these settings
[mysqld]
max_connections = 200
innodb_buffer_pool_size = 1G
innodb_log_file_size = 256M
query_cache_type = 1
query_cache_size = 64M
```

### Redis Optimization

```bash
# Edit Redis config
sudo nano /etc/redis/redis.conf

# Set max memory
maxmemory 512mb
maxmemory-policy allkeys-lru
```

---

## Backup Strategy

### Database Backup

```bash
# Create backup script
cat > ~/backup-swaya.sh << 'EOF'
#!/bin/bash
BACKUP_DIR="/home/vinay/backups"
DATE=$(date +%Y%m%d_%H%M%S)
mkdir -p $BACKUP_DIR

# Backup MySQL
mysqldump -u swaya -p swaya_production > $BACKUP_DIR/swaya_db_$DATE.sql

# Keep only last 7 days
find $BACKUP_DIR -name "swaya_db_*.sql" -mtime +7 -delete
EOF

chmod +x ~/backup-swaya.sh

# Add to crontab (daily at 2 AM)
(crontab -l 2>/dev/null; echo "0 2 * * * ~/backup-swaya.sh") | crontab -
```

---

## Access Your Application

### URLs
- **Website:** http://your-domain.com (or https:// with SSL)
- **API Docs:** http://your-domain.com/api/docs
- **Health Check:** http://your-domain.com/health

### Default Demo Account
- **Email:** demo@swaya.me
- **Password:** Demo1234

---

## Next Steps

1. ✅ Change default passwords
2. ✅ Configure your domain name
3. ✅ Set up SSL certificate
4. ✅ Create your admin account
5. ✅ Test the application
6. ✅ Set up monitoring
7. ✅ Configure backups

---

**Your Swaya.me application is now running natively on Ubuntu 22.04!** 🚀
