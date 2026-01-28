# Frontend State Management (Redux Toolkit)

This document defines the Redux Toolkit state structure, slices, and API bindings for the Swaya.me MVP.

---

## State Architecture

### Redux Store Structure

```javascript
{
  auth: { ... },          // Authentication state
  quizzes: { ... },       // Quiz management
  session: { ... },       // Live quiz session
  ui: { ... }             // UI state (modals, loading)
}
```

---

## Slice 1: Auth

### Purpose
Manage host authentication state and JWT token.

### State Shape
```javascript
{
  user: {
    user_id: "usr_123",
    email: "host@example.com",
    full_name: "John Doe"
  },
  token: "EXAMPLE_JWT_TOKEN",
  isAuthenticated: true,
  loading: false,
  error: null
}
```

### Actions

| Action | Payload | Behavior |
|--------|---------|----------|
| `login` | { email, password } | Async thunk: POST /auth/login, store token, update user |
| `logout` | None | Clear token and user, redirect to /login |
| `checkAuth` | None | Verify token validity on app load |

### Selectors
```javascript
export const selectUser = (state) => state.auth.user;
export const selectIsAuthenticated = (state) => state.auth.isAuthenticated;
export const selectAuthLoading = (state) => state.auth.loading;
export const selectAuthError = (state) => state.auth.error;
```

### Async Thunks
```javascript
export const login = createAsyncThunk(
  'auth/login',
  async ({ email, password }, { rejectWithValue }) => {
    try {
      const response = await axios.post('/auth/login', { email, password });
      localStorage.setItem('token', response.data.access_token);
      return response.data;
    } catch (error) {
      return rejectWithValue(error.response.data);
    }
  }
);
```

---

## Slice 2: Quizzes

### Purpose
Manage quiz definitions (CRUD operations).

### State Shape
```javascript
{
  list: [
    {
      quiz_id: "qz_789",
      title: "Weekly Science Quiz",
      status: "READY",
      question_count: 5,
      created_at: "2026-01-27T10:00:00Z"
    }
  ],
  current: {
    quiz_id: "qz_789",
    title: "Weekly Science Quiz",
    description: "Test your science knowledge",
    status: "DRAFT",
    questions: [
      {
        question_id: "q_456",
        text: "What is 2+2?",
        options: [
          { option_id: "opt_1", text: "3", order: 1 },
          { option_id: "opt_2", text: "4", order: 2 },
          { option_id: "opt_3", text: "5", order: 3 },
          { option_id: "opt_4", text: "6", order: 4 }
        ],
        correct_option_id: "opt_2"
      }
    ]
  },
  loading: false,
  error: null
}
```

### Actions

| Action | Payload | Behavior |
|--------|---------|----------|
| `fetchQuizzes` | None | Async thunk: GET /quizzes, populate list |
| `fetchQuiz` | { quiz_id } | Async thunk: GET /quizzes/{quiz_id}, populate current |
| `createQuiz` | { title, description } | Async thunk: POST /quizzes, add to list |
| `updateQuiz` | { quiz_id, ...data } | Async thunk: PATCH /quizzes/{quiz_id}, update current |
| `deleteQuiz` | { quiz_id } | Async thunk: DELETE /quizzes/{quiz_id}, remove from list |
| `addQuestion` | { quiz_id, question } | Async thunk: POST /quizzes/{quiz_id}/questions, add to current |
| `deleteQuestion` | { quiz_id, question_id } | Remove question from current |

### Selectors
```javascript
export const selectQuizList = (state) => state.quizzes.list;
export const selectCurrentQuiz = (state) => state.quizzes.current;
export const selectQuizzesLoading = (state) => state.quizzes.loading;
export const selectQuizzesError = (state) => state.quizzes.error;
```

---

## Slice 3: Session

### Purpose
Manage live quiz session state (host and audience).

### State Shape (Host)
```javascript
{
  session: {
    session_id: "sess_xyz",
    quiz_id: "qz_789",
    join_code: "ABC123",
    status: "ACTIVE",
    participant_count: 50,
    current_question_index: 0
  },
  current_question: {
    question_id: "q_456",
    text: "What is 2+2?",
    options: [
      { option_id: "opt_1", text: "3" },
      { option_id: "opt_2", text: "4" },
      { option_id: "opt_3", text: "5" },
      { option_id: "opt_4", text: "6" }
    ],
    state: "OPEN"
  },
  live_results: [
    { option_id: "opt_1", text: "3", count: 5, percentage: 10.0 },
    { option_id: "opt_2", text: "4", count: 40, percentage: 80.0 },
    { option_id: "opt_3", text: "5", count: 3, percentage: 6.0 },
    { option_id: "opt_4", text: "6", count: 2, percentage: 4.0 }
  ],
  loading: false,
  error: null
}
```

### State Shape (Audience)
```javascript
{
  session: {
    session_id: "sess_xyz",
    quiz_title: "Weekly Science Quiz",
    status: "ACTIVE"
  },
  participant_id: "part_123",
  current_question: {
    question_id: "q_456",
    text: "What is 2+2?",
    options: [
      { option_id: "opt_1", text: "3" },
      { option_id: "opt_2", text: "4" },
      { option_id: "opt_3", text: "5" },
      { option_id: "opt_4", text: "6" }
    ],
    state: "OPEN"
  },
  selected_option: "opt_2",
  submitted: false,
  results: null,
  loading: false,
  error: null
}
```

### Actions (Host)

| Action | Payload | Behavior |
|--------|---------|----------|
| `startSession` | { quiz_id } | Async thunk: POST /quizzes/{quiz_id}/sessions, create session |
| `startQuiz` | { session_id } | Async thunk: POST /sessions/{session_id}/start, open first question |
| `advanceQuestion` | { session_id } | Async thunk: POST /sessions/{session_id}/advance, next question |
| `endSession` | { session_id } | Async thunk: POST /sessions/{session_id}/end, close session |
| `pollSessionStatus` | { session_id } | Async thunk: GET /sessions/{session_id}/status, update live_results |

### Actions (Audience)

| Action | Payload | Behavior |
|--------|---------|----------|
| `joinSession` | { join_code } | Async thunk: POST /sessions/join, store participant_id |
| `submitAnswer` | { session_id, participant_id, question_id, option_id } | Async thunk: POST /sessions/{session_id}/submit, mark submitted |
| `pollSessionStatus` | { session_id } | Async thunk: GET /sessions/{session_id}/status, update question/results |

### Selectors
```javascript
export const selectSession = (state) => state.session.session;
export const selectCurrentQuestion = (state) => state.session.current_question;
export const selectLiveResults = (state) => state.session.live_results;
export const selectParticipantId = (state) => state.session.participant_id;
export const selectSessionLoading = (state) => state.session.loading;
export const selectSessionError = (state) => state.session.error;
```

---

## Slice 4: UI

### Purpose
Manage global UI state (modals, notifications, loading).

### State Shape
```javascript
{
  modals: {
    confirmDelete: {
      open: false,
      quiz_id: null
    }
  },
  notifications: [],
  globalLoading: false
}
```

### Actions

| Action | Payload | Behavior |
|--------|---------|----------|
| `openModal` | { modalName, ...data } | Open modal with data |
| `closeModal` | { modalName } | Close modal |
| `showNotification` | { message, type } | Add notification (success, error, info) |
| `hideNotification` | { id } | Remove notification |
| `setGlobalLoading` | { loading } | Show/hide global loading spinner |

---

## API Bindings (RTK Query Alternative)

**Note**: MVP uses **axios + async thunks** for simplicity. RTK Query can be introduced post-MVP for caching and optimistic updates.

### Example Async Thunk with Error Handling

```javascript
import { createAsyncThunk } from '@reduxjs/toolkit';
import axios from 'axios';

export const fetchQuizzes = createAsyncThunk(
  'quizzes/fetchQuizzes',
  async (_, { getState, rejectWithValue }) => {
    try {
      const { auth } = getState();
      const response = await axios.get('/api/v1/quizzes', {
        headers: { Authorization: `Bearer ${auth.token}` }
      });
      return response.data.quizzes;
    } catch (error) {
      return rejectWithValue(error.response?.data || { message: 'Network error' });
    }
  }
);
```

---

## Polling Strategy (Realtime Updates)

### Host Polling
```javascript
// Start polling when session is active
useEffect(() => {
  if (session.status === 'ACTIVE') {
    const interval = setInterval(() => {
      dispatch(pollSessionStatus({ session_id: session.session_id }));
    }, 2000); // Poll every 2 seconds
    
    return () => clearInterval(interval);
  }
}, [session.status]);
```

### Audience Polling
```javascript
// Start polling after joining session
useEffect(() => {
  if (participant_id) {
    const interval = setInterval(() => {
      dispatch(pollSessionStatus({ session_id: session.session_id }));
    }, 2000); // Poll every 2 seconds
    
    return () => clearInterval(interval);
  }
}, [participant_id]);
```

---

## State Persistence

### LocalStorage
- **Token**: Stored in localStorage, cleared on logout
- **Session Data**: Not persisted (ephemeral)

### Redux Persist (Optional Post-MVP)
- Persist auth slice for "remember me" functionality
- Whitelist: `auth.token`, `auth.user`

---

## Error Handling

### Global Error Interceptor
```javascript
axios.interceptors.response.use(
  response => response,
  error => {
    if (error.response?.status === 401) {
      dispatch(logout());
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);
```

### User-Facing Errors
- Display using Ant Design `message` or `notification`
- Error messages from API response: `error.response.data.message`

---

## Testing Strategy

### Unit Tests (Jest)
- Test reducers: verify state updates
- Test selectors: verify data extraction
- Test async thunks: mock axios, verify actions dispatched

### Integration Tests (React Testing Library)
- Test component + Redux integration
- Verify dispatch on user actions
- Verify UI updates based on state changes
