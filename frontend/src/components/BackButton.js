import { useNavigate, useLocation } from 'react-router-dom';

export default function BackButton() {
  const navigate = useNavigate();
  const location = useLocation();

  if (location.pathname === '/student/catalog' || location.pathname === '/instructor/dashboard') {
    return null;
  }

  return (
    <button className="btn-back" onClick={() => navigate(-1)}>
      ← Back
    </button>
  );
}