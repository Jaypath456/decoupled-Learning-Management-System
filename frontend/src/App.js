import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider, useAuth } from './context/AuthContext';
import ProtectedRoute from './components/ProtectedRoute';
import Navbar from './components/Navbar';
import BackButton from './components/BackButton';

// Auth pages
import Login from './pages/auth/Login';
import Register from './pages/auth/Register';

// Instructor pages
import Dashboard from './pages/instructor/Dashboard';
import CourseList from './pages/instructor/CourseList';
import CourseForm from './pages/instructor/CourseForm';
import CourseDetail from './pages/instructor/CourseDetail';
import ChapterForm from './pages/instructor/ChapterForm';
import StudentList from './pages/instructor/StudentList';
import LiveQuizHost from './pages/instructor/LiveQuizHost';
import SectionList from './pages/instructor/SectionList';
import SectionForm from './pages/instructor/SectionForm';

// Student pages
import Catalog from './pages/student/Catalog';
import MyCourses from './pages/student/MyCourses';
import CourseView from './pages/student/CourseView';
import ChapterReader from './pages/student/ChapterReader';
import LiveQuiz from './pages/student/LiveQuiz';
import ScheduleBuilder from './pages/student/ScheduleBuilder';
import ScheduleView from './pages/student/ScheduleView';

import './App.css';

function AppRoutes() {
  const { user } = useAuth();

  return (
    <Routes>
      <Route
        path="/"
        element={
          user
            ? user.role === 'instructor'
              ? <Navigate to="/instructor/dashboard" replace />
              : <Navigate to="/student/catalog" replace />
            : <Navigate to="/login" replace />
        }
      />

      {/* Auth */}
      <Route path="/login" element={<Login />} />
      <Route path="/register" element={<Register />} />

      {/* Instructor routes */}
      <Route path="/instructor/dashboard" element={
        <ProtectedRoute role="instructor"><Dashboard /></ProtectedRoute>
      } />
      <Route path="/instructor/courses" element={
        <ProtectedRoute role="instructor"><CourseList /></ProtectedRoute>
      } />
      <Route path="/instructor/courses/create" element={
        <ProtectedRoute role="instructor"><CourseForm /></ProtectedRoute>
      } />
      <Route path="/instructor/courses/:courseId" element={
        <ProtectedRoute role="instructor"><CourseDetail /></ProtectedRoute>
      } />
      <Route path="/instructor/courses/:courseId/edit" element={
        <ProtectedRoute role="instructor"><CourseForm /></ProtectedRoute>
      } />
      <Route path="/instructor/courses/:courseId/chapters/create" element={
        <ProtectedRoute role="instructor"><ChapterForm /></ProtectedRoute>
      } />
      <Route path="/instructor/chapters/:chapterId/edit" element={
        <ProtectedRoute role="instructor"><ChapterForm /></ProtectedRoute>
      } />
      <Route path="/instructor/courses/:courseId/students" element={
        <ProtectedRoute role="instructor"><StudentList /></ProtectedRoute>
      } />
      <Route path="/instructor/quizzes/:quizId/live" element={
        <ProtectedRoute role="instructor"><LiveQuizHost /></ProtectedRoute>
      } />
      <Route path="/instructor/courses/:courseId/sections" element={
        <ProtectedRoute role="instructor"><SectionList /></ProtectedRoute>
      } />
      <Route path="/instructor/courses/:courseId/sections/create" element={
        <ProtectedRoute role="instructor"><SectionForm /></ProtectedRoute>
      } />
      <Route path="/instructor/sections/:sectionId/edit" element={
        <ProtectedRoute role="instructor"><SectionForm /></ProtectedRoute>
      } />

      {/* Student routes */}
      <Route path="/student/catalog" element={
        <ProtectedRoute role="student"><Catalog /></ProtectedRoute>
      } />
      <Route path="/student/my-courses" element={
        <ProtectedRoute role="student"><MyCourses /></ProtectedRoute>
      } />
      <Route path="/student/courses/:courseId" element={
        <ProtectedRoute role="student"><CourseView /></ProtectedRoute>
      } />
      <Route path="/student/chapters/:chapterId" element={
        <ProtectedRoute role="student"><ChapterReader /></ProtectedRoute>
      } />
      <Route path="/student/live" element={
        <ProtectedRoute role="student"><LiveQuiz /></ProtectedRoute>
      } />
      <Route path="/student/live/:roomCode" element={
        <ProtectedRoute role="student"><LiveQuiz /></ProtectedRoute>
      } />
      <Route path="/student/schedule" element={
        <ProtectedRoute role="student"><ScheduleView /></ProtectedRoute>
      } />
      <Route path="/student/schedule/build" element={
        <ProtectedRoute role="student"><ScheduleBuilder /></ProtectedRoute>
      } />
    </Routes>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        {/* Global UI Components rendered outside of Routes */}
        <Navbar />
        <BackButton />
        <main className="container">
          <AppRoutes />
        </main>
      </AuthProvider>
    </BrowserRouter>
  );
}