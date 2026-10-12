"""Domain rules: approval state machine, auto-approve, activity log, health score,
onboarding, client creation and the simulated integrations.

Services raise DomainError subclasses; main.py maps them to HTTP responses so
this module has no web-framework dependency.
"""

import random
from dataclasses import dataclass
from datetime import datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.auth import generate_temp_password, hash_password
from app.models import (
    ACTION_VERBS,
    CAMPAIGN_KPIS,
    CONTENT_STATUSES,
    MEETING_STAGES,
    ONBOARDING_LABELS,
    ONBOARDING_STEPS,
    ROLES,
    TEAM_ROLES,
    Activity,
    ApprovalEvent,
    Campaign,
    Client,
    ContentPiece,
    Keyword,
    Lead,
    MetricSnapshot,
    User,
    utcnow,
)

# A piece waiting on the client longer than this counts as "stuck" for health.
STUCK_AFTER_HOURS = 48


class DomainError(Exception):
    status_code = 400

    def __init__(self, detail: str) -> None:
        super().__init__(detail)
        self.detail = detail


class NotAllowed(DomainError):
    status_code = 403


class NotFound(DomainError):
    status_code = 404


class Conflict(DomainError):
    status_code = 409


# --- Approval state machine --------------------------------------------------


@dataclass(frozen=True)
class Rule:
    from_statuses: tuple[str, ...]
    to_status: str | None  # None = no status change (comments)
    roles: tuple[str, ...]


TRANSITIONS: dict[str, Rule] = {
    "submit": Rule(("idea", "draft"), "internal_review", TEAM_ROLES),
    "send_to_client": Rule(("draft", "internal_review"), "client_review", TEAM_ROLES),
    "reject_internal": Rule(("internal_review",), "draft", TEAM_ROLES),
    "approve": Rule(("client_review",), "approved", ROLES),
    # Clients can also pull back a scheduled piece.
    "request_changes": Rule(("client_review", "scheduled"), "changes_requested", ROLES),
    # Also starts work on an idea.
    "revise": Rule(("changes_requested", "idea"), "draft", TEAM_ROLES),
    # Re-scheduling an already scheduled piece moves its slot.
    "schedule": Rule(("approved", "scheduled"), "scheduled", TEAM_ROLES),
    "publish": Rule(("approved", "scheduled"), "published", TEAM_ROLES),
    "comment": Rule(CONTENT_STATUSES, None, ROLES),
}


def log_activity(
    db: Session, client_id: int | None, user: User | None, kind: str, message: str
) -> Activity:
    activity = Activity(
        client_id=client_id, user_id=user.id if user else None, kind=kind, message=message
    )
    db.add(activity)
    return activity


def record_event(
    db: Session,
    piece: ContentPiece,
    user: User | None,
    action: str,
    from_status: str | None,
    to_status: str | None,
    note: str = "",
) -> ApprovalEvent:
    event = ApprovalEvent(
        content_id=piece.id,
        user_id=user.id if user else None,
        action=action,
        from_status=from_status,
        to_status=to_status,
        note=note,
    )
    db.add(event)
    actor = user.name if user else "System"
    message = f"{actor} {ACTION_VERBS.get(action, action)} “{piece.title or 'Untitled'}”"
    if note and action in ("request_changes", "comment"):
        message += f": {note}"
    log_activity(db, piece.client_id, user, f"content.{action}", message)
    return event


def allowed_actions(piece: ContentPiece, user: User) -> list[str]:
    return [
        action
        for action, rule in TRANSITIONS.items()
        if user.role in rule.roles and piece.status in rule.from_statuses
    ]


def apply_transition(
    db: Session,
    piece: ContentPiece,
    action: str,
    user: User,
    note: str = "",
    scheduled_at: datetime | None = None,
) -> ContentPiece:
    """Validate and apply one action. Does not commit."""
    rule = TRANSITIONS.get(action)
    if rule is None:
        raise DomainError(f"Unknown action '{action}'. Valid: {', '.join(TRANSITIONS)}")
    if user.role not in rule.roles:
        raise NotAllowed(f"Your role cannot '{action}' content")
    if piece.status not in rule.from_statuses:
        raise Conflict(f"Cannot '{action}' a piece in '{piece.status}'")
    note = (note or "").strip()
    if action in ("request_changes", "comment") and not note:
        raise DomainError("A note is required" if action == "request_changes" else "Comment is empty")
    if action == "schedule" and scheduled_at is None:
        raise DomainError("A date is required to schedule")

    from_status = piece.status
    now = utcnow()
    if rule.to_status is not None:
        piece.status = rule.to_status
        piece.status_changed_at = now
    if action == "schedule":
        piece.scheduled_at = scheduled_at
    elif action == "publish":
        piece.published_at = now
        piece.scheduled_at = piece.scheduled_at or now
    elif action == "request_changes":
        piece.scheduled_at = None

    record_event(db, piece, user, action, from_status, rule.to_status or from_status, note)
    return piece


def process_auto_approvals(db: Session, client_id: int | None = None) -> int:
    """Approve client_review pieces older than their client's auto-approve window.

    Evaluated lazily from queue/dashboard endpoints instead of a scheduler.
    """
    query = (
        select(ContentPiece, Client.auto_approve_hours)
        .join(Client, Client.id == ContentPiece.client_id)
        .where(ContentPiece.status == "client_review", Client.auto_approve_hours > 0)
    )
    if client_id is not None:
        query = query.where(ContentPiece.client_id == client_id)

    now = utcnow()
    approved = 0
    for piece, hours in db.execute(query).all():
        if piece.status_changed_at > now - timedelta(hours=hours):
            continue
        piece.status = "approved"
        piece.status_changed_at = now
        record_event(
            db,
            piece,
            None,
            "auto_approve",
            "client_review",
            "approved",
            f"No response within {hours}h, approved automatically (client opted in).",
        )
        approved += 1
    if approved:
        db.commit()
    return approved


def waiting_hours(piece: ContentPiece, now: datetime | None = None) -> float:
    return round(((now or utcnow()) - piece.status_changed_at).total_seconds() / 3600, 1)


# --- Clients & onboarding ----------------------------------------------------


def create_client(db: Session, data: dict, user: User) -> tuple[Client, User | None, str | None]:
    """Create a client and optionally its login. Returns the temp password once."""
    create_login = data.pop("create_login", False)
    manager_id = data.get("account_manager_id")
    if manager_id is not None:
        manager = db.get(User, manager_id)
        if manager is None or manager.role not in TEAM_ROLES:
            raise DomainError("Account manager must be a team member")
    client = Client(**data)
    if not client.account_manager_id and user.role == "strategist":
        client.account_manager_id = user.id
    db.add(client)

    login: User | None = None
    temp_password: str | None = None
    if create_login:
        if not client.email:
            raise DomainError("An email is required to create a client login")
        if db.scalar(select(User.id).where(User.email == client.email)):
            raise Conflict(f"A user with email {client.email} already exists")
        temp_password = generate_temp_password()
        db.flush()
        login = User(
            email=client.email,
            name=client.name,
            role="client",
            client_id=client.id,
            password_hash=hash_password(temp_password),
        )
        db.add(login)

    db.flush()
    log_activity(db, client.id, user, "client.created", f"{user.name} added {client.name} ({client.company})")
    return client, login, temp_password


def set_onboarding_step(db: Session, client: Client, step: str, done: bool, user: User) -> Client:
    """Tick or untick a step; completing all of them takes the client live."""
    state = dict(client.onboarding or {})  # new object so SQLAlchemy sees the change
    state[step] = done
    client.onboarding = state
    label = ONBOARDING_LABELS[step]
    log_activity(
        db,
        client.id,
        user,
        "onboarding.step",
        f"Onboarding: “{label}” {'completed' if done else 'reopened'} for {client.name}",
    )
    if all(state.get(s) for s in ONBOARDING_STEPS) and client.status == "onboarding":
        client.status = "active"
        client.start_date = utcnow().date()
        log_activity(db, client.id, user, "client.live", f"{client.name} is live")
    return client


def health_score(db: Session, client: Client, now: datetime | None = None) -> int | None:
    """0-100 account health; None while the client is still onboarding.

    55% posting cadence hit over 30 days, 25% if impressions over the last
    4 weeks beat the previous 4, 20% base, minus 10 per piece stuck with
    the client (max 30).
    """
    if client.status == "onboarding":
        return None
    now = now or utcnow()

    published = db.scalar(
        select(func.count(ContentPiece.id)).where(
            ContentPiece.client_id == client.id,
            ContentPiece.status == "published",
            ContentPiece.published_at >= now - timedelta(days=30),
        )
    ) or 0
    expected = client.posting_cadence * 4
    cadence_hit = min(1.0, published / expected) if expected else 1.0

    impressions = list(
        db.scalars(
            select(MetricSnapshot.impressions)
            .where(MetricSnapshot.client_id == client.id)
            .order_by(MetricSnapshot.week_start.desc())
            .limit(8)
        )
    )
    growing = len(impressions) == 8 and sum(impressions[:4]) > sum(impressions[4:])

    stuck = db.scalar(
        select(func.count(ContentPiece.id)).where(
            ContentPiece.client_id == client.id,
            ContentPiece.status == "client_review",
            ContentPiece.status_changed_at <= now - timedelta(hours=STUCK_AFTER_HOURS),
        )
    ) or 0

    score = 55 * cadence_hit + (25 if growing else 0) + 20 - min(30, 10 * stuck)
    return max(0, min(100, round(score)))


# --- Campaigns ---------------------------------------------------------------


def campaign_progress(db: Session, campaign: Campaign) -> dict[str, dict[str, float]]:
    """Actual vs target for each KPI the campaign tracks."""
    pieces = list(
        db.scalars(
            select(ContentPiece).where(
                ContentPiece.campaign_id == campaign.id, ContentPiece.status == "published"
            )
        )
    )
    leads = list(db.scalars(select(Lead).where(Lead.campaign_id == campaign.id)))
    actuals = {
        "posts": len(pieces),
        "impressions": sum(p.impressions for p in pieces),
        "engagements": sum(p.engagements for p in pieces),
        "leads": len(leads),
        "meetings": sum(1 for lead in leads if lead.stage in MEETING_STAGES),
    }
    progress = {}
    for key in CAMPAIGN_KPIS:
        target = (campaign.kpi_targets or {}).get(key)
        if target is None:
            continue
        actual = actuals[key]
        pct = round(100 * actual / target, 1) if target else 100.0
        progress[key] = {"target": target, "actual": actual, "pct": pct}
    return progress


# --- Leads -------------------------------------------------------------------


def validate_lead_links(db: Session, client_id: int, campaign_id: int | None, content_id: int | None) -> None:
    if campaign_id is not None:
        campaign = db.get(Campaign, campaign_id)
        if campaign is None or campaign.client_id != client_id:
            raise DomainError("Campaign does not belong to this client")
    if content_id is not None:
        piece = db.get(ContentPiece, content_id)
        if piece is None or piece.client_id != client_id:
            raise DomainError("Content does not belong to this client")


def change_lead_stage(db: Session, lead: Lead, stage: str, user: User) -> None:
    if stage == lead.stage:
        return
    previous = lead.stage
    lead.stage = stage
    lead.stage_changed_at = utcnow()
    label = stage.replace("_", " ")
    log_activity(
        db,
        lead.client_id,
        user,
        "lead.stage",
        f"{user.name} moved lead {lead.name} ({lead.company}) from {previous.replace('_', ' ')} to {label}",
    )


# --- Simulated integrations --------------------------------------------------


def simulate_metrics_sync(piece: ContentPiece, rng: random.Random | None = None) -> dict[str, int]:
    """Stand-in for LinkedIn/X analytics: adds a plausible bump to post metrics."""
    if piece.status != "published":
        raise Conflict("Only published content has metrics to sync")
    rng = rng or random.Random()
    gained = max(rng.randint(300, 1500), int(piece.impressions * rng.uniform(0.05, 0.25)))
    delta = {
        "impressions": gained,
        "engagements": int(gained * rng.uniform(0.02, 0.06)),
        "clicks": int(gained * rng.uniform(0.005, 0.02)),
        "leads": 1 if rng.random() < 0.2 else 0,
    }
    piece.impressions += delta["impressions"]
    piece.engagements += delta["engagements"]
    piece.clicks += delta["clicks"]
    piece.leads_generated += delta["leads"]
    return delta


def simulate_rank_refresh(keywords: list[Keyword], rng: random.Random | None = None) -> None:
    """Stand-in for a rank-tracking provider: nudges ranks, slightly biased upward."""
    rng = rng or random.Random()
    for keyword in keywords:
        keyword.previous_rank = keyword.current_rank
        if keyword.current_rank is None:
            keyword.current_rank = rng.randint(18, 60)
            keyword.trend = "new"
            continue
        keyword.current_rank = max(1, keyword.current_rank + rng.choice((-3, -2, -1, -1, 0, 1, 2)))
        if keyword.current_rank < keyword.previous_rank:
            keyword.trend = "up"
        elif keyword.current_rank > keyword.previous_rank:
            keyword.trend = "down"
        else:
            keyword.trend = "flat"
