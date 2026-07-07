# Classavo LMS — API Documentation

Complete REST and WebSocket API reference for the **final composed LMS** after all 21 milestones. Base URL defaults to `http://localhost:8000`.

| Item | Value |
|------|-------|
| REST prefix | `/api/` |
| Auth prefix | `/api/auth/` |
| Admin | `/admin/` |
| Content-Type | `application/json` |
| Auth header | `Authorization: Bearer <access_token>` |
| WebSocket base | `ws://localhost:8000/` (derived from `REACT_APP_API_URL`) |
| WS auth | Access token sent as first WebSocket subprotocol |

**Default permissions:** All REST endpoints require authentication unless marked **Public**. Global DRF default is `IsAuthenticated`.

**Error responses:** Validation errors return field-keyed objects (`400`). Simple errors return `{"error": "..."}` with appropriate status codes (`401`, `403`, `404`, `409`).

**Paginated responses:** `{ "count", "next", "previous", "results" }`. Page size defaults vary per endpoint; override with `?page_size=` (capped at 100).

---

## Authentication

### Register

| | |
|---|---|
| **Method** | `POST` |
| **URL** | `/api/auth/register/` |
| **Purpose** | Create a new user account and return JWT tokens |
| **Auth** | Public |
| **Permissions** | `AllowAny` |
| **Request** | `{ "username", "email", "password", "role" ("instructor"\|"student"), "bio" (optional) }` |
| **Response** | `201` — `{ "user": { id, username, email, role, bio }, "access", "refresh" }` |
| **Models** | `User` |
| **Example** | `curl -X POST /api/auth/register/ -d '{"username":"alice","password":"secret","role":"student","email":"a@b.com"}'` |

---

### Login

| | |
|---|---|
| **Method** | `POST` |
| **URL** | `/api/auth/login/` |
| **Purpose** | Authenticate and receive JWT tokens |
| **Auth** | Public |
| **Permissions** | `AllowAny` |
| **Request** | `{ "username", "password" }` |
| **Response** | `200` — `{ "user", "access", "refresh" }` · `401` — `{ "error": "Invalid username or password" }` |
| **Models** | `User` |
| **Example** | `curl -X POST /api/auth/login/ -d '{"username":"alice","password":"secret"}'` |

---

### Current User

| | |
|---|---|
| **Method** | `GET` |
| **URL** | `/api/auth/me/` |
| **Purpose** | Return the authenticated user's profile |
| **Auth** | Required |
| **Permissions** | `IsAuthenticated` |
| **Request** | None |
| **Response** | `200` — `{ "id", "username", "email", "role", "bio" }` |
| **Models** | `User` |
| **Example** | `curl -H "Authorization: Bearer $TOKEN" /api/auth/me/` |

---

## Courses

### List Published Courses (Catalog)

| | |
|---|---|
| **Method** | `GET` |
| **URL** | `/api/courses/` |
| **Purpose** | Paginated list of published courses for students |
| **Auth** | Required |
| **Permissions** | `IsAuthenticated` |
| **Query params** | `page`, `page_size` (default 12, max 100) |
| **Response** | Paginated `{ id, title, description, instructor, is_published, chapter_count, enrolled_count }`. On merged branches with M12, responses may be Redis-cached (60s TTL). With M15, `chat_open` boolean may be included. |
| **Models** | `Course`, `User`, `Chapter`, `Enrollment` |
| **Example** | `curl -H "Authorization: Bearer $TOKEN" "/api/courses/?page=1"` |

---

### List Instructor's Courses

| | |
|---|---|
| **Method** | `GET` |
| **URL** | `/api/courses/mine/` |
| **Purpose** | All courses owned by the authenticated instructor |
| **Auth** | Required |
| **Permissions** | `IsAuthenticated`, `IsInstructor` |
| **Response** | `200` — array of course objects (not paginated) |
| **Models** | `Course` |
| **Example** | `curl -H "Authorization: Bearer $TOKEN" /api/courses/mine/` |

---

### Create Course

| | |
|---|---|
| **Method** | `POST` |
| **URL** | `/api/courses/create/` |
| **Purpose** | Create a new course owned by the instructor |
| **Auth** | Required |
| **Permissions** | `IsAuthenticated`, `IsInstructor` |
| **Request** | `{ "title", "description" (optional), "is_published" (optional, default false) }` |
| **Response** | `201` — course object · `400` — validation errors |
| **Models** | `Course` |
| **Example** | `curl -X POST /api/courses/create/ -H "Authorization: Bearer $TOKEN" -d '{"title":"Intro CS","is_published":true}'` |

---

### Course Detail

| | |
|---|---|
| **Method** | `GET` · `PUT` · `DELETE` |
| **URL** | `/api/courses/<course_id>/` |
| **Purpose** | Read, update, or delete a single course |
| **Auth** | Required |
| **Permissions** | GET: any authenticated user if published, or course instructor. PUT/DELETE: course instructor only |
| **Request (PUT)** | Partial update: `{ "title", "description", "is_published" }` |
| **Response** | GET/PUT: `200` course object · DELETE: `204` · `403` if unpublished and not owner |
| **Models** | `Course` |
| **Example** | `curl -X PUT /api/courses/1/ -d '{"is_published":true}'` |

---

### List Chapters

| | |
|---|---|
| **Method** | `GET` |
| **URL** | `/api/courses/<course_id>/chapters/` |
| **Purpose** | List chapters for a course |
| **Auth** | Required |
| **Permissions** | Instructor sees all chapters. Others see public chapters only if course is published |
| **Response** | `200` — `[{ id, course, title, content, visibility, order_index }]` |
| **Models** | `Course`, `Chapter` |
| **Example** | `curl /api/courses/1/chapters/` |

---

### Create Chapter

| | |
|---|---|
| **Method** | `POST` |
| **URL** | `/api/courses/<course_id>/chapters/create/` |
| **Purpose** | Add a chapter to a course |
| **Auth** | Required |
| **Permissions** | `IsInstructor` + course owner |
| **Request** | `{ "title", "content" (Slate JSON array), "visibility" ("public"\|"private"), "order_index" }` |
| **Response** | `201` — chapter object |
| **Models** | `Chapter`, `Course` |
| **Example** | `curl -X POST /api/courses/1/chapters/create/ -d '{"title":"Week 1","content":[],"visibility":"public","order_index":0}'` |

---

### Chapter Detail

| | |
|---|---|
| **Method** | `GET` · `PUT` · `DELETE` |
| **URL** | `/api/chapters/<chapter_id>/` |
| **Purpose** | Read, update, or delete a chapter |
| **Auth** | Required |
| **Permissions** | GET: instructor owner, or enrolled student on public chapter in published course. PUT/DELETE: course instructor |
| **Request (PUT)** | `{ "title", "content", "visibility", "order_index" }` |
| **Response** | GET/PUT: `200` chapter · DELETE: `204` · `403` if access denied |
| **Models** | `Chapter`, `Enrollment` |
| **Example** | `curl /api/chapters/5/` |

---

### Enroll / Unenroll

| | |
|---|---|
| **Method** | `POST` · `DELETE` |
| **URL** | `/api/courses/<course_id>/enroll/` |
| **Purpose** | Enroll or unenroll the current user |
| **Auth** | Required |
| **Permissions** | Any authenticated user (typically students) |
| **Request** | None |
| **Response** | POST: `201` `{ "message": "Enrolled" }` · DELETE: `204` `{ "message": "Unenrolled" }` |
| **Models** | `Enrollment`, `Course` |
| **Example** | `curl -X POST /api/courses/1/enroll/` |

---

### Enroll (Strict)

| | |
|---|---|
| **Method** | `POST` |
| **URL** | `/api/courses/<course_id>/enroll/` (alternate view on some branches) |
| **Purpose** | Student enrolls in a published course; fails if already enrolled |
| **Auth** | Required |
| **Permissions** | `IsStudent` |
| **Response** | `201` enrollment object · `400` if already enrolled |
| **Models** | `Enrollment` |

---

### Enrollment Status

| | |
|---|---|
| **Method** | `GET` |
| **URL** | `/api/courses/<course_id>/enrollment-status/` |
| **Purpose** | Check if current student is enrolled |
| **Auth** | Required |
| **Permissions** | `IsStudent` |
| **Response** | `200` — `{ "enrolled": true \| false }` |
| **Models** | `Enrollment` |
| **Example** | `curl /api/courses/1/enrollment-status/` |

---

### My Courses

| | |
|---|---|
| **Method** | `GET` |
| **URL** | `/api/my-courses/` |
| **Purpose** | List courses the student is enrolled in |
| **Auth** | Required |
| **Permissions** | `IsStudent` |
| **Response** | `200` — `[{ id, course: { ...full course... }, enrolled_at }]` |
| **Models** | `Enrollment`, `Course` |
| **Example** | `curl /api/my-courses/` |

---

### Enrolled Students

| | |
|---|---|
| **Method** | `GET` |
| **URL** | `/api/courses/<course_id>/students/` |
| **Purpose** | List students enrolled in the instructor's course |
| **Auth** | Required |
| **Permissions** | `IsInstructor` + course owner |
| **Response** | `200` — `[{ id, name, email, phone }]` |
| **Models** | `Enrollment`, `User` |
| **Example** | `curl /api/courses/1/students/` |

---

## Quizzes

### List Quizzes

| | |
|---|---|
| **Method** | `GET` |
| **URL** | `/api/courses/<course_id>/quizzes/` |
| **Purpose** | List quizzes for a course |
| **Auth** | Required |
| **Permissions** | Instructor owner sees all. Others see published quizzes only in published courses |
| **Response** | `200` — `[{ id, course, title, description, is_published, question_count, created_at }]` |
| **Models** | `Quiz`, `Course` |
| **Example** | `curl /api/courses/1/quizzes/` |

---

### Create Quiz

| | |
|---|---|
| **Method** | `POST` |
| **URL** | `/api/courses/<course_id>/quizzes/create/` |
| **Purpose** | Create a quiz in a course |
| **Auth** | Required |
| **Permissions** | `IsInstructor` + course owner |
| **Request** | `{ "title", "description" (optional), "is_published" (optional) }` |
| **Response** | `201` — quiz object |
| **Models** | `Quiz` |
| **Example** | `curl -X POST /api/courses/1/quizzes/create/ -d '{"title":"Midterm"}'` |

---

### Quiz Detail

| | |
|---|---|
| **Method** | `GET` · `PUT` · `DELETE` |
| **URL** | `/api/quizzes/<quiz_id>/` |
| **Purpose** | Read, update, or delete a quiz |
| **Auth** | Required |
| **Permissions** | GET: owner or published quiz. PUT/DELETE: quiz owner (course instructor) |
| **Request (PUT)** | `{ "title", "description", "is_published" }` |
| **Response** | GET/PUT: `200` · DELETE: `204` |
| **Models** | `Quiz` |
| **Example** | `curl /api/quizzes/3/` |

---

### Create Question

| | |
|---|---|
| **Method** | `POST` |
| **URL** | `/api/quizzes/<quiz_id>/questions/create/` |
| **Purpose** | Add a question to a quiz |
| **Auth** | Required |
| **Permissions** | `IsInstructor` + quiz owner |
| **Request** | `{ "question_type" ("single_choice"\|"multiple_choice"\|"short_answer"), "body": { prompt, options?, correct_option_ids?, correct_answer? }, "points", "order_index" }` |
| **Response** | `201` — full question object (includes correct answers) |
| **Models** | `Question`, `Quiz` |
| **Example** | `curl -X POST /api/quizzes/3/questions/create/ -d '{"question_type":"single_choice","body":{"prompt":[],"options":[{"id":"a","text":"Yes"}],"correct_option_ids":["a"]},"points":1,"order_index":0}'` |

---

### Question Detail

| | |
|---|---|
| **Method** | `GET` · `PUT` · `DELETE` |
| **URL** | `/api/questions/<question_id>/` |
| **Purpose** | Read, update, or delete a question (instructor only) |
| **Auth** | Required |
| **Permissions** | `IsInstructor` + quiz owner |
| **Response** | GET/PUT: `200` full question · DELETE: `204` |
| **Models** | `Question` |

---

### Take Quiz

| | |
|---|---|
| **Method** | `GET` |
| **URL** | `/api/quizzes/<quiz_id>/take/` |
| **Purpose** | Fetch quiz and sanitized questions for student attempt |
| **Auth** | Required |
| **Permissions** | `IsStudent` + enrolled in course |
| **Response** | `200` — `{ "quiz": {...}, "questions": [{ id, question_type, body (no answers), points, order_index }] }` |
| **Models** | `Quiz`, `Question`, `Enrollment` |
| **Example** | `curl /api/quizzes/3/take/` |

---

### Submit Quiz

| | |
|---|---|
| **Method** | `POST` |
| **URL** | `/api/quizzes/<quiz_id>/submit/` |
| **Purpose** | Grade and persist a student's quiz attempt (idempotent) |
| **Auth** | Required |
| **Permissions** | `IsStudent` + enrolled |
| **Request** | `{ "answers": { "<question_id>": <answer> } }` — choice answers are option ID arrays; short answer is a string |
| **Response** | `201` (first submit) or `200` (duplicate) — `{ id, quiz, score, max_score, submitted_at }` · `409` if concurrent submit in progress |
| **Models** | `Submission`, `Quiz`, `Question` |
| **Example** | `curl -X POST /api/quizzes/3/submit/ -d '{"answers":{"7":["a"],"8":"photosynthesis"}}'` |

---

### My Quiz Result

| | |
|---|---|
| **Method** | `GET` |
| **URL** | `/api/quizzes/<quiz_id>/my-result/` |
| **Purpose** | Retrieve the student's submission for a quiz |
| **Auth** | Required |
| **Permissions** | `IsStudent` |
| **Response** | `200` — submission result · `404` if no submission |
| **Models** | `Submission` |
| **Example** | `curl /api/quizzes/3/my-result/` |

---

## Quiz Sessions

REST endpoints manage session lifecycle. Real-time question reveal, answers, charts, and live leaderboard use WebSocket (below).

### Create Live Session

| | |
|---|---|
| **Method** | `POST` |
| **URL** | `/api/quizzes/<quiz_id>/sessions/` |
| **Purpose** | Create a live quiz room with a unique join code |
| **Auth** | Required |
| **Permissions** | `IsInstructor` + quiz owner |
| **Request** | None |
| **Response** | `201` — `{ id, quiz, host, room_code, status ("lobby"), current_question_index (-1), started_at, ended_at, created_at }` |
| **Models** | `LiveSession`, `Quiz` |
| **Example** | `curl -X POST /api/quizzes/3/sessions/` |

---

### Session Detail (Join Lookup)

| | |
|---|---|
| **Method** | `GET` |
| **URL** | `/api/sessions/<room_code>/` |
| **Purpose** | Look up a live session by room code |
| **Auth** | Required |
| **Permissions** | Any authenticated user |
| **Response** | `200` — live session object · `404` if code invalid |
| **Models** | `LiveSession` |
| **Example** | `curl /api/sessions/ABC123/` |

---

### Start Session

| | |
|---|---|
| **Method** | `POST` |
| **URL** | `/api/sessions/<room_code>/start/` |
| **Purpose** | Move session from lobby to active |
| **Auth** | Required |
| **Permissions** | Session host only |
| **Response** | `200` — session with `status: "active"` · `400` if not in lobby |
| **Models** | `LiveSession` |
| **Example** | `curl -X POST /api/sessions/ABC123/start/` |

---

### End Session

| | |
|---|---|
| **Method** | `POST` |
| **URL** | `/api/sessions/<room_code>/end/` |
| **Purpose** | End a live session and clear ephemeral Redis state |
| **Auth** | Required |
| **Permissions** | Session host only |
| **Response** | `200` — session with `status: "ended"` (idempotent) |
| **Models** | `LiveSession` |
| **Example** | `curl -X POST /api/sessions/ABC123/end/` |

---

### Live Quiz WebSocket

| | |
|---|---|
| **Method** | WebSocket |
| **URL** | `ws://<host>/ws/live/<room_code>/` |
| **Purpose** | Real-time live quiz: state sync, question reveal, answers, charts, leaderboard |
| **Auth** | JWT via WebSocket subprotocol |
| **Permissions** | Host (session creator) or enrolled student in quiz's course. Close codes: `4001` unauthenticated, `4003` unauthorized, `4004` not found |

**Client → Server events:**

| Event | Sender | Payload | Purpose |
|-------|--------|---------|---------|
| `question.advance` | Host | `{ "type": "question.advance" }` | Reveal next question |
| `answer.submit` | Student | `{ "type": "answer.submit", "question_id", "answer" }` | Submit answer for open question |
| `session.end` | Host | `{ "type": "session.end" }` | End session |

**Server → Client events:**

| Event | Payload | Purpose |
|-------|---------|---------|
| `session.state` | `{ status, question_index, question?, chart?, leaderboard? }` | Sent on connect/reconnect |
| `question.revealed` | `{ question, question_index }` | New question broadcast |
| `answer.accepted` | `{ question_id }` | Acknowledge submitter |
| `chart.update` | `{ question_id, counts }` | Live answer distribution |
| `leaderboard.update` | `{ rankings: [{ user_id, username, score, rank }] }` | Live standings |
| `session.ended` | `{}` | Session closed |
| `error` | `{ error }` | Error detail |

**Models:** `LiveSession`, `Question`, `Submission`, `Enrollment`, `User`

**Example:** `new WebSocket('ws://localhost:8000/ws/live/ABC123/', [accessToken])`

---

### Echo WebSocket (Foundation Test)

| | |
|---|---|
| **Method** | WebSocket |
| **URL** | `ws://<host>/ws/echo/` |
| **Purpose** | Acceptance test for Channels + JWT auth (not used in production UI) |
| **Auth** | JWT subprotocol |
| **Client send** | Any text |
| **Server response** | `{ "echo": <text>, "user": <username> }` |

---

## Leaderboard

### Course Leaderboard

| | |
|---|---|
| **Method** | `GET` |
| **URL** | `/api/courses/<course_id>/leaderboard/` |
| **Purpose** | Persistent course-wide rankings from all quiz submissions |
| **Auth** | Required |
| **Permissions** | Course instructor or enrolled student |
| **Response** | `200` — `[{ user_id, username, score, rank }]` sorted by total score descending |
| **Models** | `Submission`, `Quiz`, `Course`, `Enrollment` |
| **Example** | `curl /api/courses/1/leaderboard/` |

**Note:** Live session leaderboard is ephemeral and delivered via WebSocket `leaderboard.update` (Redis ZSET). This REST endpoint aggregates Postgres `Submission` scores across all quizzes in the course.

---

## Messaging

### Message History

| | |
|---|---|
| **Method** | `GET` |
| **URL** | `/api/courses/<course_id>/messages/` |
| **Purpose** | Paginated chat history for a course |
| **Auth** | Required |
| **Permissions** | Course instructor or enrolled student |
| **Query params** | `page`, `page_size` (default 20, max 100) |
| **Response** | Paginated `{ id, course, sender, sender_username, body, created_at }` newest first |
| **Models** | `Message`, `Course`, `User` |
| **Example** | `curl "/api/courses/1/messages/?page=1"` |

---

### Course Chat WebSocket

| | |
|---|---|
| **Method** | WebSocket |
| **URL** | `ws://<host>/ws/chat/<course_id>/` |
| **Purpose** | Real-time course chat; persist-then-broadcast |
| **Auth** | JWT subprotocol |
| **Permissions** | Instructor or enrolled student. Writes blocked after `Course.term.end_date`. Rate limit: 10 messages per 10 seconds per user |

**Client → Server:** `{ "body": "Hello class" }` (plain JSON string body)

**Server → Client:** Message object `{ id, course, sender, sender_username, body, created_at }` or `{ "error": "..." }`

**Models:** `Message`, `Course`, `Enrollment`, `Term`

**Example:** Send via WebSocket; fetch history via REST for offline/reconnect catch-up.

---

## Scheduling

### List Terms

| | |
|---|---|
| **Method** | `GET` |
| **URL** | `/api/terms/` |
| **Purpose** | List all academic terms |
| **Auth** | Required |
| **Permissions** | `IsAuthenticated` |
| **Response** | `200` — `[{ id, name, start_date, end_date }]` |
| **Models** | `Term` |
| **Example** | `curl /api/terms/` |

---

### List Sections

| | |
|---|---|
| **Method** | `GET` |
| **URL** | `/api/courses/<course_id>/sections/` |
| **Purpose** | List sections for a course, optionally filtered by term |
| **Auth** | Required |
| **Permissions** | `IsAuthenticated` |
| **Query params** | `term` (term ID) |
| **Response** | `200` — `[{ id, course, term, section_code, location, capacity, meetings: [{ day_of_week, start_time, end_time }], created_at }]` |
| **Models** | `Section`, `Meeting`, `Term` |
| **Example** | `curl "/api/courses/1/sections/?term=2"` |

---

### Create Section

| | |
|---|---|
| **Method** | `POST` |
| **URL** | `/api/courses/<course_id>/sections/create/` |
| **Purpose** | Create a section with nested meetings |
| **Auth** | Required |
| **Permissions** | `IsInstructor` + course owner |
| **Request** | `{ "term": <term_id>, "section_code", "location", "capacity", "meetings": [{ "day_of_week" (0–6), "start_time", "end_time" }] }` |
| **Response** | `201` — section object |
| **Models** | `Section`, `Meeting`, `Term` |
| **Example** | `curl -X POST /api/courses/1/sections/create/ -d '{"term":2,"section_code":"001","meetings":[{"day_of_week":0,"start_time":"10:00","end_time":"11:15"}]}'` |

---

### Section Detail

| | |
|---|---|
| **Method** | `GET` · `PUT` · `DELETE` |
| **URL** | `/api/sections/<section_id>/` |
| **Purpose** | Read, update, or delete a section (meetings replaced on PUT) |
| **Auth** | Required |
| **Permissions** | GET: any authenticated. PUT/DELETE: course instructor |
| **Request (PUT)** | Same shape as create (partial allowed; meetings fully replaced if provided) |
| **Response** | GET/PUT: `200` · DELETE: `204` |
| **Models** | `Section`, `Meeting` |

---

### List / Create Breaks

| | |
|---|---|
| **Method** | `GET` · `POST` |
| **URL** | `/api/breaks/` |
| **Purpose** | Manage student's personal unavailable time blocks |
| **Auth** | Required |
| **Permissions** | `IsStudent` |
| **Request (POST)** | `{ "day_of_week" (0–6), "start_time", "end_time", "label" (optional) }` |
| **Response** | GET: array of breaks · POST: `201` break object |
| **Models** | `Break` |
| **Example** | `curl -X POST /api/breaks/ -d '{"day_of_week":0,"start_time":"08:00","end_time":"10:00","label":"No early class"}'` |

---

### Delete Break

| | |
|---|---|
| **Method** | `DELETE` |
| **URL** | `/api/breaks/<break_id>/` |
| **Purpose** | Remove a student's break |
| **Auth** | Required |
| **Permissions** | `IsStudent` (own breaks only; others 404) |
| **Response** | `204` |
| **Models** | `Break` |

---

### Generate Schedule

| | |
|---|---|
| **Method** | `POST` |
| **URL** | `/api/schedule/generate/` |
| **Purpose** | Find conflict-free section combinations for selected courses |
| **Auth** | Required |
| **Permissions** | `IsAuthenticated` (students use breaks; instructors use own meeting blocks) |
| **Request** | `{ "term_id", "course_ids": [<id>, ...] }` |
| **Response** | `200` — `{ "count", "schedules": [[ section objects per course ], ...] }` |
| **Models** | `Section`, `Meeting`, `Break`, `Term`, `Course` |
| **Example** | `curl -X POST /api/schedule/generate/ -d '{"term_id":2,"course_ids":[1,3,5]}'` |

---

### List / Create Saved Schedules

| | |
|---|---|
| **Method** | `GET` · `POST` |
| **URL** | `/api/schedule/saved/` |
| **Purpose** | Save a chosen schedule candidate |
| **Auth** | Required |
| **Permissions** | `IsStudent` |
| **Request (POST)** | `{ "term": <term_id>, "sections": [<section_id>, ...] }` |
| **Response** | GET: array with `section_details` · POST: `201` saved schedule |
| **Models** | `SavedSchedule`, `Section`, `Term` |
| **Example** | `curl -X POST /api/schedule/saved/ -d '{"term":2,"sections":[4,7,9]}'` |

---

### Confirm Saved Schedule

| | |
|---|---|
| **Method** | `POST` |
| **URL** | `/api/schedule/saved/<saved_schedule_id>/confirm/` |
| **Purpose** | Create enrollments for all courses in the saved schedule (idempotent) |
| **Auth** | Required |
| **Permissions** | `IsStudent` (own schedule only) |
| **Request** | None |
| **Response** | `200` — saved schedule with `confirmed_at` set |
| **Models** | `SavedSchedule`, `Enrollment`, `Section` |
| **Example** | `curl -X POST /api/schedule/saved/5/confirm/` |

---

## Admin

Django's built-in admin interface — not a JSON API. Requires a staff/superuser account (`is_staff=True`).

| | |
|---|---|
| **URL** | `/admin/` |
| **Purpose** | CRUD for all registered models via Django admin UI |
| **Auth** | Django session login (separate from JWT) |

**Registered models:**

| App | Models | Admin features |
|-----|--------|----------------|
| `users` | User | Role, bio fields; list by username, email, role |
| `courses` | Course, Chapter, Enrollment | Filter by published/visibility |
| `quizzes` | Quiz, Question | Filter by published/type |
| `schedule` | Term, Section (+ Meeting inline), Break | Term dates; section meetings inline |
| `messaging` | Message | Filter by course |

**Example:** Navigate to `http://localhost:8000/admin/`, log in with staff credentials.

---

## Endpoint Summary

| Group | REST endpoints | WebSocket endpoints |
|-------|----------------|---------------------|
| Authentication | 3 | — |
| Courses | 12 | — |
| Quizzes | 9 | — |
| Quiz Sessions | 4 | 1 (`/ws/live/<room_code>/`) |
| Leaderboard | 1 | (live via WS) |
| Messaging | 1 | 1 (`/ws/chat/<course_id>/`) |
| Scheduling | 9 | — |
| Admin | 1 (UI) | — |
| Foundation | — | 1 (`/ws/echo/`) |

**Total:** 39 REST endpoints + 3 WebSocket routes.

---

## Merge Notes

This documentation reflects the **fully merged** API surface. Individual milestone branches may expose subsets:

- M1–M4: Authentication + Courses only
- M5–M7: + Quizzes
- M8–M11: + Scheduling (`/api/terms/`, `/api/schedule/*`, sections, breaks)
- M12–M13: Redis optimizations + WebSocket echo
- M14–M15: + Messaging REST/WS, `chat_open` on courses
- M16–M19: + Live sessions, live WS, leaderboard
- M20–M21: Load-test tooling (no new public API endpoints)

Reference branch for fullest REST + WS stack: `cursor/load-testing-ws-graphs-7233` merged with `cursor/chat-frontend-tenure-reset-7233` and `cursor/student-schedule-builder-7233`.
