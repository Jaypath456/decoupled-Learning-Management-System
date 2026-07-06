import React, { useEffect, useRef, useState } from 'react';
import { useParams } from 'react-router-dom';
import api from '../../api/axios';
import { ReconnectingSocket } from '../../api/ws';
import LiveBarChart from '../../components/LiveBarChart';
import Leaderboard from '../../components/Leaderboard';
import './instructor.css';

export default function LiveQuizHost() {
  const { quizId } = useParams();

  const [session, setSession] = useState(null); // { room_code, status, ... }
  const [question, setQuestion] = useState(null);
  const [questionIndex, setQuestionIndex] = useState(-1);
  const [chartCounts, setChartCounts] = useState({});
  const [leaderboard, setLeaderboard] = useState([]);
  const [ended, setEnded] = useState(false);
  const [error, setError] = useState('');
  const [creating, setCreating] = useState(false);
  const socketRef = useRef(null);

  useEffect(() => {
    return () => socketRef.current?.close();
  }, []);

  const connectSocket = (roomCode) => {
    const socket = new ReconnectingSocket(`/ws/live/${roomCode}/`, {
      onMessage: (event) => {
        const data = JSON.parse(event.data);
        handleServerEvent(data);
      },
      onError: () => setError('Connection lost. Reconnecting...'),
    });
    socketRef.current = socket;
  };

  const handleServerEvent = (data) => {
    if (data.error) {
      setError(data.error);
      return;
    }
    switch (data.type) {
      case 'session.state':
        setQuestionIndex(data.question_index);
        if (data.leaderboard) setLeaderboard(data.leaderboard);
        if (data.question) {
          setQuestion(data.question);
          setChartCounts(data.chart || {});
        }
        break;
      case 'question.revealed':
        setQuestion(data.question);
        setQuestionIndex(data.question_index);
        setChartCounts({});
        setError('');
        break;
      case 'chart.update':
        setChartCounts(data.counts);
        break;
      case 'leaderboard.update':
        setLeaderboard(data.rankings);
        break;
      case 'session.ended':
        setEnded(true);
        break;
      default:
        break;
    }
  };

  const handleCreateSession = async () => {
    setCreating(true);
    setError('');
    try {
      const res = await api.post(`/quizzes/${quizId}/sessions/`);
      setSession(res.data);
    } catch (err) {
      setError('Could not create a live session for this quiz.');
    } finally {
      setCreating(false);
    }
  };

  const handleStartSession = async () => {
    try {
      const res = await api.post(`/sessions/${session.room_code}/start/`);
      setSession(res.data);
      connectSocket(session.room_code);
    } catch (err) {
      setError('Could not start the session.');
    }
  };

  const handleAdvance = () => {
    socketRef.current?.send({ type: 'question.advance' });
  };

  const handleEnd = () => {
    socketRef.current?.send({ type: 'session.end' });
  };

  const totalResponses = Object.values(chartCounts).reduce((sum, n) => sum + n, 0);

  if (!session) {
    return (
      <div className="page-container">
        <h1>Go Live</h1>
        <p className="text-muted">Start a live (Mentimeter-style) session for this quiz.</p>
        {error && <div className="error-msg">{error}</div>}
        <button className="btn-primary" onClick={handleCreateSession} disabled={creating}>
          {creating ? 'Creating...' : 'Create Live Session'}
        </button>
      </div>
    );
  }

  if (session.status === 'lobby') {
    return (
      <div className="page-container">
        <h1>Session Created</h1>
        <div className="live-room-code-display">{session.room_code}</div>
        <p className="text-muted">
          Share this code with your students. They can join at /student/live/{session.room_code}.
        </p>
        {error && <div className="error-msg">{error}</div>}
        <button className="btn-primary" onClick={handleStartSession}>
          Start Session
        </button>
      </div>
    );
  }

  if (ended) {
    return (
      <div className="page-container">
        <div className="empty-state">
          <p>Session {session.room_code} has ended.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="page-container">
      <div className="live-quiz-room-badge">Room {session.room_code} · Live</div>
      {error && <div className="error-msg">{error}</div>}

      {!question ? (
        <div className="form-card">
          <p className="text-muted">No question revealed yet.</p>
          <button className="btn-primary" onClick={handleAdvance}>
            Reveal First Question
          </button>
        </div>
      ) : (
        <div className="form-card">
          <div className="chapter-meta" style={{ marginBottom: 10 }}>
            <span className="badge badge-private">Question {questionIndex + 1}</span>
            <span className="text-muted" style={{ marginLeft: 8 }}>{totalResponses} response(s)</span>
          </div>
          <LiveBarChart question={question} counts={chartCounts} />
          <div className="form-actions">
            <button className="btn-primary" onClick={handleAdvance}>
              Next Question
            </button>
          </div>
        </div>
      )}

      <div className="form-card">
        <Leaderboard rankings={leaderboard} />
      </div>

      <div className="form-actions" style={{ marginTop: 20 }}>
        <button className="btn-secondary btn-danger" onClick={handleEnd}>
          End Session
        </button>
      </div>
    </div>
  );
}
