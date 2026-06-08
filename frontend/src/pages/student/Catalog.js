import React, { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import api from '../../api/axios';
import './student.css';

export default function Catalog() {
  const [courses, setCourses] = useState([]);
  const [loading, setLoading] = useState(true);
  const [enrolling, setEnrolling] = useState(null);
  const navigate = useNavigate();

  useEffect(() => {
    api.get('/courses/')
      .then(res => setCourses(res.data))
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  const handleEnroll = async (courseId) => {
    setEnrolling(courseId);
    try {
      await api.post(`/courses/${courseId}/enroll/`);
      navigate('/student/my-courses');
    } catch (err) {
      if (err.response?.data?.error === 'Already enrolled in this course') {
        navigate('/student/my-courses');
      } else {
        alert('Could not enroll. Please try again.');
      }
    } finally {
      setEnrolling(null);
    }
  };

  return (
    <div className="page-container">
      <div className="page-header">
        <div>
          <h1>Browse Courses</h1>
          <p className="text-muted">Find a course to start learning</p>
        </div>
      </div>

      {loading ? (
        <p>Loading courses...</p>
      ) : courses.length === 0 ? (
        <div className="empty-state">
          <p>No courses available right now. Check back soon!</p>
        </div>
      ) : (
        <div className="course-grid">
          {courses.map(course => (
            <div className="course-card" key={course.id}>
              <div className="course-card-instructor">
                by {course.instructor.username}
              </div>
              <h3>{course.title}</h3>
              <p className="course-description">
                {course.description || 'No description provided.'}
              </p>
              <div className="course-card-footer">
                <div className="course-stats">
                  <span> {course.chapter_count} chapters</span>
                  <span> {course.enrolled_count} students</span>
                </div>
                <div className="card-btns">
                  <Link to={`/student/courses/${course.id}`} className="btn-outline">
                    Preview
                  </Link>
                  <button
                    onClick={() => handleEnroll(course.id)}
                    className="btn-primary"
                    disabled={enrolling === course.id}
                  >
                    {enrolling === course.id ? 'Joining...' : 'Join Course'}
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
