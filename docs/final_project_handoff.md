# Classavo LMS — Final Project Handoff

**Document owner:** Staff Backend Engineer  
**Audience:** Incoming engineer taking over the Classavo LMS codebase  
**Repository:** `decoupled-learning-management-system`  
**Status:** All 21 milestones complete on feature branches (`origin/cursor/*-7233`); `main` retains the original baseline only.

---

## 1. Project Overview

Classavo LMS is a decoupled Learning Management System for instructors and students. Instructors create courses with rich-text chapters, manage enrollments, author quizzes, schedule sections, and run live interactive sessions. Students browse a catalog, enroll, read content, take quizzes, build term schedules, chat with classmates, and participate in live quiz rooms.

The platform evolved from a simple REST-only MVP into a multi-protocol system supporting real-time WebSockets, background jobs, Redis-backed caching, and containerized local development. Milestone work lives on parallel feature branches and must be merged in dependency order before production deployment.

---

## 2. Original LMS Architecture

The baseline on `main` is a classic decoupled client–server design:

- **Backend:** Django 4.2 + Django REST Framework, WSGI-only, two apps (`users`, `courses`)
- **Frontend:** React SPA with React Router, Axios, Plate.js/Slate for chapter authoring
- **Database:** PostgreSQL via Django ORM
- **Auth:** JWT (SimpleJWT), tokens stored in sessionStorage, attached via Axios interceptors
- **Scope:** User registration/login, role-based course CRUD, chapter management with JSON content, enrollment, student catalog

There was no Redis, Celery, Channels, Docker, quizzes, scheduling, chat, or live sessions. Settings used hardcoded secrets and permissive CORS.

---

## 3. New Architecture After All Milestones

The post-milestone system remains decoupled but adds real-time and async layers:

| Layer | Before | After |
|-------|--------|-------|
| HTTP | WSGI / DRF | DRF unchanged; Daphne ASGI serves HTTP + WebSockets |
| Real-time | None | Django Channels with Redis channel layer |
| Cache / broker | None | Single Redis: cache, Celery broker, Channels, ephemeral live state |
| Background jobs | None | Celery + Beat (heartbeat, chat purge) |
| Data | PostgreSQL only | PostgreSQL as source of truth; Redis for optimization and fan-out |
| Infra | Manual setup | Docker Compose: Postgres, Redis, backend, frontend, optional Locust |

**Design principles:** Postgres guarantees correctness; Redis accelerates and fans out but degrades gracefully when unavailable. One `Enrollment` record gates chapters, quizzes, chat, and live sessions. Chat follows persist-then-broadcast; live quizzes use server-driven state machines.

**Recommended merge order:** M1→M2→M3→M4→M5→M6→M7 (quiz track) in parallel with M8→M9→M10→M11 (schedule track); then M12→M13→M14→M15→M16→M17→M18→M19→M20→M21. Use `cursor/load-testing-ws-graphs-7233` as the reference for the live-quiz and performance stack.

---

## 4. Major Features Added

| Milestone | Branch | Feature |
|-----------|--------|---------|
| M1 | `settings-env-hardening-7233` | Env-driven settings; startup fails without SECRET_KEY |
| M2 | `permissions-cleanup-7233` | Shared DRF permissions; consistent enrollment gating |
| M3 | `docker-seed-data-7233` | Docker Compose; `seed_demo` management command |
| M4 | `pagination-query-fixes-7233` | Paginated catalog; N+1 fixes via annotated counts |
| M5 | `quizzes-instructor-crud-7233` | Quiz/Question models; instructor CRUD |
| M6 | `quiz-taking-idempotent-submit-7233` | Submission model; server grading; DB idempotency |
| M7 | `quiz-frontend-7233` | Instructor/student quiz UI |
| M8 | `schedule-models-section-api-7233` | Term, Section, Meeting, Break models; Course.term FK |
| M9 | `instructor-scheduling-frontend-7233` | Section management UI for instructors |
| M10 | `schedule-generation-engine-7233` | Backtracking schedule generator API |
| M11 | `student-schedule-builder-7233` | SavedSchedule; confirm-to-enroll; React Big Calendar |
| M12 | `redis-cache-idempotency-beat-7233` | Redis cache, quiz-submit lock, Celery/Beat scaffold |
| M13 | `channels-ws-auth-foundation-7233` | Channels, JWT WebSocket auth, EchoConsumer |
| M14 | `course-chat-backend-7233` | Messaging app; CourseChatConsumer |
| M15 | `chat-frontend-tenure-reset-7233` | CourseChat UI; tenure lock; Celery purge task |
| M16 | `live-session-room-lifecycle-7233` | LiveSession model; REST lifecycle; Redis mirror |
| M17 | `live-quiz-consumer-7233` | LiveQuizConsumer; reveal/submit/chart over WebSocket |
| M18 | `live-quiz-frontend-7233` | LiveQuiz host/join UI; LiveBarChart |
| M19 | `live-leaderboard-7233` | Redis ZSET live leaderboard; persistent course leaderboard |
| M20 | `load-testing-rest-7233` | Locust REST harness; optimization toggle |
| M21 | `load-testing-ws-graphs-7233` | WebSocket load test; graph generation; REPORT.md |

---

## 5. Final Technology Stack

**Backend:** Django 4.2+, DRF, SimpleJWT, django-cors-headers, psycopg2-binary, python-dotenv, redis, django-redis, celery, channels, channels-redis, daphne.

**Frontend:** React 19, React Router 7, Axios, Plate.js/Slate, react-big-calendar, date-fns, CRA/Jest tooling.

**Infrastructure:** Docker Compose with Postgres 16-alpine, Redis 7-alpine, optional Locust 2.44.4 (loadtest profile).

**Load testing:** Locust (REST), custom async WebSocket driver, graph generation scripts.

---

## 6. Database Architecture Changes

**users:** Custom `User` with `role` (instructor/student), validated username, optional bio. Unchanged in shape.

**courses:** `Course` gains nullable `term` FK (ties to schedule tenure for chat reset). `Chapter` stores Slate JSON in `content`. `Enrollment` unique on (student, course) — reused as idempotency anchor across features.

**quizzes:** `Quiz` (course FK), `Question` (typed JSON body with Slate prompts), `Submission` (unique quiz+student, scored answers), `LiveSession` (unique room_code, lobby/active/ended lifecycle).

**schedule:** `Term` (date range), `Section` (course+term offering), `Meeting` (recurring weekly blocks), `Break` (student blocked windows), `SavedSchedule` (student term plan, M2M sections, confirm creates enrollments).

**messaging:** `Message` (course FK + sender + body, indexed by course+created_at). No separate chat room — the course is the room.

---

## 7. Backend Modules Added

| App / Module | Responsibility |
|--------------|----------------|
| `users` | Register, login, me; JWT issuance |
| `courses` | Courses, chapters, enrollment, cached catalog, course leaderboard |
| `quizzes` | Quiz CRUD, take/submit, live sessions, LiveQuizConsumer, grading, live_state |
| `schedule` | Terms, sections, breaks, generation engine, saved schedules |
| `messaging` | Message history REST, CourseChatConsumer, purge task |
| `lms_project` | ASGI routing, ws_auth, safe_cache, Celery app, EchoConsumer, tasks |

Supporting modules: `quizzes/grading.py`, `quizzes/live_state.py`, `schedule/services.py`, `lms_project/safe_cache.py`.

---

## 8. Frontend Changes

**Auth:** Login, Register; AuthContext with sessionStorage JWT; ProtectedRoute by role.

**Instructor:** Dashboard, course/chapter CRUD, student list; QuizForm, QuizManage, QuestionForm; SectionList, SectionForm; LiveQuizHost; CourseChat on CourseDetail.

**Student:** Paginated Catalog with Load More, MyCourses, CourseView, ChapterReader; QuizTake, QuizResult; ScheduleBuilder, ScheduleView, WeeklyScheduleCalendar; LiveQuiz with room-code entry; CourseChat; course Leaderboard.

**Shared:** PlateEditor, Navbar, BackButton, CourseChat, LiveBarChart, Leaderboard, ReconnectingSocket (`api/ws.js`).

---

## 9. Infrastructure Changes

Docker Compose defines five services: **postgres** (healthcheck, persistent volume), **redis** (cache, Celery, Channels, live state), **backend** (depends on healthy postgres/redis, env-driven config, port 8000), **frontend** (port 3000, `REACT_APP_API_URL`), **locust** (profile `loadtest` only, port 8089).

Backend entrypoint runs migrations on start. Root and per-service `.env.example` files document required variables. `seed_demo --students N` creates load-test accounts and demo content idempotently.

---

## 10. Authentication and Authorization Flow

1. Register/login returns SimpleJWT access (24h) and refresh (7d) tokens in JSON.
2. REST requests: Axios interceptor attaches `Authorization: Bearer` from sessionStorage.
3. WebSocket: same access token sent as the first WebSocket subprotocol entry (not query string) to avoid log leakage and enable pre-handshake rejection.
4. `JWTAuthMiddleware` validates token, populates `scope['user']`; consumers reject anonymous (close 4001) and unauthorized (4003/4004) connections.
5. DRF permission classes (`IsInstructor`, `IsStudent`, `IsCourseInstructor`, `IsEnrolled`) gate endpoints consistently.

---

## 11. Redis Usage

Single `REDIS_URL`, logically separated:

- **Catalog cache:** django-redis, 60s TTL, invalidated on course writes; skippable via load-test toggle.
- **Quiz submit lock:** SETNX via safe_cache; DB unique_together is the real guarantee.
- **Celery broker/result:** same Redis URL; Beat runs heartbeat (60s) and chat purge (daily 3am).
- **Channels layer:** channels-redis for WebSocket group pub/sub.
- **Chat rate limit:** 10 messages per 10 seconds per (course, user); degrades open if Redis down.
- **Live session state:** pickled dict mirroring DB status; cleared on session end.
- **Live charts:** Redis HASH with HINCRBY per room+question.
- **Live leaderboard:** Redis ZSET; ephemeral per session.
- **Live answer idempotency:** SETNX keys per student/question.

All cache operations go through `safe_cache.py`, which logs failures and degrades without breaking correctness.

---

## 12. WebSocket Architecture

ASGI `ProtocolTypeRouter` splits HTTP (Django) and WebSocket (JWTAuthMiddlewareStack + URLRouter). Routes aggregated in `lms_project/routing.py`:

| Path | Consumer | Behavior |
|------|----------|----------|
| `ws/echo/` | EchoConsumer | Foundation test only; echoes username |
| `ws/chat/<course_id>/` | CourseChatConsumer | Send/receive chat; rate limit; tenure write-lock |
| `ws/live/<room_code>/` | LiveQuizConsumer | session.state, question.revealed, answer.submit → chart.update, leaderboard.update, session.ended; host-only advance/end |

Group names derive from course ID (chat) or room_code (live). Access requires instructor ownership or student enrollment.

---

## 13. Background Tasks

- **heartbeat** (every 60s): Celery/Beat scaffold for operational verification.
- **purge_ended_term_chats** (daily 3am): deletes Message rows for courses whose Term.end_date has passed.

Celery worker and beat are configured in settings but not included as default Compose services — add them for production or run manually.

---

## 14. Docker Architecture

Multi-service Compose with named volumes (`postgres_data`, `redis_data`). Backend and frontend bind-mount source for dev. Locust gated behind `--profile loadtest`. Environment variables control DB credentials, Redis URL, SECRET_KEY, DEBUG, CORS origins, and the load-test optimization toggle. Healthchecks on postgres and redis gate backend startup.

---

## 15. Testing Strategy

**Backend (~126 tests on load-test branch lineage):** Django TestCase and TransactionTestCase (WebSocket tests require TransactionTestCase). Coverage includes permission matrices, idempotency (double submit), `assertNumQueries` for N+1 regression, Channels WebsocketCommunicator, and mocked Redis failures.

**Frontend:** CRA/Jest minimal smoke tests; milestones rely on `npm run build` and manual/live verification.

**Integration:** Docker Compose stack with `seed_demo` for repeatable demo and load-test data.

---

## 16. Load Testing Strategy

**REST (M20):** Locust scenarios mirror frontend flows — login, catalog browse, course triple-fetch + enroll, quiz take + submit. `seed_demo --students N` creates accounts. Before/after comparison uses `LOAD_TEST_DISABLE_REDIS_OPTIMIZATIONS=True` to disable catalog cache and submit lock while keeping Redis running.

**WebSocket (M21):** Async driver connects N students, host reveals question, all answer simultaneously. Metrics: reveal latency and chart-update latency. `generate_graphs.py` produces PNGs from Locust CSVs and WS JSONL. See `loadtests/REPORT.md` on `cursor/load-testing-ws-graphs-7233`.

Run against `DEBUG=False` and a production-ish ASGI server for representative numbers.

---

## 17. Performance Improvements

- Catalog Redis cache with explicit invalidation (M12).
- Annotated counts eliminate N+1 on catalog (M4).
- Paginated catalog (page size 12) with stable ordering (M4).
- Quiz submit Redis lock for concurrent duplicate protection (M12).
- select_related on course serializers for instructor/term (M15).
- Ephemeral Redis for live charts and leaderboards to avoid Postgres on every fan-out (M17/M19).

**Load-test findings (sandbox, illustrative):** Catalog cache roughly halves p95 at 20–100 users. WS reveal stays fast (~25–88ms p95). WS chart update scales linearly with room size (563ms→1846ms for 30→100 students) — Postgres transaction serialization in answer recording is the bottleneck, not Channels fan-out.

---

## 18. Known Limitations

1. **No unified merge branch** — features exist on parallel `-7233` branches; full product requires ordered merge.
2. **Live and async quiz share one Submission row** per (quiz, student) — attempts collide by design.
3. **Schedule builder branch** may predate M4 pagination — frontend defensively handles both array and paginated responses.
4. **Redis required for full real-time** but not for REST correctness; degradation paths exist.
5. **Live answer throughput** bounded by Postgres row locks; batching or Redis score buffering needed at higher scale.
6. **Celery beat/worker** not in default Compose — purge task needs operational setup.
7. **M1 env hardening** may conflict with later branches that still hardcode some settings — reconcile on merge.
8. **Load-test numbers** are sandbox-only; re-run at target hardware before setting SLAs.
9. **Quiz submit lock** adds overhead for single-submit workloads (no duplicate benefit).
10. **Chart broadcast debouncing** intentionally not implemented — add only if load tests justify it.

---

## Handoff Checklist

- [ ] Merge milestone branches in recommended order; resolve settings conflicts first.
- [ ] Add Celery worker and beat services to Compose for production.
- [ ] Set `DEBUG=False`, restrict CORS, and rotate SECRET_KEY before deployment.
- [ ] Run full backend test suite and load-test ladder after merge.
- [ ] Verify WebSocket auth with production reverse proxy (subprotocol passthrough).
- [ ] Document operational runbooks for chat purge and live session cleanup.

**Reference branches:** `cursor/load-testing-ws-graphs-7233` (live quiz + performance), `cursor/chat-frontend-tenure-reset-7233` (messaging + tenure), `cursor/student-schedule-builder-7233` (scheduling UI).
