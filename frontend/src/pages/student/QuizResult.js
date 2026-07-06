import React, { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import api from '../../api/axios';
import './student.css';

export default function QuizResult() {
  const { quizId } = useParams();
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(true);
  const [notSubmitted, setNotSubmitted] = useState(false);

  useEffect(() => {
    api.get(`/quizzes/${quizId}/my-result/`)
      .then(res => setResult(res.data))
      .catch(err => {
        if (err.response?.status === 404) {
          setNotSubmitted(true);
        }
      })
      .finally(() => setLoading(false));
  }, [quizId]);

  if (loading) return <div className="page-container"><p>Loading result...</p></div>;

  if (notSubmitted) {
    return (
      <div className="page-container">
        <div className="empty-state">
          <p>You haven't taken this quiz yet.</p>
          <Link to={`/student/quizzes/${quizId}/take`} className="btn-primary">Take Quiz</Link>
        </div>
      </div>
    );
  }

  const percentage = result.max_score > 0
    ? Math.round((result.score / result.max_score) * 100)
    : 0;

  return (
    <div className="page-container">
      <div className="quiz-result-card">
        <h1>Quiz Result</h1>
        <div className="quiz-result-score">
          {result.score} / {result.max_score}
        </div>
        <div className="quiz-result-percentage">{percentage}%</div>
        <p className="text-muted">
          Submitted {new Date(result.submitted_at).toLocaleString()}
        </p>
      </div>
      <Link to="/student/my-courses" className="btn-outline">Back to my courses</Link>
    </div>
  );
}
