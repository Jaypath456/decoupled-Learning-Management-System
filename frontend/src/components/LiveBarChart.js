import React from 'react';
import './LiveBarChart.css';

// Renders the live per-question counts pushed by chart.update events.
// Mirrors the backend's two bucket schemes (quizzes/consumers.py):
//   single_choice/multiple_choice -> one bucket per option id
//   short_answer                 -> a simple correct/incorrect tally
export default function LiveBarChart({ question, counts = {} }) {
  if (!question) return null;

  const isChoice = question.question_type === 'single_choice' || question.question_type === 'multiple_choice';
  const buckets = isChoice
    ? (question.body?.options || []).map(opt => ({ id: opt.id, label: opt.text }))
    : [
        { id: 'correct', label: 'Correct' },
        { id: 'incorrect', label: 'Incorrect' },
      ];

  const total = Object.values(counts).reduce((sum, n) => sum + n, 0);
  const maxCount = Math.max(1, ...buckets.map(b => counts[b.id] || 0));

  return (
    <div className="live-bar-chart">
      {buckets.map(bucket => {
        const count = counts[bucket.id] || 0;
        const widthPct = Math.round((count / maxCount) * 100);
        return (
          <div className="live-bar-row" key={bucket.id}>
            <div className="live-bar-label">{bucket.label}</div>
            <div className="live-bar-track">
              <div className="live-bar-fill" style={{ width: `${widthPct}%` }} />
              <span className="live-bar-count">{count}</span>
            </div>
          </div>
        );
      })}
      <div className="live-bar-total text-muted">{total} response{total === 1 ? '' : 's'}</div>
    </div>
  );
}
