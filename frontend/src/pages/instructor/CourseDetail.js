import React, { useEffect, useState, useCallback } from 'react';
import { Link, useParams } from 'react-router-dom';
import api from '../../api/axios';
import './instructor.css';

export default function CourseDetail() {
  const { courseId } = useParams();
  const [course, setCourse] = useState(null);
  const [chapters, setChapters] = useState([]);
  const [loading, setLoading] = useState(true);


  const fetchData = useCallback(async () => {
    try {
      const [courseRes, chaptersRes] = await Promise.all([
        api.get(`/courses/${courseId}/`),
        api.get(`/courses/${courseId}/chapters/`),
      ]);
      setCourse(courseRes.data);
      setChapters(chaptersRes.data);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  }, [courseId]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);
  const handleDeleteChapter = async (chapterId) => {
    if (!window.confirm('Delete this chapter?')) return;
    await api.delete(`/chapters/${chapterId}/`);
    fetchData();
  };

  const handleTogglePublish = async () => {
    await api.put(`/courses/${courseId}/`, { is_published: !course.is_published });
    fetchData();
  };

  if (loading) return <div className="page-container"><p>Loading...</p></div>;
  if (!course) return <div className="page-container"><p>Course not found</p></div>;

  return (
    <div className="page-container">
      <div className="page-header">
        <div>
          <div className="breadcrumb">
            <Link to="/instructor/courses">Courses</Link> / {course.title}
          </div>
          <h1>{course.title}</h1>
          <p className="text-muted">{course.description}</p>
        </div>
        <div className="header-actions">
          <button
            onClick={handleTogglePublish}
            className={course.is_published ? 'btn-secondary' : 'btn-primary'}
          >
            {course.is_published ? 'Unpublish' : 'Publish'}
          </button>
          <Link to={`/instructor/courses/${courseId}/edit`} className="btn-secondary">
            Edit Course
          </Link>
        </div>
      </div>

      <div className="info-bar">
        <span className={`badge ${course.is_published ? 'badge-published' : 'badge-draft'}`}>
          {course.is_published ? 'Published' : 'Draft'}
        </span>
        
        <Link to={`/instructor/courses/${courseId}/students`} className="clickable-link">
          {course.enrolled_count} students enrolled (View all)
        </Link>
        
        <span>{chapters.length} chapters</span>
      </div>

      <div className="section-header">
        <h2>Chapters</h2>
        <Link to={`/instructor/courses/${courseId}/chapters/create`} className="btn-primary">
          + Add Chapter
        </Link>
      </div>

      {chapters.length === 0 ? (
        <div className="empty-state">
          <p>No chapters yet. Add your first chapter to get started.</p>
          <Link to={`/instructor/courses/${courseId}/chapters/create`} className="btn-primary">
            Add Chapter
          </Link>
        </div>
      ) : (
        <div className="chapter-list">
          {chapters.map((chapter, index) => (
            <div className="chapter-item" key={chapter.id}>
              <div className="chapter-left">
                <span className="chapter-number">{index + 1}</span>
                <div>
                  <div className="chapter-title">{chapter.title}</div>
                  <div className="chapter-meta">
                    <span className={`badge ${chapter.visibility === 'public' ? 'badge-public' : 'badge-private'}`}>
                      {chapter.visibility}
                    </span>
                  </div>
                </div>
              </div>
              <div className="chapter-actions">
                <Link to={`/instructor/chapters/${chapter.id}/edit`} className="btn-sm">Edit</Link>
                <button onClick={() => handleDeleteChapter(chapter.id)} className="btn-sm btn-danger">
                  Delete
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}