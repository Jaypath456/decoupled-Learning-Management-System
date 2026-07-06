import React from 'react';
import './Leaderboard.css';

// Shared by the live session views (fed by WS leaderboard.update events)
// and the persistent course leaderboard page (fed by a single REST
// fetch) - one rendering path for both, same principle as
// WeeklyScheduleCalendar/LiveBarChart elsewhere in this app.
export default function Leaderboard({ rankings = [], title = 'Leaderboard' }) {
  return (
    <div className="leaderboard">
      <h3 className="leaderboard-title">{title}</h3>
      {rankings.length === 0 ? (
        <p className="text-muted">No scores yet.</p>
      ) : (
        <ol className="leaderboard-list">
          {rankings.map(entry => (
            <li className="leaderboard-row" key={entry.user_id}>
              <span className="leaderboard-rank">#{entry.rank}</span>
              <span className="leaderboard-username">{entry.username}</span>
              <span className="leaderboard-score">{entry.score} pts</span>
            </li>
          ))}
        </ol>
      )}
    </div>
  );
}
