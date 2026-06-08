import React, { useState, useEffect } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import api from '../../api/axios';
import PlateEditor, { emptyDocument } from '../../components/PlateEditor';
import './instructor.css';

export default function ChapterForm() {
  const { courseId, chapterId } = useParams();
  const isEditing = Boolean(chapterId);
  const navigate = useNavigate();

  const [form, setForm] = useState({
    title: '',
    visibility: 'private',
    order_index: 0,
  });
  const [chapterCourseId, setChapterCourseId] = useState(courseId || '');
  const [content, setContent] = useState(emptyDocument);
  const [loading, setLoading] = useState(false);
  const [loadingChapter, setLoadingChapter] = useState(isEditing);
  const [error, setError] = useState('');
  
  // NEW: State to track if the form has been modified
  const [isDirty, setIsDirty] = useState(false);

  useEffect(() => {
    if (isEditing) {
      api.get(`/chapters/${chapterId}/`)
        .then(res => {
          setForm({
            title: res.data.title,
            visibility: res.data.visibility,
            order_index: res.data.order_index,
          });
          setChapterCourseId(res.data.course);
          if (res.data.content && res.data.content.length > 0) {
            setContent(res.data.content);
          }
        })
        .catch(() => setError('Could not load chapter'))
        .finally(() => setLoadingChapter(false));
    }
  }, [chapterId, isEditing]);

  // NEW: Effect to handle browser refresh/close warnings
  useEffect(() => {
    const handleBeforeUnload = (e) => {
      if (isDirty) {
        e.preventDefault();
        e.returnValue = ''; // Standard browser way to trigger the "Leave site?" prompt
      }
    };
    window.addEventListener('beforeunload', handleBeforeUnload);
    return () => window.removeEventListener('beforeunload', handleBeforeUnload);
  }, [isDirty]);

  const handleChange = (e) => {
    setForm({ ...form, [e.target.name]: e.target.value.trim() });
    setIsDirty(true); // Mark form as modified
  };

  const handleContentChange = (newContent) => {
    setContent(newContent);
    setIsDirty(true); // Mark form as modified when editor content changes
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    const payload = { ...form, content };

    try {
      if (isEditing) {
        await api.put(`/chapters/${chapterId}/`, payload);
        setIsDirty(false); // Reset so warning doesn't show
        navigate(`/instructor/courses/${courseId || chapterCourseId}`);
      } else {
        await api.post(`/courses/${courseId}/chapters/create/`, payload);
        setIsDirty(false); // Reset so warning doesn't show
        navigate(`/instructor/courses/${courseId}`);
      }
    } catch (err) {
      setError('Failed to save chapter.');
    } finally {
      setLoading(false);
    }
  };

  const handleCancel = () => {
    if (isDirty && !window.confirm('You have unsaved changes. Are you sure you want to cancel?')) {
      return;
    }
    setIsDirty(false);
    navigate(-1);
  };

  return (
    <div className="page-container">
      <div className="page-header">
        <h1>{isEditing ? 'Edit Chapter' : 'New Chapter'}</h1>
      </div>

      {error && <div className="error-msg">{error}</div>}

      {loadingChapter ? (
        <p>Loading chapter...</p>
      ) : (
      <form onSubmit={handleSubmit}>
        <div className="form-card">
          <div className="form-row">
            <div className="form-group" style={{ flex: 2 }}>
              <label>Chapter Title *</label>
              <input
                type="text"
                name="title"
                value={form.title}
                onChange={handleChange}
                placeholder="Enter your chapter title..."
                required
              />
            </div>

            <div className="form-group">
              <label>Visibility</label>
              <select name="visibility" value={form.visibility} onChange={handleChange}>
                <option value="private">Private</option>
                <option value="public">Public</option>
              </select>
            </div>

            <div className="form-group" style={{ width: '100px' }}>
              <label>Order</label>
              <input
                type="number"
                name="order_index"
                value={form.order_index}
                onChange={handleChange}
                min="0"
              />
            </div>
          </div>

          <div className="form-group">
            <label>Content</label>
            <p className="form-hint">
              Use the toolbar to format your content. Supports headings, bold, italic, lists, and more.
            </p>
            <PlateEditor
              value={content}
              onChange={handleContentChange} // Use wrapper to mark dirty
            />
          </div>
        </div>

        <div className="form-actions">
          <button type="button" onClick={handleCancel} className="btn-secondary">
            Cancel
          </button>
          <button type="submit" className="btn-primary" disabled={loading}>
            {loading ? 'Saving...' : isEditing ? 'Save Changes' : 'Create Chapter'}
          </button>
        </div>
      </form>
      )}
    </div>
  );
}