# API Layer Management Strategy (Rate Limiting, Logging & Analytics)

## Overview

This document defines the comprehensive API layer management strategy for Swaya.me, covering rate limiting, structured logging, and API analytics.

**Technology Commitment:** 100% open source components (MIT, Apache 2.0, BSD licenses).

---

## Architectural Approach: 3-Tier Defense

```
┌─────────────────────────────────────────────────────────────┐
│ Tier 1: Nginx (Edge Protection)                             │
│ - DDoS protection, connection limits, basic rate limiting    │
│ - HTTP/2 support, SSL termination, gzip compression          │
│ - Simple IP-based throttling (e.g., 1000 req/s per IP)       │
│ - Request ID generation and tracking                         │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ Tier 2: FastAPI Broker Layer (Policy Enforcement)           │
│ - Application-aware rate limiting (Slowapi + Redis)          │
│ - Role-based limits (host vs audience)                       │
│ - Per-participant tracking (session-scoped)                  │
│ - Request validation, auth, profanity checks                 │
│ - API analytics & structured logging                         │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ Tier 3: Redis (State Management)                            │
│ - Rate limit counters per participant/IP/session             │
│ - Live session state, real-time counters                     │
│ - Distributed state across multiple FastAPI instances        │
└─────────────────────────────────────────────────────────────┘
```

---

## Technology Stack

| Component | License | Purpose | Layer |
|-----------|---------|---------|-------|
| **Nginx** | BSD 2-Clause | Edge rate limiting, SSL, reverse proxy | Tier 1 |
| **Slowapi** | MIT | Context-aware application rate limiting | Tier 2 |
| **python-json-logger** | BSD 2-Clause | Structured JSON logging | Tier 2 |
| **better-profanity** | MIT | Profanity detection and filtering | Tier 2 |
| **bleach** | Apache 2.0 | HTML/text sanitization | Tier 2 |
| **Redis** | BSD 3-Clause | Distributed rate limit counters | Tier 3 |
| **FastAPI** | MIT | Application framework | Tier 2 |

**All components are 100% open source with zero licensing costs.**

---

## Tier 1: Nginx Edge Protection

### Purpose
Protect backend services from connection floods and basic DDoS attacks before requests reach the application layer.

### Configuration

```nginx
# /etc/nginx/nginx.conf
http {
    # Rate limiting zones
    limit_req_zone $binary_remote_addr zone=general:10m rate=1000r/s;
    limit_req_zone $binary_remote_addr zone=login:10m rate=30r/m;
    limit_req_zone $binary_remote_addr zone=join:10m rate=60r/m;
    
    # Connection limits
    limit_conn_zone $binary_remote_addr zone=addr:10m;
    
    upstream backend {
        server backend:8000;
    }
    
    server {
        listen 80;
        server_name swaya.me;
        return 301 https://$server_name$request_uri;
    }
    
    server {
        listen 443 ssl http2;
        server_name swaya.me;
        
        ssl_certificate /etc/letsencrypt/live/swaya.me/fullchain.pem;
        ssl_certificate_key /etc/letsencrypt/live/swaya.me/privkey.pem;
        
        # Connection limit per IP
        limit_conn addr 50;
        
        # Frontend static files
        location / {
            root /var/www/frontend;
            try_files $uri /index.html;
        }
        
        # API backend with general rate limit
        location /api/v1/ {
            limit_req zone=general burst=100 nodelay;
            
            # Pass request tracking headers
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
            proxy_set_header X-Request-ID $request_id;
            proxy_set_header Host $host;
            
            proxy_pass http://backend;
            proxy_redirect off;
        }
        
        # Specific limits for auth endpoints
        location /api/v1/auth/login {
            limit_req zone=login burst=5 nodelay;
            proxy_pass http://backend;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Request-ID $request_id;
        }
        
        # Specific limits for join endpoints
        location /api/v1/sessions/join {
            limit_req zone=join burst=10 nodelay;
            proxy_pass http://backend;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Request-ID $request_id;
        }
        
        # JSON-formatted access logs
        access_log /var/log/nginx/access.log json;
        error_log /var/log/nginx/error.log warn;
    }
}

# Structured JSON logging format
log_format json escape=json
    '{'
    '"timestamp":"$time_iso8601",'
    '"remote_addr":"$remote_addr",'
    '"request_id":"$request_id",'
    '"method":"$request_method",'
    '"uri":"$request_uri",'
    '"status":$status,'
    '"body_bytes_sent":$body_bytes_sent,'
    '"request_time":$request_time,'
    '"upstream_response_time":"$upstream_response_time",'
    '"user_agent":"$http_user_agent"'
    '}';
```

### Capabilities
- ✅ Basic IP-based rate limiting
- ✅ Connection limiting (max concurrent connections per IP)
- ✅ Request ID generation for distributed tracing
- ✅ SSL/TLS termination
- ✅ HTTP/2 support
- ✅ JSON access logs for analytics

---

## Tier 2: Application-Level Rate Limiting (Slowapi)

### Why Slowapi?

| Criterion | Slowapi | fastapi-ratelimiter | Nginx Only |
|---|---|---|---|
| **Context-Aware** | ✅ IP, participant, user, session | ⚠️ Basic | ❌ IP only |
| **Redis Support** | ✅ Native | ⚠️ Custom needed | ❌ N/A |
| **Distributed State** | ✅ Perfect for multi-VM | ⚠️ Limited | ❌ N/A |
| **Production Maturity** | ✅ 4+ years | ⚠️ Newer | ✅ Mature |
| **Business Logic Aware** | ✅ Host vs audience | ❌ No | ❌ No |
| **License** | ✅ MIT | ✅ MIT | ✅ BSD 2-Clause |

**Decision: Slowapi** for context-aware, distributed rate limiting.

### Installation

```bash
pip install slowapi python-json-logger redis
```

### Configuration

```python
# backend/core/config.py
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # Rate limiting policies
    rate_limit_login: str = "5/minute"      # Per IP
    rate_limit_join: str = "10/minute"      # Per IP
    rate_limit_submit: str = "100/minute"   # Per participant
    
    # Redis for distributed rate limiting
    redis_url: str = "redis://redis:6379/0"
    
    # Logging
    log_level: str = "INFO"
    log_format: str = "json"  # json or text
    log_file: str = "/var/log/swaya/backend.log"
    
    class Config:
        env_file = ".env"

settings = Settings()
```

### Implementation

#### Rate Limit Middleware

```python
# backend/broker/middleware/rate_limit.py
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from fastapi import Request
import logging

logger = logging.getLogger("swaya.rate_limit")

# Initialize Limiter with Redis backend
limiter = Limiter(
    key_func=get_remote_address,
    storage_uri=settings.redis_url,
    default_limits=["1000/minute"]  # Global fallback
)

# Custom key functions for context-aware limiting
def get_host_id(request: Request) -> str:
    """Extract host ID from JWT token"""
    try:
        token = request.headers.get("Authorization", "").replace("Bearer ", "")
        payload = decode_jwt(token)
        return f"host:{payload['user_id']}"
    except:
        return f"ip:{get_remote_address(request)}"

def get_participant_id(request: Request) -> str:
    """Extract participant from session context"""
    session_id = getattr(request.state, "session_id", None)
    participant_id = getattr(request.state, "participant_id", None)
    if participant_id:
        return f"participant:{participant_id}:session:{session_id}"
    return f"ip:{get_remote_address(request)}"

def get_ip(request: Request) -> str:
    """Get IP address"""
    return get_remote_address(request)
```

#### Rate Limited Endpoints

```python
# backend/api/routes/auth.py
from fastapi import APIRouter, Depends, HTTPException, Request
from broker.middleware.rate_limit import limiter, get_ip
from core.config import settings

router = APIRouter(prefix="/auth", tags=["auth"])

@router.post("/login")
@limiter.limit(settings.rate_limit_login)  # 5/minute per IP
async def login(
    request: Request,
    credentials: LoginSchema,
    db: Session = Depends(get_db)
):
    """
    Host login endpoint
    Rate limited: 5 attempts per minute per IP
    """
    ip = get_remote_address(request)
    request_id = request.headers.get("X-Request-ID", "unknown")
    
    logger.info(
        "login_attempt",
        extra={
            "request_id": request_id,
            "ip": ip,
            "email": credentials.email,
            "timestamp": datetime.utcnow().isoformat()
        }
    )
    
    # Verify credentials
    user = db.query(User).filter(User.email == credentials.email).first()
    if not user or not verify_password(credentials.password, user.password_hash):
        logger.warning(
            "login_failed",
            extra={
                "request_id": request_id,
                "ip": ip,
                "email": credentials.email,
                "reason": "invalid_credentials"
            }
        )
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    token = create_jwt_token(user.user_id)
    logger.info(
        "login_successful",
        extra={
            "request_id": request_id,
            "user_id": user.user_id,
            "ip": ip
        }
    )
    
    return {"access_token": token, "token_type": "bearer"}
```

```python
# backend/api/routes/sessions.py
@router.post("/sessions/{session_id}/join")
@limiter.limit(settings.rate_limit_join)  # 10/minute per IP
async def join_session(
    request: Request,
    session_id: str,
    db: Session = Depends(get_db)
):
    """
    Join quiz session (audience)
    Rate limited: 10 attempts per minute per IP
    """
    ip = get_remote_address(request)
    request_id = request.headers.get("X-Request-ID", "unknown")
    
    session = db.query(QuizSession).filter(QuizSession.id == session_id).first()
    if not session:
        logger.warning(
            "join_failed_session_not_found",
            extra={
                "request_id": request_id,
                "session_id": session_id,
                "ip": ip
            }
        )
        raise HTTPException(status_code=404, detail="Session not found")
    
    participant = create_participant(session_id)
    logger.info(
        "participant_joined",
        extra={
            "request_id": request_id,
            "session_id": session_id,
            "participant_id": participant.id,
            "ip": ip
        }
    )
    
    return {"participant_id": participant.id, "session_id": session_id}
```

```python
# backend/api/routes/answers.py
@router.post("/answers/submit")
@limiter.limit(settings.rate_limit_submit, key_func=get_participant_id)  # 100/min per participant
async def submit_answer(
    request: Request,
    answer: AnswerSchema,
    db: Session = Depends(get_db)
):
    """
    Submit answer to quiz question
    Rate limited: 100 per minute per participant
    """
    participant_id = getattr(request.state, "participant_id")
    session_id = getattr(request.state, "session_id")
    request_id = request.headers.get("X-Request-ID", "unknown")
    
    logger.info(
        "answer_submitted",
        extra={
            "request_id": request_id,
            "participant_id": participant_id,
            "session_id": session_id,
            "question_id": answer.question_id,
            "selected_option": answer.selected_option,
            "timestamp": datetime.utcnow().isoformat()
        }
    )
    
    # Process answer through Platform Kernel → Quiz Feature
    result = submit_quiz_answer(
        session_id=session_id,
        participant_id=participant_id,
        question_id=answer.question_id,
        selected_option=answer.selected_option,
        db=db
    )
    
    return result
```

#### Global Exception Handler

```python
# backend/broker/error_handlers.py
from slowapi.errors import RateLimitExceeded
from fastapi import Request
from fastapi.responses import JSONResponse
import logging

logger = logging.getLogger("swaya.errors")

@app.exception_handler(RateLimitExceeded)
async def rate_limit_exception_handler(request: Request, exc: RateLimitExceeded):
    """Handle rate limit exceeded errors"""
    ip = get_remote_address(request)
    request_id = request.headers.get("X-Request-ID", "unknown")
    
    logger.warning(
        "rate_limit_exceeded",
        extra={
            "request_id": request_id,
            "ip": ip,
            "endpoint": request.url.path,
            "method": request.method,
            "timestamp": datetime.utcnow().isoformat()
        }
    )
    
    return JSONResponse(
        status_code=429,
        content={
            "error_code": "RATE_LIMIT_EXCEEDED",
            "message": "Too many requests. Please try again later.",
            "retry_after": 60
        },
        headers={"Retry-After": "60"}
    )
```

---

## Tier 3: Structured Logging & Analytics

### Setup

```python
# backend/core/logging.py
import logging
import sys
from pythonjsonlogger import jsonlogger
from core.config import settings

def setup_logging():
    """Configure structured JSON logging"""
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    
    if settings.log_format == "json":
        formatter = jsonlogger.JsonFormatter(
            '%(timestamp)s %(level)s %(name)s %(message)s',
            rename_fields={"levelname": "level"}
        )
    else:
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
    
    console_handler.setFormatter(formatter)
    
    # Root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(settings.log_level)
    root_logger.addHandler(console_handler)
    
    return root_logger
```

### Request Logging Middleware

```python
# backend/broker/middleware/logging.py
import logging
import time
import uuid
from fastapi import Request
from slowapi.util import get_remote_address

logger = logging.getLogger("swaya.api")

@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all API requests with context"""
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    request.state.request_id = request_id
    
    start_time = time.time()
    
    # Log incoming request
    logger.info(
        "request_started",
        extra={
            "request_id": request_id,
            "method": request.method,
            "path": request.url.path,
            "remote_addr": get_remote_address(request),
            "user_agent": request.headers.get("User-Agent", "unknown")
        }
    )
    
    response = await call_next(request)
    process_time = time.time() - start_time
    
    # Log response
    logger.info(
        "request_completed",
        extra={
            "request_id": request_id,
            "method": request.method,
            "path": request.url.path,
            "status": response.status_code,
            "duration_ms": round(process_time * 1000, 2),
            "remote_addr": get_remote_address(request)
        }
    )
    
    response.headers["X-Request-ID"] = request_id
    return response
```

### Event-Based Analytics Logging

```python
# backend/broker/analytics.py
import logging

analytics_logger = logging.getLogger("swaya.analytics")

def log_quiz_event(event_type: str, **kwargs):
    """Log quiz-related events for analytics"""
    analytics_logger.info(
        event_type,
        extra={
            "event_type": event_type,
            "timestamp": datetime.utcnow().isoformat(),
            **kwargs
        }
    )

# Usage examples:
log_quiz_event("quiz_created", quiz_id="quiz_123", host_id="usr_456")
log_quiz_event("session_started", session_id="sess_789", quiz_id="quiz_123")
log_quiz_event("participant_joined", session_id="sess_789", participant_id="p_001")
log_quiz_event("answer_submitted", session_id="sess_789", participant_id="p_001", question_id="q_1")
log_quiz_event("question_closed", session_id="sess_789", question_id="q_1", total_submissions=25)
```

---

## Content Moderation & Profanity Filtering (MVP)

### Overview

All user-generated text must pass through profanity detection **before** reaching feature services or being stored. This is a **mandatory MVP requirement** per business scope.

**Enforcement Point:** Broker Layer (Policy Enforcement)

### Libraries

```bash
pip install better-profanity==0.7.0  # MIT License
pip install bleach==6.1.0  # Apache 2.0
```

### Implementation

#### Profanity Detection Module

```python
# backend/broker/middleware/profanity.py
from better_profanity import profanity
import bleach
from fastapi import HTTPException
import logging

logger = logging.getLogger("swaya.profanity")

# Initialize profanity detector
profanity.load_censor_words()

# Optional: Add custom words
# profanity.add_censor_words(['custom', 'words'])

class ContentModerationConfig:
    """Event-level profanity policies"""
    QUIZ_QUESTIONS = "reject"  # Host-created content
    QUIZ_ANSWERS = "reject"     # Audience responses
    DISPLAY_NAMES = "mask"      # Audience names
    POLL_OPTIONS = "reject"     # Host-created (post-MVP)
    WORD_CLOUD = "mask"         # Audience input (post-MVP)


def sanitize_html(text: str) -> str:
    """
    Remove potentially dangerous HTML tags and attributes
    
    Args:
        text: Raw user input
        
    Returns:
        Sanitized text with dangerous HTML removed
    """
    return bleach.clean(
        text,
        tags=[],  # Remove all HTML tags
        strip=True,  # Strip tags instead of escaping
        strip_comments=True
    )


def validate_text_input(
    text: str,
    field_name: str,
    mode: str = "reject"
) -> str:
    """
    Validate and sanitize user text input
    
    Args:
        text: Raw user input
        field_name: Field name for error messages and logging
        mode: Enforcement mode
            - "reject": Raise exception if profanity detected
            - "mask": Replace profanity with asterisks
            - "moderate": Flag for manual review (post-MVP)
    
    Returns:
        Sanitized text (if allowed)
        
    Raises:
        HTTPException: If profanity detected and mode is 'reject'
    """
    # Step 1: HTML sanitization (prevent XSS)
    clean_text = sanitize_html(text)
    
    # Step 2: Check for profanity
    if profanity.contains_profanity(clean_text):
        logger.warning(
            "profanity_detected",
            extra={
                "field": field_name,
                "text_preview": clean_text[:50],
                "mode": mode,
                "timestamp": datetime.utcnow().isoformat()
            }
        )
        
        if mode == "reject":
            raise HTTPException(
                status_code=400,
                detail={
                    "error_code": "PROFANITY_DETECTED",
                    "message": f"Inappropriate content detected in {field_name}. Please revise your input.",
                    "field": field_name
                }
            )
        elif mode == "mask":
            clean_text = profanity.censor(clean_text)
            logger.info(
                "profanity_masked",
                extra={
                    "field": field_name,
                    "timestamp": datetime.utcnow().isoformat()
                }
            )
        elif mode == "moderate":
            # Future: Send to moderation queue
            logger.info(
                "profanity_flagged_for_moderation",
                extra={
                    "field": field_name,
                    "timestamp": datetime.utcnow().isoformat()
                }
            )
    
    return clean_text


# Pydantic validators for common schemas
from pydantic import validator

class ContentValidationMixin:
    """Mixin for Pydantic models requiring content validation"""
    
    @classmethod
    def validate_content_field(cls, v: str, field_name: str, mode: str = "reject") -> str:
        """Reusable validator for content fields"""
        return validate_text_input(v, field_name, mode)
```

#### Integration with API Schemas

```python
# backend/api/schemas/quiz.py
from pydantic import BaseModel, validator
from broker.middleware.profanity import validate_text_input, ContentModerationConfig

class QuestionCreateSchema(BaseModel):
    text: str
    options: List[str]
    correct_option_index: int
    
    @validator('text')
    def validate_question_text(cls, v):
        return validate_text_input(
            v,
            field_name="question text",
            mode=ContentModerationConfig.QUIZ_QUESTIONS
        )
    
    @validator('options', each_item=True)
    def validate_option_text(cls, v):
        return validate_text_input(
            v,
            field_name="answer option",
            mode=ContentModerationConfig.QUIZ_ANSWERS
        )


class ParticipantJoinSchema(BaseModel):
    display_name: Optional[str] = None
    
    @validator('display_name')
    def validate_display_name(cls, v):
        if v:
            return validate_text_input(
                v,
                field_name="display name",
                mode=ContentModerationConfig.DISPLAY_NAMES
            )
        return v
```

#### Usage in Endpoints

```python
# backend/api/routes/quizzes.py
@router.post("/quizzes/{quiz_id}/questions")
async def add_question(
    quiz_id: str,
    question: QuestionCreateSchema,  # Validation happens automatically
    db: Session = Depends(get_db)
):
    """
    Add question to quiz
    - Question text is validated for profanity
    - Options are validated for profanity
    - Raises 400 if profanity detected
    """
    # question.text and question.options are already sanitized
    new_question = create_question(quiz_id, question, db)
    return new_question
```

### Profanity Detection Scope (MVP)

| Content Type | Enforcement Mode | Actor | Rationale |
|-------------|------------------|-------|-----------|
| Quiz questions | Reject | Host | Maintain professional content |
| Quiz answer options | Reject | Host | Maintain professional content |
| Participant display names | Mask | Audience | Allow participation, hide profanity |
| Quiz titles | Reject | Host | Public-facing, must be clean |
| Quiz descriptions | Reject | Host | Public-facing, must be clean |

### Error Response

When profanity is detected and rejected:

**HTTP 400 Bad Request**
```json
{
  "error_code": "PROFANITY_DETECTED",
  "message": "Inappropriate content detected in question text. Please revise your input.",
  "field": "question text"
}
```

### Testing Profanity Filter

```python
# tests/test_profanity.py
import pytest
from broker.middleware.profanity import validate_text_input
from fastapi import HTTPException

def test_profanity_rejection():
    """Test that profane content is rejected"""
    with pytest.raises(HTTPException) as exc_info:
        validate_text_input("This is a damn test", "question", mode="reject")
    
    assert exc_info.value.status_code == 400
    assert exc_info.value.detail["error_code"] == "PROFANITY_DETECTED"

def test_profanity_masking():
    """Test that profane content can be masked"""
    result = validate_text_input("This is a damn test", "display name", mode="mask")
    assert "****" in result  # Profanity masked
    assert "damn" not in result

def test_clean_content_passes():
    """Test that clean content passes validation"""
    result = validate_text_input("What is 2+2?", "question", mode="reject")
    assert result == "What is 2+2?"

def test_html_sanitization():
    """Test that HTML is stripped"""
    result = validate_text_input("<script>alert('xss')</script>Safe text", "question", mode="reject")
    assert "<script>" not in result
    assert "Safe text" in result
```

---

## Rate Limiting Policies (MVP)

| Endpoint | Limit | Key | Rationale |
|---------|-------|-----|-----------|
| `POST /auth/login` | 5/minute | IP | Prevent brute-force attacks |
| `POST /sessions/join` | 10/minute | IP | Prevent session flooding |
| `POST /answers/submit` | 100/minute | Participant ID | Prevent spam submissions |
| `GET /sessions/{id}/results` | 200/minute | Session ID | High read volume expected |
| `POST /quizzes` (host) | 20/hour | User ID | Prevent quiz spam |

---

## Monitoring & Observability

### Health Check Endpoints

```python
# backend/api/routes/health.py
from fastapi import APIRouter

router = APIRouter(tags=["health"])

@router.get("/health")
async def health_check():
    """Overall system health"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat()
    }

@router.get("/ping")
async def ping():
    """Basic connectivity check"""
    return {"message": "pong"}
```

### Log Aggregation Strategy (Post-MVP)

```yaml
Nginx Logs:
  Format: JSON
  Location: /var/log/nginx/access.log
  Aggregation: Ship to ELK Stack or Loki

Backend Logs:
  Format: JSON
  Location: stdout (captured by Docker)
  Aggregation: Ship to ELK Stack or Loki

Analytics Logs:
  Format: JSON
  Purpose: Business intelligence, usage metrics
  Storage: Separate analytics DB or data warehouse
```

---

## Security Best Practices

### Rate Limit Bypass Prevention

```python
# Validate X-Forwarded-For headers
def get_client_ip(request: Request) -> str:
    """Securely extract client IP"""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded and settings.trust_proxy:
        # Take first IP in chain (original client)
        return forwarded.split(",")[0].strip()
    return request.client.host
```

### Rate Limit Header Exposure

```python
# Add rate limit info to responses
response.headers["X-RateLimit-Limit"] = "100"
response.headers["X-RateLimit-Remaining"] = "87"
response.headers["X-RateLimit-Reset"] = "1643234567"
```

---

## Testing Rate Limits

### Unit Tests

```python
# tests/test_rate_limits.py
import pytest
from fastapi.testclient import TestClient

def test_login_rate_limit(client: TestClient):
    """Test login rate limit enforcement"""
    # Make 5 valid requests (should succeed)
    for i in range(5):
        response = client.post("/api/v1/auth/login", json={
            "email": "test@example.com",
            "password": "wrong"
        })
        assert response.status_code in [200, 401]
    
    # 6th request should be rate limited
    response = client.post("/api/v1/auth/login", json={
        "email": "test@example.com",
        "password": "wrong"
    })
    assert response.status_code == 429
    assert response.json()["error_code"] == "RATE_LIMIT_EXCEEDED"
```

---

## Future Enhancements (Post-MVP)

- **Dynamic Rate Limits**: Adjust limits based on system load
- **User-Based Tiers**: Premium hosts get higher limits
- **Distributed Tracing**: OpenTelemetry integration
- **Real-Time Monitoring**: Grafana dashboards for rate limit metrics
- **Anomaly Detection**: ML-based abuse pattern detection
- **API Analytics Dashboard**: Self-service analytics for hosts

---

## Summary

| Layer | Technology | Responsibility | License |
|---|---|---|---|
| **Edge** | Nginx | DDoS protection, SSL, basic IP rate limits | BSD 2-Clause |
| **Application** | Slowapi + FastAPI | Context-aware rate limiting, validation | MIT |
| **Content Moderation** | better-profanity + bleach | Profanity detection, HTML sanitization | MIT + Apache 2.0 |
| **State** | Redis | Distributed rate limit counters | BSD 3-Clause |
| **Logging** | python-json-logger | Structured JSON logs, analytics | BSD 2-Clause |

**All components are 100% open source with zero licensing costs, fully aligned with Swaya.me's technology philosophy.**
