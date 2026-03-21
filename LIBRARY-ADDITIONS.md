# Library Additions Summary

**Date:** January 29, 2026  
**Purpose:** Document all recommended open source libraries incorporated into Swaya.me technology stack.

---

## Overview

Added **10 production-ready open source libraries** across backend, frontend, and testing layers to enhance functionality while maintaining 100% open source commitment.

**Total Licensing Cost:** $0 (All MIT, Apache 2.0, BSD, or CC BY 4.0)

---

## Backend Libraries (Python)

### 1. **python-statemachine** (MIT) - HIGH PRIORITY ✅

**Purpose:** Enforce quiz session state transitions  
**Version:** 2.3.0+  
**Layer:** Features (Quiz)  

**Why:**
- Enforces valid state transitions (CREATED → ACTIVE → QUESTION_CLOSED → ENDED)
- Prevents invalid state changes
- Makes state rules explicit and testable
- Aligns with "no hidden state" architecture principle

**Usage:**
```python
from statemachine import StateMachine, State

class QuizSessionStateMachine(StateMachine):
    created = State('CREATED', initial=True)
    active = State('ACTIVE')
    question_closed = State('QUESTION_CLOSED')
    ended = State('ENDED')
    
    start = created.to(active)
    close_question = active.to(question_closed)
    next_question = question_closed.to(active)
    end = question_closed.to(ended)
```

---

### 2. **better-profanity** (MIT) - HIGH PRIORITY (MVP) ✅

**Purpose:** Profanity detection and filtering  
**Version:** 0.7.0+  
**Layer:** Core (Broker - Policy Enforcement)  

**Why:**
- **MVP requirement** per business scope
- Lightweight and customizable
- Supports masking and custom word lists
- Server-side enforcement at Broker layer

**Scope:**
- Quiz questions and answer options
- Display names
- Poll options (post-MVP)
- Word cloud submissions (post-MVP)

**Usage:**
```python
from better_profanity import profanity

profanity.load_censor_words()

if profanity.contains_profanity(text):
    # Reject or mask
    clean_text = profanity.censor(text)
```

---

### 3. **bleach** (Apache 2.0) - HIGH PRIORITY (MVP) ✅

**Purpose:** HTML/text sanitization (XSS prevention)  
**Version:** 6.1.0+  
**Layer:** Core (Broker - Policy Enforcement)  

**Why:**
- **MVP requirement** for input sanitization
- Industry standard for preventing XSS attacks
- Strips dangerous HTML tags and attributes
- Works alongside profanity detection

**Usage:**
```python
import bleach

clean_text = bleach.clean(
    user_input,
    tags=[],
    strip=True,
    strip_comments=True
)
```

---

### 4. **pytest-asyncio** (Apache 2.0) - HIGH PRIORITY ✅

**Purpose:** Test async functions and FastAPI endpoints  
**Version:** 0.23.0+  
**Layer:** Testing  

**Why:**
- **Required** for testing FastAPI async routes
- Standard for async test support
- Integrates seamlessly with pytest

**Usage:**
```python
@pytest.mark.asyncio
async def test_submit_answer(test_client):
    response = await test_client.post("/api/v1/answers/submit", json={...})
    assert response.status_code == 200
```

---

### 5. **pytest-cov** (MIT) - MEDIUM PRIORITY

**Purpose:** Code coverage reporting  
**Version:** Latest  
**Layer:** Testing  

**Why:**
- Track test coverage metrics
- Identify untested code paths
- Quality assurance

**Usage:**
```bash
pytest --cov=backend --cov-report=html
```

---

### 6. **cachetools** (MIT) - LOW PRIORITY

**Purpose:** In-memory caching for computed results  
**Version:** Latest  
**Layer:** Features  

**Why:**
- Cache quiz aggregation results
- Performance optimization
- Simple decorator-based API

**Usage:**
```python
from cachetools import cached, TTLCache

@cached(cache=TTLCache(maxsize=100, ttl=60))
def get_question_results(session_id, question_id):
    return aggregate_answers(session_id, question_id)
```

---

## Frontend Libraries (JavaScript/TypeScript)

### 7. **React Hook Form** (MIT) - HIGH PRIORITY ✅

**Purpose:** Form state management with validation  
**Version:** 7.50.0+  
**Layer:** Frontend (Forms)  

**Why:**
- Less boilerplate than manual state management
- Better performance (fewer re-renders)
- Built-in validation support
- Works perfectly with Ant Design

**Scope:**
- Login form
- Quiz builder (add questions, options)
- All user input forms

**Usage:**
```javascript
import { useForm } from 'react-hook-form';

function Login() {
  const { register, handleSubmit, formState: { errors } } = useForm();
  
  return (
    <Form onFinish={handleSubmit(onSubmit)}>
      <Input {...register('email', { required: true })} />
    </Form>
  );
}
```

---

### 8. **Yup** (MIT) - HIGH PRIORITY ✅

**Purpose:** Schema-based validation for forms  
**Version:** 1.3.0+  
**Layer:** Frontend (Validation)  

**Why:**
- Declarative validation rules
- Integrates with React Hook Form
- Reusable schemas
- Type-safe validation

**Usage:**
```javascript
import * as yup from 'yup';
import { yupResolver } from '@hookform/resolvers/yup';

const schema = yup.object({
  email: yup.string().email('Invalid email').required('Email required'),
  password: yup.string().min(8, 'Min 8 characters').required()
});

const { register, handleSubmit } = useForm({
  resolver: yupResolver(schema)
});
```

---

### 9. **Font Awesome** (MIT / CC BY 4.0) - HIGH PRIORITY ✅

**Purpose:** Consistent icon set across application  
**Version:** 6.5.0+ (Free version)  
**Layer:** Frontend (UI)  

**Why:**
- Comprehensive free icon library
- Consistent visual language
- MIT licensed for code, CC BY 4.0 for icons
- Industry standard

**Scope:**
- UI actions (save, delete, edit, share)
- Status indicators (loading, success, error)
- Navigation icons

**Usage:**
```javascript
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import { faSave, faPlay, faStop } from '@fortawesome/free-solid-svg-icons';

<Button icon={<FontAwesomeIcon icon={faSave} />}>Save</Button>
```

---

### 10. **date-fns** (MIT) - MEDIUM PRIORITY ✅

**Purpose:** Date formatting and manipulation  
**Version:** 3.0.0+  
**Layer:** Frontend (Utilities)  

**Why:**
- Lightweight (tree-shakeable)
- Modern alternative to moment.js
- Simple API for common date operations

**Scope:**
- Display timestamps
- Relative time display ("2 minutes ago")
- Date formatting

**Usage:**
```javascript
import { formatDistanceToNow, format } from 'date-fns';

// "2 minutes ago"
<span>{formatDistanceToNow(new Date(quiz.created_at), { addSuffix: true })}</span>

// "Jan 29, 2026"
<span>{format(new Date(quiz.created_at), 'MMM dd, yyyy')}</span>
```

---

## Implementation Priority

### Phase 1: MVP (Implement Now)

| Priority | Library | Reason |
|----------|---------|--------|
| 🔴 CRITICAL | **python-statemachine** | Core to quiz state management |
| 🔴 CRITICAL | **better-profanity** | MVP business requirement |
| 🔴 CRITICAL | **bleach** | MVP security requirement |
| 🔴 CRITICAL | **React Hook Form** | Quiz builder form handling |
| 🔴 CRITICAL | **Yup** | Form validation with React Hook Form |
| 🔴 CRITICAL | **Font Awesome** | UI consistency |
| 🔴 CRITICAL | **pytest-asyncio** | Required for FastAPI testing |

### Phase 2: Post-MVP (Quality & Polish)

| Priority | Library | Reason |
|----------|---------|--------|
| 🟡 MEDIUM | **date-fns** | Better UX for timestamps |
| 🟡 MEDIUM | **pytest-cov** | Code coverage tracking |
| 🟢 LOW | **cachetools** | Performance optimization |

---

## Installation Commands

### Backend (requirements.txt)
```txt
# Core dependencies (already in stack)
fastapi==0.109.0
pydantic==2.5.0
sqlalchemy==2.0.25
alembic==1.13.0
redis==5.0.1
pyjwt==2.8.0
bcrypt==4.1.2
slowapi==0.1.9
python-json-logger==2.0.7

# New additions (MVP)
python-statemachine==2.3.0
better-profanity==0.7.0
bleach==6.1.0
pytest-asyncio==0.23.0

# New additions (Post-MVP)
pytest-cov==4.1.0
cachetools==5.3.2
```

### Frontend (package.json)
```json
{
  "dependencies": {
    "react": "^18.2.0",
    "antd": "^5.12.0",
    "@reduxjs/toolkit": "^2.0.0",
    "react-router-dom": "^6.21.0",
    "axios": "^1.6.0",
    
    "react-hook-form": "^7.50.0",
    "yup": "^1.3.0",
    "@hookform/resolvers": "^3.3.0",
    "@fortawesome/react-fontawesome": "^0.2.0",
    "@fortawesome/free-solid-svg-icons": "^6.5.0",
    "date-fns": "^3.0.0"
  }
}
```

---

## Documentation Updates

### Files Modified

1. **Docs/Technology_Stack_Final.md**
   - Added all 10 libraries to Table 1
   - Added functional responsibilities to Table 2

2. **specs/TECHNOLOGY_REFERENCE.md**
   - Added comprehensive YAML documentation for each library
   - Included version requirements and use cases

3. **specs/frontend/screens.md**
   - Updated technology stack section
   - Added React Hook Form, Yup, Font Awesome, date-fns

4. **specs/backend/api-layer-strategy.md**
   - Added profanity detection section (300+ lines)
   - Implementation examples with better-profanity and bleach
   - Integration with Pydantic schemas
   - Testing examples

---

## Architecture Alignment

All libraries align with Swaya.me's architectural principles:

✅ **100% Open Source** - All use permissive licenses (MIT, Apache 2.0, BSD, CC BY)  
✅ **Zero Licensing Costs** - No subscription or usage fees  
✅ **Vendor Neutral** - No lock-in to proprietary platforms  
✅ **Production Ready** - All have proven track records at scale  
✅ **Layer Separation** - Each library respects architectural boundaries:
  - Core: profanity, bleach, python-statemachine
  - Broker: Slowapi, python-json-logger
  - Frontend: React Hook Form, Yup, Font Awesome, date-fns
  - Testing: pytest-asyncio, pytest-cov

---

## License Summary

| License | Libraries | Count |
|---------|-----------|-------|
| **MIT** | python-statemachine, better-profanity, React Hook Form, Yup, date-fns, Font Awesome (code) | 6 |
| **Apache 2.0** | bleach, pytest-asyncio | 2 |
| **BSD 2-Clause** | python-json-logger | 1 |
| **CC BY 4.0** | Font Awesome (icons) | 1 |

**Total:** 10 libraries, 0 licensing costs, 100% open source ✅

---

## Testing Coverage

With these additions, testing capabilities expand:

**Backend:**
- ✅ Unit tests (pytest)
- ✅ Async endpoint tests (pytest-asyncio)
- ✅ State machine tests (python-statemachine)
- ✅ Profanity filter tests (better-profanity)
- ✅ Coverage reports (pytest-cov)

**Frontend:**
- ✅ Form validation tests (React Hook Form + Yup)
- ✅ Component tests (Jest + React Testing Library)
- ✅ Integration tests

---

## Next Steps

1. ✅ **Documentation Updated** (Complete)
2. ⏭️ Add dependencies to requirements.txt / package.json
3. ⏭️ Implement python-statemachine for quiz sessions
4. ⏭️ Implement profanity filter middleware
5. ⏭️ Integrate React Hook Form into quiz builder
6. ⏭️ Add Font Awesome icons to UI components
7. ⏭️ Write unit tests using pytest-asyncio
8. ⏭️ Set up pytest-cov for coverage tracking

---

## References

- [python-statemachine](https://github.com/fgmacedo/python-statemachine)
- [better-profanity](https://github.com/snguyenthanh/better_profanity)
- [bleach](https://github.com/mozilla/bleach)
- [React Hook Form](https://react-hook-form.com/)
- [Yup](https://github.com/jquense/yup)
- [Font Awesome](https://fontawesome.com/)
- [date-fns](https://date-fns.org/)
- [pytest-asyncio](https://github.com/pytest-dev/pytest-asyncio)
