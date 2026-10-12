"""End-to-end smoke test of the Growth OS demo flow, through the public API.

Run against a running backend (ideally freshly seeded):

    python scripts/smoke_test.py                 # http://localhost:8000
    python scripts/smoke_test.py http://host:8000

Prints PASS/FAIL per step and exits non-zero if any step fails. Uses only
httpx, which is already a backend dependency.
"""

import sys
import time
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from typing import Any

import httpx

BASE_URL = (sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000").rstrip("/")
ADMIN = ("admin@growthos.dev", "admin123")
OTHER_CLIENT_ID = 1  # a seeded client the new client must not see

results: list[tuple[str, bool, str]] = []
state: dict[str, Any] = {}


class StepFailed(Exception):
    pass


def check(condition: bool, message: str) -> None:
    if not condition:
        raise StepFailed(message)


def call(method: str, path: str, token: str | None = None, expect: int = 200, **kwargs) -> Any:
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    response = httpx.request(method, f"{BASE_URL}/api{path}", headers=headers, timeout=60, **kwargs)
    if response.status_code != expect:
        raise StepFailed(f"{method} {path} -> {response.status_code} (expected {expect}): {response.text[:200]}")
    return response.json() if response.content else None


def login(email: str, password: str) -> str:
    return call("POST", "/auth/login", json={"email": email, "password": password})["access_token"]


def transition(token: str, content_id: int, action: str, expect: int = 200, **extra) -> dict:
    return call("POST", f"/content/{content_id}/transition", token, expect=expect, json={"action": action, **extra})


def step(name: str, fn: Callable[[], str | None]) -> None:
    try:
        detail = fn() or ""
        results.append((name, True, detail))
        print(f"PASS  {name}{f'  ({detail})' if detail else ''}")
    except (StepFailed, httpx.HTTPError, KeyError, IndexError) as exc:
        results.append((name, False, str(exc)))
        print(f"FAIL  {name}\n      {exc}")


# --- 1. Onboard a client ------------------------------------------------------


def onboard_client() -> str:
    admin = login(*ADMIN)
    state["admin"] = admin
    email = f"smoke-{int(time.time())}@founder.example"
    created = call(
        "POST",
        "/clients",
        admin,
        expect=201,
        json={
            "name": "Sam Smoke",
            "title": "Founder & CEO",
            "email": email,
            "company": "Smoke Labs",
            "industry": "B2B SaaS",
            "positioning": "Smoke Labs makes release testing boring.",
            "brand_voice": "Plain, practical, a little dry.",
            "target_audience": "Engineering leaders at growth-stage startups",
            "content_pillars": ["Release engineering", "Founder lessons"],
            "channels": ["linkedin", "x"],
            "posting_cadence": 3,
            "create_login": True,
        },
    )
    check(created["login"] and created["login"]["temp_password"], "no temp password returned")
    client_id = created["client"]["id"]
    state.update(client_id=client_id, client_email=email, client_password=created["login"]["temp_password"])
    for step_key in ("intake", "access", "strategy", "first_batch", "launch"):
        client = call("POST", f"/clients/{client_id}/onboarding", admin, json={"step": step_key, "done": True})
    check(client["status"] == "active", f"client status is {client['status']} after onboarding")
    return f"client #{client_id} live, login {email}"


# --- 2. AI drafts into the approval flow ----------------------------------------


def draft_and_send() -> str:
    admin = state["admin"]
    generated = call(
        "POST",
        "/ai/generate-content",
        admin,
        json={"client_id": state["client_id"], "channel": "linkedin", "count": 3, "topic": "Shipping on Fridays"},
    )
    items = generated["items"]
    check(len(items) == 3, f"expected 3 drafts, got {len(items)}")
    check(all(i["status"] == "draft" and i["ai_generated"] for i in items), "AI output must land as draft")
    first, second, _ = (item["id"] for item in items)
    check(transition(admin, first, "submit")["status"] == "internal_review", "submit failed")
    check(transition(admin, first, "send_to_client")["status"] == "client_review", "send_to_client failed")
    # Fast path straight from draft, so the client has two posts to review.
    check(transition(admin, second, "send_to_client")["status"] == "client_review", "fast-path send failed")
    state.update(approve_id=first, change_id=second)
    return f"source={generated['source']}, sent #{first} and #{second}"


# --- 3. Client approves and requests changes -------------------------------------


def client_reviews() -> str:
    client = login(state["client_email"], state["client_password"])
    state["client"] = client
    inbox = call("GET", "/approvals", client)
    waiting = {item["id"] for item in inbox["client_review"]}
    check({state["approve_id"], state["change_id"]} <= waiting, "posts missing from the client inbox")
    check(transition(client, state["approve_id"], "approve")["status"] == "approved", "client approve failed")
    transition(client, state["change_id"], "request_changes", expect=400)  # note is required
    changed = transition(client, state["change_id"], "request_changes", note="Make the hook punchier.")
    check(changed["status"] == "changes_requested", "request_changes failed")
    return "approved one, requested changes on one"


# --- 4. Team revises, approves on behalf, schedules, publishes ---------------------


def team_finishes() -> str:
    admin = state["admin"]
    piece = state["change_id"]
    for action, expected in (("revise", "draft"), ("send_to_client", "client_review"), ("approve", "approved")):
        check(transition(admin, piece, action)["status"] == expected, f"{action} failed")
    slot = (datetime.now(UTC) + timedelta(days=2)).isoformat()
    check(transition(admin, piece, "schedule", scheduled_at=slot)["status"] == "scheduled", "schedule failed")
    published = transition(admin, piece, "publish")
    check(published["status"] == "published" and published["published_at"], "publish failed")
    transition(admin, state["approve_id"], "publish")
    actions = [event["action"] for event in published["events"]]
    check(actions.count("approve") == 1 and "request_changes" in actions, "audit trail incomplete")
    return f"#{piece} published with {len(actions)} audit events"


# --- 5. Metrics and a lead from the post -------------------------------------------


def metrics_and_lead() -> str:
    admin = state["admin"]
    piece = state["change_id"]
    synced = call("POST", f"/content/{piece}/sync-metrics", admin)
    check(synced["method"] == "simulated" and synced["item"]["metrics"]["impressions"] > 0, "metrics sync failed")
    lead = call(
        "POST",
        "/leads",
        admin,
        expect=201,
        json={
            "client_id": state["client_id"],
            "content_id": piece,
            "name": "Dana Prospect",
            "title": "VP Engineering",
            "company": "Prospect Co",
            "source": "content",
            "deal_value": 24000,
        },
    )
    moved = call("PATCH", f"/leads/{lead['id']}", admin, json={"stage": "meeting_booked"})
    check(moved["stage"] == "meeting_booked", "lead stage not updated")
    return f"+{synced['delta']['impressions']} impressions, lead #{lead['id']} at meeting_booked"


# --- 6. Impact and report ------------------------------------------------------------


def impact_and_report() -> str:
    admin = state["admin"]
    client_id = state["client_id"]
    impact = call("GET", f"/clients/{client_id}/impact", admin)
    check({"kpis", "funnel", "top_posts", "leads"} <= impact.keys(), "impact payload incomplete")
    check(impact["leads"]["total"] == 1, "new lead missing from impact")
    report = call("GET", f"/clients/{client_id}/report?days=30", admin)
    check(report["summary"] and len(report["next_steps"]) == 3, "report summary missing")
    check(report["highlights"]["posts_published"] == 2, "report should count both published posts")
    return f"summary source={report['summary_source']}"


# --- 7. Tenant isolation ---------------------------------------------------------------


def isolation() -> str:
    client = state["client"]
    for path in (
        f"/clients/{OTHER_CLIENT_ID}",
        f"/content?client_id={OTHER_CLIENT_ID}",
        f"/leads?client_id={OTHER_CLIENT_ID}",
        f"/clients/{OTHER_CLIENT_ID}/report",
    ):
        call("GET", path, client, expect=403)
    call("GET", "/dashboard", client, expect=403)
    return "403 on another client's client, content, leads and report"


def main() -> int:
    print(f"Growth OS smoke test against {BASE_URL}\n")
    try:
        health = httpx.get(f"{BASE_URL}/api/health", timeout=10).json()
    except httpx.HTTPError as exc:
        print(f"FAIL  backend not reachable: {exc}")
        return 1
    print(f"health: {health}\n")

    step("1. Admin creates a client with a login and completes onboarding", onboard_client)
    step("2. Admin generates 3 AI drafts, submits one and sends to the client", draft_and_send)
    step("3. Client approves one and requests changes on another", client_reviews)
    step("4. Team revises, re-sends, approves on behalf, schedules and publishes", team_finishes)
    step("5. Team syncs metrics and moves a lead from the post to meeting_booked", metrics_and_lead)
    step("6. Team fetches the impact and report endpoints", impact_and_report)
    step("7. Client gets 403 on another client's data", isolation)

    failed = [name for name, ok, _ in results if not ok]
    print(f"\n{len(results) - len(failed)}/{len(results)} steps passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
