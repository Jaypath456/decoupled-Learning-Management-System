import React, { useEffect, useRef, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import PlateEditor from '../../components/PlateEditor';
import LiveBarChart from '../../components/LiveBarChart';
import { ReconnectingSocket } from '../../api/ws';
import './student.css';

// The whole point of this page: the client never decides what to show
// - it renders whatever the server's last event said. 'view' is set
// directly from server events (session.state / question.revealed /
// answer.accepted / session.ended), never inferred client-side.
export default function LiveQuiz() {
  const { roomCode: roomCodeParam } = useParams();
  const navigate = useNavigate();

  const [roomCodeInput, setRoomCodeInput] = useState('');
  const [roomCode, setRoomCode] = useState(roomCodeParam || null);
  const [view, setView] = useState('connecting'); // connecting|waiting|question|chart|ended|error
  const [question, setQuestion] = useState(null);
  const [chartCounts, setChartCounts] = useState({});
  const [selectedOptions, setSelectedOptions] = useState([]);
  const [shortAnswer, setShortAnswer] = useState('');
  const [error, setError] = useState('');
  const socketRef = useRef(null);

  useEffect(() => {
    if (!roomCode) return;

    setView('connecting');
    const socket = new ReconnectingSocket(`/ws/live/${roomCode}/`, {
      onOpen: () => setError(''),
      onMessage: (event) => {
        const data = JSON.parse(event.data);
        handleServerEvent(data);
      },
      onError: () => setError('Connection lost. Reconnecting...'),
      onClose: (event) => {
        // 4001/4003/4004 are the backend's application close codes for
        // auth/membership/room failures (see quizzes/consumers.py).
        if ([4001, 4003, 4004].includes(event.code)) {
          setView('error');
          setError('Could not join this room. Check the code and that you are enrolled in the course.');
        }
      },
    });
    socketRef.current = socket;

    return () => socket.close();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [roomCode]);

  const handleServerEvent = (data) => {
    if (data.error) {
      setError(data.error);
      return;
    }

    switch (data.type) {
      case 'session.state':
        if (data.status === 'ended') {
          setView('ended');
        } else if (data.question) {
          setQuestion(data.question);
          setChartCounts(data.chart || {});
          // A reconnecting client can't tell from this event alone
          // whether it already answered - the server doesn't track
          // that in this snapshot, so default to the question view;
          // if they already answered, resubmitting is a harmless
          // idempotent no-op (see quizzes/consumers.py).
          setView('question');
          resetAnswerState();
        } else {
          setView('waiting');
        }
        break;
      case 'question.revealed':
        setQuestion(data.question);
        setChartCounts({});
        resetAnswerState();
        setView('question');
        break;
      case 'answer.accepted':
        setView('chart');
        break;
      case 'chart.update':
        setChartCounts(data.counts);
        break;
      case 'session.ended':
        setView('ended');
        break;
      default:
        break;
    }
  };

  const resetAnswerState = () => {
    setSelectedOptions([]);
    setShortAnswer('');
  };

  const handleJoinSubmit = (e) => {
    e.preventDefault();
    const trimmed = roomCodeInput.trim().toUpperCase();
    if (!trimmed) return;
    navigate(`/student/live/${trimmed}`);
    setRoomCode(trimmed);
  };

  const handleToggleOption = (optionId) => {
    if (question.question_type === 'single_choice') {
      setSelectedOptions([optionId]);
    } else {
      setSelectedOptions(prev =>
        prev.includes(optionId) ? prev.filter(id => id !== optionId) : [...prev, optionId]
      );
    }
  };

  const handleSubmitAnswer = (e) => {
    e.preventDefault();
    const answer = question.question_type === 'short_answer' ? shortAnswer.trim() : selectedOptions;
    socketRef.current?.send({ type: 'answer.submit', question_id: question.id, answer });
  };

  if (!roomCode) {
    return (
      <div className="page-container">
        <div className="form-card" style={{ maxWidth: 360, margin: '40px auto' }}>
          <h1>Join a Live Quiz</h1>
          <form onSubmit={handleJoinSubmit}>
            <div className="form-group">
              <label>Room Code</label>
              <input
                type="text"
                value={roomCodeInput}
                onChange={(e) => setRoomCodeInput(e.target.value)}
                placeholder="e.g. ABC123"
                autoFocus
              />
            </div>
            <button type="submit" className="btn-primary" style={{ width: '100%' }}>
              Join
            </button>
          </form>
        </div>
      </div>
    );
  }

  return (
    <div className="page-container">
      <div className="live-quiz-room-badge">Room {roomCode}</div>
      {error && <div className="error-msg">{error}</div>}

      {view === 'connecting' && <p className="text-muted">Connecting...</p>}

      {view === 'waiting' && (
        <div className="live-waiting-screen">
          <div className="live-waiting-spinner" />
          <h2>Waiting for the instructor...</h2>
          <p className="text-muted">The quiz will begin shortly.</p>
        </div>
      )}

      {view === 'question' && question && (
        <div className="form-card">
          <div className="quiz-question-prompt">
            <PlateEditor value={question.body.prompt} readOnly />
          </div>

          <form onSubmit={handleSubmitAnswer}>
            {question.question_type === 'short_answer' ? (
              <input
                type="text"
                className="quiz-short-answer-input"
                value={shortAnswer}
                onChange={(e) => setShortAnswer(e.target.value)}
                placeholder="Your answer"
                autoFocus
              />
            ) : (
              <div className="quiz-options">
                {(question.body.options || []).map(option => (
                  <label className="quiz-option-row" key={option.id}>
                    <input
                      type={question.question_type === 'single_choice' ? 'radio' : 'checkbox'}
                      name="live-question-option"
                      checked={selectedOptions.includes(option.id)}
                      onChange={() => handleToggleOption(option.id)}
                    />
                    {option.text}
                  </label>
                ))}
              </div>
            )}
            <div className="form-actions">
              <button type="submit" className="btn-primary">Submit Answer</button>
            </div>
          </form>
        </div>
      )}

      {view === 'chart' && question && (
        <div className="form-card">
          <p className="text-muted">Answer submitted! Here's how everyone's answering:</p>
          <LiveBarChart question={question} counts={chartCounts} />
        </div>
      )}

      {view === 'ended' && (
        <div className="empty-state">
          <p>This live quiz session has ended. Thanks for playing!</p>
        </div>
      )}
    </div>
  );
}
