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

## ⚙️ Local Setup & Installation

### 1. Clone the repository
```bash
git clone [https://github.com/Jaypath456/decoupled-Learning-Management-System.git](https://github.com/Jaypath456/decoupled-Learning-Management-System.git)
cd decoupled-Learning-Management-System