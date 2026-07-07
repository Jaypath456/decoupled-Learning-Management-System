# Classavo LMS — Final Database Architecture

This document describes the **composed post-milestone schema** across all Django apps (`users`, `courses`, `quizzes`, `schedule`, `messaging`). The database engine is **PostgreSQL**. Models exist on feature branches (`origin/cursor/*-7233`); `main` currently contains only `users` and `courses`.

---

## Entity Relationship Overview

```
User ──┬──< Course (instructor)
       ├──< Enrollment >── Course
       ├──< Chapter (via Course)
       ├──< Quiz/Submission/LiveSession (via quizzes)
       ├──< Section/Break/SavedSchedule (via schedule)
       └──< Message (sender)

Course ──┬──< Chapter, Enrollment, Quiz, Message, Section
         └──> Term (nullable)

Term ──┬──< Section, SavedSchedule
       └──< Course

Quiz ──┬──< Question, Submission, LiveSession
       └── (via Course) >── Course

Section ──┬──< Meeting
          └──<> SavedSchedule (M2M)

SavedSchedule >── User, Term
LiveSession >── Quiz, User (host)
Submission >── Quiz, User (student)
Message >── Course, User (sender)
```

**Legend:** `──<` one-to-many · `>──` many-to-one · `<>──` many-to-many

---

## 1. Every Model

| App | Model | Table purpose |
|-----|-------|---------------|
| `users` | **User** | Authentication, roles, profiles |
| `courses` | **Course** | Top-level learning container |
| `courses` | **Chapter** | Ordered rich-text content within a course |
| `courses` | **Enrollment** | Student membership in a course |
| `quizzes` | **Quiz** | Assessment attached to a course |
| `quizzes` | **Question** | Typed question within a quiz |
| `quizzes` | **Submission** | One graded attempt per student per quiz |
| `quizzes` | **LiveSession** | Real-time quiz room instance |
| `schedule` | **Term** | Academic period (e.g. Summer 2026) |
| `schedule` | **Section** | Course offering for a specific term |
| `schedule` | **Meeting** | Recurring weekly time block for a section |
| `schedule` | **Break** | Student personal unavailable time window |
| `schedule` | **SavedSchedule** | Student draft/confirmed section selection |
| `messaging` | **Message** | Course-scoped chat message |

Django also creates implicit junction tables for `User.groups`, `User.user_permissions`, and `SavedSchedule.sections`.

---

## 2. Fields and Purpose

### User (`users_user`)

Extends Django's `AbstractUser`.

| Field | Type | Purpose |
|-------|------|---------|
| `id` | BigAutoField PK | Surrogate primary key |
| `password` | CharField(128) | Hashed credential |
| `last_login` | DateTime, nullable | Last successful login timestamp |
| `is_superuser` | Boolean | Django admin superuser flag |
| `username` | CharField(150), unique | Login identifier; validated to alphanumeric, `@`, `_` |
| `first_name` | CharField(150) | Display name (optional) |
| `last_name` | CharField(150) | Display name (optional) |
| `email` | EmailField(254) | Contact email (optional) |
| `is_staff` | Boolean | Django admin access |
| `is_active` | Boolean | Account enabled/disabled |
| `date_joined` | DateTime | Registration timestamp |
| `role` | CharField(20) | Application role: `instructor` or `student` |
| `bio` | TextField | Optional profile text |
| `groups` | M2M → `auth.Group` | Django permission groups (unused by app logic) |
| `user_permissions` | M2M → `auth.Permission` | Direct Django permissions (unused by app logic) |

---

### Course (`courses_course`)

| Field | Type | Purpose |
|-------|------|---------|
| `id` | BigAutoField PK | Surrogate primary key |
| `title` | CharField(200) | Course display name |
| `description` | TextField | Course summary |
| `instructor_id` | FK → User | Owning instructor |
| `is_published` | Boolean | Visible in public catalog when true |
| `term_id` | FK → Term, nullable | Academic period; drives chat tenure reset |
| `created_at` | DateTime | Creation timestamp |
| `updated_at` | DateTime | Last modification timestamp |

Default ordering: `-created_at`.

---

### Chapter (`courses_chapter`)

| Field | Type | Purpose |
|-------|------|---------|
| `id` | BigAutoField PK | Surrogate primary key |
| `course_id` | FK → Course | Parent course |
| `title` | CharField(200) | Chapter heading |
| `content` | JSONField (list) | Plate.js/Slate document tree |
| `visibility` | CharField(10) | `public` or `private` access flag |
| `order_index` | Integer | Sort position within course |
| `created_at` | DateTime | Creation timestamp |
| `updated_at` | DateTime | Last modification timestamp |

Default ordering: `order_index`, `created_at`.

---

### Enrollment (`courses_enrollment`)

| Field | Type | Purpose |
|-------|------|---------|
| `id` | BigAutoField PK | Surrogate primary key |
| `student_id` | FK → User | Enrolled student |
| `course_id` | FK → Course | Target course |
| `enrolled_at` | DateTime | Enrollment timestamp |

Central membership record gating chapters, quizzes, chat, and live sessions.

---

### Quiz (`quizzes_quiz`)

| Field | Type | Purpose |
|-------|------|---------|
| `id` | BigAutoField PK | Surrogate primary key |
| `course_id` | FK → Course | Parent course |
| `title` | CharField(200) | Quiz name |
| `description` | TextField | Instructions or summary |
| `is_published` | Boolean | Student-visible when true |
| `created_at` | DateTime | Creation timestamp |
| `updated_at` | DateTime | Last modification timestamp |

---

### Question (`quizzes_question`)

| Field | Type | Purpose |
|-------|------|---------|
| `id` | BigAutoField PK | Surrogate primary key |
| `quiz_id` | FK → Quiz | Parent quiz |
| `question_type` | CharField(20) | `single_choice`, `multiple_choice`, or `short_answer` |
| `body` | JSONField (dict) | Prompt (Slate JSON), options, correct answers |
| `points` | PositiveInteger | Score weight |
| `order_index` | Integer | Sort position within quiz |
| `created_at` | DateTime | Creation timestamp |
| `updated_at` | DateTime | Last modification timestamp |

Shape of `body` is validated in serializers, not at the database layer.

---

### Submission (`quizzes_submission`)

| Field | Type | Purpose |
|-------|------|---------|
| `id` | BigAutoField PK | Surrogate primary key |
| `quiz_id` | FK → Quiz | Target quiz |
| `student_id` | FK → User | Submitting student |
| `answers` | JSONField (dict) | Map of question ID → answer payload |
| `score` | PositiveInteger | Points earned |
| `max_score` | PositiveInteger | Maximum possible points |
| `submitted_at` | DateTime | Submission timestamp |

Shared by async quiz-taking and live quiz sessions (one row per student per quiz).

---

### LiveSession (`quizzes_livesession`)

| Field | Type | Purpose |
|-------|------|---------|
| `id` | BigAutoField PK | Surrogate primary key |
| `quiz_id` | FK → Quiz | Quiz being run live |
| `host_id` | FK → User | Instructor running the session |
| `room_code` | CharField(6), unique | Join code for students |
| `status` | CharField(20) | `lobby`, `active`, or `ended` |
| `current_question_index` | Integer | Active question pointer (-1 = none) |
| `started_at` | DateTime, nullable | Session start time |
| `ended_at` | DateTime, nullable | Session end time |
| `created_at` | DateTime | Room creation timestamp |

Fine-grained per-question state lives in Redis, not Postgres.

---

### Term (`schedule_term`)

| Field | Type | Purpose |
|-------|------|---------|
| `id` | BigAutoField PK | Surrogate primary key |
| `name` | CharField(100), unique | Human-readable label (e.g. Summer 2026) |
| `start_date` | DateField | Term begins |
| `end_date` | DateField | Term ends; triggers chat purge and write-lock |

---

### Section (`schedule_section`)

| Field | Type | Purpose |
|-------|------|---------|
| `id` | BigAutoField PK | Surrogate primary key |
| `course_id` | FK → Course | Course being offered |
| `term_id` | FK → Term | Term of offering |
| `section_code` | CharField(20) | Section identifier (e.g. 001) |
| `location` | CharField(100) | Room or virtual location |
| `capacity` | PositiveInteger, nullable | Optional enrollment cap (not DB-enforced) |
| `created_at` | DateTime | Creation timestamp |
| `updated_at` | DateTime | Last modification timestamp |

---

### Meeting (`schedule_meeting`)

| Field | Type | Purpose |
|-------|------|---------|
| `id` | BigAutoField PK | Surrogate primary key |
| `section_id` | FK → Section | Parent section |
| `day_of_week` | Integer (0–6) | Monday=0 through Sunday=6 |
| `start_time` | TimeField | Block start |
| `end_time` | TimeField | Block end |

Model-level validation ensures `end_time > start_time` (not a database CHECK constraint).

---

### Break (`schedule_break`)

| Field | Type | Purpose |
|-------|------|---------|
| `id` | BigAutoField PK | Surrogate primary key |
| `student_id` | FK → User | Owning student |
| `day_of_week` | Integer (0–6) | Blocked day |
| `start_time` | TimeField | Unavailable from |
| `end_time` | TimeField | Unavailable until |
| `label` | CharField(100) | Optional description |

Model-level validation ensures `end_time > start_time`.

---

### SavedSchedule (`schedule_savedschedule`)

| Field | Type | Purpose |
|-------|------|---------|
| `id` | BigAutoField PK | Surrogate primary key |
| `student_id` | FK → User | Schedule owner |
| `term_id` | FK → Term | Target academic period |
| `sections` | M2M → Section | Selected section combination |
| `confirmed_at` | DateTime, nullable | Null = draft; set on confirm → creates Enrollments |
| `created_at` | DateTime | Creation timestamp |

---

### Message (`messaging_message`)

| Field | Type | Purpose |
|-------|------|---------|
| `id` | BigAutoField PK | Surrogate primary key |
| `course_id` | FK → Course | Chat room (course-scoped) |
| `sender_id` | FK → User | Message author |
| `body` | CharField(1000) | Message text |
| `created_at` | DateTime | Send timestamp |

No separate chat room table — the course is the room.

---

## 3. Relationships Between Models

| Relationship | Cardinality | Description |
|--------------|-------------|-------------|
| User → Course | 1:N | Instructor owns many courses |
| User → Enrollment | 1:N | Student has many enrollments |
| Course → Enrollment | 1:N | Course has many enrolled students |
| Course → Chapter | 1:N | Course contains ordered chapters |
| Course → Quiz | 1:N | Course contains quizzes |
| Course → Message | 1:N | Course has chat history |
| Course → Section | 1:N | Course offered in multiple sections |
| Course → Term | N:1 | Optional academic period assignment |
| Term → Section | 1:N | Term contains section offerings |
| Term → SavedSchedule | 1:N | Students save schedules per term |
| Section → Meeting | 1:N | Section has recurring meeting blocks |
| Quiz → Question | 1:N | Quiz contains ordered questions |
| Quiz → Submission | 1:N | Quiz receives student submissions |
| Quiz → LiveSession | 1:N | Quiz can have multiple live runs |
| User → Submission | 1:N | Student has submissions across quizzes |
| User → LiveSession | 1:N | Instructor hosts live sessions |
| User → Break | 1:N | Student defines personal breaks |
| User → SavedSchedule | 1:N | Student may have multiple saved schedules |
| SavedSchedule ↔ Section | M:N | Schedule selects a set of sections |

---

## 4. Foreign Keys

| From | Column | To | ON DELETE | Rationale |
|------|--------|----|-----------|-----------|
| Course | `instructor_id` | User | CASCADE | Delete instructor's courses |
| Course | `term_id` | Term | SET NULL | Preserve course if term removed |
| Chapter | `course_id` | Course | CASCADE | Chapters die with course |
| Enrollment | `student_id` | User | CASCADE | Remove enrollments with user |
| Enrollment | `course_id` | Course | CASCADE | Remove enrollments with course |
| Quiz | `course_id` | Course | CASCADE | Quizzes die with course |
| Question | `quiz_id` | Quiz | CASCADE | Questions die with quiz |
| Submission | `quiz_id` | Quiz | CASCADE | Submissions die with quiz |
| Submission | `student_id` | User | CASCADE | Submissions die with user |
| LiveSession | `quiz_id` | Quiz | CASCADE | Sessions die with quiz |
| LiveSession | `host_id` | User | CASCADE | Sessions die with host user |
| Section | `course_id` | Course | CASCADE | Sections die with course |
| Section | `term_id` | Term | CASCADE | Sections die with term |
| Meeting | `section_id` | Section | CASCADE | Meetings die with section |
| Break | `student_id` | User | CASCADE | Breaks die with user |
| SavedSchedule | `student_id` | User | CASCADE | Schedules die with user |
| SavedSchedule | `term_id` | Term | CASCADE | Schedules die with term |
| Message | `course_id` | Course | CASCADE | Messages die with course |
| Message | `sender_id` | User | CASCADE | Messages die with sender user |

All foreign keys use Django's default indexing (B-tree index on FK column in PostgreSQL).

---

## 5. Many-to-Many Relationships

| Relationship | Junction table | Purpose |
|--------------|----------------|---------|
| User ↔ Group | `users_user_groups` | Django auth groups (framework default) |
| User ↔ Permission | `users_user_user_permissions` | Django direct permissions (framework default) |
| SavedSchedule ↔ Section | `schedule_savedschedule_sections` | Links a saved schedule to its chosen sections |

The SavedSchedule M2M is the only application-level many-to-many. It stores the student's candidate section combination before confirmation creates `Enrollment` rows.

---

## 6. Database Constraints

### Uniqueness

| Constraint | Model | Columns | Purpose |
|------------|-------|---------|---------|
| UNIQUE | User | `username` | One account per username |
| UNIQUE | Term | `name` | One record per term label |
| UNIQUE | LiveSession | `room_code` | Globally unique join codes |
| UNIQUE TOGETHER | Enrollment | (`student`, `course`) | One enrollment per student per course |
| UNIQUE TOgether | Submission | (`quiz`, `student`) | One submission per student per quiz (idempotency) |

### Field-level constraints

- **PositiveIntegerField** on `Question.points`, `Submission.score`, `Submission.max_score`, `Section.capacity` — non-negative values enforced by Django.
- **CharField max lengths** on all string fields (e.g. message body capped at 1000 characters).
- **Choice constraints** enforced at application layer: `User.role`, `Chapter.visibility`, `Question.question_type`, `LiveSession.status`, `Meeting.day_of_week`, `Break.day_of_week`.
- **Username validator** (regex) enforced in Django, not PostgreSQL.
- **JSONField defaults** (`list` for Chapter.content, `dict` for Question.body and Submission.answers).

### Application-only validation (not DB CHECK)

- `Meeting.clean()` and `Break.clean()` — `end_time` must be after `start_time`.
- `Term.start_date` / `end_date` ordering not enforced at DB level.
- `Question.body` JSON shape validated in serializers.
- `Section.capacity` not enforced against enrollment count.

### NOT NULL

All fields except those explicitly marked `null=True, blank=True`: `Course.term`, `LiveSession.started_at`, `LiveSession.ended_at`, `Section.capacity`, `SavedSchedule.confirmed_at`, and standard Django nullable auth fields (`last_login`, optional name/email).

---

## 7. Indexes

### Explicit indexes

| Index | Table | Columns | Purpose |
|-------|-------|---------|---------|
| PK (implicit) | All tables | `id` | Primary key lookups |
| UNIQUE | `users_user` | `username` | Fast login lookup |
| UNIQUE | `schedule_term` | `name` | Term name lookup |
| UNIQUE + B-tree | `quizzes_livesession` | `room_code` | Fast room join by code |
| Composite | `messaging_message` | (`course_id`, `created_at`) | Paginated chat history per course, newest-first |

Named index: `messaging_m_course__e7e90d_idx` on `messaging_message`.

### Implicit indexes (Django/PostgreSQL defaults)

- **Foreign key columns** — automatic B-tree index on every FK listed in Section 4.
- **unique_together** on Enrollment and Submission — creates composite unique indexes on (`student_id`, `course_id`) and (`quiz_id`, `student_id`) respectively, also serving lookup queries.

### Not indexed (gaps)

- `Course.is_published` — filtered on every catalog query (mitigated by Redis cache, not DB index).
- `Quiz.is_published` — filtered in quiz list views.
- `LiveSession.status` — no index for finding active sessions.
- `Enrollment.enrolled_at`, `Submission.submitted_at` — no index beyond FK; leaderboard queries sort by score, not time.
- JSONField columns — no GIN indexes; content is fetched by primary key only.

---

## 8. Potential Scalability Problems

### High write contention

**Live quiz answer recording** inserts/updates `Submission` rows under row-level locks when many students answer simultaneously. Load tests show chart-update latency scaling linearly with room size (563ms → 1846ms for 30→100 students). Redis handles fan-out; Postgres is the bottleneck.

**Mitigation options:** Buffer scores in Redis and batch-write; separate live-attempt table from async submissions; optimistic concurrency.

### Shared Submission row

Live and async quizzes share `unique_together (quiz, student)`. A student who submits asynchronously cannot also participate in a live run of the same quiz without overwriting or conflicting.

**Mitigation:** Split into `AsyncSubmission` and `LiveAttempt`, or scope uniqueness to `(quiz, student, session)`.

### Message table growth

Chat messages accumulate for all active courses. Purge job deletes messages only after `Term.end_date` passes. Courses without a term never purge automatically.

**Mitigation:** Archive table, message retention policy, partitioning by `course_id` or date.

### JSONField payload size

`Chapter.content`, `Question.body`, and `Submission.answers` store unbounded JSON documents. Large Slate trees increase row size, backup time, and memory per query.

**Mitigation:** External object storage for content; size limits in serializers; normalize options into relational tables if search/filter needed.

### Enrollment as universal gate

Nearly every access check queries `Enrollment`. At very large scale, hot courses with thousands of enrollments increase join/filter cost.

**Mitigation:** Denormalized membership cache in Redis; partial index on active enrollments; read replicas for catalog.

### SavedSchedule M2M explosion

Schedule generation can produce many candidate combinations stored as SavedSchedule rows with M2M section links. Unconfirmed drafts accumulate without automatic cleanup.

**Mitigation:** TTL on unconfirmed drafts; limit drafts per student per term.

### Missing indexes on filter columns

`is_published`, `status`, and term date range queries (chat purge: `course__term__end_date__lt`) may scan large tables as data grows.

**Mitigation:** Partial indexes (e.g. `WHERE is_published = true`); index on `Term.end_date`; composite index on `Course(term_id)`.

### Section capacity not enforced

`Section.capacity` is informational only. Schedule confirm creates enrollments without checking capacity, risking over-enrollment.

**Mitigation:** DB constraint or transactional check at confirm time.

### Cascade delete chains

Deleting a User or Course cascades through enrollments, quizzes, submissions, messages, and sections. Accidental deletion is irreversible and expensive at scale.

**Mitigation:** Soft deletes; `PROTECT` on critical FKs; archival before purge.

### No horizontal partitioning or sharding

Single PostgreSQL instance holds all tenants/courses. No multi-tenant isolation at the database level.

**Mitigation:** Read replicas, connection pooling (PgBouncer), eventual sharding by institution if needed.

### Term/Course integrity

`Course.term` is nullable and uses SET NULL on term deletion, leaving courses in an ambiguous tenure state for chat lock/purge logic.

**Mitigation:** Require term for chat-enabled courses; soft-delete terms instead of hard delete.

---

## Summary Statistics

| Metric | Value |
|--------|-------|
| Django apps with models | 5 |
| Domain models | 14 |
| Foreign keys | 18 |
| Many-to-many (app-level) | 1 (SavedSchedule ↔ Section) |
| Unique constraints | 5 (3 single-column + 2 composite) |
| Explicit composite indexes | 1 (Message) |
| JSONField columns | 3 |
| Database engine | PostgreSQL 16 |

---

## Migration Dependency Order

When merging branches, apply migrations in this order to avoid circular dependencies:

1. `users` (0001, 0002)
2. `courses` (0001, 0002)
3. `schedule` (0001) — depends on `courses.0002`
4. `courses` (0003) — adds `Course.term`, depends on `schedule.0001`
5. `schedule` (0002) — SavedSchedule
6. `quizzes` (0001, 0002, 0003)
7. `messaging` (0001)

**Reference branches:** `cursor/student-schedule-builder-7233` (schedule), `cursor/chat-frontend-tenure-reset-7233` (messaging + Course.term), `cursor/load-testing-ws-graphs-7233` (quizzes + LiveSession).
