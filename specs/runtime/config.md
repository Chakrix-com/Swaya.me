# Configuration & Environment Variables

This document defines all configuration settings and environment variables for the Swaya.me MVP.

---

## Environment Variables

### Backend Configuration

#### Database (MySQL on OCI VM)
```bash
DB_HOST=<mysql-host-endpoint>
DB_PORT=3306
DB_NAME=swaya_db
DB_USER=admin
DB_PASSWORD=<secure_password>
DB_POOL_SIZE=10
DB_MAX_OVERFLOW=5
DB_ECHO=false  # Set to true for SQL query logging in development
```

#### Redis (Local)
```bash
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=  # Empty for local, set for production
REDIS_DB=0
REDIS_MAX_CONNECTIONS=50
```

#### Authentication
```bash
JWT_SECRET=<random_256_bit_secret>
JWT_ALGORITHM=HS256
JWT_EXPIRATION_HOURS=24
PASSWORD_SALT_ROUNDS=12  # bcrypt cost factor
```

#### Server
```bash
HOST=0.0.0.0
PORT=8000
DEBUG=false  # Set to true for development
ALLOWED_ORIGINS=http://localhost:3000,https://swaya.me
```

#### Logging
```bash
LOG_LEVEL=INFO  # DEBUG, INFO, WARNING, ERROR, CRITICAL
LOG_FORMAT=json  # json or text
LOG_FILE=/var/log/swaya/backend.log
```

#### Rate Limiting
```bash
RATE_LIMIT_LOGIN=5  # Max login attempts per minute per IP
RATE_LIMIT_JOIN=10  # Max join attempts per minute per IP
RATE_LIMIT_SUBMIT=100  # Max answer submissions per minute per participant
```

---

### Frontend Configuration

#### API
```bash
REACT_APP_API_URL=http://localhost:8000/api/v1  # Development
REACT_APP_API_URL=https://swaya.me/api/v1  # Production
REACT_APP_WS_URL=ws://localhost:8000/api/v1  # WebSocket (if used)
```

#### Polling
```bash
REACT_APP_POLL_INTERVAL=2000  # Milliseconds (2 seconds)
```

#### Debugging
```bash
REACT_APP_DEBUG=false  # Enable Redux DevTools and console logging
```

---

## Configuration Files

### Backend: config.py

```python
import os
from pydantic import BaseSettings

class Settings(BaseSettings):
    # Database
    db_host: str = os.getenv("DB_HOST")
    db_port: int = int(os.getenv("DB_PORT", 3306))
    db_name: str = os.getenv("DB_NAME")
    db_user: str = os.getenv("DB_USER")
    db_password: str = os.getenv("DB_PASSWORD")
    db_pool_size: int = int(os.getenv("DB_POOL_SIZE", 10))
    db_max_overflow: int = int(os.getenv("DB_MAX_OVERFLOW", 5))
    db_echo: bool = os.getenv("DB_ECHO", "false").lower() == "true"
    
    # Redis
    redis_host: str = os.getenv("REDIS_HOST", "localhost")
    redis_port: int = int(os.getenv("REDIS_PORT", 6379))
    redis_password: str = os.getenv("REDIS_PASSWORD", "")
    redis_db: int = int(os.getenv("REDIS_DB", 0))
    redis_max_connections: int = int(os.getenv("REDIS_MAX_CONNECTIONS", 50))
    
    # Authentication
    jwt_secret: str = os.getenv("JWT_SECRET")
    jwt_algorithm: str = os.getenv("JWT_ALGORITHM", "HS256")
    jwt_expiration_hours: int = int(os.getenv("JWT_EXPIRATION_HOURS", 24))
    password_salt_rounds: int = int(os.getenv("PASSWORD_SALT_ROUNDS", 12))
    
    # Server
    host: str = os.getenv("HOST", "0.0.0.0")
    port: int = int(os.getenv("PORT", 8000))
    debug: bool = os.getenv("DEBUG", "false").lower() == "true"
    allowed_origins: list = os.getenv("ALLOWED_ORIGINS", "").split(",")
    
    # Logging
    log_level: str = os.getenv("LOG_LEVEL", "INFO")
    log_format: str = os.getenv("LOG_FORMAT", "json")
    log_file: str = os.getenv("LOG_FILE", "/var/log/swaya/backend.log")
    
    # Rate Limiting
    rate_limit_login: int = int(os.getenv("RATE_LIMIT_LOGIN", 5))
    rate_limit_join: int = int(os.getenv("RATE_LIMIT_JOIN", 10))
    rate_limit_submit: int = int(os.getenv("RATE_LIMIT_SUBMIT", 100))
    
    @property
    def database_url(self) -> str:
        return f"mysql+pymysql://{self.db_user}:{self.db_password}@{self.db_host}:{self.db_port}/{self.db_name}"
    
    @property
    def redis_url(self) -> str:
        if self.redis_password:
            return f"redis://:{self.redis_password}@{self.redis_host}:{self.redis_port}/{self.redis_db}"
        return f"redis://{self.redis_host}:{self.redis_port}/{self.redis_db}"

    class Config:
        env_file = ".env"

settings = Settings()
```

---

### Frontend: .env

**Development (.env.development)**:
```bash
REACT_APP_API_URL=http://localhost:8000/api/v1
REACT_APP_POLL_INTERVAL=2000
REACT_APP_DEBUG=true
```

**Production (.env.production)**:
```bash
REACT_APP_API_URL=https://swaya.me/api/v1
REACT_APP_POLL_INTERVAL=2000
REACT_APP_DEBUG=false
```

---

## Docker Configuration

### docker-compose.yml

```yaml
version: '3.8'

services:
  backend:
    build: ./backend
    container_name: swaya-backend
    restart: unless-stopped
    ports:
      - "8000:8000"
    environment:
      - DB_HOST=${DB_HOST}
      - DB_PORT=${DB_PORT}
      - DB_NAME=${DB_NAME}
      - DB_USER=${DB_USER}
      - DB_PASSWORD=${DB_PASSWORD}
      - REDIS_HOST=redis
      - REDIS_PORT=6379
      - JWT_SECRET=${JWT_SECRET}
      - ALLOWED_ORIGINS=${ALLOWED_ORIGINS}
    depends_on:
      - redis
    networks:
      - swaya-network

  frontend:
    build: ./frontend
    container_name: swaya-frontend
    restart: unless-stopped
    ports:
      - "3000:80"
    environment:
      - REACT_APP_API_URL=${REACT_APP_API_URL}
    networks:
      - swaya-network

  redis:
    image: redis:7-alpine
    container_name: swaya-redis
    restart: unless-stopped
    ports:
      - "6379:6379"
    volumes:
      - redis-data:/data
    networks:
      - swaya-network

  nginx:
    image: nginx:alpine
    container_name: swaya-nginx
    restart: unless-stopped
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf
      - ./nginx/ssl:/etc/nginx/ssl
    depends_on:
      - backend
      - frontend
    networks:
      - swaya-network

volumes:
  redis-data:

networks:
  swaya-network:
    driver: bridge
```

---

## Nginx Configuration

### nginx.conf

```nginx
events {
    worker_connections 1024;
}

http {
    upstream backend {
        server backend:8000;
    }

    upstream frontend {
        server frontend:80;
    }

    server {
        listen 80;
        server_name swaya.me www.swaya.me;

        # Redirect HTTP to HTTPS
        return 301 https://$host$request_uri;
    }

    server {
        listen 443 ssl http2;
        server_name swaya.me www.swaya.me;

        ssl_certificate /etc/nginx/ssl/cert.pem;
        ssl_certificate_key /etc/nginx/ssl/key.pem;

        # Frontend
        location / {
            proxy_pass http://frontend;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }

        # Backend API
        location /api/ {
            proxy_pass http://backend;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }

        # WebSocket (if used)
        location /api/v1/sessions/ {
            proxy_pass http://backend;
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection "upgrade";
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
        }
    }
}
```

---

## Secrets Management

### Local Development
- Use `.env` file (not committed to git)
- Add `.env` to `.gitignore`

### Production
- Store secrets in OCI VM environment variables
- Or use secrets management service (post-MVP: AWS Secrets Manager, HashiCorp Vault)

### Example .env Template (.env.example)

```bash
# Database
DB_HOST=your-rds-endpoint
DB_PORT=3306
DB_NAME=swaya_db
DB_USER=admin
DB_PASSWORD=change_me

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=

# Authentication
JWT_SECRET=change_me_to_random_256_bit_secret
JWT_ALGORITHM=HS256
JWT_EXPIRATION_HOURS=24

# Server
HOST=0.0.0.0
PORT=8000
DEBUG=false
ALLOWED_ORIGINS=http://localhost:3000,https://swaya.me

# Frontend
REACT_APP_API_URL=http://localhost:8000/api/v1
REACT_APP_POLL_INTERVAL=2000
REACT_APP_DEBUG=false
```

---

## Configuration Validation

### Backend Startup Check
```python
def validate_config():
    required_vars = [
        "DB_HOST", "DB_NAME", "DB_USER", "DB_PASSWORD",
        "JWT_SECRET", "ALLOWED_ORIGINS"
    ]
    missing = [var for var in required_vars if not os.getenv(var)]
    if missing:
        raise RuntimeError(f"Missing required environment variables: {missing}")

validate_config()
```

---

## Defaults Summary

| Variable | Default | Notes |
|----------|---------|-------|
| DB_POOL_SIZE | 10 | Adjust based on load |
| DB_MAX_OVERFLOW | 5 | Additional connections under load |
| REDIS_MAX_CONNECTIONS | 50 | Adjust based on concurrent sessions |
| JWT_EXPIRATION_HOURS | 24 | Token lifetime |
| PASSWORD_SALT_ROUNDS | 12 | bcrypt cost (higher = slower) |
| RATE_LIMIT_LOGIN | 5 | Attempts per minute per IP |
| RATE_LIMIT_JOIN | 10 | Attempts per minute per IP |
| RATE_LIMIT_SUBMIT | 100 | Submissions per minute per participant |
| LOG_LEVEL | INFO | DEBUG for development |
| REACT_APP_POLL_INTERVAL | 2000 | Milliseconds |
