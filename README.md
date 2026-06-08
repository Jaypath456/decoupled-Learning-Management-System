# Classavo LMS

A Learning Management System built for Classavo.

## Tech Stack

- **Backend:** Django, Django REST Framework, SimpleJWT
- **Frontend:** React, React Router, Plate.js, Axios
- **Database:** PostgreSQL

## Features

### Instructor

- Register and log in as an instructor
- Create, edit, publish, unpublish, and delete courses
- Create, edit, and delete chapters inside a course
- Write chapter content with a Plate.js rich text editor
- Mark each chapter as public or private
- View enrollment counts and access a detailed list of enrolled students with contact details
- "Save as Draft" functionality for form progress

### Student

- Register and log in as a student
- Browse published courses
- Join/Unenroll from a published course
- View joined courses
- Read public chapters from courses they have joined
- Private chapters and unjoined course content are restricted by backend permissions

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