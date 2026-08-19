import os

from fastapi import FastAPI
from routers import companies, auth, session, coding
from fastapi.middleware.cors import CORSMiddleware
from routers.interview import router as interview_router

app = FastAPI(title="Mock Interview Backend", version="1.0")

# CORS — explicit origin list only. "*" must never sit in this list alongside
# allow_credentials=True: that combination is invalid per the CORS spec (a
# wildcard can't be paired with credentials) and browsers reject it
# inconsistently. ALLOWED_ORIGINS is a comma-separated env var; defaults to
# the two local dev ports so `npm run dev` keeps working out of the box.
_default_origins = "http://localhost:5173,http://localhost:3000"
ALLOWED_ORIGINS = [
    origin.strip()
    for origin in os.getenv("ALLOWED_ORIGINS", _default_origins).split(",")
    if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(interview_router, prefix="/interview", tags=["interview"])
app.include_router(coding.router, prefix="/coding", tags=["Coding"])
app.include_router(companies.router, prefix="/companies", tags=["Companies"])
app.include_router(auth.router, prefix="/auth", tags=["Auth"])
app.include_router(session.router, prefix="/session", tags=["Session"])


@app.get("/")
def root():
    return {"message": "Mock Interview API is running!"}
