# Multi-Tenant Data Isolation & Query Scoping

## Overview

This document defines the technical strategy for ensuring strict data isolation between tenants at the database, ORM, and application layers.

**Principle:** Every query must be tenant-scoped. Cross-tenant data access is a critical security bug.

---

## Data Isolation Strategy

### Layer 1: Database (Row-Level Security)

#### Every Domain Table Includes tenant_id

```sql
-- Quiz table example
CREATE TABLE quizzes (
    quiz_id CHAR(36) PRIMARY KEY,
    tenant_id CHAR(36) NOT NULL,  -- ← Every row scoped to tenant
    host_id CHAR(36) NOT NULL,
    title VARCHAR(255) NOT NULL,
    ...
    FOREIGN KEY (tenant_id) REFERENCES tenants(tenant_id),
    INDEX idx_tenant_quiz (tenant_id, quiz_id)
) ENGINE=InnoDB;

-- Participants table example
CREATE TABLE participants (
    participant_id CHAR(36) PRIMARY KEY,
    session_id CHAR(36) NOT NULL,
    tenant_id CHAR(36) NOT NULL,  -- ← Required even with FK to session
    display_name VARCHAR(255),
    ...
    FOREIGN KEY (tenant_id) REFERENCES tenants(tenant_id),
    FOREIGN KEY (session_id) REFERENCES quiz_sessions(session_id),
    INDEX idx_tenant_participant (tenant_id, participant_id)
) ENGINE=InnoDB;
```

#### Composite Indexes for Tenant Scoping

```sql
-- Fast queries with tenant context
CREATE INDEX idx_tenant_created ON quizzes(tenant_id, created_at);
CREATE INDEX idx_tenant_status ON quiz_sessions(tenant_id, status, started_at);
CREATE INDEX idx_tenant_user ON users(tenant_id, email);

-- Prevents cross-tenant accidents
ALTER TABLE quizzes ADD CONSTRAINT chk_tenant_not_null CHECK (tenant_id IS NOT NULL);
```

### Layer 2: ORM (SQLAlchemy Filter Configuration)

#### Automatic Tenant Filtering with Event Listeners

```python
# File: backend/persistence/models.py

from sqlalchemy import event
from sqlalchemy.orm import Session

# Base class for all tenant-scoped entities
class TenantScoped(Base):
    """
    Base class for all domain models that must be tenant-scoped.
    
    Automatically filters queries to current tenant.
    """
    __abstract__ = True
    
    tenant_id: Column = Column(UUID, ForeignKey("tenants.tenant_id"), nullable=False)
    
    @classmethod
    def for_tenant(cls, tenant_id: UUID):
        """Chainable tenant filter"""
        return cls.query.filter(cls.tenant_id == tenant_id)


# Domain models inherit from TenantScoped
class Quiz(TenantScoped, Base):
    __tablename__ = "quizzes"
    
    quiz_id: Column = Column(UUID, primary_key=True)
    tenant_id: Column = Column(UUID, ForeignKey("tenants.tenant_id"), nullable=False)
    host_id: Column = Column(UUID, ForeignKey("users.user_id"))
    title: Column = Column(String(255), nullable=False)
    status: Column = Column(Enum(QuizStatus), default=QuizStatus.DRAFT)


class QuizSession(TenantScoped, Base):
    __tablename__ = "quiz_sessions"
    
    session_id: Column = Column(UUID, primary_key=True)
    tenant_id: Column = Column(UUID, ForeignKey("tenants.tenant_id"), nullable=False)
    quiz_id: Column = Column(UUID, ForeignKey("quizzes.quiz_id"))
    host_id: Column = Column(UUID, ForeignKey("users.user_id"))
    status: Column = Column(Enum(SessionStatus), default=SessionStatus.CREATED)


class Participant(TenantScoped, Base):
    __tablename__ = "participants"
    
    participant_id: Column = Column(UUID, primary_key=True)
    session_id: Column = Column(UUID, ForeignKey("quiz_sessions.session_id"))
    tenant_id: Column = Column(UUID, ForeignKey("tenants.tenant_id"), nullable=False)
    display_name: Column = Column(String(255))


# Event listener to enforce tenant scoping
@event.listens_for(Session, "do_orm_execute")
def enforce_tenant_filtering(orm_execute):
    """
    Global listener: Enforce tenant_id filter on all queries for TenantScoped models.
    
    This is a safety net—explicit tenant filters are still required.
    """
    # Implementation: Check query statements and log non-tenant-filtered queries
    pass
```

#### Repository Pattern for Explicit Scoping

```python
# File: backend/persistence/repositories.py

class TenantScopedRepository:
    """
    Base repository for tenant-scoped entities.
    
    Forces explicit tenant_id parameter on all queries.
    """
    
    def __init__(self, db: Session, model_class):
        self.db = db
        self.model_class = model_class
    
    def get_by_id(self, tenant_id: UUID, entity_id: UUID):
        """Get entity for specific tenant"""
        return self.db.query(self.model_class).filter(
            self.model_class.tenant_id == tenant_id,
            self.model_class.{id_field} == entity_id
        ).first()
    
    def list_for_tenant(self, tenant_id: UUID, skip: int = 0, limit: int = 10):
        """List entities for specific tenant"""
        return self.db.query(self.model_class).filter(
            self.model_class.tenant_id == tenant_id
        ).offset(skip).limit(limit).all()
    
    def create(self, tenant_id: UUID, **kwargs):
        """Create entity for specific tenant"""
        entity = self.model_class(tenant_id=tenant_id, **kwargs)
        self.db.add(entity)
        self.db.commit()
        return entity
    
    def delete(self, tenant_id: UUID, entity_id: UUID):
        """Delete entity (verified to belong to tenant)"""
        entity = self.get_by_id(tenant_id, entity_id)
        if not entity:
            raise EntityNotFoundError(entity_id)
        
        self.db.delete(entity)
        self.db.commit()


# Instantiate repositories for each model
class QuizRepository(TenantScopedRepository):
    def __init__(self, db: Session):
        super().__init__(db, Quiz)


class QuizSessionRepository(TenantScopedRepository):
    def __init__(self, db: Session):
        super().__init__(db, QuizSession)
```

### Layer 3: Application (Request-Level Scoping)

#### Middleware Attaches Tenant Context

```python
# File: backend/broker/middleware/tenant_context.py

@app.middleware("http")
async def tenant_context_middleware(request: Request, call_next):
    """
    Extract tenant from JWT/session and attach to request.
    
    All downstream code accesses tenant via request.state.tenant_id
    """
    tenant_id = extract_tenant_from_request(request)
    request.state.tenant_id = tenant_id
    
    response = await call_next(request)
    return response
```

#### Endpoints Always Include Tenant Context

```python
# File: backend/broker/routes/quiz.py

@router.get("/quiz/{quiz_id}")
async def get_quiz(
    quiz_id: UUID,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Get quiz details.
    
    Always scoped to current tenant via middleware.
    """
    tenant_id = request.state.tenant_id  # ← From middleware
    
    # Query is automatically tenant-scoped
    quiz = db.query(Quiz).filter(
        Quiz.quiz_id == quiz_id,
        Quiz.tenant_id == tenant_id  # ← Explicit filter
    ).first()
    
    if not quiz:
        # Don't reveal whether quiz exists in different tenant
        raise HTTPException(status_code=404, detail="Quiz not found")
    
    return quiz.to_dict()
```

#### Feature Layer Receives Tenant Context

```python
# File: backend/features/quiz/quiz_feature.py

class QuizFeature:
    """
    Quiz feature operations.
    
    Always receives tenant_id from Platform layer.
    Never resolves tenant context itself.
    """
    
    async def create_quiz(
        self,
        tenant_id: UUID,  # ← Provided by Platform
        host_id: UUID,
        title: str,
        description: str = None
    ) -> Quiz:
        """
        Create new quiz.
        
        Tenant context is provided, not resolved.
        """
        quiz = Quiz(
            tenant_id=tenant_id,  # ← Always attach tenant
            host_id=host_id,
            title=title,
            description=description,
            status=QuizStatus.DRAFT
        )
        
        self.db.add(quiz)
        self.db.commit()
        
        return quiz
    
    async def add_question(
        self,
        tenant_id: UUID,  # ← Always required
        quiz_id: UUID,
        text: str,
        options: List[str],
        correct_option: int
    ) -> Question:
        """
        Add question to quiz.
        
        Verify quiz belongs to tenant before modifying.
        """
        # Verify ownership
        quiz = self.db.query(Quiz).filter(
            Quiz.quiz_id == quiz_id,
            Quiz.tenant_id == tenant_id
        ).first()
        
        if not quiz:
            raise QuizNotFoundError(quiz_id)
        
        # Create question
        question = Question(
            quiz_id=quiz_id,
            tenant_id=tenant_id,  # ← Inherit from quiz
            text=text,
            ...
        )
        
        self.db.add(question)
        self.db.commit()
        
        return question
```

---

## Cross-Tenant Access Prevention

### Principle: Fail Safely on Tenant Mismatch

```python
# File: backend/persistence/safety.py

async def verify_entity_ownership(
    tenant_id: UUID,
    entity: TenantScoped,
    entity_name: str = "Entity"
):
    """
    Verify entity belongs to tenant.
    
    Raises TenantMismatchError if mismatch detected.
    """
    if entity.tenant_id != tenant_id:
        # Log security incident
        logger.warning(
            f"Cross-tenant access attempt: {entity_name}",
            extra={
                "requested_tenant": tenant_id,
                "actual_tenant": entity.tenant_id,
                "entity_id": entity.id
            }
        )
        
        raise TenantMismatchError(
            f"Entity does not belong to current tenant"
        )
    
    return entity


# Usage in operations
async def update_quiz(
    tenant_id: UUID,
    quiz_id: UUID,
    title: str,
    db: Session
):
    """Update quiz (with safety check)"""
    quiz = db.query(Quiz).filter_by(quiz_id=quiz_id).first()
    
    if not quiz:
        raise QuizNotFoundError(quiz_id)
    
    # Safety check
    await verify_entity_ownership(tenant_id, quiz, "Quiz")
    
    # Update
    quiz.title = title
    db.commit()
    
    return quiz
```

### Query Validation Pattern

```python
# File: backend/persistence/validators.py

class QueryValidator:
    """
    Validates all database queries include tenant scoping.
    
    Catches errors during development/testing.
    """
    
    @staticmethod
    def validate_tenant_filter(query_str: str, model_name: str):
        """
        Check query includes tenant_id filter.
        
        Raises if tenant filter missing.
        """
        if "tenant_id" not in query_str:
            raise MissingTenantFilterError(
                f"Query for {model_name} missing tenant_id filter. "
                f"This is a security issue."
            )
    
    @staticmethod
    def validate_join_includes_tenant(join_table: str, main_table: str):
        """
        Check multi-table joins include tenant scoping.
        """
        # Ensure both tables filtered by same tenant_id
        pass
```

---

## Testing Tenant Isolation

### Unit Tests: Verify Queries Are Scoped

```python
# File: tests/persistence/test_tenant_isolation.py

async def test_quiz_query_filters_by_tenant():
    """Verify quiz queries include tenant_id filter"""
    tenant1 = create_test_tenant("Org1")
    tenant2 = create_test_tenant("Org2")
    
    quiz1 = create_test_quiz(tenant1.id, "Quiz 1")
    quiz2 = create_test_quiz(tenant2.id, "Quiz 2")
    
    # Tenant1 should only see Quiz1
    quizzes = quiz_repo.list_for_tenant(tenant1.id)
    
    assert len(quizzes) == 1
    assert quizzes[0].quiz_id == quiz1.quiz_id
    assert quiz2.quiz_id not in [q.quiz_id for q in quizzes]


async def test_cross_tenant_access_blocked():
    """Verify tenant2 cannot access tenant1 data"""
    tenant1 = create_test_tenant("Org1")
    tenant2 = create_test_tenant("Org2")
    
    quiz1 = create_test_quiz(tenant1.id, "Quiz 1")
    
    # Tenant2 tries to access Quiz1
    result = quiz_repo.get_by_id(tenant2.id, quiz1.quiz_id)
    
    assert result is None  # Should not be found


async def test_participant_cannot_join_wrong_tenant_session():
    """Verify session isolation"""
    tenant1 = create_test_tenant("Org1")
    tenant2 = create_test_tenant("Org2")
    
    session1 = create_test_session(tenant1.id)
    
    # Tenant2 tries to join Tenant1's session
    with pytest.raises(SessionNotFoundError):
        await quiz_feature.add_participant(
            tenant_id=tenant2.id,
            session_id=session1.session_id,
            display_name="Intruder"
        )
```

### Integration Tests: Verify API Isolation

```python
# File: tests/api/test_tenant_isolation_e2e.py

async def test_api_endpoint_respects_tenant():
    """Verify API endpoints return 404 for cross-tenant access"""
    tenant1_client = create_client(tenant_id=TENANT1_ID)
    tenant2_client = create_client(tenant_id=TENANT2_ID)
    
    quiz1 = create_test_quiz(TENANT1_ID, "Secret Quiz")
    
    # Tenant1 can see own quiz
    response = await tenant1_client.get(f"/api/quiz/{quiz1.quiz_id}")
    assert response.status_code == 200
    
    # Tenant2 cannot see tenant1's quiz
    response = await tenant2_client.get(f"/api/quiz/{quiz1.quiz_id}")
    assert response.status_code == 404
```

---

## Audit Logging

### Log All Data Access

```python
# File: backend/persistence/audit.py

@event.listens_for(Session, "after_bulk_update")
@event.listens_for(Session, "after_bulk_delete")
def audit_bulk_operations(context):
    """Log bulk operations with tenant context"""
    logger.info(
        "Bulk database operation",
        extra={
            "operation": context.operation,
            "table": context.mapper.class_.__name__,
            "count": context.execution_options.get("count", 0),
            "tenant_id": context.state.tenant_id
        }
    )


def log_data_access(
    tenant_id: UUID,
    entity_type: str,
    entity_id: UUID,
    action: str = "read"
):
    """Log entity access for audit trail"""
    logger.info(
        f"Data access: {action}",
        extra={
            "tenant_id": tenant_id,
            "entity_type": entity_type,
            "entity_id": entity_id,
            "action": action,
            "timestamp": datetime.utcnow().isoformat()
        }
    )
```

---

## Performance Considerations

### Indexing Strategy

```sql
-- Primary query pattern: single tenant
CREATE INDEX idx_tenant_primary ON quizzes(tenant_id);
CREATE INDEX idx_tenant_primary ON quiz_sessions(tenant_id);

-- Secondary pattern: tenant + time
CREATE INDEX idx_tenant_time ON quiz_sessions(tenant_id, created_at DESC);
CREATE INDEX idx_tenant_time ON quizzes(tenant_id, created_at DESC);

-- Tertiary pattern: tenant + status
CREATE INDEX idx_tenant_status ON quiz_sessions(tenant_id, status);
```

### Query Optimization

```python
# Good: Filters on tenant first
query = db.query(Quiz).filter(
    Quiz.tenant_id == tenant_id
).filter(
    Quiz.status == QuizStatus.ACTIVE
)

# Avoid: Secondary filters before tenant
query = db.query(Quiz).filter(
    Quiz.status == QuizStatus.ACTIVE
).filter(
    Quiz.tenant_id == tenant_id
)
```

---

## Implementation Checklist

- [ ] All domain tables include `tenant_id` column
- [ ] Composite indexes created for common queries
- [ ] Repository pattern implemented for all models
- [ ] ORM models inherit from `TenantScoped`
- [ ] Middleware extracts and attaches tenant context
- [ ] Features receive tenant_id as parameter
- [ ] All queries verified to include tenant filter
- [ ] Cross-tenant access tests passing
- [ ] Audit logging implemented
- [ ] Performance tests validated

---

## Security Audit

**Critical:** Before deploying multi-tenant system:

1. [ ] Audit all database queries for tenant_id filter
2. [ ] Verify no raw SQL queries without tenant scoping
3. [ ] Check middleware applies to all routes
4. [ ] Test cross-tenant access rejection
5. [ ] Review audit logs for security incidents
6. [ ] Load test quota enforcement
7. [ ] Penetration test multi-tenant boundaries
