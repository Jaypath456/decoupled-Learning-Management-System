import React from 'react';
import { Link, useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import './Navbar.css';

export default function Navbar() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  const isActive = (path) => location.pathname.startsWith(path);

  if (!user) return null;

  return (
    <nav className="navbar">
      <div className="navbar-left">
        <span className="navbar-brand">Classavo</span>
        {user.role === 'instructor' ? (
          <div className="navbar-links">
            <Link to="/instructor/dashboard" className={isActive('/instructor/dashboard') ? 'active' : ''}>
              Dashboard
            </Link>
            <Link to="/instructor/courses" className={isActive('/instructor/courses') ? 'active' : ''}>
              My Courses
            </Link>
          </div>
        ) : (
          <div className="navbar-links">
            <Link to="/student/catalog" className={isActive('/student/catalog') ? 'active' : ''}>
              Browse Courses
            </Link>
            <Link to="/student/my-courses" className={isActive('/student/my-courses') ? 'active' : ''}>
              My Learning
            </Link>
            <Link to="/student/live" className={isActive('/student/live') ? 'active' : ''}>
              Join Live Quiz
            </Link>
          </div>
        )}
      </div>

      <div className="navbar-right">
        <span className="user-badge">{user.username}</span>
        <button className="logout-btn" onClick={handleLogout}>Logout</button>
      </div>
    </nav>
  );
}
