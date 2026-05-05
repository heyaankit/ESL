# ESL Backend - Phase 2: Full Features

## TL;DR
> **Summary**: Extend Phase 1 with authentication, favorites, gamification (streaks/points/achievements), leaderboard, TTS integration, AI webhook, SRS, and admin endpoints.
> **Deliverables**: Complete FastAPI backend with all production features
> **Effort**: Large
> **Parallel**: YES - 4 waves
> **Critical Path**: Auth → User Features → SRS → Admin

## Context
### Original Request
Build full backend for ESL app for Mongolian learners. Python + FastAPI + SQLite. Phase 2 adds all features to Phase 1.

### Phase 1 Completion
Assumes Phase 1 is complete with:
- FastAPI app running on localhost:8000
- SQLite database with 579 lesson items
- Basic endpoints (lessons, words, grammar, exercises, progress)
- User table with simple user_id

### Interview Summary
- **Features Added**: User Auth (JWT), Favorites/Bookmarks, Daily Streaks & Gamification, Global Leaderboard, AI Webhook, TTS integration, SRS algorithm, Admin endpoints
- **Excluded**: Multi-language UI (EN/MN only), Offline Sync, Content Export
- **AI Conversation**: Webhook endpoint for external AI connection
- **Audio**: TTS service integration (not stored files)
- **Social**: Global leaderboard only

## Work Objectives
### Core Objective
Deliver complete FastAPI backend with:
1. JWT Authentication (register, login, protected routes)
2. Favorites/Bookmarks system
3. Gamification (streaks, points, achievements)
4. Global leaderboard
5. AI conversation webhook
6. TTS integration for pronunciation
7. Spaced Repetition System (SRS)
8. Admin endpoints for content management

### Deliverables
- Authentication system with JWT
- User profile with stats
- Favorites endpoints
- Gamification service (streaks, points, achievements)
- Leaderboard endpoint
- AI webhook endpoint
- TTS endpoint
- SRS scheduler
- Admin endpoints (CRUD on content)

### Definition of Done
- [ ] User can register and login with JWT
- [ ] Protected endpoints require valid token
- [ ] Users can favorite words/lessons
- [ ] Streak tracking works correctly
- [ ] Points awarded for activities
- [ ] Achievements unlock based on milestones
- [ ] Leaderboard shows top users
- [ ] AI webhook returns proper response
- [ ] TTS endpoint returns audio/text
- [ ] SRS schedules next review dates
- [ ] Admin can manage content

### Must Have
- JWT auth (access + refresh tokens)
- Password hashing (bcrypt)
- Protected routes
- Favorites CRUD
- Streak calculation
- Point system
- Achievement definitions
- Leaderboard ranking
- AI webhook POST endpoint
- TTS GET endpoint
- SRS review scheduling
- Admin role + endpoints

### Must NOT Have
- Frontend
- Test files
- Offline sync
- Content export
- Multi-language UI beyond EN/MN

## Verification Strategy
> ZERO HUMAN INTERVENTION - all verification is agent-executed.
- Test decision: tests-after (manual verification)
- QA policy: Every task has agent-executed scenarios
- Evidence: .sisyphus/evidence/task-{N}-{slug}.{ext}

## Execution Strategy
### Parallel Execution Waves

Wave 1: Authentication (add to existing auth structure)
- JWT setup (secret, algorithm, expiry)
- Password hashing
- Register endpoint
- Login endpoint
- Token refresh
- Dependencies for protected routes

Wave 2: User Features (Favorites, Profile)
- Favorites endpoints (add/remove/list)
- User profile endpoint
- Update profile settings
- Protected route setup for user data

Wave 3: Gamification (Streaks, Points, Achievements, Leaderboard)
- Streak calculation service
- Points award system
- Achievement definitions and tracking
- Leaderboard endpoint
- Activity logging

Wave 4: Advanced Features (AI, TTS, SRS, Admin)
- AI conversation webhook
- TTS integration
- SRS algorithm and scheduling
- Admin endpoints
- User management (admin)

### Dependency Matrix
| Task | Blocks | Blocked By |
|------|--------|------------|
| T1. Auth Setup | - | Phase1 Complete |
| T2. Register/Login | T1 | T1 |
| T3. Protected Routes | T2 | T2 |
| T4. Favorites | T3 | T3 |
| T5. User Profile | T3 | T3 |
| T6. Streaks | T3 | T3 |
| T7. Points | T6 | T6 |
| T8. Achievements | T7 | T7 |
| T9. Leaderboard | T8 | T8 |
| T10. AI Webhook | T3 | T3 |
| T11. TTS | T3 | T3 |
| T12. SRS | T3 | T3 |
| T13. Admin Endpoints | T3 | T3 |

### Agent Dispatch Summary
- Wave 1: 3 tasks (auth foundation)
- Wave 2: 2 tasks (favorites, profile)
- Wave 3: 4 tasks (gamification)
- Wave 4: 4 tasks (advanced features)

## TODOs

- [ ] T1. Setup JWT authentication infrastructure

  **What to do**: Create `app/auth/` with:
  - JWT config (SECRET_KEY, ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES)
  - Password hashing (bcrypt)
  - Token creation/verification functions
  - Add to requirements: python-jose, passlib[bcrypt]

  **Must NOT do**: Don't create login/register yet, just the infrastructure

  **Recommended Agent Profile**:
  - Category: `unspecified-high` - Security infrastructure setup
  - Skills: []
  - Omitted: []

  **Parallelization**: Can Parallel: NO | Wave 1 | Blocks: [T2] | Blocked By: [Phase1]

  **References**:
  - External: https://fastapi.tiangolo.com/tutorial/security/
  - Pattern: JWT with python-jose, bcrypt for passwords

  **Acceptance Criteria**:
  - [ ] SECRET_KEY generated or configured
  - [ ] ALGORITHM set to HS256
  - [ ] Token creation works
  - [ ] Token verification works
  - [ ] Password hashing works

  **QA Scenarios**:
  ```
  Scenario: Token creation
    Tool: Bash
    Steps: python3 -c "from app.auth.jwt import create_access_token; token = create_access_token({'sub': 'test'}); print(len(token) > 0)"
    Expected: True
    Evidence: .sisyphus/evidence/t1-token.{ext}

  Scenario: Password hashing
    Tool: Bash
    Steps: python3 -c "from app.auth.utils import hash_password, verify_password; pw = 'test123'; h = hash_password(pw); print(verify_password(pw, h))"
    Expected: True
    Evidence: .sisyphus/evidence/t1-password.{ext}
  ```

  **Commit**: YES | Message: `feat: add JWT authentication infrastructure` | Files: [app/auth/__init__.py, app/auth/jwt.py, app/auth/utils.py]

- [ ] T2. Create register and login endpoints

  **What to do**: Create `app/routers/auth.py`:
  - POST /auth/register - username, email, password → user + token
  - POST /auth/login - email, password → access_token
  - POST /auth/refresh - refresh_token → new access_token
  - User model update: add email, hashed_password, created_at

  **Must NOT do**: No OAuth, no social login

  **Recommended Agent Profile**:
  - Category: `unspecified-high` - User authentication endpoints
  - Skills: []
  - Omitted: []

  **Parallelization**: Can Parallel: NO | Wave 1 | Blocks: [T3] | Blocked By: [T1]

  **References**:
  - API Pattern: FastAPI form data or JSON body

  **Acceptance Criteria**:
  - [ ] POST /auth/register creates user and returns token
  - [ ] POST /auth/login validates password and returns token
  - [ ] Duplicate email returns 400 error
  - [ ] Invalid password returns 401 error

  **QA Scenarios**:
  ```
  Scenario: Register new user
    Tool: Bash
    Steps: curl -s -X POST http://localhost:8000/auth/register -H "Content-Type: application/json" -d '{"username": "test", "email": "test@test.com", "password": "test123"}'
    Expected: access_token returned
    Evidence: .sisyphus/evidence/t2-register.{ext}

  Scenario: Login
    Tool: Bash
    Steps: curl -s -X POST http://localhost:8000/auth/login -H "Content-Type: application/json" -d '{"email": "test@test.com", "password": "test123"}'
    Expected: access_token returned
    Evidence: .sisyphus/evidence/t2-login.{ext}
  ```

  **Commit**: YES | Message: `feat: add register and login endpoints` | Files: [app/routers/auth.py, app/models/user.py (updated)]

- [ ] T3. Create protected route dependencies

  **What to do**: Create `app/dependencies.py`:
  - get_current_user dependency - extract token from Authorization header
  - Optional current_user for public routes
  - Admin role check dependency

  **Must NOT do**: Don't apply to all routes

  **Recommended Agent Profile**:
  - Category: `unspecified-high` - FastAPI dependency injection
  - Skills: []
  - Omitted: []

  **Parallelization**: Can Parallel: NO | Wave 1 | Blocks: [T4,T5,T6,T10,T11,T12,T13] | Blocked By: [T2]

  **References**:
  - Pattern: FastAPI Depends()

  **Acceptance Criteria**:
  - [ ] Valid token returns user
  - [ ] Missing token returns 401
  - [ ] Invalid token returns 401
  - [ ] Admin dependency works

  **QA Scenarios**:
  ```
  Scenario: Valid token
    Tool: Bash
    Steps: TOKEN=$(curl -s -X POST http://localhost:8000/auth/login -H "Content-Type: application/json" -d '{"email": "test@test.com", "password": "test123"}' | python3 -c "import json,sys; print(json.load(sys.stdin)['access_token'])"); curl -s -H "Authorization: Bearer $TOKEN" http://localhost:8000/users/me
    Expected: User data returned
    Evidence: .sisyphus/evidence/t3-valid-token.{ext}
  ```

  **Commit**: YES | Message: `feat: add protected route dependencies` | Files: [app/dependencies.py]

- [ ] T4. Create favorites endpoints

  **What to do**: Create/update `app/routers/favorites.py`:
  - POST /favorites - add item to favorites (item_id, item_type)
  - DELETE /favorites/{item_id} - remove from favorites
  - GET /favorites - list all user favorites
  - Update UserProgress to track favorites

  **Must NOT do**: Don't allow favoriting other users' data

  **Recommended Agent Profile**:
  - Category: `unspecified-high` - CRUD operations with auth
  - Skills: []
  - Omitted: []

  **Parallelization**: Can Parallel: YES | Wave 2 | Blocks: [] | Blocked By: [T3]

  **References**:
  - API: RESTful design with resource-based URLs

  **Acceptance Criteria**:
  - [ ] POST /favorites adds favorite (authenticated)
  - [ ] DELETE /favorites/{id} removes favorite
  - [ ] GET /favorites returns user's favorites
  - [ ] Cannot favorite same item twice

  **QA Scenarios**:
  ```
  Scenario: Add favorite
    Tool: Bash
    Steps: TOKEN="valid_token"; curl -s -X POST http://localhost:8000/favorites -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" -d '{"item_id": 1, "item_type": "word"}'
    Expected: favorite created
    Evidence: .sisyphus/evidence/t4-favorite-add.{ext}

  Scenario: List favorites
    Tool: Bash
    Steps: TOKEN="valid_token"; curl -s http://localhost:8000/favorites -H "Authorization: Bearer $TOKEN"
    Expected: favorites list
    Evidence: .sisyphus/evidence/t4-favorites-list.{ext}
  ```

  **Commit**: YES | Message: `feat: add favorites endpoints` | Files: [app/routers/favorites.py, app/models/favorite.py]

- [ ] T5. Create user profile endpoints

  **What to do**: Create `app/routers/users.py`:
  - GET /users/me - current user profile with stats
  - PUT /users/me - update profile (display_name, preferred_lesson)
  - GET /users/me/stats - detailed learning statistics
  - GET /users/{user_id}/profile - public profile (for leaderboard)

  **Must NOT do**: Don't expose passwords

  **Recommended Agent Profile**:
  - Category: `unspecified-high` - User data endpoints
  - Skills: []
  - Omitted: []

  **Parallelization**: Can Parallel: YES | Wave 2 | Blocks: [] | Blocked By: [T3]

  **Acceptance Criteria**:
  - [ ] GET /users/me returns user data
  - [ ] PUT /users/me updates profile
  - [ ] GET /users/me/stats returns learning stats
  - [ ] GET /users/{id}/profile returns public profile

  **QA Scenarios**:
  ```
  Scenario: Get own profile
    Tool: Bash
    Steps: TOKEN="valid_token"; curl -s http://localhost:8000/users/me -H "Authorization: Bearer $TOKEN"
    Expected: user data without password
    Evidence: .sisyphus/evidence/t5-profile.{ext}
  ```

  **Commit**: YES | Message: `feat: add user profile endpoints` | Files: [app/routers/users.py]

- [ ] T6. Create streak service

  **What to do**: Create `app/services/streak.py`:
  - Calculate current streak (consecutive days with activity)
  - Update streak on user activity
  - Track last activity date
  - Streak model: user_id, current_streak, longest_streak, last_activity_date
  - Reset streak if more than 1 day gap

  **Must NOT do**: Don't count multiple activities same day as multiple days

  **Recommended Agent Profile**:
  - Category: `unspecified-high` - Business logic for gamification
  - Skills: []
  - Omitted: []

  **Parallelization**: Can Parallel: YES | Wave 3 | Blocks: [T7] | Blocked By: [T3]

  **References**:
  - Algorithm: Check if last_activity == yesterday → increment, else reset to 1

  **Acceptance Criteria**:
  - [ ] Consecutive days increments streak
  - [ ] Gap of 1+ days resets streak
  - [ ] Streak updates on any learning activity
  - [ ] Longest streak tracked

  **QA Scenarios**:
  ```
  Scenario: Streak calculation
    Tool: Bash
    Steps: python3 -c "from app.services.streak import update_streak; update_streak('test_user')"
    Expected: Streak incremented or reset
    Evidence: .sisyphus/evidence/t6-streak.{ext}
  ```

  **Commit**: YES | Message: `feat: add streak tracking service` | Files: [app/services/streak.py, app/models/streak.py]

- [ ] T7. Create points system

  **What to do**: Create `app/services/points.py`:
  - Point values: word_viewed=1, exercise_correct=5, streak_day=10, achievement=20
  - Track total points per user
  - Add/remove points with reason logging
  - Points history table

  **Must NOT do**: No negative points

  **Recommended Agent Profile**:
  - Category: `unspecified-high` - Gamification logic
  - Skills: []
  - Omitted: []

  **Parallelization**: Can Parallel: YES | Wave 3 | Blocks: [T8] | Blocked By: [T6]

  **Acceptance Criteria**:
  - [ ] Points awarded for correct exercise
  - [ ] Points awarded for daily streak
  - [ ] Points history tracked
  - [ ] Total points accessible

  **QA Scenarios**:
  ```
  Scenario: Award points
    Tool: Bash
    Steps: python3 -c "from app.services.points import award_points; award_points('test_user', 'exercise_correct')"
    Expected: 5 points added
    Evidence: .sisyphus/evidence/t7-points.{ext}
  ```

  **Commit**: YES | Message: `feat: add points system` | Files: [app/services/points.py, app/models/points.py]

- [ ] T8. Create achievements system

  **What to do**: Create `app/services/achievements.py`:
  - Achievement definitions:
    - "First Word" - view first word
    - "10 Words" - view 10 words
    - "100 Words" - view 100 words
    - "First Exercise" - complete first exercise
    - "Perfect Score" - 100% on exercise
    - "7 Day Streak" - streak of 7 days
    - "30 Day Streak" - streak of 30 days
    - "100 Points" - earn 100 points
    - "500 Points" - earn 500 points
    - "1000 Points" - earn 1000 points
  - Check and unlock on activity
  - Track unlocked achievements per user

  **Must NOT do**: Don't manually award achievements

  **Recommended Agent Profile**:
  - Category: `unspecified-high` - Gamification milestone tracking
  - Skills: []
  - Omitted: []

  **Parallelization**: Can Parallel: YES | Wave 3 | Blocks: [T9] | Blocked By: [T7]

  **Acceptance Criteria**:
  - [ ] Achievements defined in code
  - [ ] Unlock on meeting criteria
  - [ ] GET /users/me/achievements returns unlocked
  - [ ] New achievement triggers notification

  **QA Scenarios**:
  ```
  Scenario: Check achievement
    Tool: Bash
    Steps: python3 -c "from app.services.achievements import check_achievements; check_achievements('test_user')"
    Expected: Achievements checked and possibly unlocked
    Evidence: .sisyphus/evidence/t8-achievements.{ext}
  ```

  **Commit**: YES | Message: `feat: add achievements system` | Files: [app/services/achievements.py, app/models/achievement.py]

- [ ] T9. Create leaderboard endpoint

  **What to do**: Create `app/routers/leaderboard.py`:
  - GET /leaderboard - top users by points (limit, offset)
  - GET /leaderboard/me - current user's rank
  - GET /leaderboard/weekly - top users this week
  - Rankings by: total_points, streak, exercises_completed

  **Must NOT do**: No friend-only leaderboard

  **Recommended Agent Profile**:
  - Category: `unspecified-high` - Ranking/aggregation queries
  - Skills: []
  - Omitted: []

  **Parallelization**: Can Parallel: YES | Wave 3 | Blocks: [] | Blocked By: [T8]

  **Acceptance Criteria**:
  - [ ] GET /leaderboard returns top 20 by default
  - [ ] User rank shown for current user
  - [ ] Pagination works
  - [ ] Different ranking types work

  **QA Scenarios**:
  ```
  Scenario: Get leaderboard
    Tool: Bash
    Steps: curl -s http://localhost:8000/leaderboard | python3 -c "import json,sys; d=json.load(sys.stdin); print(f\"Users: {len(d['users'])}\")"
    Expected: Users list with rank
    Evidence: .sisyphus/evidence/t9-leaderboard.{ext}
  ```

  **Commit**: YES | Message: `feat: add leaderboard endpoint` | Files: [app/routers/leaderboard.py]

- [ ] T10. Create AI conversation webhook

  **What to do**: Create `app/routers/ai_chat.py`:
  - POST /ai/chat - receive user message, lesson_context, return response
  - Webhook format: accepts JSON, returns JSON (ready for OpenAI/Anthropic integration)
  - Endpoint for frontend to call, returns structure for AI provider
  - Optional: mock response for testing

  **Must NOT do**: Don't call actual AI, just prepare webhook

  **Recommended Agent Profile**:
  - Category: `unspecified-high` - External API integration preparation
  - Skills: []
  - Omitted: []

  **Parallelization**: Can Parallel: YES | Wave 4 | Blocks: [] | Blocked By: [T3]

  **References**:
  - Request body: { message, lesson_id, sub_topic, conversation_type }
  - Response: { reply, suggested_responses, grammar_hint }

  **Acceptance Criteria**:
  - [ ] POST /ai/chat accepts message with context
  - [ ] Returns structured response for AI provider
  - [ ] Works with mock response for testing

  **QA Scenarios**:
  ```
  Scenario: Chat webhook
    Tool: Bash
    Steps: TOKEN="valid_token"; curl -s -X POST http://localhost:8000/ai/chat -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" -d '{"message": "Hello", "lesson_id": "1.1"}'
    Expected: Response structure returned
    Evidence: .sisyphus/evidence/t10-ai-chat.{ext}
  ```

  **Commit**: YES | Message: `feat: add AI conversation webhook` | Files: [app/routers/ai_chat.py]

- [ ] T11. Create TTS endpoint

  **What to do**: Create `app/routers/tts.py`:
  - GET /tts?text={text}&lang=en - returns audio or text-to-speech
  - Use gTTS (Google TTS) or similar library
  - Return audio file or base64 encoded audio
  - Support: English (en), Mongolian (mn)

  **Must NOT do**: Don't store audio files, generate on demand

  **Recommended Agent Profile**:
  - Category: `unspecified-high` - External service integration
  - Skills: []
  - Omitted: []

  **Parallelization**: Can Parallel: YES | Wave 4 | Blocks: [] | Blocked By: [T3]

  **References**:
  - Library: gTTS or edge-tts

  **Acceptance Criteria**:
  - [ ] GET /tts?text=hello returns audio
  - [ ] Language parameter works
  - [ ] Returns proper content-type (audio/mpeg)

  **QA Scenarios**:
  ```
  Scenario: TTS request
    Tool: Bash
    Steps: curl -s "http://localhost:8000/tts?text=hello&lang=en" -o /tmp/test.mp3 && file /tmp/test.mp3
    Expected: Audio file created
    Evidence: .sisyphus/evidence/t11-tts.{ext}
  ```

  **Commit**: YES | Message: `feat: add TTS endpoint` | Files: [app/routers/tts.py]

- [ ] T12. Create SRS (Spaced Repetition System)

  **What to do**: Create `app/services/srs.py`:
  - SM-2 algorithm variant: intervals = [1, 3, 7, 14, 30, 60] days
  - Track: item_id, user_id, ease_factor, interval, next_review, review_count
  - On correct answer: increase interval, update ease
  - On incorrect: reset to interval 1, decrease ease
  - GET /users/me/review - get items due for review
  - Update intervals on exercise completion

  **Must NOT do**: Don't use external SRS service

  **Recommended Agent Profile**:
  - Category: `unspecified-high` - Algorithm implementation
  - Skills: []
  - Omitted: []

  **Parallelization**: Can Parallel: YES | Wave 4 | Blocks: [] | Blocked By: [T3]

  **References**:
  - Algorithm: SM-2 formula (SuperMemo 2)

  **Acceptance Criteria**:
  - [ ] Correct answer increases interval
  - [ ] Wrong answer resets to day 1
  - [ ] GET /review returns due items
  - [ ] Next review date calculated

  **QA Scenarios**:
  ```
  Scenario: SRS calculation
    Tool: Bash
    Steps: python3 -c "from app.services.srs import calculate_next_review; result = calculate_next_review(True, 2.5, 3); print(result)"
    Expected: interval increased
    Evidence: .sisyphus/evidence/t12-srs.{ext}
  ```

  **Commit**: YES | Message: `feat: add SRS algorithm` | Files: [app/services/srs.py, app/models/srs.py]

- [ ] T13. Create admin endpoints

  **What to do**: Create `app/routers/admin.py`:
  - GET /admin/users - list all users (paginated)
  - PUT /admin/users/{user_id}/role - change user role
  - GET /admin/lessons - list lessons (for content management)
  - PUT /admin/lessons/{id} - update lesson item
  - POST /admin/lessons - add new lesson item
  - DELETE /admin/lessons/{id} - delete lesson item
  - GET /admin/stats - platform statistics

  **Must NOT do**: Don't create admin UI, just API

  **Recommended Agent Profile**:
  - Category: `unspecified-high` - CRUD with role checks
  - Skills: []
  - Omitted: []

  **Parallelization**: Can Parallel: YES | Wave 4 | Blocks: [] | Blocked By: [T3]

  **References**:
  - Role: user, admin

  **Acceptance Criteria**:
  - [ ] Admin-only endpoints require admin role
  - [ ] CRUD on lesson items works
  - [ ] User management works
  - [ ] Stats endpoint returns platform data

  **QA Scenarios**:
  ```
  Scenario: Admin stats
    Tool: Bash
    Steps: ADMIN_TOKEN="admin_token"; curl -s http://localhost:8000/admin/stats -H "Authorization: Bearer $ADMIN_TOKEN"
    Expected: Platform stats
    Evidence: .sisyphus/evidence/t13-admin.{ext}
  ```

  **Commit**: YES | Message: `feat: add admin endpoints` | Files: [app/routers/admin.py]

## Final Verification Wave (MANDATORY — after ALL implementation tasks)
> 4 review agents run in PARALLEL. ALL must APPROVE. Present consolidated results to user and get explicit "okay" before completing.
> **Do NOT auto-proceed after verification. Wait for user's explicit approval before marking work complete.**
> **Never mark F1-F4 as checked before getting user's okay.** Rejection or user feedback -> fix -> re-run -> present again -> wait for okay.
- [ ] F1. Plan Compliance Audit — oracle
- [ ] F2. Code Quality Review — unspecified-high
- [ ] F3. Real Manual QA — unspecified-high
- [ ] F4. Scope Fidelity Check — deep

## Commit Strategy
Commit after each task. Use conventional commits: `feat:`, `fix:`, `refactor:`.

## Success Criteria
- [ ] JWT authentication working
- [ ] Protected routes enforced
- [ ] Favorites CRUD working
- [ ] Streaks calculated correctly
- [ ] Points awarded for activities
- [ ] Achievements unlock on milestones
- [ ] Leaderboard shows top users
- [ ] AI webhook returns response structure
- [ ] TTS returns audio
- [ ] SRS schedules reviews
- [ ] Admin endpoints functional