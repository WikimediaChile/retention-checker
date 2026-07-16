from datetime import date
from typing import List

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi import HTTPException
from pydantic import BaseModel

from retention import analyze_manual_placeholder

from dashboard_api import (
    DashboardApiError,
    get_dashboard_course_preview
)

app = FastAPI(title="Retention Checker API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class DashboardPreviewRequest(BaseModel):
    course_slug: str

class ManualAnalysisRequest(BaseModel):
    usernames: List[str]
    wiki: str
    reference_date: date
    retention_windows: List[int] = [30, 90, 180, 360]
    newbie_threshold_days: int = 60
    reactivation_threshold_days: int = 90
    active_edit_threshold: int = 5
    very_active_edit_threshold: int = 20


@app.get("/")
def read_root():
    return {
        "message": "Retention Checker API is running"
    }


@app.post("/api/analyze/manual")
def analyze_manual(request: ManualAnalysisRequest):
    return analyze_manual_placeholder(request)

@app.post("/api/dashboard/preview")
def preview_dashboard_course(
    request: DashboardPreviewRequest
):
    try:
        return get_dashboard_course_preview(
            request.course_slug
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc)
        ) from exc
    except DashboardApiError as exc:
        raise HTTPException(
            status_code=502,
            detail=str(exc)
        ) from exc