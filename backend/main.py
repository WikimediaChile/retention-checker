from datetime import date
from typing import List

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from retention import analyze_manual_placeholder

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