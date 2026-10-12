# Decisions

Choices made where the brief or ARCHITECTURE.md left something open. One line each.

## Data model
- Datetimes are stored as naive UTC (SQLite has no tz type); the API always returns them with a `Z` suffix.
- `Client` gains `title`, `email`, `website` and `positioning`: the brand profile needs positioning, and the client post preview needs name + title.
- `ContentPiece.status_changed_at` records when a piece entered its current status; it drives "waiting for" times and auto-approve.
- `ContentPiece.ai_source` stores which generator wrote a draft (`llm:anthropic`, `llm:openai`, `template`).
- Onboarding step keys: `intake`, `access`, `strategy`, `first_batch`, `launch` (labels match the doc's five steps).
- Campaign KPI targets are limited to `posts`, `impressions`, `engagements`, `leads`, `meetings`, because progress for those can be computed from our own data.
- `MetricSnapshot.profile_views` is included because section 9 lists it.
- SQLite foreign keys are switched on per connection so `ON DELETE CASCADE` works locally as it will on Postgres.

## Tooling
- `pytest` lives in `backend/requirements-dev.txt` so production installs stay lean.
- Frontend runtime dependencies are only `react` and `react-dom`; the Vite template's dev tooling (`@vitejs/plugin-react`, `@types/*`, `oxlint`) is kept for building and linting.
- The default dev `JWT_SECRET` is 32+ bytes so PyJWT does not warn; it must still be replaced outside local dev.

## Seed data
- Seed dates are relative to the moment it runs, so the demo always looks current; randomness uses a fixed seed (42) so data shapes are repeatable.
- Fictional companies use the reserved `.example` domain; prospects and clients are invented names.
- Onboarding clients with 3+ steps done get a "first batch" of three pieces (draft, internal review, client review); earlier ones have no content yet.
- LedgerLoop (client1) has 48h auto-approve on and one piece waiting 60h, so auto-approve fires the first time a queue or dashboard loads.
- Seed post bodies come from the same frameworks as the AI template fallback (`app/post_templates.py`), so seeded and generated drafts read consistently.
