import React, { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import api from '../../api/axios';
import './student.css';

export default function CourseView() {
  const { courseId } = useParams();
  const [course, setCourse] = useState(null);
  const [chapters, setChapters] = useState([]);
  const [loading, setLoading] = useState(true);
  const [isEnrolled, setIsEnrolled] = useState(false);
  const [enrolling, setEnrolling] = useState(false);

  useEffect(() => {
    const fetchAll = async () => {
      try {
        const [courseRes, chaptersRes, enrollRes] = await Promise.all([
          api.get(`/courses/${courseId}/`),
          api.get(`/courses/${courseId}/chapters/`),
          api.get(`/courses/${courseId}/enrollment-status/`),
        ]);
        setCourse(courseRes.data);
        setChapters(chaptersRes.data);
        setIsEnrolled(enrollRes.data.enrolled);
      } catch (err) {
        console.error(err);
      } finally {
        setLoading(false);
      }
    };
    fetchAll();
  }, [courseId]);

  const handleEnroll = async () => {
    setEnrolling(true);
    try {
      await api.post(`/courses/${courseId}/enroll/`);
      setIsEnrolled(true);
    } catch (err) {
      if (err.response?.data?.error === 'Already enrolled in this course') {
        setIsEnrolled(true);
      } else {
        alert('Could not join course.');
      }
    } finally {
      setEnrolling(false);
    }
  };

  if (loading) return <div className="page-container"><p>Loading course...</p></div>;
  if (!course) return <div className="page-container"><p>Course not found.</p></div>;

  return (
    <div className="page-container">
      <div className="course-hero">
        <div className="breadcrumb">
          <Link to="/student/catalog">Courses</Link> / {course.title}
        </div>
        <h1>{course.title}</h1>
        <p className="course-hero-desc">{course.description}</p>
        <div className="course-hero-meta">
          <span>instructor:  {course.instructor.username}</span>
          <span> {course.chapter_count} chapters</span>
          <span> {course.enrolled_count} students</span>
        </div>

        {!isEnrolled && (
          <button onClick={handleEnroll} className="btn-primary" disabled={enrolling}>
            {enrolling ? 'Joining...' : 'Join This Course'}
          </button>
        )}
        {isEnrolled && (
          <span className="enrolled-tag"> You're enrolled</span>
        )}
      </div>

      <h2 className="chapters-heading">Chapters</h2>

      {chapters.length === 0 ? (
        <p className="text-muted">No public chapters available yet.</p>
      ) : (
        <div className="chapter-list">
          {chapters.map((chapter, index) => (
            <div className="student-chapter-item" key={chapter.id}>
              <div className="chapter-left">
                <span className="chapter-number">{index + 1}</span>
                <div>
                  <div className="chapter-title">{chapter.title}</div>
                </div>
              </div>
              {isEnrolled ? (
                <Link to={`/student/chapters/${chapter.id}`} className="btn-outline">
                  Read
                </Link>
              ) : (
                <span className="locked-msg">Join to read</span>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
