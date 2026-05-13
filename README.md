# AI-Powered Code Review & Documentation Assistant

A comprehensive tool that uses LLMs to automate code review, suggest improvements, and generate documentation.

## Architecture

```
├── backend/          # Python FastAPI backend
│   ├── api/          # REST API routes
│   ├── analysis/     # Code analysis engine (AST, metrics)
│   ├── ai/           # AI integration (Claude/GPT)
│   ├── models/       # SQLAlchemy database models
│   ├── services/     # Business logic services
│   └── integrations/ # GitHub, Slack integrations
├── frontend/         # React + TypeScript frontend
│   ├── src/
│   │   ├── components/
│   │   ├── pages/
│   │   ├── hooks/
│   │   └── api/
├── migrations/       # Alembic database migrations
├── .github/          # GitHub Actions workflows
└── docker-compose.yml
```

## Quick Start

### Prerequisites
- Python 3.11+
- Node.js 18+
- Docker & Docker Compose
- PostgreSQL 15+

### Environment Setup

1. Copy environment files:
```bash
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env
```

2. Fill in your API keys in `backend/.env`:
   - `OPENAI_API_KEY` or `ANTHROPIC_API_KEY`
   - `GITHUB_APP_ID`, `GITHUB_APP_PRIVATE_KEY`, `GITHUB_WEBHOOK_SECRET`
   - `SLACK_BOT_TOKEN`, `SLACK_CHANNEL_ID`

### Run with Docker Compose

```bash
docker compose up -d
```

- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs

### Reseed Realistic Demo Data

Use this when you want to reset and repopulate the dashboard with realistic sample reviews/comments.

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\reseed-demo-data.ps1
```

Optional parameters:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\reseed-demo-data.ps1 -DbService db -DbUser codereview -DbName codereview
```

### Full Reset + Reseed (Clean Demo Start)

Use this when you want a guaranteed clean review dataset before every demo run.

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\reseed-demo-data.ps1 -Reset
```

Optional parameters:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\reseed-demo-data.ps1 -Reset -DbService db -DbUser codereview -DbName codereview
```

### Load Validation (1000+ PRs)

Use this script to seed synthetic review data and benchmark list endpoint performance for scale checks.

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\load-validate-1000prs.ps1
```

Optional cleanup run:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\load-validate-1000prs.ps1 -Cleanup
```

### Run Locally

**Backend:**
```bash
cd backend
python -m venv .venv
.venv\Scripts\activate      # Windows
pip install -r requirements.txt
alembic upgrade head
uvicorn main:app --reload --port 8000
```

**Frontend:**
```bash
cd frontend
npm install
npm run dev
```

## Features

- **Automated Code Review**: Security, performance, best practices, edge cases
- **AI-Generated Insights**: Inline comments, suggested fixes with diffs, auto-generated unit tests
- **Documentation Generation**: Markdown docs extracted from code changes
- **Complexity Metrics**: Cyclomatic & cognitive complexity, dependency tracking
- **Dashboard**: Historical code quality trends, per-engineer metrics
- **Integrations**: GitHub webhooks, GitHub Actions, Slack notifications
- **Feedback Loop**: Accept/reject suggestions to improve AI over time

## GitHub Webhook Setup

1. Create a GitHub App or configure webhook in repo Settings → Webhooks
2. Point it to: `https://your-domain/api/webhooks/github`
3. Select events: `Pull requests`, `Pull request reviews`
4. Set the same secret as `GITHUB_WEBHOOK_SECRET`

## Review Profiles

- `pedantic` — Flags everything including style nits
- `balanced` — Default; flags real issues
- `relaxed` — Only critical bugs and security issues

## License

MIT
