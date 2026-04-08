from fastapi import FastAPI
from routers import interview, companies, auth, session
from fastapi.middleware.cors import CORSMiddleware
from routers.interview import router as interview_router

app = FastAPI(title="Mock Interview Backend", version="1.0")

# CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
# app.include_router(interview.router, prefix="/interview", tags=["Interviews"])
app.include_router(interview_router, prefix="/interview", tags=["interview"])
app.include_router(companies.router, prefix="/companies", tags=["Companies"])
app.include_router(auth.router, prefix="/auth", tags=["Auth"])
app.include_router(session.router, prefix="/session", tags=["Session"])


@app.get("/")
def root():
    return {"message": "Mock Interview API is running!"}
