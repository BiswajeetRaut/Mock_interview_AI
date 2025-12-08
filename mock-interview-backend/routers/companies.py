from fastapi import APIRouter
from data.companies import TOP_100_TECH_COMPANIES

router = APIRouter()

@router.get("/top")
def get_top_companies():
    return {"companies": TOP_100_TECH_COMPANIES}
