from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.schemas import DailyBriefingResponse, MorningCheckInRequest
from app.workflow.graph import run_morning_check_in

app = FastAPI(
    title="Agentic Fitness Supervisor API",
    description="Multi-agent RAG workflow for adaptive fitness coaching.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/check-ins/simulate", response_model=DailyBriefingResponse)
def simulate_morning_check_in(payload: MorningCheckInRequest) -> DailyBriefingResponse:
    return run_morning_check_in(payload)

