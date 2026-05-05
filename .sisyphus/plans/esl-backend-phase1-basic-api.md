# ESL Backend - Phase 1: Basic API

## TL;DR
> **Summary**: Build a minimal FastAPI backend serving English learning content from Excel data in SQLite. No authentication, simple user_id tracking only.
> **Deliverables**: FastAPI application with 10 core endpoints, SQLite database with imported Excel data, minimal user table
> **Effort**: Medium
> **Parallel**: YES - 3 waves
> **Critical Path**: Data Import → Core Endpoints → Exercise Validation

## Context
### Original Request
Build backend only (no frontend) for an ESL app for Mongolian learners. Python + FastAPI + SQLite. Phase 1 = bare minimum API to learn English - no auth, no features.

### Data Source
- File: `English_Learning_Data_Clean.xlsx` (579 records, 9 lessons, 17 columns)
- Sheet: `All_Lessons`
- Columns: id, lesson, sub_topic, grammar_topic, word_number, vocabulary_word, meaning, example_sentence, conversation_question, conversation_affirmative, conversation_interrogative, conversation_yes, conversation_no, grammar_explanation, exercise_type, exercise_answers, notes

### Interview Summary
- User table: Create with simple user_id (no password/auth)
- Database: SQLite
- API Base: localhost:8000
- No test files needed

## Work Objectives
### Core Objective
Deliver a working FastAPI backend that:
1. Imports Excel data into SQLite on startup
2. Serves lesson content (list, detail, subtopics, items)
3. Serves vocabulary words (detail, random)
4. Serves grammar explanations
5. Serves exercises with answer validation
6. Tracks basic user progress by simple user_id

### Deliverables
- FastAPI app in `app/main.py`
- Database models in `app/models/`
- API routers in `app/routers/`
- Data import script
- SQLite database file

### Definition of Done
- [x] All 10 endpoints return valid JSON responses
- [x] Excel data successfully imported to SQLite
- [x] Exercise answer validation works correctly
- [x] API starts with `uvicorn app.main:app --reload`
- [x] No authentication required

### Must Have
- FastAPI with SQLite (SQLAlchemy)
- Data import from Excel on startup
- User table with simple user_id
- Progress table (minimal, user_id + item tracking)
- All endpoints from reference doc

### Must NOT Have
- JWT/Auth middleware
- Favorites, bookmarks
- Gamification (streaks, points, achievements)
- Leaderboard
- Admin endpoints
- AI conversation webhook
- TTS integration
- SRS algorithm

## Verification Strategy
> ZERO HUMAN INTERVENTION - all verification is agent-executed.
- Test decision: tests-after (manual curl/httpie verification)
- QA policy: Every task has agent-executed scenarios
- Evidence: .sisyphus/evidence/task-{N}-{slug}.{ext}

## Execution Strategy
### Parallel Execution Waves

Wave 1: Foundation (setup, data import, models)
- Project structure setup
- Database models (SQLAlchemy)
- Excel data import script

Wave 2: Core Endpoints (lessons, words, grammar)
- Lesson endpoints (list, detail, subtopics, items)
- Word endpoints (detail, random)
- Grammar endpoints

Wave 3: Exercises & Progress
- Exercise endpoints (list, detail, check)
- Basic progress tracking

### Dependency Matrix
| Task | Blocks | Blocked By |
|------|--------|------------|
| T1. Project Structure | - | - |
| T2. Database Models | T1 | - |
| T3. Data Import | T2 | T2 |
| T4. Lesson Endpoints | T3 | T3 |
| T5. Word Endpoints | T3 | T3 |
| T6. Grammar Endpoints | T3 | T3 |
| T7. Exercise Endpoints | T3 | T3 |
| T8. Progress Endpoints | T3 | T3 |

### Agent Dispatch Summary
- Wave 1: 3 tasks (foundation)
- Wave 2: 3 tasks (content delivery)
- Wave 3: 2 tasks (exercises + progress)

## TODOs

- [x] T1. Create project structure and dependencies
- [x] T2. Create database models
- [x] T3. Create data import service
- [x] T4. Create lesson endpoints
- [x] T5. Create word endpoints
- [x] T6. Create grammar endpoints
- [x] T7. Create exercise endpoints
- [x] T8. Create basic progress endpoints

  **What to do**: Implement in `app/routers/progress.py`:
  - POST /users/{user_id}/progress - Record learning event (item_id, activity_type, correct, time_spent)
  - GET /users/{user_id}/progress - Get user progress summary
  - GET /users/{user_id}/weak-words - Get words user struggles with

  **Must NOT do**: No authentication, just use user_id from path

  **Recommended Agent Profile**:
  - Category: `unspecified-high` - API with CRUD operations
  - Skills: []
  - Omitted: []

  **Parallelization**: Can Parallel: YES | Wave 3 | Blocks: [] | Blocked By: [T3]

  **References**:
  - API Spec: FastAPI_Endpoints_Reference.md lines 784-968

  **Acceptance Criteria**:
  - [ ] POST /users/test_user/progress records word_viewed event
  - [ ] GET /users/test_user/progress returns progress stats
  - [ ] GET /users/test_user/weak-words returns incorrect words

  **QA Scenarios**:
  ```
  Scenario: Record progress
    Tool: Bash
    Steps: curl -s -X POST http://localhost:8000/users/test_user/progress -H "Content-Type: application/json" -d '{"item_id": 1, "activity_type": "word_viewed", "correct": true}'
    Expected: recorded: true
    Evidence: .sisyphus/evidence/t8-progress-post.{ext}

  Scenario: Get progress
    Tool: Bash
    Steps: curl -s http://localhost:8000/users/test_user/progress | python3 -c "import json,sys; d=json.load(sys.stdin); print(f\"user_id: {d['user_id']}\")"
    Expected: user_id: test_user
    Evidence: .sisyphus/evidence/t8-progress-get.{ext}
  ```

  **Commit**: YES | Message: `feat: add basic progress endpoints` | Files: [app/routers/progress.py, app/schemas/progress.py]

## Final Verification Wave (MANDATORY — after ALL implementation tasks)
> 4 review agents run in PARALLEL. ALL must APPROVE. Present consolidated results to user and get explicit "okay" before completing.
> **Do NOT auto-proceed after verification. Wait for user's explicit approval before marking work complete.**
> **Never mark F1-F4 as checked before getting user's okay.** Rejection or user feedback -> fix -> re-run -> present again -> wait for okay.
- [x] F1. Plan Compliance Audit — oracle ✅ APPROVE
- [x] F2. Code Quality Review — unspecified-high ✅ APPROVE
- [x] F3. Real Manual QA — unspecified-high ✅ APPROVE
- [x] F4. Scope Fidelity Check — deep ✅ APPROVE
## Commit Strategy
Commit after each task. Use conventional commits: `feat:`, `fix:`, `refactor:`.

## Success Criteria
- [ ] All 10 endpoints functional at http://localhost:8000
- [ ] 579 lesson items in database
- [ ] Exercise validation working
- [ ] Basic progress tracking functional
- [ ] No auth required for any endpoint