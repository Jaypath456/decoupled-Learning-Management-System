# Classavo LMS — Feature Inventory

Complete inventory of the final LMS after all 21 milestones. Features live on `origin/cursor/*-7233` branches unless noted. **Status key:** ✅ Complete on branch · ⚠️ Partial / merge needed · 🔵 Baseline on `main`

---

## 1. User Authentication

- **Purpose:** Register, log in, and maintain session identity via JWT.
- **Users:** Student, Instructor
- **Backend:** `users` app — views, serializers, SimpleJWT token issuance
- **Frontend:** `Login`, `Register`, `AuthContext`, `ProtectedRoute`, `api/axios.js`
- **Models:** `User` (role, bio, validated username)
- **APIs:** `POST /api/auth/register/`, `POST /api/auth/login/`, `GET /api/auth/me/`
- **Dependencies:** Django, DRF, SimpleJWT, Axios
- **Status:** 🔵 Baseline on `main`; unchanged by milestones

---

## 2. Environment Configuration Hardening (M1)

- **Purpose:** Externalize secrets and runtime config; fail fast on missing `SECRET_KEY`.
- **Users:** DevOps, developers
- **Backend:** `lms_project/settings.py` — env helpers for `SECRET_KEY`, `DEBUG`, `ALLOWED_HOSTS`, `CORS_ALLOWED_ORIGINS`
- **Frontend:** `.env.example` (`REACT_APP_API_URL`)
- **Models:** None
- **APIs:** None (infrastructure)
- **Dependencies:** python-dotenv
- **Tests:** Startup validation (implicit)
- **Status:** ✅ `cursor/settings-env-hardening-7233`

---

## 3. Shared Permission Framework (M2)

- **Purpose:** Consistent role and enrollment checks across all apps.
- **Users:** All authenticated users (enforced server-side)
- **Backend:** `courses/permissions.py` — `IsInstructor`, `IsStudent`, `IsCourseInstructor`, `IsEnrolled`; reused by quizzes, messaging, schedule
- **Frontend:** `ProtectedRoute` (role-based routing)
- **Models:** `Enrollment` (lookup for `IsEnrolled`)
- **APIs:** Applied to all protected endpoints
- **Dependencies:** DRF permissions
- **Tests:** Exercised across chapter, quiz, chat test suites
- **Status:** ✅ `cursor/permissions-cleanup-7233`

---

## 4. Docker Dev Stack & Demo Seeding (M3)

- **Purpose:** One-command local stack; reproducible demo and load-test data.
- **Users:** Developers, QA
- **Backend:** `Dockerfile`, `docker-entrypoint.sh`, `courses/management/commands/seed_demo.py`
- **Frontend:** `Dockerfile`
- **Models:** All (seed creates users, courses, chapters, enrollments, quizzes)
- **APIs:** None (ops)
- **Dependencies:** Docker Compose, Postgres 16, Redis 7 (when merged with M12+)
- **Tests:** `SeedDemoCommandTests`
- **Status:** ✅ `cursor/docker-seed-data-7233`; extended on load-test branches with `--students N`

---

## 5. Course & Chapter Management

- **Purpose:** Instructors create/edit courses and rich-text chapters; students read enrolled content.
- **Users:** Instructor (CRUD), Student (read)
- **Backend:** `courses` app — views, serializers, permissions
- **Frontend:** `CourseList`, `CourseForm`, `CourseDetail`, `ChapterForm`, `ChapterReader`, `PlateEditor`
- **Models:** `Course`, `Chapter`, `Enrollment`
- **APIs:**
  - `GET/POST /api/courses/`, `GET /api/courses/mine/`, `POST /api/courses/create/`
  - `GET/PUT/DELETE /api/courses/<id>/`
  - `GET/POST /api/courses/<id>/chapters/`, `POST .../chapters/create/`
  - `GET/PUT/DELETE /api/chapters/<id>/`
  - `GET /api/courses/<id>/students/`
- **Dependencies:** Plate.js/Slate (JSON chapter content)
- **Tests:** `ChapterAccessTests`
- **Status:** 🔵 Baseline on `main`

---

## 6. Enrollment Management

- **Purpose:** Students enroll/unenroll; instructors view rosters; enrollment gates content access.
- **Users:** Student, Instructor
- **Backend:** `courses/views.py` — `manage_enrollment`, `enrollment_status`, `my_courses`
- **Frontend:** `Catalog`, `MyCourses`, `CourseView`, `StudentList`
- **Models:** `Enrollment` (unique student+course)
- **APIs:**
  - `POST/DELETE /api/courses/<id>/enroll/`
  - `GET /api/courses/<id>/enrollment-status/`
  - `GET /api/my-courses/`
- **Dependencies:** None
- **Tests:** `ChapterAccessTests`, enrollment flows in quiz/chat tests
- **Status:** 🔵 Baseline on `main`

---

## 7. Paginated Course Catalog (M4)

- **Purpose:** Scale public catalog; eliminate N+1 count queries.
- **Users:** Student
- **Backend:** `courses/pagination.py`, `_with_course_counts()` annotate, `StandardResultsPagination`
- **Frontend:** `Catalog` (Load More pagination)
- **Models:** `Course`, `Chapter`, `Enrollment`
- **APIs:** `GET /api/courses/` (paginated, page size 12)
- **Dependencies:** None
- **Tests:** Query-count assertions in catalog tests
- **Status:** ✅ `cursor/pagination-query-fixes-7233`

---

## 8. Catalog Redis Cache (M12)

- **Purpose:** Cache published catalog responses; invalidate on course writes.
- **Users:** Student (transparent)
- **Backend:** `lms_project/safe_cache.py`, cache logic in `courses/views.py`
- **Frontend:** None
- **Models:** `Course`
- **APIs:** `GET /api/courses/` (cached path)
- **Dependencies:** Redis, django-redis
- **Tests:** `CatalogCacheTests`
- **Status:** ✅ `cursor/redis-cache-idempotency-beat-7233`

---

## 9. Quiz Authoring (M5)

- **Purpose:** Instructors create quizzes and typed questions with Slate JSON prompts.
- **Users:** Instructor
- **Backend:** `quizzes` app — views, serializers, models
- **Frontend:** `QuizForm`, `QuizManage`, `QuestionForm` (M7)
- **Models:** `Quiz`, `Question` (single/multiple choice, short answer)
- **APIs:**
  - `GET/POST /api/courses/<id>/quizzes/`, `POST .../quizzes/create/`
  - `GET/PUT/DELETE /api/quizzes/<id>/`
  - `POST /api/quizzes/<id>/questions/create/`
  - `GET/PUT/DELETE /api/questions/<id>/`
- **Dependencies:** Plate.js (shared with chapters)
- **Tests:** `QuizOwnershipTests`, `QuizVisibilityTests`, `QuestionOwnershipTests`, `QuestionBodyValidationTests`
- **Status:** ✅ `cursor/quizzes-instructor-crud-7233`

---

## 10. Quiz Taking & Graded Submission (M6)

- **Purpose:** Students take published quizzes; server grades and stores one attempt per student.
- **Users:** Student
- **Backend:** `quizzes/views.py`, `quizzes/grading.py`
- **Frontend:** `QuizTake`, `QuizResult` (M7)
- **Models:** `Submission` (unique quiz+student, JSON answers, score)
- **APIs:**
  - `GET /api/quizzes/<id>/take/` (sanitized, no answers)
  - `POST /api/quizzes/<id>/submit/`
  - `GET /api/quizzes/<id>/my-result/`
- **Dependencies:** None (Postgres unique constraint = idempotency anchor)
- **Tests:** `QuizTakeTests`, `QuizSubmitTests`, `QuizMyResultTests`
- **Status:** ✅ `cursor/quiz-taking-idempotent-submit-7233`

---

## 11. Quiz Submit Redis Lock (M12)

- **Purpose:** Fast-path duplicate-submit protection under concurrent load.
- **Users:** Student (transparent)
- **Backend:** `safe_cache.safe_add` in `quizzes/views.py`
- **Frontend:** None
- **Models:** `Submission`
- **APIs:** `POST /api/quizzes/<id>/submit/`
- **Dependencies:** Redis
- **Tests:** `QuizSubmitRedisLockTests`
- **Status:** ✅ `cursor/redis-cache-idempotency-beat-7233`

---

## 12. Quiz Frontend UI (M7)

- **Purpose:** End-to-end instructor authoring and student take/result flows.
- **Users:** Instructor, Student
- **Backend:** Same as M5/M6
- **Frontend:** `QuizForm`, `QuizManage`, `QuestionForm`, `QuizTake`, `QuizResult`; routes in `App.js`
- **Models:** `Quiz`, `Question`, `Submission`
- **APIs:** All quiz endpoints
- **Dependencies:** React Router, Axios, PlateEditor
- **Tests:** Frontend build (`npm run build`); backend tests cover API
- **Status:** ✅ `cursor/quiz-frontend-7233`

---

## 13. Academic Terms & Section API (M8)

- **Purpose:** Model terms, course sections, recurring meetings, and student breaks.
- **Users:** Instructor (sections), Student (breaks)
- **Backend:** `schedule` app — models, serializers, views
- **Frontend:** None yet (M9/M11)
- **Models:** `Term`, `Section`, `Meeting`, `Break`; `Course.term` FK added
- **APIs:**
  - `GET /api/terms/`
  - `GET/POST /api/courses/<id>/sections/`, `POST .../sections/create/`
  - `GET/PUT/DELETE /api/sections/<id>/`
  - `GET/POST /api/breaks/`, `DELETE /api/breaks/<id>/`
- **Dependencies:** None
- **Tests:** `TermTests`, section CRUD tests
- **Status:** ✅ `cursor/schedule-models-section-api-7233`

---

## 14. Instructor Section Management UI (M9)

- **Purpose:** Instructors create and manage sections/meetings per course.
- **Users:** Instructor
- **Backend:** `schedule` app (M8)
- **Frontend:** `SectionList`, `SectionForm`
- **Models:** `Section`, `Meeting`, `Term`
- **APIs:** Section endpoints (M8)
- **Dependencies:** Axios, React Router
- **Tests:** Backend section tests
- **Status:** ✅ `cursor/instructor-scheduling-frontend-7233`

---

## 15. Schedule Generation Engine (M10)

- **Purpose:** Backtracking engine finds conflict-free section combinations respecting student breaks.
- **Users:** Student, Instructor
- **Backend:** `schedule/services.py` (pure Python), `schedule/views.py`
- **Frontend:** Consumed by M11 builder
- **Models:** `Term`, `Section`, `Meeting`, `Break`
- **APIs:** `POST /api/schedule/generate/`
- **Dependencies:** None
- **Tests:** `IntervalsOverlapTests`, `GenerateSchedulesUnitTests`
- **Status:** ✅ `cursor/schedule-generation-engine-7233`

---

## 16. Student Schedule Builder (M11)

- **Purpose:** Students generate, save, and confirm schedules; confirmation creates enrollments.
- **Users:** Student
- **Backend:** `SavedSchedule` model, confirm endpoint
- **Frontend:** `ScheduleBuilder`, `ScheduleView`, `WeeklyScheduleCalendar`
- **Models:** `SavedSchedule` (student+term, M2M sections)
- **APIs:**
  - `GET/POST /api/schedule/saved/`
  - `POST /api/schedule/saved/<id>/confirm/`
- **Dependencies:** react-big-calendar, date-fns
- **Tests:** Saved schedule and confirm tests
- **Status:** ✅ `cursor/student-schedule-builder-7233`

---

## 17. Celery & Beat Scaffold (M12)

- **Purpose:** Background job infrastructure; heartbeat verifies worker/beat wiring.
- **Users:** System (ops)
- **Backend:** `lms_project/celery.py`, `lms_project/tasks.py` (heartbeat)
- **Frontend:** None
- **Models:** None
- **APIs:** None
- **Dependencies:** Celery, Redis (broker/result)
- **Tests:** `CeleryScaffoldTests`
- **Status:** ✅ `cursor/redis-cache-idempotency-beat-7233`; purge task added in M15

---

## 18. WebSocket JWT Auth Foundation (M13)

- **Purpose:** Authenticate WebSocket connections with same JWT as REST; reject before handshake.
- **Users:** All (infrastructure for chat/live quiz)
- **Backend:** `lms_project/asgi.py`, `ws_auth.py`, `routing.py`, `EchoConsumer`
- **Frontend:** `api/ws.js` (`ReconnectingSocket`)
- **Models:** `User`
- **APIs:** `WS /ws/echo/` (acceptance test only)
- **Dependencies:** Django Channels, Daphne, channels-redis
- **Tests:** `WebSocketJWTAuthTests`
- **Status:** ✅ `cursor/channels-ws-auth-foundation-7233`

---

## 19. Course Chat — Backend (M14)

- **Purpose:** Real-time per-course messaging; persist-then-broadcast; enrollment-gated.
- **Users:** Enrolled Student, Course Instructor
- **Backend:** `messaging` app — `CourseChatConsumer`, views, serializers, `pagination.py`
- **Frontend:** None yet (M15)
- **Models:** `Message` (course+sender+body, indexed by course+created_at)
- **APIs:**
  - `GET /api/courses/<id>/messages/` (paginated history)
  - `WS /ws/chat/<course_id>/` — send/receive events
- **Dependencies:** Channels, Redis (channel layer, rate limit)
- **Tests:** `MessageHistoryAPITests`, `CourseChatConsumerTests`
- **Status:** ✅ `cursor/course-chat-backend-7233`

---

## 20. Course Chat — Frontend & Tenure Reset (M15)

- **Purpose:** Chat UI embedded in course pages; block writes after term ends; purge old messages.
- **Users:** Enrolled Student, Instructor
- **Backend:** Tenure check in consumer; `messaging/tasks.py` (`purge_ended_term_chats`, daily 3am Beat)
- **Frontend:** `CourseChat` on `CourseDetail` / `CourseView`
- **Models:** `Message`, `Course.term`, `Term`
- **APIs:** Same as M14 + Celery purge task
- **Dependencies:** `api/ws.js`, Redis, Celery Beat
- **Tests:** `test_write_is_refused_once_term_has_ended`, `PurgeEndedTermChatsTaskTests`
- **Status:** ✅ `cursor/chat-frontend-tenure-reset-7233`

---

## 21. Live Quiz Session Lifecycle (M16)

- **Purpose:** Mentimeter-style rooms with unique codes; lobby → active → ended lifecycle.
- **Users:** Instructor (host), Student (participant)
- **Backend:** `LiveSession` model, REST lifecycle views, `quizzes/live_state.py` (Redis mirror)
- **Frontend:** None yet (M18)
- **Models:** `LiveSession` (room_code, status, current_question_index, timestamps)
- **APIs:**
  - `POST /api/quizzes/<id>/sessions/`
  - `GET /api/sessions/<room_code>/`
  - `POST /api/sessions/<room_code>/start/`
  - `POST /api/sessions/<room_code>/end/`
- **Dependencies:** Redis (session state cache)
- **Tests:** `LiveSessionLifecycleTests`, `RoomCodeGenerationTests`
- **Status:** ✅ `cursor/live-session-room-lifecycle-7233`

---

## 22. Live Quiz Real-Time Consumer (M17)

- **Purpose:** Host reveals questions; students submit answers; live chart and leaderboard updates.
- **Users:** Instructor (host controls), Student (answer)
- **Backend:** `quizzes/consumers.py` (`LiveQuizConsumer`), `live_state.py` (Redis HASH charts, ZSET leaderboard)
- **Frontend:** None yet (M18)
- **Models:** `LiveSession`, `Submission` (shared with async quiz — one row per student+quiz)
- **APIs:** `WS /ws/live/<room_code>/` — `session.state`, `question.revealed`, `answer.submit`, `chart.update`, `leaderboard.update`, `session.ended`
- **Dependencies:** Channels, Redis
- **Tests:** `LiveQuizConsumerTests`
- **Status:** ✅ `cursor/live-quiz-consumer-7233`

---

## 23. Live Quiz Frontend (M18)

- **Purpose:** Host console and student join-by-code UI with live bar charts.
- **Users:** Instructor, Student
- **Backend:** M16/M17
- **Frontend:** `LiveQuizHost`, `LiveQuiz`, `LiveBarChart`
- **Models:** `LiveSession`, `Quiz`, `Question`
- **APIs:** Session REST + live WebSocket
- **Dependencies:** `api/ws.js`, Chart rendering in `LiveBarChart`
- **Tests:** Backend consumer tests; manual UI verification
- **Status:** ✅ `cursor/live-quiz-frontend-7233`

---

## 24. Leaderboards (M19)

- **Purpose:** Ephemeral live-session leaderboard (Redis ZSET) and persistent course-wide leaderboard (Postgres).
- **Users:** Student, Instructor
- **Backend:** `live_state.py` (ZINCRBY/ZREVRANGE), `courses/views.py` or `quizzes/views.py` leaderboard endpoint
- **Frontend:** `Leaderboard` component on course pages
- **Models:** `Submission` (persistent scores)
- **APIs:** `GET /api/courses/<id>/leaderboard/`; WS `leaderboard.update`
- **Dependencies:** Redis (live), Postgres (persistent)
- **Tests:** `LiveStateLeaderboardUnitTests`, `CourseLeaderboardAPITests`
- **Status:** ✅ `cursor/live-leaderboard-7233`

---

## 25. REST Load Testing Harness (M20)

- **Purpose:** Locust-based REST load tests with before/after Redis optimization toggle.
- **Users:** QA, developers
- **Backend:** `LOAD_TEST_DISABLE_REDIS_OPTIMIZATIONS` env flag; `seed_demo --students N`
- **Frontend:** None
- **Models:** All seeded entities
- **APIs:** Exercises catalog, enroll, quiz submit paths
- **Dependencies:** Locust 2.44.4 (Docker profile `loadtest`), `loadtests/locustfile.py`
- **Tests:** Produces CSV reports in `loadtests/reports/`; not unit tests
- **Status:** ✅ `cursor/load-testing-rest-7233`

---

## 26. WebSocket Load Testing & Graphs (M21)

- **Purpose:** Measure live-quiz reveal/chart latency at scale; generate comparison graphs.
- **Users:** QA, developers
- **Backend:** Live quiz stack (M16–M19)
- **Frontend:** None
- **Models:** `LiveSession`, seeded quiz data
- **APIs:** WS live quiz endpoints under concurrent load
- **Dependencies:** `loadtests/ws_load_test.py`, `generate_graphs.py`, `loadtests/REPORT.md`
- **Tests:** JSONL metrics + PNG graphs; documents Postgres bottleneck on concurrent answers
- **Status:** ✅ `cursor/load-testing-ws-graphs-7233`

---

## Milestone → Feature Map

| # | Branch suffix | Primary feature(s) |
|---|---------------|-------------------|
| M1 | settings-env-hardening | §2 Environment Configuration |
| M2 | permissions-cleanup | §3 Shared Permissions |
| M3 | docker-seed-data | §4 Docker & Seeding |
| M4 | pagination-query-fixes | §7 Paginated Catalog |
| M5 | quizzes-instructor-crud | §9 Quiz Authoring |
| M6 | quiz-taking-idempotent-submit | §10 Quiz Taking |
| M7 | quiz-frontend | §12 Quiz Frontend UI |
| M8 | schedule-models-section-api | §13 Terms & Sections |
| M9 | instructor-scheduling-frontend | §14 Section Management UI |
| M10 | schedule-generation-engine | §15 Schedule Generator |
| M11 | student-schedule-builder | §16 Schedule Builder |
| M12 | redis-cache-idempotency-beat | §8 Catalog Cache, §11 Submit Lock, §17 Celery |
| M13 | channels-ws-auth-foundation | §18 WebSocket Auth |
| M14 | course-chat-backend | §19 Course Chat Backend |
| M15 | chat-frontend-tenure-reset | §20 Chat UI & Tenure Purge |
| M16 | live-session-room-lifecycle | §21 Live Session Lifecycle |
| M17 | live-quiz-consumer | §22 Live Quiz Consumer |
| M18 | live-quiz-frontend | §23 Live Quiz Frontend |
| M19 | live-leaderboard | §24 Leaderboards |
| M20 | load-testing-rest | §25 REST Load Tests |
| M21 | load-testing-ws-graphs | §26 WS Load Tests |

**Baseline features (§1, §5, §6)** predate milestones and remain on `main`. Full product requires merging all branches in dependency order (see `docs/final_project_handoff.md`).
