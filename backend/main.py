"""JobFish — Autonomous Job Application Agent powered by TinyFish Web Agent API"""
import asyncio
import json
import os
import sqlite3
import uuid
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Optional, AsyncGenerator

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

DB_PATH = os.getenv("DB_PATH", "jobfish.db")
TINYFISH_API_KEY = os.getenv("TINYFISH_API_KEY", "")
TINYFISH_URL = "https://agent.tinyfish.ai/v1/automation/run-sse"


def init_db():
    con = sqlite3.connect(DB_PATH)
    con.execute("""CREATE TABLE IF NOT EXISTS applications (
        id TEXT PRIMARY KEY,
        status TEXT,
        job_url TEXT,
        job_title TEXT,
        company TEXT,
        applicant TEXT,
        created_at TEXT,
        result TEXT,
        error TEXT
    )""")
    con.execute("""CREATE TABLE IF NOT EXISTS job_searches (
        id TEXT PRIMARY KEY,
        board TEXT,
        query TEXT,
        created_at TEXT,
        results TEXT
    )""")
    con.commit()
    con.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="JobFish API", version="1.0.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Models ────────────────────────────────────────────────────────────────────

class ResumeProfile(BaseModel):
    full_name: str
    email: str
    phone: str
    location: str
    linkedin_url: Optional[str] = None
    github_url: Optional[str] = None
    years_experience: int
    skills: list[str]
    summary: str
    education: str
    most_recent_role: str
    most_recent_company: str


class JobPreferences(BaseModel):
    job_titles: list[str]
    locations: list[str]
    remote_ok: bool = True
    min_salary: Optional[int] = None
    job_boards: list[str] = ["greenhouse", "lever", "indeed"]
    max_applications: int = 5


class ApplicationRequest(BaseModel):
    profile: ResumeProfile
    preferences: JobPreferences
    job_url: Optional[str] = None


class JobSearchRequest(BaseModel):
    preferences: JobPreferences


# ── TinyFish SSE streaming ────────────────────────────────────────────────────

async def tinyfish_stream(url: str, goal: str) -> AsyncGenerator[dict, None]:
    """Stream SSE events from TinyFish Web Agent API."""
    if not TINYFISH_API_KEY:
        raise HTTPException(500, "TINYFISH_API_KEY not configured")
    async with httpx.AsyncClient(timeout=300) as client:
        async with client.stream(
            "POST", TINYFISH_URL,
            headers={"X-API-Key": TINYFISH_API_KEY, "Content-Type": "application/json"},
            json={"url": url, "goal": goal, "proxy_config": {"enabled": True}},
        ) as r:
            if r.status_code != 200:
                body = await r.aread()
                raise HTTPException(r.status_code, f"TinyFish error: {body.decode()}")
            async for line in r.aiter_lines():
                if line.startswith("data: "):
                    try:
                        yield json.loads(line[6:])
                    except json.JSONDecodeError:
                        pass


# ── Goal builders ─────────────────────────────────────────────────────────────

def build_search_goal(p: JobPreferences) -> str:
    titles = ", ".join(p.job_titles)
    locs = ", ".join(p.locations)
    remote = "Remote OK" if p.remote_ok else "On-site only"
    salary = f"\n- Minimum salary: ${p.min_salary:,}" if p.min_salary else ""
    return f"""Search for job openings matching these criteria:
- Job titles: {titles}
- Locations: {locs}
- Work arrangement: {remote}{salary}

For each job found, extract and return as a JSON array of objects with fields:
  title, company, location, application_url, description (1 sentence), posted_date

Find up to {p.max_applications} relevant positions. Return ONLY a valid JSON array."""


def build_apply_goal(profile: ResumeProfile, title: str, company: str) -> str:
    skills = ", ".join(profile.skills[:8])
    linkedin = f"\n- LinkedIn: {profile.linkedin_url}" if profile.linkedin_url else ""
    github = f"\n- GitHub: {profile.github_url}" if profile.github_url else ""
    return f"""Apply for the {title} position at {company}.

Fill the application form with these details:
- Full Name: {profile.full_name}
- Email: {profile.email}
- Phone: {profile.phone}
- Location: {profile.location}{linkedin}{github}
- Years of Experience: {profile.years_experience}
- Current/Most Recent Role: {profile.most_recent_role} at {profile.most_recent_company}
- Key Skills: {skills}

For cover letter or "tell us about yourself" fields, use:
"{profile.summary}"

Education: {profile.education}

Steps:
1. Navigate to the application form
2. Fill ALL required fields with the data above
3. Leave optional unlisted fields blank
4. Review and click Submit/Apply
5. Return JSON: {{ "success": bool, "confirmation_id": "...", "message": "..." }}

STOP and report if you encounter a CAPTCHA or mandatory login wall."""


# ── Routes ────────────────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    return {"status": "ok", "service": "JobFish", "version": "1.0.0"}


@app.post("/api/search-jobs")
async def search_jobs(req: JobSearchRequest):
    """Search a job board for matching positions using TinyFish agent."""
    board_urls = {
        "greenhouse": "https://boards.greenhouse.io",
        "lever": "https://jobs.lever.co",
        "indeed": "https://www.indeed.com/jobs",
        "linkedin": "https://www.linkedin.com/jobs/search",
        "workday": "https://www.myworkdayjobs.com",
    }
    board = req.preferences.job_boards[0] if req.preferences.job_boards else "indeed"
    url = board_urls.get(board, "https://www.indeed.com/jobs")
    search_id = str(uuid.uuid4())
    results = []

    async for event in tinyfish_stream(url, build_search_goal(req.preferences)):
        if event.get("type") == "COMPLETE" and event.get("status") == "COMPLETED":
            r = event.get("resultJson", [])
            results = r if isinstance(r, list) else r.get("jobs", []) if isinstance(r, dict) else []

    con = sqlite3.connect(DB_PATH)
    con.execute(
        "INSERT INTO job_searches VALUES (?,?,?,?,?)",
        (search_id, board, ", ".join(req.preferences.job_titles),
         datetime.utcnow().isoformat(), json.dumps(results)),
    )
    con.commit()
    con.close()
    return {"search_id": search_id, "board": board, "jobs": results, "count": len(results)}


@app.post("/api/apply")
async def apply_to_job(req: ApplicationRequest):
    """Apply to a specific job URL. Streams SSE progress events."""
    if not req.job_url:
        raise HTTPException(400, "job_url is required")

    job_id = str(uuid.uuid4())
    con = sqlite3.connect(DB_PATH)
    con.execute(
        "INSERT INTO applications VALUES (?,?,?,?,?,?,?,?,?)",
        (job_id, "running", req.job_url, "", "", req.profile.full_name,
         datetime.utcnow().isoformat(), None, None),
    )
    con.commit()
    con.close()

    goal = build_apply_goal(req.profile, "the position", "the company")

    async def stream():
        yield f"data: {json.dumps({'type': 'JOB_STARTED', 'jobId': job_id})}\n\n"
        try:
            async for event in tinyfish_stream(req.job_url, goal):
                yield f"data: {json.dumps(event)}\n\n"
                if event.get("type") == "COMPLETE":
                    ok = event.get("status") == "COMPLETED"
                    c = sqlite3.connect(DB_PATH)
                    c.execute(
                        "UPDATE applications SET status=?, result=? WHERE id=?",
                        ("completed" if ok else "failed", json.dumps(event.get("resultJson")), job_id),
                    )
                    c.commit()
                    c.close()
        except Exception as e:
            yield f"data: {json.dumps({'type': 'ERROR', 'message': str(e)})}\n\n"
            c = sqlite3.connect(DB_PATH)
            c.execute("UPDATE applications SET status='error', error=? WHERE id=?", (str(e), job_id))
            c.commit()
            c.close()

    return StreamingResponse(
        stream(), media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.post("/api/autopilot")
async def autopilot(req: ApplicationRequest):
    """Full autopilot: search for jobs then apply to each. Streams SSE progress."""
    session_id = str(uuid.uuid4())
    board_urls = {
        "greenhouse": "https://boards.greenhouse.io",
        "lever": "https://jobs.lever.co",
        "indeed": "https://www.indeed.com/jobs",
        "linkedin": "https://www.linkedin.com/jobs/search",
    }

    async def stream():
        yield f"data: {json.dumps({'type': 'SESSION_STARTED', 'sessionId': session_id})}\n\n"

        board = req.preferences.job_boards[0] if req.preferences.job_boards else "indeed"
        search_url = board_urls.get(board, "https://www.indeed.com/jobs")
        yield f"data: {json.dumps({'type': 'SEARCHING', 'board': board})}\n\n"

        found = []
        try:
            async for event in tinyfish_stream(search_url, build_search_goal(req.preferences)):
                yield f"data: {json.dumps({'type': 'SEARCH_PROGRESS', 'event': event})}\n\n"
                if event.get("type") == "COMPLETE" and event.get("status") == "COMPLETED":
                    r = event.get("resultJson", [])
                    found = r if isinstance(r, list) else r.get("jobs", []) if isinstance(r, dict) else []
        except Exception as e:
            yield f"data: {json.dumps({'type': 'SEARCH_ERROR', 'message': str(e)})}\n\n"
            return

        yield f"data: {json.dumps({'type': 'JOBS_FOUND', 'count': len(found), 'jobs': found})}\n\n"

        if not found:
            yield f"data: {json.dumps({'type': 'COMPLETE', 'status': 'NO_JOBS_FOUND'})}\n\n"
            return

        applied = 0
        for i, job in enumerate(found[: req.preferences.max_applications]):
            job_url = job.get("application_url") or job.get("url", "")
            if not job_url:
                continue
            title = job.get("title", "Position")
            company = job.get("company", "Company")
            yield f"data: {json.dumps({'type': 'APPLYING', 'jobIndex': i + 1, 'jobTitle': title, 'company': company})}\n\n"
            try:
                async for event in tinyfish_stream(job_url, build_apply_goal(req.profile, title, company)):
                    yield f"data: {json.dumps({'type': 'APP_PROGRESS', 'jobIndex': i + 1, 'event': event})}\n\n"
                    if event.get("type") == "COMPLETE":
                        ok = event.get("status") == "COMPLETED"
                        if ok:
                            applied += 1
                        yield f"data: {json.dumps({'type': 'APP_DONE', 'jobIndex': i + 1, 'success': ok, 'result': event.get('resultJson')})}\n\n"
            except Exception as e:
                yield f"data: {json.dumps({'type': 'APP_ERROR', 'jobIndex': i + 1, 'message': str(e)})}\n\n"
            await asyncio.sleep(2)

        yield f"data: {json.dumps({'type': 'SESSION_COMPLETE', 'applied': applied, 'attempted': min(req.preferences.max_applications, len(found))})}\n\n"

    return StreamingResponse(
        stream(), media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.get("/api/applications")
async def list_applications():
    con = sqlite3.connect(DB_PATH)
    rows = con.execute("SELECT * FROM applications ORDER BY created_at DESC").fetchall()
    con.close()
    keys = ["id", "status", "job_url", "job_title", "company", "applicant", "created_at", "result", "error"]
    return {"applications": [dict(zip(keys, r)) for r in rows]}
