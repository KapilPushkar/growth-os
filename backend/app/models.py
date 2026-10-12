"""SQLAlchemy models and the controlled vocabularies the API validates against.

All datetimes are stored as naive UTC (SQLite has no timezone type);
serializers mark them as UTC on the way out.
"""

from datetime import UTC, date, datetime

from sqlalchemy import JSON, Boolean, Date, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

# --- Vocabularies -----------------------------------------------------------

ROLES = ("admin", "strategist", "client")
TEAM_ROLES = ("admin", "strategist")

CLIENT_STATUSES = ("onboarding", "active", "paused")
PLANS = ("starter", "growth", "scale")

CHANNELS = ("linkedin", "x", "blog", "newsletter", "instagram")
FORMATS = ("post", "carousel", "article", "thread", "video_script")

CONTENT_STATUSES = (
    "idea",
    "draft",
    "internal_review",
    "client_review",
    "changes_requested",
    "approved",
    "scheduled",
    "published",
)
# Internal work-in-progress that clients never see.
CLIENT_HIDDEN_STATUSES = ("idea", "draft", "internal_review")

CAMPAIGN_TYPES = ("content", "personal_brand", "lead_gen", "performance")
CAMPAIGN_STATUSES = ("planned", "active", "paused", "completed")
# KPI keys a campaign can target; progress is computed from content and leads.
CAMPAIGN_KPIS = ("posts", "impressions", "engagements", "leads", "meetings")

LEAD_STAGES = ("new", "contacted", "engaged", "meeting_booked", "proposal", "won", "lost")
OPEN_LEAD_STAGES = ("new", "contacted", "engaged", "meeting_booked", "proposal")
# Stages that count as "reached a meeting" in the funnel.
MEETING_STAGES = ("meeting_booked", "proposal", "won")
LEAD_SOURCES = ("content", "inbound", "outbound", "referral")
OUTREACH_KINDS = ("connection_note", "follow_up", "meeting_request")

KEYWORD_INTENTS = ("informational", "commercial", "transactional", "navigational")
KEYWORD_TRENDS = ("up", "down", "flat", "new")

GEO_ENGINES = ("chatgpt", "perplexity", "gemini", "claude")
GEO_METHODS = ("live", "simulated")

ONBOARDING_STEPS = ("intake", "access", "strategy", "first_batch", "launch")
ONBOARDING_LABELS = {
    "intake": "Intake & brand profile",
    "access": "Account access",
    "strategy": "Strategy, pillars & ICP",
    "first_batch": "First batch approved",
    "launch": "Go live",
}


def utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def empty_onboarding() -> dict[str, bool]:
    return {step: False for step in ONBOARDING_STEPS}


# --- Models -----------------------------------------------------------------


class Client(Base):
    __tablename__ = "clients"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    title: Mapped[str] = mapped_column(String(120), default="")
    email: Mapped[str] = mapped_column(String(255), default="")
    company: Mapped[str] = mapped_column(String(160))
    industry: Mapped[str] = mapped_column(String(80), default="")
    website: Mapped[str] = mapped_column(String(255), default="")
    plan: Mapped[str] = mapped_column(String(20), default="growth")
    status: Mapped[str] = mapped_column(String(20), default="onboarding", index=True)

    positioning: Mapped[str] = mapped_column(Text, default="")
    brand_voice: Mapped[str] = mapped_column(Text, default="")
    tone_tags: Mapped[list[str]] = mapped_column(JSON, default=list)
    target_audience: Mapped[str] = mapped_column(Text, default="")
    content_pillars: Mapped[list[str]] = mapped_column(JSON, default=list)
    topics_to_avoid: Mapped[str] = mapped_column(Text, default="")
    goals: Mapped[list[str]] = mapped_column(JSON, default=list)
    channels: Mapped[list[str]] = mapped_column(JSON, default=list)
    posting_cadence: Mapped[int] = mapped_column(Integer, default=3)
    auto_approve_hours: Mapped[int] = mapped_column(Integer, default=0)
    onboarding: Mapped[dict[str, bool]] = mapped_column(JSON, default=empty_onboarding)

    # Plain int rather than a FK: users.client_id already points at clients,
    # and a second FK in the other direction would create a cycle.
    account_manager_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(120))
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(20))
    client_id: Mapped[int | None] = mapped_column(
        ForeignKey("clients.id", ondelete="CASCADE"), nullable=True, index=True
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    @property
    def is_team(self) -> bool:
        return self.role in TEAM_ROLES


class Campaign(Base):
    __tablename__ = "campaigns"

    id: Mapped[int] = mapped_column(primary_key=True)
    client_id: Mapped[int] = mapped_column(ForeignKey("clients.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(160))
    type: Mapped[str] = mapped_column(String(20))
    status: Mapped[str] = mapped_column(String(20), default="planned")
    objective: Mapped[str] = mapped_column(Text, default="")
    channels: Mapped[list[str]] = mapped_column(JSON, default=list)
    start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    kpi_targets: Mapped[dict[str, int]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class ContentPiece(Base):
    __tablename__ = "content"

    id: Mapped[int] = mapped_column(primary_key=True)
    client_id: Mapped[int] = mapped_column(ForeignKey("clients.id", ondelete="CASCADE"), index=True)
    campaign_id: Mapped[int | None] = mapped_column(
        ForeignKey("campaigns.id", ondelete="SET NULL"), nullable=True, index=True
    )
    title: Mapped[str] = mapped_column(String(200), default="")
    channel: Mapped[str] = mapped_column(String(20))
    format: Mapped[str] = mapped_column(String(20), default="post")
    pillar: Mapped[str] = mapped_column(String(120), default="")
    body: Mapped[str] = mapped_column(Text, default="")
    hashtags: Mapped[list[str]] = mapped_column(JSON, default=list)
    target_keyword: Mapped[str] = mapped_column(String(160), default="")
    status: Mapped[str] = mapped_column(String(20), default="draft", index=True)
    # When the piece entered its current status; drives wait times and auto-approve.
    status_changed_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    scheduled_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    ai_generated: Mapped[bool] = mapped_column(Boolean, default=False)
    ai_source: Mapped[str] = mapped_column(String(40), default="")
    impressions: Mapped[int] = mapped_column(Integer, default=0)
    engagements: Mapped[int] = mapped_column(Integer, default=0)
    clicks: Mapped[int] = mapped_column(Integer, default=0)
    leads_generated: Mapped[int] = mapped_column(Integer, default=0)
    created_by_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)

    events: Mapped[list["ApprovalEvent"]] = relationship(
        back_populates="content",
        order_by="ApprovalEvent.created_at",
        cascade="all, delete-orphan",
    )


class ApprovalEvent(Base):
    __tablename__ = "approval_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    content_id: Mapped[int] = mapped_column(ForeignKey("content.id", ondelete="CASCADE"), index=True)
    # Null for system actions such as auto-approve.
    user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    action: Mapped[str] = mapped_column(String(30))
    from_status: Mapped[str | None] = mapped_column(String(20), nullable=True)
    to_status: Mapped[str | None] = mapped_column(String(20), nullable=True)
    note: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    content: Mapped[ContentPiece] = relationship(back_populates="events")
    user: Mapped[User | None] = relationship()


class Lead(Base):
    __tablename__ = "leads"

    id: Mapped[int] = mapped_column(primary_key=True)
    client_id: Mapped[int] = mapped_column(ForeignKey("clients.id", ondelete="CASCADE"), index=True)
    campaign_id: Mapped[int | None] = mapped_column(
        ForeignKey("campaigns.id", ondelete="SET NULL"), nullable=True
    )
    content_id: Mapped[int | None] = mapped_column(
        ForeignKey("content.id", ondelete="SET NULL"), nullable=True
    )
    name: Mapped[str] = mapped_column(String(120))
    title: Mapped[str] = mapped_column(String(120), default="")
    company: Mapped[str] = mapped_column(String(160), default="")
    email: Mapped[str] = mapped_column(String(255), default="")
    linkedin_url: Mapped[str] = mapped_column(String(255), default="")
    source: Mapped[str] = mapped_column(String(20), default="inbound")
    stage: Mapped[str] = mapped_column(String(20), default="new", index=True)
    score: Mapped[int] = mapped_column(Integer, default=50)
    deal_value: Mapped[float] = mapped_column(Float, default=0.0)
    notes: Mapped[str] = mapped_column(Text, default="")
    stage_changed_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)


class Keyword(Base):
    __tablename__ = "keywords"

    id: Mapped[int] = mapped_column(primary_key=True)
    client_id: Mapped[int] = mapped_column(ForeignKey("clients.id", ondelete="CASCADE"), index=True)
    keyword: Mapped[str] = mapped_column(String(160))
    intent: Mapped[str] = mapped_column(String(20), default="informational")
    search_volume: Mapped[int] = mapped_column(Integer, default=0)
    difficulty: Mapped[int] = mapped_column(Integer, default=0)
    current_rank: Mapped[int | None] = mapped_column(Integer, nullable=True)
    previous_rank: Mapped[int | None] = mapped_column(Integer, nullable=True)
    trend: Mapped[str] = mapped_column(String(10), default="new")
    target_url: Mapped[str] = mapped_column(String(255), default="")
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)


class GeoCheck(Base):
    __tablename__ = "geo_checks"

    id: Mapped[int] = mapped_column(primary_key=True)
    client_id: Mapped[int] = mapped_column(ForeignKey("clients.id", ondelete="CASCADE"), index=True)
    prompt: Mapped[str] = mapped_column(Text)
    engine: Mapped[str] = mapped_column(String(20))
    mentioned: Mapped[bool] = mapped_column(Boolean, default=False)
    position: Mapped[int | None] = mapped_column(Integer, nullable=True)
    method: Mapped[str] = mapped_column(String(20), default="simulated")
    excerpt: Mapped[str] = mapped_column(Text, default="")
    checked_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class MetricSnapshot(Base):
    __tablename__ = "metric_snapshots"

    id: Mapped[int] = mapped_column(primary_key=True)
    client_id: Mapped[int] = mapped_column(ForeignKey("clients.id", ondelete="CASCADE"), index=True)
    week_start: Mapped[date] = mapped_column(Date)
    followers: Mapped[int] = mapped_column(Integer, default=0)
    impressions: Mapped[int] = mapped_column(Integer, default=0)
    engagements: Mapped[int] = mapped_column(Integer, default=0)
    profile_views: Mapped[int] = mapped_column(Integer, default=0)
    website_visits: Mapped[int] = mapped_column(Integer, default=0)
    leads: Mapped[int] = mapped_column(Integer, default=0)
    meetings: Mapped[int] = mapped_column(Integer, default=0)
    # Share of tracked AI-assistant prompts that mention the client, 0-100.
    ai_visibility: Mapped[float] = mapped_column(Float, default=0.0)


class Activity(Base):
    __tablename__ = "activities"

    id: Mapped[int] = mapped_column(primary_key=True)
    client_id: Mapped[int | None] = mapped_column(
        ForeignKey("clients.id", ondelete="CASCADE"), nullable=True, index=True
    )
    user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    kind: Mapped[str] = mapped_column(String(40))
    message: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)

    user: Mapped[User | None] = relationship()

