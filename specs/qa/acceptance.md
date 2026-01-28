# Acceptance Criteria (MVP)

This document defines the acceptance criteria for each user flow in the Swaya.me MVP.

---

## Host Flow: Create and Run Quiz

### Feature 1: Host Login

**Given** a registered host user exists  
**When** the host navigates to `/login`  
**And** enters valid email and password  
**And** clicks "Login" button  
**Then** the host should be authenticated  
**And** a JWT token should be stored  
**And** the host should be redirected to `/dashboard`

**Acceptance Criteria**:
- [ ] Login form displays email and password fields
- [ ] Email field validates format (user@domain.com)
- [ ] Password field masks input
- [ ] Successful login returns JWT token
- [ ] Token is stored in localStorage or httpOnly cookie
- [ ] Invalid credentials show error message: "Invalid email or password"
- [ ] Rate limiting: 5 attempts per minute per IP
- [ ] Redirect to dashboard after successful login

---

### Feature 2: Create Quiz

**Given** a host is authenticated  
**When** the host clicks "Create New Quiz" on dashboard  
**Then** the host should be navigated to `/quiz/new`  
**And** should see an empty quiz builder form

**Acceptance Criteria**:
- [ ] Quiz builder displays title and description fields
- [ ] Title field is required (1-255 characters)
- [ ] Description field is optional (0-1000 characters)
- [ ] Save Draft button creates quiz with status DRAFT
- [ ] Created quiz appears in dashboard quiz list
- [ ] Error messages display for validation failures

---

### Feature 3: Add Questions

**Given** a host has created a quiz  
**When** the host clicks "Add Question"  
**Then** a new question card should appear  
**And** the host should be able to enter question text and 4 options

**Acceptance Criteria**:
- [ ] Question text field is required (1-500 characters)
- [ ] Exactly 4 option fields are displayed
- [ ] Each option field is required (1-200 characters)
- [ ] Radio button group allows selecting one correct answer
- [ ] Correct answer selection is required
- [ ] Question can be deleted before saving
- [ ] Save Draft persists questions to database
- [ ] Multiple questions can be added (no limit in MVP)

---

### Feature 3.5: Autosave and Validation

**Given** a host is editing quiz or questions  
**When** the host stops typing for 1 second  
**Then** changes should be automatically saved  
**And** a "Saved" indicator should appear briefly

**Acceptance Criteria**:
- [ ] Autosave triggers 1 second after last keystroke
- [ ] "Saving..." indicator displays during save
- [ ] "Saved" checkmark appears after successful save
- [ ] Unsaved changes indicator (* in title) appears if pending
- [ ] Save error displays with retry message if failed
- [ ] Validation runs before publish attempt
- [ ] Validation errors list all issues (missing title, no questions, etc.)
- [ ] Cannot publish quiz if validation fails

---

### Feature 3.6: Reorder Questions

**Given** a host has multiple questions in a quiz  
**When** the host drags a question card to a new position  
**Then** the question order should update  
**And** changes should be persisted

**Acceptance Criteria**:
- [ ] Questions display in correct order on screen
- [ ] Drag-and-drop reordering works smoothly
- [ ] Order is persisted after reorder API call
- [ ] Question numbers update automatically
- [ ] Reordering works with any number of questions
- [ ] Undo/redo not required (MVP)

---

### Feature 3.7: Preview Quiz

**Given** a host has created a quiz with questions  
**When** the host clicks "Preview"  
**Then** a modal should display the quiz as audience sees it  
**And** host should see all questions in sequence (read-only)

**Acceptance Criteria**:
- [ ] Preview modal displays quiz title and description
- [ ] All questions display in order
- [ ] Question options display as radio buttons
- [ ] Preview is read-only (cannot modify from preview)
- [ ] Close button returns to edit mode
- [ ] Preview shows exactly what audience will see

---

### Feature 4: Publish Quiz

**Given** a host has created a quiz with at least one question  
**When** the host clicks "Publish Quiz"  
**Then** the quiz status should change to READY  
**And** the host should be redirected to dashboard  
**And** the quiz should appear as READY in the quiz list

**Acceptance Criteria**:
- [ ] Publish button triggers validation check
- [ ] If invalid, error modal displays with issues to fix
- [ ] If valid, status changes from DRAFT to READY
- [ ] Success message displays: "Quiz published successfully"
- [ ] Quiz appears in dashboard with "Start Session" button enabled
- [ ] Published quiz cannot be edited during live session (MVP constraint)
- [ ] User can only publish their own quizzes

---

### Feature 5: Start Quiz Session

**Given** a host has a READY quiz  
**When** the host clicks "Start Session"  
**Then** a quiz session should be created  
**And** a unique 6-character join code should be generated  
**And** the host should be navigated to `/session/{session_id}/control`

**Acceptance Criteria**:
- [ ] Session created with status CREATED
- [ ] Join code is 6 characters, alphanumeric, case-insensitive
- [ ] Join code is unique (no duplicates)
- [ ] Host sees join code displayed prominently
- [ ] Participant count shows 0 initially
- [ ] "Start Quiz" button is visible
- [ ] Only one active session allowed per quiz (MVP constraint)

---

### Feature 6: Start Quiz and Open First Question

**Given** a host has created a quiz session  
**When** the host clicks "Start Quiz"  
**Then** the session status should change to ACTIVE  
**And** the first question should be opened  
**And** the question should be broadcast to audience

**Acceptance Criteria**:
- [ ] Session status changes from CREATED to ACTIVE
- [ ] First question (order_index = 1) is displayed
- [ ] Question state is OPEN
- [ ] Audience members can submit answers
- [ ] Live answer counts start at 0
- [ ] Start Quiz button is replaced by "Next Question" and "Close Question" buttons

---

### Feature 7: View Live Answer Counts

**Given** a quiz question is open  
**When** audience members submit answers  
**Then** the host should see live answer counts update in real-time

**Acceptance Criteria**:
- [ ] Answer counts displayed as bar chart or table
- [ ] Counts update automatically (polling every 2s)
- [ ] Each option shows count and percentage
- [ ] Total responses count is displayed
- [ ] No participant identities are revealed (anonymous)
- [ ] Counts are accurate (match database submissions)

---

### Feature 8: Close Question and Show Results

**Given** a quiz question is open  
**When** the host clicks "Close Question"  
**Then** the question state should change to CLOSED  
**And** no more answers should be accepted  
**And** the correct answer should be highlighted  
**And** results should be broadcast to audience

**Acceptance Criteria**:
- [ ] Question state changes from OPEN to CLOSED
- [ ] Late submissions are rejected with error
- [ ] Correct answer is highlighted (e.g., green background)
- [ ] Final answer distribution is displayed
- [ ] Results are broadcast to all audience members
- [ ] "Next Question" button becomes active

---

### Feature 9: Advance to Next Question

**Given** a question is closed  
**When** the host clicks "Next Question"  
**Then** the next question should be opened  
**And** the question should be broadcast to audience

**Acceptance Criteria**:
- [ ] Next question (order_index incremented) is displayed
- [ ] Question state is OPEN
- [ ] Previous question results are cleared from host view
- [ ] Audience sees new question automatically (via polling)
- [ ] Answer counts reset to 0
- [ ] Process repeats until all questions are complete

---

### Feature 10: End Quiz Session

**Given** all questions have been presented  
**When** the host clicks "End Quiz"  
**Then** the session status should change to ENDED  
**And** the audience should be notified  
**And** no more interactions should be allowed

**Acceptance Criteria**:
- [ ] Confirmation modal appears: "Are you sure you want to end the quiz?"
- [ ] Session status changes to ENDED
- [ ] Audience sees "Quiz has ended" message
- [ ] Join code becomes invalid
- [ ] Audience participants are cleared from Redis
- [ ] Host can return to dashboard
- [ ] Final summary is displayed (optional MVP feature)

---

## Audience Flow: Join and Participate

### Feature 11: Join Quiz Session

**Given** a host has started a quiz session  
**When** an audience member enters the join code  
**Then** the audience member should join the session  
**And** should be assigned a participant ID

**Acceptance Criteria**:
- [ ] Join page displays input field for join code
- [ ] Join code input accepts 6 alphanumeric characters
- [ ] Join code is case-insensitive (ABC123 = abc123)
- [ ] Valid join code creates participant session
- [ ] Participant ID is generated and stored
- [ ] Audience is navigated to `/session/{session_id}/play`
- [ ] Invalid join code shows error: "Quiz session not found or has ended"
- [ ] Rate limiting: 10 join attempts per minute per IP

---

### Feature 12: Wait for Quiz to Start

**Given** an audience member has joined  
**When** the host has not yet started the quiz  
**Then** the audience should see a waiting message

**Acceptance Criteria**:
- [ ] Waiting message displays: "Waiting for host to start quiz..."
- [ ] Quiz title is displayed
- [ ] Polling occurs every 2 seconds
- [ ] When host starts quiz, first question is displayed automatically
- [ ] No action buttons are visible during wait

---

### Feature 13: View Question and Submit Answer

**Given** a question is open  
**When** the audience member selects an answer  
**And** clicks "Submit Answer"  
**Then** the answer should be recorded  
**And** a confirmation message should be displayed

**Acceptance Criteria**:
- [ ] Question text is displayed clearly
- [ ] 4 answer options are displayed as radio buttons
- [ ] Only one option can be selected
- [ ] Submit button is enabled when an option is selected
- [ ] Submit request includes participant_id, question_id, option_id
- [ ] Successful submission shows: "Answer submitted!"
- [ ] Selected option is visually marked as submitted
- [ ] Submit button is disabled after submission
- [ ] Duplicate submission is rejected with error
- [ ] Late submission (after close) is rejected with error

---

### Feature 14: View Results After Question Close

**Given** an audience member has submitted an answer  
**When** the host closes the question  
**Then** the audience should see the correct answer and results

**Acceptance Criteria**:
- [ ] Correct answer is highlighted (e.g., green)
- [ ] Audience's selected answer is indicated
- [ ] Bar chart shows answer distribution
- [ ] Percentages are displayed for each option
- [ ] Total responses count is shown
- [ ] Waiting message displays: "Waiting for next question..."
- [ ] Results update automatically (via polling)

---

### Feature 15: Participate in Multiple Questions

**Given** the quiz has multiple questions  
**When** the host advances to the next question  
**Then** the audience should see the new question automatically  
**And** should be able to submit a new answer

**Acceptance Criteria**:
- [ ] New question is displayed automatically (via polling)
- [ ] Previous question results are cleared
- [ ] Answer selection is reset (no option selected)
- [ ] Submit button is enabled again
- [ ] Process repeats for each question
- [ ] Audience can participate in all questions

---

### Feature 16: Quiz Ends

**Given** the host has ended the quiz  
**When** the audience polls for status  
**Then** the audience should see an end message  
**And** the session should be closed

**Acceptance Criteria**:
- [ ] End message displays: "Quiz has ended. Thank you for participating!"
- [ ] No more questions are displayed
- [ ] Polling stops
- [ ] Participant session is cleared
- [ ] Audience cannot submit more answers
- [ ] Join code becomes invalid for new participants

---

## Non-Functional Acceptance Criteria

### Performance

- [ ] API response time < 500ms (95th percentile) for read operations
- [ ] API response time < 1s (95th percentile) for write operations
- [ ] Realtime message latency < 2s from host action to audience notification
- [ ] Quiz result aggregation displayed within 2s of question close
- [ ] System supports 200 concurrent participants per quiz session
- [ ] System supports 5 simultaneous live quiz sessions
- [ ] Polling does not cause UI lag or blocking

### Security

- [ ] JWT tokens expire after 24 hours
- [ ] Passwords are hashed with bcrypt (cost factor 12)
- [ ] HTTPS enforced in production
- [ ] CORS configured to allow only frontend domain
- [ ] Rate limiting enforced on login, join, and submit endpoints
- [ ] SQL injection prevented via parameterized queries (SQLAlchemy)
- [ ] XSS prevented via input sanitization

### Reliability

- [ ] Database connection pooling prevents connection exhaustion
- [ ] Redis connection failures degrade gracefully (show cached data or error)
- [ ] Session state is recoverable from database if Redis fails
- [ ] Quiz session state is consistent across page refreshes
- [ ] No data loss on server restart (persistent data in MySQL)

### Usability

- [ ] All forms display clear validation errors
- [ ] Loading states are shown during API requests
- [ ] Success messages confirm user actions
- [ ] Error messages are user-friendly (no stack traces)
- [ ] UI is responsive on desktop and tablet (mobile optional MVP)

---

## Definition of Done (Per Feature)

A feature is considered **DONE** when:

1. [ ] All acceptance criteria are met
2. [ ] Unit tests are written and passing
3. [ ] Integration tests are written and passing (if applicable)
4. [ ] Code is reviewed and approved
5. [ ] Documentation is updated
6. [ ] Feature is deployed to staging/test environment
7. [ ] Manual testing is completed
8. [ ] No critical or high-priority bugs remain
