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

// Student pages
import Catalog from './pages/student/Catalog';
import MyCourses from './pages/student/MyCourses';
import CourseView from './pages/student/CourseView';
import ChapterReader from './pages/student/ChapterReader';

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