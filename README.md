# Growth OS

Growth OS is the client portal for a done-for-you growth agency. The agency team runs content marketing, personal branding, lead generation and SEO/GEO for busy founders and executives. Clients don't do the work: they approve content and see results. Strategists use the portal to draft, review, schedule and report. Clients use it to approve, request changes and follow their growth.

> **Status:** project skeleton only. The features below are planned, not built yet. See the [roadmap](#roadmap).

## Planned modules

| Module | What it does |
| --- | --- |
| **Client onboarding** | Captures each client's goals, audience, channels and voice. |
| **Content & personal branding** | AI drafts posts and articles in the client's own voice. |
| **Approval layer** | Team review → client approves or requests changes → schedule → publish. Optional auto-approve per client. |
| **Campaigns** | Groups content and outreach around one goal. |
| **Lead generation pipeline** | Tracks leads from first touch to booked call. |
| **Performance marketing** | SEO keyword tracking plus GEO: visibility in AI-assistant answers. |
| **Impact dashboards & monthly reports** | Shows clients what the work produced, with a monthly report. |

## Roles

| Role | Who | Can do |
| --- | --- | --- |
| `admin` | Agency owner / ops | Everything: users, clients, settings. |
| `strategist` | Agency team | Onboard clients, draft and review content, run campaigns, leads and SEO/GEO, prepare reports. |
| `client` | Founder or executive | Approve content or request changes, and view results. Nothing else. |

## Tech stack

| Layer | Technology |
| --- | --- |
| Backend | Python 3.11+, FastAPI, Uvicorn |
| ORM / database | SQLAlchemy 2.0; SQLite for local dev, Postgres later via `DATABASE_URL` |
| Auth | PyJWT |
| Config | python-dotenv |
| HTTP client | httpx (for AI provider and third-party APIs) |
| Frontend | React + TypeScript + Vite |
| Repo layout | Monorepo: `backend/` and `frontend/` |

## Project structure

```text
growth-os/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py          # FastAPI app, CORS, GET /api/health
│   │   ├── config.py        # Settings loaded from environment / .env
│   │   ├── database.py      # SQLAlchemy engine, SessionLocal, Base, get_db
│   │   ├── models.py        # ORM models (placeholder)
│   │   └── routers/
│   │       └── __init__.py
│   ├── requirements.txt     # Pinned backend dependencies
│   └── .env.example         # Template for backend/.env
├── frontend/                # React + TypeScript + Vite
│   ├── vite.config.ts       # Dev server proxies /api -> http://localhost:8000
│   └── src/
│       └── App.tsx          # Minimal page that calls /api/health
├── docs/
│   └── ARCHITECTURE.md
├── .gitignore
├── LICENSE
└── README.md
```

## Local setup

Prerequisites: Python 3.11+, Node.js 20.19+ (or 22.12+) with npm, and Git.

```bash
git clone https://github.com/KapilPushkar/growth-os.git
cd growth-os
```

### Backend (terminal 1)

**macOS / Linux**

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload --port 8000
```

**Windows (PowerShell)**

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
uvicorn app.main:app --reload --port 8000
```

> If PowerShell blocks `Activate.ps1`, run `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` once, then activate again.

### Frontend (terminal 2)

Same on macOS, Linux and Windows:

```bash
cd frontend
npm install
npm run dev
```

The frontend runs at http://localhost:5173. Its dev server forwards `/api/*` to the backend on port 8000.

### Check it works

- http://localhost:8000/docs: interactive API docs. `GET /api/health` should return `{"status": "ok", "db": "ok"}`. The endpoint runs `SELECT 1`, so `db: ok` means the database answered.
- http://localhost:5173: the Growth OS page, showing `status: ok · db: ok`.

## Environment variables

Set these in `backend/.env`. Copy them from `backend/.env.example`.

| Name | Purpose | Default |
| --- | --- | --- |
| `DATABASE_URL` | SQLAlchemy database URL. Use a Postgres URL in production. | `sqlite:///./growth_os.db` |
| `JWT_SECRET` | Secret for signing auth tokens. **Change it outside local dev.** | `dev-only-change-me` |
| `ANTHROPIC_API_KEY` | Anthropic API key for AI content generation. | *(blank)* |
| `OPENAI_API_KEY` | OpenAI API key for AI content generation. | *(blank)* |
| `CORS_ORIGINS` | Comma-separated list of origins allowed to call the API. | `http://localhost:5173` |

## Roadmap

- [x] Repo & skeleton
- [ ] Data model & auth
- [ ] Clients & onboarding
- [ ] Content + approval workflow
- [ ] AI content generation
- [ ] Campaigns
- [ ] Leads
- [ ] SEO/GEO
- [ ] Dashboards & reports
- [ ] Seed data (12 demo clients)

## Architecture

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

## License

[MIT](LICENSE) © 2026 Kapil Pushkar
