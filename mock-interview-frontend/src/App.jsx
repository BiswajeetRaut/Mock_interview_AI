import React from 'react'
import { Routes, Route } from 'react-router-dom'
import Header from './components/Header'
import Landing from './pages/Landing'
import Login from './pages/Login'
import TakeInterview from './pages/TakeInterview'
import InterviewPage from './pages/InterviewPage'
import Results from './pages/Results'
import AskMockGPT from './pages/AskMockGPT'

export default function App() {
  const [user, setUser] = React.useState(null)

  return (
    <div style={{ minHeight: '100vh' }}>
      <Header user={user} setUser={setUser} />
      <main style={{ maxWidth: 1200, margin: '0 auto', padding: '2rem' }}>
        <Routes>
          <Route path="/" element={<Landing user={user} />} />
          <Route path="/login" element={<Login setUser={setUser} />} />
          <Route path="/take-interview" element={<TakeInterview />} />
          <Route path="/interview/:id" element={<InterviewPage />} />
          <Route path="/results" element={<Results />} />
          <Route path="/ask" element={<AskMockGPT />} />
        </Routes>
      </main>
    </div>
  )
}
