"""The AI layer works with no keys and never fails a request."""

from dataclasses import replace

import httpx
import pytest

from app import ai
from app.models import Lead
from tests.conftest import auth


@pytest.fixture
def team_and_client(make_user, make_client):
    client, client_user = make_client()
    return make_user("strategist"), client, client_user


def test_status_reports_template_mode(api, team_and_client):
    team, _, _ = team_and_client

    assert api.get("/api/ai/status", headers=auth(team)).json() == {
        "provider": "none",
        "model": None,
        "mode": "template",
    }


def test_generate_content_saves_drafts_from_templates(api, team_and_client):
    team, client, _ = team_and_client

    response = api.post(
        "/api/ai/generate-content",
        headers=auth(team),
        json={"client_id": client.id, "channel": "x", "format": "thread", "topic": "Hiring", "count": 3},
    )

    body = response.json()
    assert response.status_code == 200
    assert body["source"] == "template"
    assert len(body["items"]) == 3
    for item in body["items"]:
        assert item["status"] == "draft"
        assert item["ai_generated"] is True
        assert item["ai_source"] == "template"
        assert item["body"].startswith("1/")
    assert len({item["body"] for item in body["items"]}) == 3


@pytest.mark.parametrize(
    ("path", "payload", "key"),
    [
        ("/api/ai/topics", {"count": 4}, "topics"),
        ("/api/ai/keywords", {"seed": "workflow automation", "count": 5}, "keywords"),
    ],
)
def test_idea_endpoints_use_templates(api, team_and_client, path, payload, key):
    team, client, _ = team_and_client

    body = api.post(path, headers=auth(team), json={"client_id": client.id, **payload}).json()

    assert body["source"] == "template"
    assert len(body[key]) == payload["count"]


def test_topics_have_the_documented_fields(api, team_and_client):
    team, client, _ = team_and_client

    topic = api.post("/api/ai/topics", headers=auth(team), json={"client_id": client.id}).json()["topics"][0]

    assert set(topic) >= {"topic", "angle", "pillar", "why_now", "channel", "keywords", "momentum"}


def test_outreach_and_repurpose_use_templates(api, db, team_and_client, make_content):
    team, client, _ = team_and_client
    post = make_content(client, status="published", title="Playbook: Operations excellence")
    lead = Lead(client_id=client.id, content_id=post.id, name="Dana Lead", company="Lead Co", source="content")
    db.add(lead)
    db.commit()

    for kind in ("connection_note", "follow_up", "meeting_request"):
        message = api.post("/api/ai/outreach", headers=auth(team), json={"lead_id": lead.id, "kind": kind}).json()
        assert message["source"] == "template"
        assert "Dana" in message["message"]
    note = api.post("/api/ai/outreach", headers=auth(team), json={"lead_id": lead.id}).json()
    assert len(note["message"]) <= 300

    repurposed = api.post(
        "/api/ai/repurpose", headers=auth(team), json={"content_id": post.id, "channel": "newsletter"}
    ).json()
    assert repurposed["source"] == "template"
    assert repurposed["item"]["status"] == "draft"
    assert repurposed["item"]["channel"] == "newsletter"


def test_report_includes_template_summary(api, team_and_client):
    _, client, client_user = team_and_client

    report = api.get(f"/api/clients/{client.id}/report?days=30", headers=auth(client_user)).json()

    assert report["summary_source"] == "template"
    assert report["summary"]
    assert len(report["next_steps"]) == 3


def test_geo_run_is_simulated_without_keys(api, team_and_client):
    team, client, _ = team_and_client

    body = api.post(
        "/api/geo/run", headers=auth(team), json={"client_id": client.id, "prompt": "Best ops tools?"}
    ).json()

    assert {c["engine"] for c in body["checks"]} == {"chatgpt", "perplexity", "gemini", "claude"}
    assert {c["method"] for c in body["checks"]} == {"simulated"}


def test_provider_failure_falls_back_to_templates(monkeypatch, api, team_and_client):
    team, client, _ = team_and_client
    monkeypatch.setattr(ai, "settings", replace(ai.settings, anthropic_api_key="test-key"))

    def boom(*_args, **_kwargs):
        raise httpx.ConnectTimeout("no network in tests")

    monkeypatch.setattr(ai.httpx, "post", boom)

    assert ai.status()["provider"] == "anthropic"
    response = api.post("/api/ai/generate-content", headers=auth(team), json={"client_id": client.id})
    assert response.status_code == 200
    assert response.json()["source"] == "template"


def test_bad_llm_json_falls_back_to_templates(monkeypatch, api, team_and_client):
    team, client, _ = team_and_client
    monkeypatch.setattr(ai, "settings", replace(ai.settings, openai_api_key="test-key"))
    monkeypatch.setattr(ai, "_call_openai", lambda *a, **k: "Sure! Here are some topics without JSON.")

    body = api.post("/api/ai/topics", headers=auth(team), json={"client_id": client.id}).json()

    assert body["source"] == "template"


def test_llm_json_is_used_when_valid(monkeypatch, api, team_and_client):
    team, client, _ = team_and_client
    monkeypatch.setattr(ai, "settings", replace(ai.settings, anthropic_api_key="test-key"))
    reply = '```json\n{"drafts": [{"title": "T", "body": "From the model", "hashtags": ["Ops"]}]}\n```'
    monkeypatch.setattr(ai, "_call_anthropic", lambda *a, **k: reply)

    body = api.post("/api/ai/generate-content", headers=auth(team), json={"client_id": client.id}).json()

    assert body["source"] == "llm:anthropic"
    assert body["items"][0]["body"] == "From the model"
    assert body["items"][0]["hashtags"] == ["#Ops"]
    assert body["items"][0]["status"] == "draft"


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ('{"a": 1}', {"a": 1}),
        ('```json\n[1, 2]\n```', [1, 2]),
        ('Here you go:\n{"a": [1]} hope that helps', {"a": [1]}),
    ],
)
def test_parse_json_is_defensive(text, expected):
    assert ai.parse_json(text) == expected


def test_parse_json_raises_on_garbage():
    with pytest.raises(ai.AIError):
        ai.parse_json("no json here")
