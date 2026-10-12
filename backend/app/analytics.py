"""Read-side computations for the agency dashboard, client impact view and report."""

from collections import Counter, defaultdict
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.models import (
    LEAD_STAGES,
    MEETING_STAGES,
    ONBOARDING_LABELS,
    ONBOARDING_STEPS,
    OPEN_LEAD_STAGES,
    Activity,
    Client,
    ContentPiece,
    GeoCheck,
    Keyword,
    Lead,
    MetricSnapshot,
    utcnow,
)
from app.serializers import (
    activity_out,
    content_out,
    geo_out,
    iso,
    keyword_out,
    lead_out,
    onboarding_pct,
    snapshot_out,
)
from app.services import health_score

# (key, label, how to aggregate a window of weekly snapshots)
KPI_DEFS = (
    ("impressions", "Impressions", "sum"),
    ("engagements", "Engagements", "sum"),
    ("followers", "Followers", "last"),
    ("website_visits", "Website visits", "sum"),
    ("leads", "Leads", "sum"),
    ("meetings", "Meetings", "sum"),
    ("ai_visibility", "AI visibility %", "avg"),
)


def change_pct(current: float, previous: float) -> float | None:
    if not previous:
        return None
    return round(100 * (current - previous) / previous, 1)


def _aggregate(window: list[MetricSnapshot], key: str, how: str) -> float:
    values = [getattr(s, key) for s in window]
    if not values:
        return 0
    if how == "last":
        return values[-1]
    if how == "avg":
        return round(sum(values) / len(values), 1)
    return sum(values)


def _snapshots(db: Session, client_id: int) -> list[MetricSnapshot]:
    return list(
        db.scalars(
            select(MetricSnapshot)
            .where(MetricSnapshot.client_id == client_id)
            .order_by(MetricSnapshot.week_start)
        )
    )


def kpis(snapshots: list[MetricSnapshot], weeks: int) -> list[dict[str, Any]]:
    """Each KPI for the last `weeks` snapshots vs the `weeks` before that."""
    current = snapshots[-weeks:]
    previous = snapshots[-2 * weeks : -weeks] if len(snapshots) > weeks else []
    result = []
    for key, label, how in KPI_DEFS:
        now_value = _aggregate(current, key, how)
        before = _aggregate(previous, key, how)
        result.append(
            {
                "key": key,
                "label": label,
                "current": now_value,
                "previous": before,
                "change_pct": change_pct(now_value, before),
            }
        )
    return result


def keyword_movers(db: Session, client_id: int, limit: int = 6) -> list[dict[str, Any]]:
    keywords = db.scalars(
        select(Keyword).where(
            Keyword.client_id == client_id,
            Keyword.current_rank.is_not(None),
            Keyword.previous_rank.is_not(None),
        )
    )
    moved = [k for k in keywords if k.current_rank != k.previous_rank]
    moved.sort(key=lambda k: abs(k.previous_rank - k.current_rank), reverse=True)
    return [keyword_out(k) for k in moved[:limit]]


def latest_geo_checks(db: Session, client_id: int) -> list[GeoCheck]:
    """Most recent check per (prompt, engine) pair."""
    checks = db.scalars(
        select(GeoCheck).where(GeoCheck.client_id == client_id).order_by(GeoCheck.checked_at.desc())
    )
    latest: dict[tuple[str, str], GeoCheck] = {}
    for check in checks:
        latest.setdefault((check.prompt, check.engine), check)
    return list(latest.values())


def geo_by_engine(checks: list[GeoCheck]) -> list[dict[str, Any]]:
    grouped: dict[str, list[GeoCheck]] = defaultdict(list)
    for check in checks:
        grouped[check.engine].append(check)
    return [
        {
            "engine": engine,
            "checks": len(items),
            "mentioned": sum(1 for c in items if c.mentioned),
            "visibility_pct": round(100 * sum(1 for c in items if c.mentioned) / len(items), 1),
            "method": "live" if any(c.method == "live" for c in items) else "simulated",
        }
        for engine, items in sorted(grouped.items())
    ]


def lead_summary(db: Session, client_id: int | None = None) -> dict[str, Any]:
    query = select(Lead)
    if client_id is not None:
        query = query.where(Lead.client_id == client_id)
    leads = list(db.scalars(query))
    by_stage = Counter(lead.stage for lead in leads)
    return {
        "total": len(leads),
        "by_stage": [
            {
                "stage": stage,
                "count": by_stage.get(stage, 0),
                "value": sum(lead.deal_value for lead in leads if lead.stage == stage),
            }
            for stage in LEAD_STAGES
        ],
        "open_value": sum(lead.deal_value for lead in leads if lead.stage in OPEN_LEAD_STAGES),
        "won_value": sum(lead.deal_value for lead in leads if lead.stage == "won"),
    }


def _top_posts(db: Session, client_id: int, since: datetime | None = None, limit: int = 5) -> list[dict]:
    query = select(ContentPiece).where(
        ContentPiece.client_id == client_id, ContentPiece.status == "published"
    )
    if since is not None:
        query = query.where(ContentPiece.published_at >= since)
    query = query.order_by(ContentPiece.engagements.desc()).limit(limit)
    return [content_out(p) for p in db.scalars(query)]


def _won_leads(db: Session, client_id: int, since: datetime) -> list[Lead]:
    return list(
        db.scalars(
            select(Lead)
            .where(Lead.client_id == client_id, Lead.stage == "won", Lead.stage_changed_at >= since)
            .order_by(Lead.stage_changed_at.desc())
        )
    )


def impact(db: Session, client: Client, weeks: int = 4) -> dict[str, Any]:
    now = utcnow()
    snapshots = _snapshots(db, client.id)
    window = snapshots[-weeks:]
    since = now - timedelta(weeks=weeks)
    return {
        "client_id": client.id,
        "weeks": weeks,
        "kpis": kpis(snapshots, weeks),
        "series": [snapshot_out(s) for s in snapshots],
        "funnel": [
            {"stage": "impressions", "label": "Impressions", "value": _aggregate(window, "impressions", "sum")},
            {"stage": "engagements", "label": "Engagements", "value": _aggregate(window, "engagements", "sum")},
            {"stage": "leads", "label": "Leads", "value": _aggregate(window, "leads", "sum")},
            {"stage": "meetings", "label": "Meetings", "value": _aggregate(window, "meetings", "sum")},
            {"stage": "won", "label": "Won", "value": len(_won_leads(db, client.id, since))},
        ],
        "top_posts": _top_posts(db, client.id),
        "keyword_movers": keyword_movers(db, client.id),
        "geo": geo_by_engine(latest_geo_checks(db, client.id)),
        "leads": lead_summary(db, client.id),
        "health": health_score(db, client, now),
    }


def report(db: Session, client: Client, days: int = 30) -> dict[str, Any]:
    """Period report data. The AI summary is attached by the router."""
    now = utcnow()
    start = now - timedelta(days=days)
    weeks = max(1, round(days / 7))
    snapshots = _snapshots(db, client.id)
    won = _won_leads(db, client.id, start)
    published = db.scalar(
        select(func.count(ContentPiece.id)).where(
            ContentPiece.client_id == client.id,
            ContentPiece.status == "published",
            ContentPiece.published_at >= start,
        )
    ) or 0
    new_leads = db.scalar(
        select(func.count(Lead.id)).where(Lead.client_id == client.id, Lead.created_at >= start)
    ) or 0
    meetings = db.scalar(
        select(func.count(Lead.id)).where(
            Lead.client_id == client.id,
            Lead.stage.in_(MEETING_STAGES),
            Lead.stage_changed_at >= start,
        )
    ) or 0
    return {
        "client": {
            "id": client.id,
            "name": client.name,
            "title": client.title,
            "company": client.company,
            "industry": client.industry,
            "goals": list(client.goals or []),
        },
        "period": {"start": iso(start), "end": iso(now), "days": days},
        "kpis": kpis(snapshots, weeks),
        "highlights": {
            "posts_published": published,
            "new_leads": new_leads,
            "meetings_booked": meetings,
            "deals_won": len(won),
            "won_value": sum(lead.deal_value for lead in won),
        },
        "series": [snapshot_out(s) for s in snapshots[-2 * weeks :]],
        "top_content": _top_posts(db, client.id, since=start),
        "leads_won": [lead_out(lead) for lead in won],
        "keyword_movers": keyword_movers(db, client.id),
        "geo": geo_by_engine(latest_geo_checks(db, client.id)),
    }


def dashboard(db: Session) -> dict[str, Any]:
    now = utcnow()
    week_ago = now - timedelta(days=7)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    clients = list(db.scalars(select(Client).order_by(Client.name)))
    names = {c.id: c.name for c in clients}

    status_counts: dict[int, Counter] = defaultdict(Counter)
    for client_id, status, count in db.execute(
        select(ContentPiece.client_id, ContentPiece.status, func.count()).group_by(
            ContentPiece.client_id, ContentPiece.status
        )
    ):
        status_counts[client_id][status] = count

    sparklines: dict[int, list[int]] = defaultdict(list)
    for snapshot in db.scalars(select(MetricSnapshot).order_by(MetricSnapshot.week_start)):
        sparklines[snapshot.client_id].append(snapshot.impressions)

    rows = []
    for client in clients:
        counts = status_counts[client.id]
        series = sparklines[client.id][-12:]
        rows.append(
            {
                "id": client.id,
                "name": client.name,
                "company": client.company,
                "industry": client.industry,
                "status": client.status,
                "account_manager_id": client.account_manager_id,
                "health": health_score(db, client, now),
                "onboarding_pct": onboarding_pct(client),
                "approvals_waiting": counts.get("client_review", 0),
                "internal_review": counts.get("internal_review", 0),
                "changes_requested": counts.get("changes_requested", 0),
                "scheduled": counts.get("scheduled", 0),
                "impressions_series": series,
                "impressions_change_pct": (
                    change_pct(sum(series[-4:]), sum(series[-8:-4])) if len(series) >= 8 else None
                ),
            }
        )

    pipeline = []
    for step in ONBOARDING_STEPS:
        waiting = [
            {"id": c.id, "name": c.name, "company": c.company, "onboarding_pct": onboarding_pct(c)}
            for c in clients
            if c.status == "onboarding" and _current_step(c) == step
        ]
        pipeline.append({"step": step, "label": ONBOARDING_LABELS[step], "clients": waiting})

    def count_content(*conditions) -> int:
        return db.scalar(select(func.count(ContentPiece.id)).where(*conditions)) or 0

    open_pipeline = db.scalar(
        select(func.coalesce(func.sum(Lead.deal_value), 0)).where(Lead.stage.in_(OPEN_LEAD_STAGES))
    )
    activities = db.scalars(
        select(Activity).options(selectinload(Activity.user)).order_by(Activity.created_at.desc()).limit(20)
    )
    return {
        "totals": {
            "active_clients": sum(1 for c in clients if c.status == "active"),
            "onboarding_clients": sum(1 for c in clients if c.status == "onboarding"),
            "published_this_week": count_content(
                ContentPiece.status == "published", ContentPiece.published_at >= week_ago
            ),
            "awaiting_approval": count_content(ContentPiece.status == "client_review"),
            "internal_review": count_content(ContentPiece.status == "internal_review"),
            "changes_requested": count_content(ContentPiece.status == "changes_requested"),
            "leads_this_month": db.scalar(
                select(func.count(Lead.id)).where(Lead.created_at >= month_start)
            ) or 0,
            "pipeline_value": float(open_pipeline or 0),
        },
        "clients": rows,
        "onboarding_pipeline": pipeline,
        "activity": [activity_out(a, names) for a in activities],
        "generated_at": iso(now),
    }


def _current_step(client: Client) -> str:
    state = client.onboarding or {}
    for step in ONBOARDING_STEPS:
        if not state.get(step):
            return step
    return ONBOARDING_STEPS[-1]


def geo_overview(db: Session, client_id: int) -> dict[str, Any]:
    checks = latest_geo_checks(db, client_id)
    checks.sort(key=lambda c: (c.prompt, c.engine))
    return {
        "checks": [geo_out(c) for c in checks],
        "by_engine": geo_by_engine(checks),
        "prompts": sorted({c.prompt for c in checks}),
    }
