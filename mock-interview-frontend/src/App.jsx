import React from 'react'
import { Routes, Route, useLocation, Navigate } from 'react-router-dom'
import Header from './components/Header'
import Landing from './pages/Landing'
import Login from './pages/Login'
import InterviewPage from './pages/InterviewPage'
import Results from './pages/Results'
import AskMockGPT from './pages/AskMockGPT'
import TakeInterviewKnown from './pages/TakeInterviewKnown'
import TakeInterviewCustom from './pages/TakeInterviewCustom'
import TakeInterviewSelectCompany from './pages/TakeInterviewSelectCompany'
import CustomAdvancedSetup from './pages/CustomAdvancedSetup'
import ResultDetails from './pages/ResultDetails'
import { useAuth } from './context/AuthContext'

// The backend now requires a verified token on every /session/* call
// (P2-102/103) — these are the pages that create or read a session. Landing
// already redirected its own CTAs to /login when signed out; this makes
// that the same rule everywhere, including direct navigation to the URL.
function RequireAuth({ children }) {
  const { isAuthenticated } = useAuth()
  const location = useLocation()
  if (!isAuthenticated) {
    return <Navigate to="/login" replace state={{ from: location }} />
  }
  return children
}

export default function App() {
  const location = useLocation();
  const hideHeader = location.pathname.startsWith("/interview");
  return (
    <div style={{ minHeight: '100vh' }}>
      {!hideHeader && <Header />}
      <main style={{ margin: '0 auto', padding: '5px' }}>
        <Routes>
          <Route path="/" element={<Landing />} />
          <Route path="/login" element={<Login />} />
          <Route path="/take-interview" element={<RequireAuth><TakeInterviewSelectCompany /></RequireAuth>} />
          <Route path="/take-interview/known" element={<RequireAuth><TakeInterviewKnown /></RequireAuth>} />
          <Route path="/take-interview/custom" element={<RequireAuth><TakeInterviewCustom /></RequireAuth>} />
          <Route path="/take-interview/custom-advanced" element={<RequireAuth><CustomAdvancedSetup /></RequireAuth>} />
          <Route path="/interview/:id" element={<RequireAuth><InterviewPage /></RequireAuth>} />
          <Route path="/results" element={<Results />} />
          <Route path="/result-details" element={<ResultDetails />} />
          <Route path="/ask" element={<AskMockGPT />} />
        </Routes>
      </main>
    </div>
  )
}
