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

## Workflow and API
- `revise` also moves an `idea` to `draft` (the doc's idea → draft edge had no named action).
- `schedule` is allowed from `scheduled` too, so a slot can be moved; `request_changes` on a scheduled piece clears its date.
- Clients get 404 (not 403) for their own internal drafts: they should not learn those exist.
- Clients also see their `changes_requested` items in the approvals inbox, read-only, so they know what is being revised.
- Clients may edit only voice, tone, audience, pillars, topics to avoid, goals and auto-approve hours; on leads only notes.
- A piece counts as "stuck" for the health score after 48h in `client_review`.
- "Posts published this week" on the dashboard means the last 7 days, not since Monday.
- Report periods use weekly snapshots: `weeks = round(days / 7)`, compared with the same number of weeks before.
- Services raise domain errors (400/403/404/409) that `main.py` turns into JSON responses, so `services.py` has no FastAPI dependency.
- Read-side computations live in `analytics.py`, separate from the write rules in `services.py`.
- Creating a lead from a post increments that post's `leads_generated`.

## AI layer
- `ANTHROPIC_MODEL` defaults to `claude-opus-5-5`; `AI_EFFORT` (default `low`) sets Anthropic reasoning effort so interactive generation stays fast.
- Anthropic requests opt into server-side refusal fallbacks (`fallbacks: "default"`); a `refusal` stop reason, like any other failure, falls back to templates.
- Every AI function catches all exceptions and falls back to templates, so no AI endpoint can return a 500.
- Template output is deterministic per client, day and request, so demos are repeatable but drafts change day to day.
- Live GEO checks map `claude` to Anthropic and `chatgpt` to OpenAI; `gemini` and `perplexity` are always simulated, weighted by the client's latest AI-visibility snapshot.
- GEO checks ask the buyer's question without the brand brief (the point is to see if the assistant names the client unprompted).
- AI keyword ideas are suggestions only; the team adds them with `POST /keywords/bulk`. Volumes from templates are labelled as estimates.
- Repurposing creates a new draft linked to the same campaign and keyword; the original is unchanged.
- Report summaries return `summary`, `next_steps` and `summary_source` alongside the report data.
