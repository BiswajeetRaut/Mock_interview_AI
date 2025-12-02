export const api = {
    signInWithGoogle: async () => new Promise(res => setTimeout(() => res({ id: 'user_1', name: 'Demo User', email: 'demo@example.com' }), 700)),
    createInterview: async (payload) => new Promise(res => setTimeout(() => res({ id: 'int_' + Date.now(), ...payload }), 600)),
    fetchResults: async () => new Promise(res => setTimeout(() => res([
      { id: 'res_1', company: 'Acme Corp', role: 'SWE', date: '2025-11-01', score: 78 }
    ]), 500)),
    askMockGPT: async (q) => new Promise(res => setTimeout(() => res({ answer: `MockGPT answer to: ${q}` }), 700)),
  }
  