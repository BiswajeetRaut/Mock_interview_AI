from fastapi import FastAPI
from routers import interview, companies, auth
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Mock Interview Backend", version="1.0")

# CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(interview.router, prefix="/interview", tags=["Interviews"])
app.include_router(companies.router, prefix="/companies", tags=["Companies"])
app.include_router(auth.router, prefix="/auth", tags=["Auth"])


@app.get("/")
def root():
    return {"message": "Mock Interview API is running!"}
