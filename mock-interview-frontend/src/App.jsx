import React from 'react'
import { Routes, Route, useLocation } from 'react-router-dom'
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

export default function App() {
  const [user, setUser] = React.useState(null)
  const location = useLocation();
  const hideHeader = location.pathname.startsWith("/interview");
  return (
    <div style={{ minHeight: '100vh' }}>
      {!hideHeader && <Header user={user} setUser={setUser} />}
      <main style={{ margin: '0 auto', padding: '5px' }}>
        <Routes>
          <Route path="/" element={<Landing user={user} />} />
          <Route path="/login" element={<Login setUser={setUser} />} />
          <Route path="/take-interview" element={<TakeInterviewSelectCompany user={user} />} />
          <Route path="/take-interview/known" element={<TakeInterviewKnown />} />
          <Route path="/take-interview/custom" element={<TakeInterviewCustom />} />
          <Route path="/take-interview/custom-advanced" element={<CustomAdvancedSetup />} />
          <Route path="/interview/:id" element={<InterviewPage />} />
          <Route path="/results" element={<Results />} />
          <Route path="/ask" element={<AskMockGPT />} />
        </Routes>
      </main>
    </div>
  )
}
