# CHANGELOG - Word Cloud Feature

## [Unreleased] - 2026-02-13

### Added - Word Cloud Question Type

#### Backend
- **Database Schema**:
  - Added `question_type` enum column to `questions` table (`mcq` | `word_cloud`)
  - Added `text_answer` varchar(100) column to `answers` table for word cloud responses
  - Made `options` and `correct_answer_index` nullable (required only for MCQ)
  - Made `selected_option_index` and `is_correct` nullable in answers table
  - Migration: `20260213_2347_add_word_cloud_question_type.py`

- **Pydantic Schemas** (`features/quiz/schemas.py`):
  - `QuestionTypeEnum` - Enum with MCQ and WORD_CLOUD values
  - `WordCloudAnswerSubmitRequest` - Schema for submitting word cloud answers (text field, max 100 chars)
  - `WordCloudResultsResponse` - Schema for aggregated word frequencies
  - Updated `QuestionCreate`, `QuestionUpdate`, `QuestionResponse` to include `question_type`
  - Added validators to ensure MCQ questions have options and correct answer

- **Business Logic**:
  - `question_service.py` - Extended to support creating/updating word cloud questions
  - `answer_service.py` - Added:
    - `submit_word_cloud_answer()` - Submit word cloud response (unlimited submissions)
    - `get_word_cloud_results()` - Aggregate word frequencies (case-insensitive, sorted)
    - `_update_word_cloud_aggregation()` - Cache word frequencies in Redis

- **API Endpoints** (`broker/api/quiz.py`):
  - `POST /quizzes/sessions/submit-word-cloud` - Submit word cloud answer
  - `GET /quizzes/questions/{question_id}/word-cloud-results` - Get aggregated results
  - Updated `POST /quizzes/{quiz_id}/questions` to accept `question_type`

#### Frontend
- **Quiz Builder** (`QuizBuilder.jsx`):
  - Added question type selector (Radio: MCQ | Word Cloud)
  - Conditional form rendering based on question type
  - MCQ shows 4 options + correct answer selector
  - Word Cloud shows description text only
  - Question list displays type badge (MCQ = cyan, Word Cloud = purple)
  - Proper data transformation between frontend/backend formats

- **Translations** (`locales/en/translation.json`):
  - `quiz.wordCloud` - "Word Cloud"
  - `quiz.wordCloudDescription` - Instructions for hosts
  - `quiz.wordCloudQuestionDescription` - Description in question list

### Changed
- **Question Model**: `options` and `correct_answer_index` now nullable (NULL for word cloud questions)
- **Answer Model**: `selected_option_index` and `is_correct` now nullable (NULL for word cloud answers)
- **Answer Submission**: MCQ submission now validates question type before accepting

### Technical Details
- **Word Frequency Aggregation**: Case-insensitive, sorted by frequency descending
- **Submission Limit**: Unlimited submissions per participant for word cloud (MCQ remains one-per-participant)
- **Character Limit**: 100 characters per word cloud submission (enforced at schema level)
- **Profanity Filter**: Word cloud submissions route through existing broker layer profanity checks
- **Tier Access**: Word cloud available to all tiers (no restrictions)
- **Backward Compatibility**: Existing MCQ questions unaffected (default `question_type` = 'mcq')

### Not Yet Implemented (Future Work)
- Audience word cloud submission view
- Word cloud visualization component (react-wordcloud or react-d3-cloud)
- Real-time broadcasting of word cloud updates via WebSocket
- Enhanced results view with word cloud display
- Stopword filtering (optional)
- Word cloud export functionality

### Migration Status
- ✅ Database migration applied successfully (revision: 035ab11d95fd)
- ✅ Schema changes backward compatible
- ✅ Rollback supported via `alembic downgrade -1`

### Testing Status
- ✅ Python syntax validation passed
- ✅ Frontend build successful (no errors)
- ⏳ Unit tests pending
- ⏳ Integration tests pending
- ⏳ E2E tests pending

---

**Related Files**:
- Backend: `persistence/models/quiz.py`, `features/quiz/schemas.py`, `features/quiz/answer_service.py`, `broker/api/quiz.py`
- Frontend: `features/quiz/QuizBuilder.jsx`, `locales/en/translation.json`
- Migration: `persistence/migrations/versions/20260213_2347_add_word_cloud_question_type.py`
- Documentation: Session state `files/IMPLEMENTATION_SUMMARY.md`
