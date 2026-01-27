# Sequence diagram #

## Phase 1 — Macro view (big picture)

```mermaid
sequenceDiagram
  autonumber
  actor U as Presenter/User
  participant UI as Quiz Builder UI
  participant BE as Backend (APIs)
  participant DB as Database
  participant Live as Live Session Engine
  participant Res as Results/Export

  U->>UI: Start "New Quiz"
  UI->>BE: Create quiz draft
  BE->>DB: Save draft
  DB-->>BE: quizId
  BE-->>UI: quizId

  U->>UI: Build quiz (questions + settings)
  UI->>BE: Save changes (autosave)
  BE->>DB: Persist quiz content
  DB-->>BE: OK
  BE-->>UI: OK

  U->>UI: Preview & publish
  UI->>BE: Validate + publish
  BE->>DB: Update status READY
  DB-->>BE: OK
  BE-->>UI: Published

  U->>UI: Start live quiz
  UI->>Live: Create session + join code
  Live-->>UI: joinCode

  U->>UI: Run quiz live
  UI->>Live: Next question / timer / lock
  Live->>BE: Fetch question payload
  BE->>DB: Read question
  DB-->>BE: Question data
  BE-->>Live: Question data
  Live-->>UI: State updated

  U->>UI: End quiz + view results
  UI->>Res: Compute + show results
  Res->>DB: Read responses&#59; write summaries
  DB-->>Res: OK
  Res-->>UI: Results + exports
```

## Phase 2 - Phase 2 — First-level click-through (user journey steps)

```mermaid
sequenceDiagram
  autonumber
  actor U as Presenter/User
  participant UI as Quiz Builder UI
  participant Auth as Auth
  participant Quiz as Quiz API
  participant Media as Media/Assets API
  participant DB as DB
  participant Live as Live Session
  participant Results as Results/Export

  U->>UI: Open app
  UI->>Auth: Validate session
  Auth-->>UI: OK (user, org, roles)

  U->>UI: Click "Create" → "Quiz"
  UI->>Quiz: POST /quizzes (status=DRAFT)
  Quiz->>DB: Insert quiz shell
  DB-->>Quiz: quizId
  Quiz-->>UI: quizId

  U->>UI: Enter title + description
  UI->>Quiz: PATCH /quizzes/{quizId} metadata
  Quiz->>DB: Update quiz
  DB-->>Quiz: OK
  Quiz-->>UI: OK

  loop Add each question
    U->>UI: Click "Add question"
    UI->>Quiz: POST /quizzes/{quizId}/questions
    Quiz->>DB: Insert question
    DB-->>Quiz: questionId
    Quiz-->>UI: questionId

    U->>UI: Type question + options
    UI->>Quiz: PATCH /questions/{questionId}
    Quiz->>DB: Update question
    DB-->>Quiz: OK
    Quiz-->>UI: OK

    opt Attach image/video
      U->>UI: Click "Add media"
      UI->>Media: POST /assets (upload/select)
      Media->>DB: Store asset metadata + URL
      DB-->>Media: assetUrl
      Media-->>UI: assetUrl
      UI->>Quiz: PATCH /questions/{questionId} attach assetUrl
      Quiz->>DB: Persist attachment
      DB-->>Quiz: OK
      Quiz-->>UI: OK
    end
  end

  U->>UI: Open "Quiz settings"
  UI->>Quiz: PATCH /quizzes/{quizId}/settings (timer, scoring, randomize, leaderboard)
  Quiz->>DB: Update settings
  DB-->>Quiz: OK
  Quiz-->>UI: OK

  U->>UI: Click "Preview"
  UI->>Quiz: GET /quizzes/{quizId}?expand=questions,settings
  Quiz->>DB: Read quiz model
  DB-->>Quiz: quizModel
  Quiz-->>UI: quizModel
  UI-->>U: Render preview

  U->>UI: Click "Publish / Ready"
  UI->>Quiz: POST /quizzes/{quizId}/validate
  Quiz->>DB: Read quiz for validation
  DB-->>Quiz: quizData
  alt Valid
    Quiz-->>UI: Validation OK
    UI->>Quiz: PATCH /quizzes/{quizId} status=READY
    Quiz->>DB: Update status
    DB-->>Quiz: OK
    Quiz-->>UI: Published
  else Invalid
    Quiz-->>UI: Validation errors (missing correct answer, too few options, etc.)
    UI-->>U: Highlight fixes
  end

  U->>UI: Click "Start quiz" (host view / slide)
  UI->>Live: POST /sessions {quizId}
  Live->>DB: Create session + joinCode
  DB-->>Live: sessionId + joinCode
  Live-->>UI: sessionId + joinCode
  UI-->>U: Show joinCode

  loop Live control per question
    U->>UI: Start question / next
    UI->>Live: POST /sessions/{sessionId}/advance
    Live->>Quiz: GET question payload
    Quiz->>DB: Read question+settings
    DB-->>Quiz: questionPayload
    Quiz-->>Live: questionPayload
    Live-->>UI: Live state updated (timer, question index
  end

  U->>UI: End quiz
  UI->>Live: POST /sessions/{sessionId}/close
  Live->>Results: POST /results/compute {sessionId}
  Results->>DB: Aggregate responses → summary
  DB-->>Results: OK
  Results-->>UI: Results + leaderboard

  U->>UI: Export results
  UI->>Results: POST /results/export {sessionId, format}
  Results->>DB: Read summary/details
  DB-->>Results: data
  Results-->>UI: Export file/link
```

## Phase 3 — Most detailed (first-time-reader friendly, includes autosave, collaboration, error paths) ##

```mermaid
sequenceDiagram
  autonumber
  actor U as Presenter/User
  actor C as Co-host/Editor (optional)
  participant UI as Quiz Builder UI
  participant Auth as Auth Service
  participant Perm as Permissions/Org Service
  participant Quiz as Quiz Service
  participant Media as Media Service
  participant Realtime as Realtime Sync (WS)
  participant DB as Database
  participant Live as Live Session Service
  participant Results as Results/Analytics
  participant Export as Export Service

  U->>UI: Open deck or workspace then Quiz
  UI->>Auth: Verify session token
  Auth-->>UI: Session OK with userId and orgId
  UI->>Perm: Check role for create and edit quizzes
  Perm-->>UI: Allowed

  U->>UI: Click New Quiz
  UI->>Quiz: Create draft quiz with status DRAFT
  Quiz->>DB: Insert quiz record and default settings
  DB-->>Quiz: quizId
  Quiz-->>UI: quizId and initial model

  UI->>Realtime: Connect WS channel for quizId
  Realtime-->>UI: Connected

  opt Co-host joins
    C->>UI: Open same quiz
    UI->>Auth: Verify session
    Auth-->>UI: Session OK for cohost
    UI->>Perm: Check role for edit
    Perm-->>UI: Allowed
    UI->>Realtime: Connect WS channel for quizId
    Realtime-->>UI: Connected
  end

  U->>UI: Type title and description
  UI-->>UI: Debounce changes
  UI->>Quiz: Patch metadata for quizId
  Quiz->>DB: Update quiz metadata
  DB-->>Quiz: OK
  Quiz-->>UI: OK
  UI->>Realtime: Broadcast metadata patch
  opt Co-host sees update
    Realtime-->>C: Metadata patch event
  end

  U->>UI: Click Add question and choose MCQ
  UI->>Quiz: Create question under quizId
  Quiz->>DB: Insert question shell
  DB-->>Quiz: questionId
  Quiz-->>UI: questionId
  UI->>Realtime: Broadcast question added
  opt Co-host sees new question
    Realtime-->>C: Question added event
  end

  U->>UI: Type prompt and options
  UI-->>UI: Client checks for non empty prompt and at least 2 options
  UI-->>UI: Show inline warnings if needed
  UI-->>UI: Debounce
  UI->>Quiz: Patch question content for questionId
  Quiz->>DB: Update question
  DB-->>Quiz: OK
  Quiz-->>UI: OK
  UI->>Realtime: Broadcast question patch
  opt Co-host sees edits live
    Realtime-->>C: Question patch event
  end

  U->>UI: Select correct option
  UI->>Quiz: Patch correctAnswer for questionId
  Quiz->>DB: Persist correctAnswer
  DB-->>Quiz: OK
  Quiz-->>UI: OK
  UI->>Realtime: Broadcast correctAnswer set
  opt Co-host sees correct answer set
    Realtime-->>C: Correct answer event
  end

  U->>UI: Click Add image
  UI->>Media: Upload asset
  Media->>DB: Store asset metadata
  DB-->>Media: assetId and assetUrl
  Media-->>UI: assetId and assetUrl
  UI->>Quiz: Attach assetId to questionId
  Quiz->>DB: Persist attachment
  DB-->>Quiz: OK
  Quiz-->>UI: OK
  UI->>Realtime: Broadcast media attached
  opt Upload fails
    Media-->>UI: Upload error
    UI-->>U: Show retry and allowed formats
  end

  U->>UI: Drag and drop reorder questions
  UI->>Quiz: Patch ordering for quizId
  Quiz->>DB: Persist ordering
  DB-->>Quiz: OK
  Quiz-->>UI: OK
  UI->>Realtime: Broadcast ordering update
  opt Co-host sees reorder
    Realtime-->>C: Ordering update event
  end

  U->>UI: Open settings
  UI-->>UI: Optimistic UI update
  UI->>Quiz: Patch settings for quizId
  Quiz->>DB: Persist settings
  DB-->>Quiz: OK
  Quiz-->>UI: OK
  UI->>Realtime: Broadcast settings update

  U->>UI: Click Preview
  UI->>Quiz: Get compiled quiz model for quizId
  Quiz->>DB: Read quiz questions and settings
  DB-->>Quiz: quizModel
  Quiz-->>UI: quizModel
  UI-->>U: Render preview

  U->>UI: Click Publish or Mark Ready
  UI->>Quiz: Validate quizId
  Quiz->>DB: Read full quiz
  DB-->>Quiz: quizData
  Quiz-->>UI: Validation result

  alt Validation OK
    UI->>Quiz: Patch status READY
    Quiz->>DB: Update status
    DB-->>Quiz: OK
    Quiz-->>UI: Ready
    UI->>Realtime: Broadcast status READY
  else Validation errors
    Quiz-->>UI: Errors like missing correct answer, empty prompt, not enough options
    UI-->>U: Highlight problems and link to fixes
  end

  U->>UI: Click Start quiz
  UI->>Live: Create session for quizId
  Live->>DB: Insert session in LOBBY state
  DB-->>Live: sessionId and joinCode
  Live-->>UI: sessionId and joinCode
  UI-->>U: Display joinCode

  loop For each question live
    U->>UI: Start question or Next
    UI->>Live: Advance session
    Live->>Quiz: Get question payload
    Quiz->>DB: Read question and settings
    DB-->>Quiz: payload
    Quiz-->>Live: payload
    Live->>DB: Update session state
    DB-->>Live: OK
    Live-->>UI: Broadcast live state
    opt Reveal answer
      U->>UI: Click Reveal
      UI->>Live: Reveal answer
      Live->>DB: Mark revealed
      DB-->>Live: OK
      Live-->>UI: Answer shown
    end
    opt Host reconnect
      UI->>Live: Get session snapshot
      Live-->>UI: State restored
    end
  end

  U->>UI: End quiz
  UI->>Live: Close session
  Live->>DB: Mark session CLOSED
  DB-->>Live: OK
  Live->>Results: Compute results
  Results->>DB: Aggregate responses and save summary
  DB-->>Results: OK
  Results-->>UI: Results ready

  U->>UI: Export results
  UI->>Export: Create export for sessionId
  Export->>DB: Read results
  DB-->>Export: data
  Export-->>UI: File link
  UI-->>U: Download export
```

# Use case diagram #

## Phase 1 — Macro use cases (big picture) ##

```mermaid
---
config:
  layout: elk
---
flowchart LR
    actorU["Presenter or User"] --- UC1(("Create quiz")) & UC2(("Build quiz content")) & UC3(("Configure quiz settings")) & UC4(("Preview and validate")) & UC5(("Publish quiz")) & UC6(("Run live quiz")) & UC7(("View and export results"))
    SYS[["System: Slides and Quiz"]] --- UC1 & UC2 & UC3 & UC4 & UC5 & UC6 & UC7
```

## Phase 2 — First level click-through (core use cases + relationships) ##

```mermaid
---
config:
  layout: elk
---
flowchart LR
  U[Presenter or User]
  C[Co-host or Editor]
  A[Org Admin]
  SYS[[System: Quiz Builder in Slides]]

  subgraph B[Build quiz]
    UC1((Create quiz))
    UC2((Set title and details))
    UC3((Add question))
    UC4((Edit question))
    UC5((Add options))
    UC6((Mark correct answer))
    UC7((Attach media))
    UC8((Reorder questions))
    UC9((Save changes))
  end

  subgraph P[Prepare and publish]
    UC10((Preview quiz))
    UC11((Validate quiz))
    UC12((Publish or mark ready))
    UC13((Duplicate quiz))
    UC14((Import questions))
  end

  subgraph L[Live and results]
    UC15((Start live session))
    UC16((Control live quiz))
    UC17((View results))
    UC18((Export results))
  end

  subgraph M[Administration]
    UC19((Manage permissions))
  end
  U --- UC1
  U --- UC2
  U --- UC3
  U --- UC4
  U --- UC5
  U --- UC6
  U --- UC7
  U --- UC8
  U --- UC9
  U --- UC10
  U --- UC12
  U --- UC13
  U --- UC14
  U --- UC15
  U --- UC16
  U --- UC17
  U --- UC18

  C --- UC3
  C --- UC4
  C --- UC7
  C --- UC8
  C --- UC10
  C --- UC11
  C --- UC12
  C --- UC16
  C --- UC17

  A --- UC19
  SYS --- UC1
  SYS --- UC15
  SYS --- UC17
  SYS --- UC19
  UC1 -.-> UC2
  UC3 -.-> UC5
  UC4 -.-> UC5
  UC5 -.-> UC6
  UC12 -.-> UC11
  UC15 -.-> UC12
  UC17 -.-> UC18
```

## Phase 3 — Most detailed (first-time reader, includes “extend” scenarios and guardrails) ##

```mermaid
flowchart LR
  %% Actors
  U[Presenter or User]
  C[Co-host or Editor]
  A[Org Admin]

  %% System boundary
  subgraph SYS[System: Slides quiz feature]
    %% Core creation
    UC1((Create quiz draft))
    UC2((Set title and description))
    UC3((Choose quiz mode and template))
    UC4((Add question))
    UC5((Edit question prompt))
    UC6((Add answer options))
    UC7((Mark correct answer))
    UC8((Set points and timer per question))
    UC9((Attach media to question))
    UC10((Reorder questions))
    UC11((Autosave and version history))

    %% Quiz level settings
    UC12((Configure quiz settings))
    UC13((Shuffle question order))
    UC14((Shuffle answer order))
    UC15((Enable leaderboard))
    UC16((Set join and access rules))

    %% Preview and publish
    UC17((Preview quiz))
    UC18((Validate quiz))
    UC19((Publish or mark ready))

    %% Collaboration
    UC20((Invite co-host))
    UC21((Co-edit with live sync))
    UC22((Resolve edit conflicts))

    %% Live
    UC23((Start live session))
    UC24((Show join code))
    UC25((Advance to next question))
    UC26((Start timer))
    UC27((Lock answers))
    UC28((Reveal correct answer))
    UC29((End quiz session))

    %% Results
    UC30((Compute leaderboard and stats))
    UC31((View results dashboard))
    UC32((Export results))
    UC33((Archive session results))

    %% Admin and compliance
    UC34((Manage permissions and roles))
    UC35((Data retention and privacy controls))
  end

  %% Actor associations
  U --- UC1
  U --- UC2
  U --- UC3
  U --- UC4
  U --- UC5
  U --- UC6
  U --- UC7
  U --- UC8
  U --- UC9
  U --- UC10
  U --- UC12
  U --- UC17
  U --- UC19
  U --- UC20
  U --- UC23
  U --- UC24
  U --- UC25
  U --- UC26
  U --- UC27
  U --- UC28
  U --- UC29
  U --- UC31
  U --- UC32
  U --- UC33

  C --- UC21
  C --- UC4
  C --- UC5
  C --- UC6
  C --- UC7
  C --- UC9
  C --- UC10
  C --- UC17
  C --- UC18
  C --- UC25
  C --- UC28
  C --- UC31

  A --- UC34
  A --- UC35

  %% Include relationships
  UC1 -.-> UC11
  UC2 -.-> UC11
  UC4 -.-> UC11
  UC12 -.-> UC11

  UC4 -.-> UC5
  UC4 -.-> UC6
  UC6 -.-> UC7
  UC4 -.-> UC8
  UC4 -.-> UC9
  UC10 -.-> UC11

  UC12 -.-> UC13
  UC12 -.-> UC14
  UC12 -.-> UC15
  UC12 -.-> UC16

  UC17 -.-> UC18
  UC19 -.-> UC18

  UC20 -.-> UC21

  UC23 -.-> UC24
  UC23 -.-> UC19

  UC25 -.-> UC26
  UC25 -.-> UC27
  UC25 -.-> UC28

  UC29 -.-> UC30
  UC30 -.-> UC31
  UC31 -.-> UC32
  UC31 -.-> UC33

  %% Extend style scenarios (optional flows)
  UC22 -.-> UC21
  UC35 -.-> UC33

```