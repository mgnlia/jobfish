# 🐟 JobFish — Autonomous Job Application Agent

> Apply to hundreds of jobs while you sleep. Powered by [TinyFish Web Agent API](https://tinyfish.ai).

Built for the **TinyFish $2M Pre-Accelerator Hackathon** (March 2026).

## What It Does

JobFish is a fully autonomous web agent that:
1. **Searches** real job boards (Indeed, LinkedIn, Greenhouse, Lever) for matching positions
2. **Reads** each job posting and determines fit
3. **Fills out** multi-step application forms autonomously
4. **Streams** a live browser view so you can watch the agent work in real-time
5. **Reports** application status, confirmation IDs, and any blockers

## Architecture

```
Frontend (Next.js)          Backend (FastAPI + uv)
┌─────────────────┐         ┌──────────────────────┐
│  Resume Form    │──POST──▶│  /api/autopilot      │
│  Job Prefs      │         │  /api/search-jobs    │
│  Live Stream    │◀─SSE───│  /api/apply          │
│  App History    │         │  /api/applications   │
└─────────────────┘         └──────────┬───────────┘
                                        │ SSE stream
                             ┌──────────▼───────────┐
                             │  TinyFish Web Agent  │
                             │  agent.tinyfish.ai   │
                             │  (real browser runs) │
                             └──────────────────────┘
```

## Key Feature: Live Browser View

TinyFish returns a `STREAMING_URL` — a live view of the agent's browser session. JobFish embeds this directly in the dashboard so you can watch the agent navigate job boards and fill forms in real time.

## Setup

### Backend
```bash
cd backend
uv sync
TINYFISH_API_KEY=your_key uvicorn main:app --reload
```

### Frontend
```bash
cd frontend
npm install
NEXT_PUBLIC_API_URL=http://localhost:8000 npm run dev
```

## Deploy

- **Backend**: Railway (`railway up` from `/backend`)
- **Frontend**: Vercel (`vercel --prod` from `/frontend`)

## Environment Variables

| Variable | Description |
|----------|-------------|
| `TINYFISH_API_KEY` | Get from [tinyfish.ai](https://tinyfish.ai) |
| `NEXT_PUBLIC_API_URL` | Backend URL (Railway URL in prod) |

## Hackathon Submission

- Platform: HackerEarth — TinyFish Hackathon 2026
- Demo: [YouTube link TBD]
- X post: [@Tiny_fish TBD]
