# Mock Interview AI Platform

End-to-end mock interview system with:
- **React + Chakra UI frontend**
- **FastAPI backend**
- **Agentic multi-round interview orchestration** (Code / Resume / HR)
- **Resume ingestion + parsing**
- **Coding runner with test-case evaluation**
- **Session scoring + interview report generation**

---

## 1) Product Overview

This platform simulates a realistic interviewer that:
1. Starts an interview session from selected rounds/topics/company/role.
2. Curates next questions dynamically using a supervisor + specialist agents.
3. Captures candidate responses (voice transcript + typed/coding answers).
4. Evaluates each turn and updates strengths/weaknesses continuously.
5. Produces domain scores and an overall recommendation at the end.

The current architecture is optimized for rapid iteration and local development, with optional Redis persistence and LLM-backed generation.  

---

## 2) Repository Structure

```text
mock-interview-backend/
  agents/                   # Specialist + supervisor agent logic and prompts
  models/                   # Pydantic request/response models
  routers/                  # FastAPI route modules
  services/session_engine.py# Core orchestration and scoring pipeline
  main.py                   # FastAPI app bootstrap

mock-interview-frontend/
  src/pages/InterviewPage.jsx
  src/components/CodingPlayground.jsx
  src/api/*.js              # API client wrappers
```

---

## 3) Architecture (Client ↔ Backend ↔ Agentic Pipeline)

```mermaid
flowchart LR
  A[Frontend React App] -->|HTTP JSON| B[FastAPI Routers]
  B --> C[Session Engine]
  C --> D[Supervisor Decision]
  C --> E[Code Agent]
  C --> F[Resume Agent]
  C --> G[HR Agent]
  C --> H[Scoring + Coverage Context]
  C --> I[(Redis/In-Memory Session Store)]
  A -->|/coding/run| J[Coding Runner]
  J --> A
```

### Runtime orchestration summary
- Frontend calls `/session/start`.
- Session engine creates `turn_plan`, generates first question, returns `latest_question`.
- Frontend renders question + live transcript.
- Candidate submits answer via `/session/{id}/answer`.
- Session engine evaluates, asks supervisor for routing decision, generates next question, and updates scores.

---

## 4) Agentic Model Design

### 4.1 Specialist agents
- **Code agent**: technical DSA/system-design prompts and follow-ups.
- **Resume agent**: STAR-style probing using resume summary/topics.
- **HR agent**: behavioral/collaboration evaluation.

### 4.2 Supervisor logic
- Decides whether to:
  - continue in same round,
  - ask follow-up,
  - switch to another round,
  - end interview.
- Uses:
  - current turn quality,
  - candidate “stuck” signals,
  - selected round order/topics,
  - turn limits.

### 4.3 “Multi-model” behavior
- The system is **multi-agent** by default (supervisor + 3 specialists).
- Model provider integration is through shared `build_llm()` abstraction, so you can swap to other providers/models without changing orchestration surface.
- Fallback logic keeps interview flow operational when LLM is unavailable.

---

## 5) Interview Curation + Evaluation Flow

### Curation inputs
- company, role, experience
- selected interview types
- topic preferences
- difficulty
- job description
- resume content (text / url / base64 pdf)

### Curation logic
- Build round sequence from selected types and/or distributions.
- Normalize topics and deduplicate.
- Merge inferred resume topics into `resume-based` round.
- Generate first question pack from active specialist.

### Evaluation logic
- Dimension-based scoring per round (rubric-based).
- Weak/strong tags captured in coverage context.
- Final scores aggregate by domain + overall average.

---

## 6) Coding Experience (LeetCode-style)

When current question is coding:
- Coding panel auto-opens.
- Candidate sees:
  - problem statement,
  - approach hints,
  - examples + explanation,
  - test cases list,
  - solve-function contract.
- Candidate can:
  - choose Python/JavaScript,
  - run tests (`/coding/run`),
  - submit solution to interview session (`/session/{id}/answer` with code payload).

### Solve function contract
- Python: `solve(input_data)`
- JavaScript: `solve(inputData)`
- Must **return** the final output directly.

---

## 7) Resume Ingestion + Topic Extraction

Resume supports:
- `format=text`
- `format=url`
- `format=pdf_base64`

Pipeline:
1. Extract text.
2. Basic parse (skills, etc.).
3. Optional LLM structured enrichment (topics, summary, projects, strengths).
4. Merge enriched topics into interview topic map.
5. Feed resume summary into resume question generation.

---

## 8) API Reference (End-to-End)

## Root
- `GET /` → health message.

## Companies
- `GET /companies/top` → top tech companies.

## Auth
- `POST /auth/google` → creates/returns user profile using Firebase-authenticated context.

## Session (primary interview engine)
- `POST /session/start`
- `POST /session/{session_id}/answer`
- `GET /session/{session_id}/state`
- `POST /session/{session_id}/end`
- `GET /session/{session_id}/report`
- `GET /session/{session_id}/logs`

## Coding runner
- `POST /coding/run`
  - payload: `{ code, language, test_cases[] }`
  - response: `{ total, passed, all_passed, results[] }`

## Legacy interview routes (demo CRUD)
- `/interview/create`
- `/interview/{id}`
- `/interview/{id}/reply`
- `/interview/{id}/complete`

---

## 9) Data & Persistence Model

### Session storage
- Uses Redis when configured (`REDIS_URL`), otherwise in-memory dictionary.
- TTL controlled by `SESSION_TTL_SECONDS`.

### Session object includes
- candidate metadata + parsed resume
- interview config and turn plan
- active question and pending turn id
- full turn history
- coverage context
- final score card

### External databases
- Firebase Firestore is used for user profile persistence in auth flow.

---

## 10) Frontend ↔ Backend Communication

### Client flow
1. Setup page collects config.
2. Frontend calls `/session/start`.
3. Interview page renders `latest_question`.
4. Candidate submits text/voice or code outcome.
5. Frontend polls/refreshes session state and eventually fetches report.

### Payload highlights
- Text answer submission supports optional:
  - `code_submitted`
  - `language`
  - request id for idempotency.

---

## 11) Environment & Setup

### Backend
```bash
cd mock-interview-backend
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

### Frontend
```bash
cd mock-interview-frontend
npm install
npm run dev
```

### Optional env vars
- `GROQ_API_KEY` (LLM generation)
- `REDIS_URL` (session persistence)
- `SESSION_TTL_SECONDS` (cache TTL)

---

## 12) Screenshots

> The environment used for this update did not provide browser screenshot tooling.
> Add real screenshots at these paths when running locally:

- `docs/screenshots/setup-page.png`
- `docs/screenshots/interview-live-panel.png`
- `docs/screenshots/coding-playground-problem.png`
- `docs/screenshots/coding-test-results.png`
- `docs/screenshots/result-report.png`

Markdown references (ready to use):

```md
![Setup](docs/screenshots/setup-page.png)
![Interview Live Panel](docs/screenshots/interview-live-panel.png)
![Coding Playground](docs/screenshots/coding-playground-problem.png)
![Test Results](docs/screenshots/coding-test-results.png)
![Result Report](docs/screenshots/result-report.png)
```

---

## 13) User Guidelines

### Candidate
1. Choose company/role/experience.
2. Select interview rounds and topics.
3. Upload/paste resume if using resume-based rounds.
4. For coding rounds, implement `solve(...)`, run tests, then submit.
5. Complete session and review detailed report.

### Interview designer / recruiter
1. Define topic distributions and selected rounds.
2. Use logs endpoint to inspect routing/debug trace.
3. Evaluate score breakdown and weak/strong indicators.

---

## 14) Developer Notes

- Keep prompt contracts strict JSON.
- Ensure coding test cases are always present for coding rounds.
- Maintain idempotent answer submissions using request ids.
- Add automated tests for:
  - coding runner harnesses,
  - session turn transitions,
  - scoring stability.
