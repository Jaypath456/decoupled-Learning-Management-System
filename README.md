# Classavo LMS

A Learning Management System built for Classavo.

## Tech Stack

- **Backend:** Django, Django REST Framework, SimpleJWT
- **Frontend:** React, React Router, Plate.js, Axios
- **Database:** PostgreSQL

## Project Structure

```text
backend/
  lms_project/      Django project settings and URLs
  users/            Custom user model, auth endpoints, serializers
  courses/          Course, chapter, enrollment models and APIs

frontend/
  src/
    api/            Axios API client
    components/     Navbar, protected routes, Plate editor, BackButton
    context/        Auth state
    pages/          Auth, instructor, and student screens
    utils/          Form helper utilities
```

## Setup Instructions

### 1. Backend

```bash
cd backend
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate

# macOS/Linux:
source venv/bin/activate

pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

The API runs at:
```
http://localhost:8000
```

### 2. Frontend

```bash
cd frontend
npm install
npm start
```

The React app runs at:
```
http://localhost:3000
```

## Configuration

This project uses environment variables to manage the API connection, ensuring the application remains environment-agnostic.

- Create a `.env` file in the `frontend/` directory.
- Copy the contents of `.env.example` into your new `.env` file.
- Set `REACT_APP_API_URL` to your backend endpoint (e.g., `http://localhost:8000/api`).

## Key Features

### Instructor

- Course Management: Create, publish/unpublish, and manage course lifecycles.
- Content Creation: Utilize the Plate.js rich-text editor for detailed chapter content.
- Reporting: View real-time enrollment counts and generate detailed student lists.
- Form Intelligence: Built-in "Save as Draft" functionality for course/chapter forms, powered by sessionStorage.

### Student

- Catalog Browsing: View and search published courses.
- Enrollment: Join or unenroll from courses seamlessly.
- Access Control: Content access is strictly enforced by backend permissions—only enrolled students can read chapter content.

## API Highlights

- Parallel Data Fetching: Frontend uses `Promise.all` to fetch course, chapter, and enrollment data concurrently, reducing load time.
- Role-Based Access Control (RBAC): All API endpoints are protected using JWT authentication and custom permission classes.
- Dirty-State Tracking: Custom hooks detect unsaved changes to prevent accidental data loss.