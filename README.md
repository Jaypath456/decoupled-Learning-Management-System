# Decoupled Learning Management System

A comprehensive, scalable educational platform designed to facilitate course management, interactive content creation, real-time communication, scheduling, and automated assessments for students and professors. 

Built with a **Decoupled Client-Server (REST API)** architecture, this platform leverages the robustness of Django for the backend and the dynamic component-based rendering of React for the frontend.

## 🚀 Key Features

* **Role-Based Access Control:** Distinct user flows for "Students" (viewing catalogs, enrolling) and "Instructors" (creating courses, managing content, grading).
* **Rich-Text Course Authoring:** Instructors can build structured modules and chapters using a **Plate.js / Slate.js** headless rich text editor, which outputs highly structured, database-friendly JSON trees.
* **Automated Quiz Engine:** Professors can build multiple-choice and short-answer quizzes. The engine handles automated grading, immediate feedback delivery, and securely logs scores to the student's academic profile.
* **Real-Time Communication:** Enabled by **Django Channels (ASGI)** and **WebSockets**, allowing direct, real-time messaging between students and professors for virtual office hours and instant announcements without page refreshes.
* **Interactive Schedule Maker:** A dynamic calendar system integrating **React Big Calendar** with Django Date/Time models. Students receive a personalized, aggregated calendar view of all assignment deadlines, lectures, and office hours.
* **Dynamic Course Catalog:** A unified dashboard optimized via `Promise.all` in React to prevent UI flickering, allowing students to view available courses and current enrollments seamlessly.

## 🛠️ Architecture & Tech Stack

### Frontend (`/frontend`)
* **Framework:** React.js, React Router DOM (Protected Routes)
* **State & Lifecycle:** Heavily utilizes React Hooks (`useEffect`, `useState`) for side-effect handling and asynchronous data fetching.
* **API Communication:** **Axios** with centralized interceptors.
* **Editor:** Plate.js (Slate.js) headless framework for UI-agnostic JSON-tree data structuring.
* **UI/Calendar:** React Big Calendar.

### Backend (`/backend`)
* **Framework:** Django & Django REST Framework (DRF)
* **Protocols:** Dual-configured with `wsgi.py` for traditional REST HTTP requests and `asgi.py` for asynchronous WebSocket operations.
* **Database Management:** Leveraged Django's native ORM and Admin panel for rapid prototyping and secure relational data mapping.

### Authentication & Security
* **Stateless Auth:** JSON Web Tokens (JWT) implemented via `simplejwt`. 
* **Dry Routing:** Axios Interceptors automatically attach JWTs (stored securely in memory/localStorage) to the `Authorization` header of every outgoing request, decoupling the frontend from traditional Django session cookies and eliminating CORS friction.

## 🧠 Architectural Highlights
* **Horizontal Scalability:** By keeping the backend stateless via JWT authentication and decoupling the React frontend entirely, both layers can scale independently in a cloud environment.
* **Maintainability:** Centralized API management and modular Django applications (e.g., `users`, `courses`) strictly adhere to the Single Responsibility Principle.
* **Performance:** Strategic use of React's asynchronous data fetching ensures smooth loading states and minimizes unnecessary DOM re-renders.

## 🐳 Docker Setup (recommended)

The fastest way to run the full stack (PostgreSQL, Redis, backend, frontend) locally is Docker Compose. No local Python/Node/Postgres installation is required.

### 1. Configure environment variables (optional)
Every variable has a working default, so this step can be skipped for a quick start. To customize ports or credentials:
```bash
cp .env.example .env
```

### 2. Start the stack
```bash
docker compose up --build
```
This builds the backend and frontend images, starts PostgreSQL and Redis, waits for both to report healthy, and then starts the backend (which automatically runs `manage.py migrate` on boot) and the frontend dev server.

* Frontend: [http://localhost:3000](http://localhost:3000)
* Backend API: [http://localhost:8000/api](http://localhost:8000/api)
* Django admin: [http://localhost:8000/admin](http://localhost:8000/admin)

Redis backs Django's cache, Celery, Channels, and live-session state — keep it running alongside Postgres.

### 3. Seed demo data
In a second terminal, populate the database with demo instructors, students, courses, chapters, and enrollments:
```bash
docker compose exec backend python manage.py seed_demo
```
This command is idempotent - safe to re-run at any time. It prints login credentials for a demo instructor and demo student account when finished.

### 4. Stopping / resetting
```bash
docker compose down        # stop containers, keep data
docker compose down -v     # stop containers and wipe the database/redis volumes
```
PostgreSQL data is stored in a named volume (`postgres_data`), so it survives `docker compose down` and container restarts - only `-v` removes it.

## ⚙️ Local Setup & Installation (without Docker)

### 1. Clone the repository
```bash
git clone https://github.com/Jaypath456/decoupled-Learning-Management-System.git
cd decoupled-Learning-Management-System
```

### 2. Start PostgreSQL and Redis
Django connects to Postgres at `127.0.0.1:5432` and Redis at `127.0.0.1:6379` by default. A `connection refused` error on migrate means Postgres is not running (or the DB/user from `.env` do not exist yet).

```bash
# Debian/Ubuntu examples — adjust for your OS
sudo service postgresql start   # or: sudo pg_ctlcluster 16 main start
redis-server --daemonize yes    # or: sudo service redis-server start
```

Create the database and role to match `backend/.env.example` (once per machine):
```bash
sudo -u postgres psql -v ON_ERROR_STOP=1 <<'SQL'
DO $$
BEGIN
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'classavo_user') THEN
    CREATE ROLE classavo_user LOGIN PASSWORD 'your_password_here';
  END IF;
END
$$;
SELECT 'CREATE DATABASE classavo_db OWNER classavo_user'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'classavo_db')\gexec
GRANT ALL PRIVILEGES ON DATABASE classavo_db TO classavo_user;
\c classavo_db
GRANT ALL ON SCHEMA public TO classavo_user;
ALTER SCHEMA public OWNER TO classavo_user;
SQL
```

Confirm both services are up before continuing:
```bash
pg_isready -h 127.0.0.1 -p 5432
redis-cli ping   # expect PONG
```

### 3. Backend setup
```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
```

Edit `.env` and set at minimum:
* `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT` — must match the Postgres role/database you created above.
* `REDIS_URL` — defaults to `redis://127.0.0.1:6379/0`.
* `SECRET_KEY` — a unique Django secret. Generate one with:
  ```bash
  python -c "import secrets; print(secrets.token_urlsafe(50))"
  ```
* `DEBUG` — `True` for local development, `False` in any deployed environment.
* `ALLOWED_HOSTS` — comma-separated hostnames allowed to serve the API (defaults to `localhost,127.0.0.1`).
* `CORS_ALLOWED_ORIGINS` — comma-separated frontend origins allowed to call the API (defaults to `http://localhost:3000`).

The app will refuse to start if `SECRET_KEY` is missing, so this step is not optional.

Then apply migrations, seed demo data, and run the server:
```bash
python manage.py migrate
python manage.py seed_demo
python manage.py runserver
```

Demo logins printed by `seed_demo`:
* Instructor: `demo_instructor` / `password123`
* Student: `demo_student` / `password123`

### 4. Frontend setup
```bash
cd frontend
cp .env.example .env
npm install
npm start
```

* Frontend: [http://localhost:3000](http://localhost:3000)
* Backend API: [http://localhost:8000/api](http://localhost:8000/api)
