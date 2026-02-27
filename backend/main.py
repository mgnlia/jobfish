import asyncio
import json
import os
import sqlite3
import uuid
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Optional

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

TINYFISH_API_KEY = os.getenv("TINYFISH_API_KEY", "")
TINYFISH_URL = "https://agent.tinyfish.ai/v1/automation/run-sse"
DB_PATH = os.getenv("DB_PATH", "jobfish.db")


# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------

def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS jobs (
            id TEXT PRIMARY KEY,
            title TEXT,
            company TEXT,
            location TEXT,
            apply_url TEXT,
            board TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS applications (
            id TEXT PRIMARY KEY,
            job_id TEXT,
            status TEXT DEFAULT 'pending',
            streaming_url TEXT,
            result_json TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="JobFish API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

class SearchRequest(BaseModel):
    query: str
    location: str = "Remote"
    boards: list[str] = ["linkedin", "indeed"]


class ApplyRequest(BaseModel):
    job_id: str
    job_url: str
    resume_data: dict


# ---------------------------------------------------------------------------
# Mock data (used when TINYFISH_API_KEY is not set)
# ---------------------------------------------------------------------------

MOCK_JOBS = [
    {"id": str(uuid.uuid4()), "title": "Senior Software Engineer", "company": "Acme Corp", "location": "Remote", "apply_url": "https://example.com/apply/1", "board": "linkedin"},
    {"id": str(uuid.uuid4()), "title": "Full Stack Developer", "company": "TechStart", "location": "San Francisco, CA", "apply_url": "https://example.com/apply/2", "board": "indeed"},
    {"id": str(uuid.uuid4()), "title": "Backend Engineer (Python)", "company": "DataFlow", "location": "New York, NY", "apply_url": "https://example.com/apply/3", "board": "linkedin"},
    {"id": str(uuid.uuid4()), "title": "AI/ML Engineer", "company": "NeuralWorks", "location": "Remote", "apply_url": "https://example.com/apply/4", "board": "greenhouse"},
]


async def mock_sse_stream(events: list[dict]) -> AsyncGenerator[str, None]:
    for event in events:
        yield f"data: {json.dumps(event)}\n\n"
        await asyncio.sleep(0.3)


# ---------------------------------------------------------------------------
# TinyFish helpers
# ---------------------------------------------------------------------------

async def call_tinyfish_sse(url: str, goal: str) -> AsyncGenerator[dict, None]:
    """Stream SSE events from TinyFish API."""
    if not TINYFISH_API_KEY:
        # Mock mode
        mock_events = [
            {"event": "STARTED", "runId": str(uuid.uuid4())},
            {"event": "STREAMING_URL", "streamingUrl": "https://example.com/stream/mock"},
            {"event": "PROGRESS", "message": "Navigating to job board..."},
            {"event": "PROGRESS", "message": "Extracting job listings..."},
            {"event": "COMPLETE", "resultJson": json.dumps(MOCK_JOBS[:2])},
        ]
        for event in mock_events:
            yield event
            await asyncio.sleep(0.2)
        return

    async with httpx.AsyncClient(timeout=120) as client:
        async with client.stream(
            "POST",
            TINYFISH_URL,
            headers={"X-API-Key": TINYFISH_API_KEY, "Content-Type": "application/json"},
            json={"url": url, "goal": goal},
        ) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    try:
                        yield json.loads(line[6:])
                    except json.JSONDecodeError:
                        pass


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.get("/health")
async def health():
    return {"status": "ok", "mock_mode": not bool(TINYFISH_API_KEY)}


@app.post("/api/search-jobs")
async def search_jobs(req: SearchRequest):
    """Search job boards via TinyFish and return structured listings."""
    boards_str = ", ".join(req.boards)
    goal = (
        f"Search for '{req.query}' jobs in '{req.location}' on {boards_str}. "
        "Extract title, company, location, and direct apply link as a JSON array."
    )
    target_url = f"https://www.linkedin.com/jobs/search/?keywords={req.query.replace(' ', '+')}&location={req.location.replace(' ', '+')}"

    jobs = []
    run_id = None
    streaming_url = None

    async for event in call_tinyfish_sse(target_url, goal):
        etype = event.get("event")
        if etype == "STARTED":
            run_id = event.get("runId", str(uuid.uuid4()))
        elif etype == "STREAMING_URL":
            streaming_url = event.get("streamingUrl")
        elif etype == "COMPLETE":
            result = event.get("resultJson", "[]")
            try:
                raw = json.loads(result) if isinstance(result, str) else result
                if isinstance(raw, list):
                    jobs = raw
            except Exception:
                jobs = MOCK_JOBS

    # Persist to DB
    conn = sqlite3.connect(DB_PATH)
    for job in jobs:
        jid = job.get("id") or str(uuid.uuid4())
        conn.execute(
            "INSERT OR REPLACE INTO jobs (id, title, company, location, apply_url, board) VALUES (?,?,?,?,?,?)",
            (jid, job.get("title",""), job.get("company",""), job.get("location",""), job.get("apply_url",""), job.get("board", boards_str)),
        )
    conn.commit()
    conn.close()

    return {"run_id": run_id, "streaming_url": streaming_url, "jobs": jobs, "mock_mode": not bool(TINYFISH_API_KEY)}


@app.post("/api/apply")
async def apply_to_job(req: ApplyRequest):
    """Use TinyFish agent to fill out a job application form."""
    resume = req.resume_data
    goal = (
        f"Fill out the job application form at this URL. "
        f"Applicant name: {resume.get('name', 'Jane Doe')}. "
        f"Email: {resume.get('email', 'applicant@example.com')}. "
        f"Phone: {resume.get('phone', '555-0100')}. "
        f"Submit the form when complete and return the confirmation details."
    )

    app_id = str(uuid.uuid4())
    streaming_url = None
    result = None

    async for event in call_tinyfish_sse(req.job_url, goal):
        etype = event.get("event")
        if etype == "STREAMING_URL":
            streaming_url = event.get("streamingUrl")
        elif etype == "COMPLETE":
            result = event.get("resultJson")

    # Persist application
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        "INSERT INTO applications (id, job_id, status, streaming_url, result_json) VALUES (?,?,?,?,?)",
        (app_id, req.job_id, "submitted", streaming_url, json.dumps(result)),
    )
    conn.commit()
    conn.close()

    return {"application_id": app_id, "status": "submitted", "streaming_url": streaming_url, "result": result, "mock_mode": not bool(TINYFISH_API_KEY)}


@app.get("/api/status/{run_id}")
async def stream_status(run_id: str):
    """SSE endpoint — streams TinyFish events to frontend for a given run."""
    async def event_generator():
        # In production, retrieve the stored streaming_url for run_id and proxy events.
        # For now, emit a status heartbeat.
        yield f"data: {json.dumps({'run_id': run_id, 'status': 'active'})}\n\n"
        await asyncio.sleep(1)
        yield f"data: {json.dumps({'run_id': run_id, 'status': 'complete'})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@app.get("/api/applications")
async def list_applications():
    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute("SELECT id, job_id, status, streaming_url, created_at FROM applications ORDER BY created_at DESC LIMIT 50").fetchall()
    conn.close()
    return [{"id": r[0], "job_id": r[1], "status": r[2], "streaming_url": r[3], "created_at": r[4]} for r in rows]


@app.get("/api/jobs")
async def list_jobs():
    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute("SELECT id, title, company, location, apply_url, board, created_at FROM jobs ORDER BY created_at DESC LIMIT 100").fetchall()
    conn.close()
    return [{"id": r[0], "title": r[1], "company": r[2], "location": r[3], "apply_url": r[4], "board": r[5], "created_at": r[6]} for r in rows]
