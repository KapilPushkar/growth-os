"""Pydantic request bodies. Vocabulary fields are validated against models.py."""

import re
from collections.abc import Callable, Sequence
from datetime import date, datetime
from typing import Annotated

from pydantic import AfterValidator, BaseModel, ConfigDict, Field

from app.models import (
    CAMPAIGN_KPIS,
    CAMPAIGN_STATUSES,
    CAMPAIGN_TYPES,
    CHANNELS,
    CLIENT_STATUSES,
    FORMATS,
    GEO_ENGINES,
    KEYWORD_INTENTS,
    LEAD_SOURCES,
    LEAD_STAGES,
    ONBOARDING_STEPS,
    OUTREACH_KINDS,
    PLANS,
)

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _one_of(allowed: Sequence[str], label: str) -> Callable[[str], str]:
    def check(value: str) -> str:
        if value not in allowed:
            raise ValueError(f"{label} must be one of: {', '.join(allowed)}")
        return value

    return check


def _all_of(allowed: Sequence[str], label: str) -> Callable[[list[str]], list[str]]:
    check = _one_of(allowed, label)

    def check_all(values: list[str]) -> list[str]:
        for value in values:
            check(value)
        return list(dict.fromkeys(values))  # de-duplicate, keep order

    return check_all


def _email(value: str) -> str:
    value = value.strip().lower()
    if not _EMAIL_RE.match(value):
        raise ValueError("must be a valid email address")
    return value


def _strip_list(values: list[str]) -> list[str]:
    return [v.strip() for v in values if v and v.strip()]


Email = Annotated[str, AfterValidator(_email)]
Channel = Annotated[str, AfterValidator(_one_of(CHANNELS, "channel"))]
Channels = Annotated[list[str], AfterValidator(_all_of(CHANNELS, "channel"))]
Format = Annotated[str, AfterValidator(_one_of(FORMATS, "format"))]
Plan = Annotated[str, AfterValidator(_one_of(PLANS, "plan"))]
ClientStatus = Annotated[str, AfterValidator(_one_of(CLIENT_STATUSES, "status"))]
CampaignType = Annotated[str, AfterValidator(_one_of(CAMPAIGN_TYPES, "type"))]
CampaignStatus = Annotated[str, AfterValidator(_one_of(CAMPAIGN_STATUSES, "status"))]
LeadStage = Annotated[str, AfterValidator(_one_of(LEAD_STAGES, "stage"))]
LeadSource = Annotated[str, AfterValidator(_one_of(LEAD_SOURCES, "source"))]
Intent = Annotated[str, AfterValidator(_one_of(KEYWORD_INTENTS, "intent"))]
Engines = Annotated[list[str], AfterValidator(_all_of(GEO_ENGINES, "engine"))]
OnboardingStep = Annotated[str, AfterValidator(_one_of(ONBOARDING_STEPS, "step"))]
OutreachKind = Annotated[str, AfterValidator(_one_of(OUTREACH_KINDS, "kind"))]
TextList = Annotated[list[str], AfterValidator(_strip_list)]


class Body(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


# --- Auth -------------------------------------------------------------------


class LoginIn(Body):
    email: str
    password: str


# --- Clients ----------------------------------------------------------------


class BrandProfile(Body):
    positioning: str = ""
    brand_voice: str = ""
    tone_tags: TextList = []
    target_audience: str = ""
    content_pillars: TextList = []
    topics_to_avoid: str = ""
    goals: TextList = []


class ClientCreate(BrandProfile):
    name: str = Field(min_length=1, max_length=120)
    title: str = ""
    email: Email | None = None
    company: str = Field(min_length=1, max_length=160)
    industry: str = ""
    website: str = ""
    plan: Plan = "growth"
    channels: Channels = ["linkedin"]
    posting_cadence: int = Field(default=3, ge=0, le=21)
    auto_approve_hours: int = Field(default=0, ge=0, le=720)
    account_manager_id: int | None = None
    create_login: bool = True


class ClientUpdate(Body):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    title: str | None = None
    email: Email | None = None
    company: str | None = Field(default=None, min_length=1, max_length=160)
    industry: str | None = None
    website: str | None = None
    plan: Plan | None = None
    status: ClientStatus | None = None
    positioning: str | None = None
    brand_voice: str | None = None
    tone_tags: TextList | None = None
    target_audience: str | None = None
    content_pillars: TextList | None = None
    topics_to_avoid: str | None = None
    goals: TextList | None = None
    channels: Channels | None = None
    posting_cadence: int | None = Field(default=None, ge=0, le=21)
    auto_approve_hours: int | None = Field(default=None, ge=0, le=720)
    account_manager_id: int | None = None


class OnboardingUpdate(Body):
    step: OnboardingStep
    done: bool = True


# --- Content ----------------------------------------------------------------


class ContentCreate(Body):
    client_id: int
    campaign_id: int | None = None
    title: str = ""
    channel: Channel
    format: Format = "post"
    pillar: str = ""
    body: str = ""
    hashtags: TextList = []
    target_keyword: str = ""
    status: Annotated[str, AfterValidator(_one_of(("idea", "draft"), "status"))] = "draft"


class ContentUpdate(Body):
    campaign_id: int | None = None
    title: str | None = None
    channel: Channel | None = None
    format: Format | None = None
    pillar: str | None = None
    body: str | None = None
    hashtags: TextList | None = None
    target_keyword: str | None = None


class TransitionIn(Body):
    action: str
    note: str = ""
    scheduled_at: datetime | None = None


class BulkTransitionIn(TransitionIn):
    ids: list[int] = Field(min_length=1, max_length=200)


# --- Campaigns --------------------------------------------------------------


def _kpis(value: dict[str, int]) -> dict[str, int]:
    for key, target in value.items():
        if key not in CAMPAIGN_KPIS:
            raise ValueError(f"KPI must be one of: {', '.join(CAMPAIGN_KPIS)}")
        if target < 0:
            raise ValueError("KPI targets must be zero or more")
    return value


KpiTargets = Annotated[dict[str, int], AfterValidator(_kpis)]


class CampaignCreate(Body):
    client_id: int
    name: str = Field(min_length=1, max_length=160)
    type: CampaignType
    status: CampaignStatus = "planned"
    objective: str = ""
    channels: Channels = []
    start_date: date | None = None
    end_date: date | None = None
    kpi_targets: KpiTargets = {}


class CampaignUpdate(Body):
    name: str | None = Field(default=None, min_length=1, max_length=160)
    type: CampaignType | None = None
    status: CampaignStatus | None = None
    objective: str | None = None
    channels: Channels | None = None
    start_date: date | None = None
    end_date: date | None = None
    kpi_targets: KpiTargets | None = None


# --- Leads ------------------------------------------------------------------


class LeadCreate(Body):
    client_id: int
    campaign_id: int | None = None
    content_id: int | None = None
    name: str = Field(min_length=1, max_length=120)
    title: str = ""
    company: str = ""
    email: str = ""
    linkedin_url: str = ""
    source: LeadSource = "inbound"
    stage: LeadStage = "new"
    score: int = Field(default=50, ge=0, le=100)
    deal_value: float = Field(default=0, ge=0)
    notes: str = ""


class LeadUpdate(Body):
    campaign_id: int | None = None
    content_id: int | None = None
    name: str | None = Field(default=None, min_length=1, max_length=120)
    title: str | None = None
    company: str | None = None
    email: str | None = None
    linkedin_url: str | None = None
    source: LeadSource | None = None
    stage: LeadStage | None = None
    score: int | None = Field(default=None, ge=0, le=100)
    deal_value: float | None = Field(default=None, ge=0)
    notes: str | None = None


# --- SEO / GEO --------------------------------------------------------------


class KeywordItem(Body):
    keyword: str = Field(min_length=1, max_length=160)
    intent: Intent = "informational"
    search_volume: int = Field(default=0, ge=0)
    difficulty: int = Field(default=0, ge=0, le=100)
    target_url: str = ""


class KeywordCreate(KeywordItem):
    client_id: int


class KeywordBulk(Body):
    client_id: int
    keywords: list[KeywordItem] = Field(min_length=1, max_length=100)


class ClientRef(Body):
    client_id: int


class GeoRunIn(Body):
    client_id: int
    prompt: str = Field(min_length=3, max_length=500)
    engines: Engines = list(GEO_ENGINES)


# --- AI ---------------------------------------------------------------------


class GenerateContentIn(Body):
    client_id: int
    channel: Channel = "linkedin"
    format: Format = "post"
    pillar: str = ""
    topic: str = ""
    keyword: str = ""
    count: int = Field(default=1, ge=1, le=5)
    campaign_id: int | None = None


class TopicsIn(Body):
    client_id: int
    count: int = Field(default=6, ge=1, le=10)


class KeywordIdeasIn(Body):
    client_id: int
    seed: str = ""
    count: int = Field(default=8, ge=1, le=20)


class OutreachIn(Body):
    lead_id: int
    kind: OutreachKind = "connection_note"


class RepurposeIn(Body):
    content_id: int
    channel: Channel
    format: Format | None = None
