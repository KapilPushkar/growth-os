"""Explicit model -> JSON-ready dict functions.

Keeping these hand-written (rather than auto-dumping ORM objects) makes the
API contract readable in one place and stops internal fields leaking out.
"""

from datetime import date, datetime
from typing import Any

from app.models import (
    ONBOARDING_LABELS,
    ONBOARDING_STEPS,
    Activity,
    ApprovalEvent,
    Campaign,
    Client,
    ContentPiece,
    GeoCheck,
    Keyword,
    Lead,
    MetricSnapshot,
    User,
)


def iso(value: datetime | None) -> str | None:
    """Naive UTC datetime -> ISO 8601 string with an explicit UTC offset."""
    if value is None:
        return None
    return value.isoformat(timespec="seconds") + "Z"


def iso_date(value: date | None) -> str | None:
    return value.isoformat() if value else None


def user_out(user: User) -> dict[str, Any]:
    return {
        "id": user.id,
        "email": user.email,
        "name": user.name,
        "role": user.role,
        "client_id": user.client_id,
        "is_active": user.is_active,
    }


def onboarding_steps(client: Client) -> list[dict[str, Any]]:
    state = client.onboarding or {}
    return [
        {"key": step, "label": ONBOARDING_LABELS[step], "done": bool(state.get(step))}
        for step in ONBOARDING_STEPS
    ]


def onboarding_pct(client: Client) -> int:
    state = client.onboarding or {}
    done = sum(1 for step in ONBOARDING_STEPS if state.get(step))
    return round(100 * done / len(ONBOARDING_STEPS))


def client_out(client: Client) -> dict[str, Any]:
    return {
        "id": client.id,
        "name": client.name,
        "title": client.title,
        "email": client.email,
        "company": client.company,
        "industry": client.industry,
        "website": client.website,
        "plan": client.plan,
        "status": client.status,
        "positioning": client.positioning,
        "brand_voice": client.brand_voice,
        "tone_tags": list(client.tone_tags or []),
        "target_audience": client.target_audience,
        "content_pillars": list(client.content_pillars or []),
        "topics_to_avoid": client.topics_to_avoid,
        "goals": list(client.goals or []),
        "channels": list(client.channels or []),
        "posting_cadence": client.posting_cadence,
        "auto_approve_hours": client.auto_approve_hours,
        "onboarding": onboarding_steps(client),
        "onboarding_pct": onboarding_pct(client),
        "account_manager_id": client.account_manager_id,
        "start_date": iso_date(client.start_date),
        "created_at": iso(client.created_at),
    }


def event_out(event: ApprovalEvent) -> dict[str, Any]:
    return {
        "id": event.id,
        "action": event.action,
        "from_status": event.from_status,
        "to_status": event.to_status,
        "note": event.note,
        "created_at": iso(event.created_at),
        "user": (
            {"id": event.user.id, "name": event.user.name, "role": event.user.role}
            if event.user
            else None
        ),
    }


def content_out(
    piece: ContentPiece,
    *,
    events: bool = False,
    allowed_actions: list[str] | None = None,
) -> dict[str, Any]:
    data: dict[str, Any] = {
        "id": piece.id,
        "client_id": piece.client_id,
        "campaign_id": piece.campaign_id,
        "title": piece.title,
        "channel": piece.channel,
        "format": piece.format,
        "pillar": piece.pillar,
        "body": piece.body,
        "hashtags": list(piece.hashtags or []),
        "target_keyword": piece.target_keyword,
        "status": piece.status,
        "status_changed_at": iso(piece.status_changed_at),
        "scheduled_at": iso(piece.scheduled_at),
        "published_at": iso(piece.published_at),
        "ai_generated": piece.ai_generated,
        "ai_source": piece.ai_source,
        "metrics": {
            "impressions": piece.impressions,
            "engagements": piece.engagements,
            "clicks": piece.clicks,
            "leads": piece.leads_generated,
        },
        "created_at": iso(piece.created_at),
        "updated_at": iso(piece.updated_at),
    }
    if events:
        data["events"] = [event_out(e) for e in piece.events]
    if allowed_actions is not None:
        data["allowed_actions"] = allowed_actions
    return data


def campaign_out(campaign: Campaign, progress: dict[str, Any] | None = None) -> dict[str, Any]:
    return {
        "id": campaign.id,
        "client_id": campaign.client_id,
        "name": campaign.name,
        "type": campaign.type,
        "status": campaign.status,
        "objective": campaign.objective,
        "channels": list(campaign.channels or []),
        "start_date": iso_date(campaign.start_date),
        "end_date": iso_date(campaign.end_date),
        "kpi_targets": dict(campaign.kpi_targets or {}),
        "progress": progress or {},
        "created_at": iso(campaign.created_at),
    }


def lead_out(lead: Lead) -> dict[str, Any]:
    return {
        "id": lead.id,
        "client_id": lead.client_id,
        "campaign_id": lead.campaign_id,
        "content_id": lead.content_id,
        "name": lead.name,
        "title": lead.title,
        "company": lead.company,
        "email": lead.email,
        "linkedin_url": lead.linkedin_url,
        "source": lead.source,
        "stage": lead.stage,
        "score": lead.score,
        "deal_value": lead.deal_value,
        "notes": lead.notes,
        "stage_changed_at": iso(lead.stage_changed_at),
        "created_at": iso(lead.created_at),
        "updated_at": iso(lead.updated_at),
    }


def keyword_out(keyword: Keyword) -> dict[str, Any]:
    change = None
    if keyword.current_rank is not None and keyword.previous_rank is not None:
        # Positive = moved up the results page.
        change = keyword.previous_rank - keyword.current_rank
    return {
        "id": keyword.id,
        "client_id": keyword.client_id,
        "keyword": keyword.keyword,
        "intent": keyword.intent,
        "search_volume": keyword.search_volume,
        "difficulty": keyword.difficulty,
        "current_rank": keyword.current_rank,
        "previous_rank": keyword.previous_rank,
        "rank_change": change,
        "trend": keyword.trend,
        "target_url": keyword.target_url,
        "updated_at": iso(keyword.updated_at),
    }


def geo_out(check: GeoCheck) -> dict[str, Any]:
    return {
        "id": check.id,
        "client_id": check.client_id,
        "prompt": check.prompt,
        "engine": check.engine,
        "mentioned": check.mentioned,
        "position": check.position,
        "method": check.method,
        "excerpt": check.excerpt,
        "checked_at": iso(check.checked_at),
    }


def snapshot_out(snapshot: MetricSnapshot) -> dict[str, Any]:
    return {
        "week_start": iso_date(snapshot.week_start),
        "followers": snapshot.followers,
        "impressions": snapshot.impressions,
        "engagements": snapshot.engagements,
        "profile_views": snapshot.profile_views,
        "website_visits": snapshot.website_visits,
        "leads": snapshot.leads,
        "meetings": snapshot.meetings,
        "ai_visibility": snapshot.ai_visibility,
    }


def activity_out(activity: Activity, client_names: dict[int, str] | None = None) -> dict[str, Any]:
    return {
        "id": activity.id,
        "client_id": activity.client_id,
        "client_name": (client_names or {}).get(activity.client_id or 0),
        "kind": activity.kind,
        "message": activity.message,
        "user": activity.user.name if activity.user else "System",
        "created_at": iso(activity.created_at),
    }
