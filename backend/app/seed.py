"""Demo data for Growth OS.

    python -m app.seed

Drops and recreates every table, then loads the agency team, 12 fictional
clients (3 live with history, 9 at different onboarding steps) and the
content, campaigns, leads, keywords, GEO checks and activity that make the
dashboards meaningful. All dates are relative to "now", so the demo always
looks current. Companies use the reserved .example domain.
"""

import random
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta

from sqlalchemy.orm import Session

from app.auth import hash_password
from app.database import Base, SessionLocal, engine
from app.models import (
    ACTION_VERBS,
    GEO_ENGINES,
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
    utcnow,
)
from app.post_templates import FRAMEWORKS, build_post

TEAM = (
    ("admin@growthos.dev", "Growth OS Admin", "admin", "admin123"),
    ("priya@growthos.dev", "Priya Sharma", "strategist", "team123"),
    ("arjun@growthos.dev", "Arjun Nair", "strategist", "team123"),
)
CLIENT_PASSWORD = "client123"


@dataclass
class Profile:
    name: str
    title: str
    company: str
    industry: str
    domain: str
    plan: str
    positioning: str
    brand_voice: str
    tone_tags: list[str]
    target_audience: str
    content_pillars: list[str]
    topics_to_avoid: str
    goals: list[str]
    channels: list[str]
    posting_cadence: int
    steps_done: int
    auto_approve_hours: int = 0
    # Live clients only.
    keywords: list[tuple[str, str, int, int, int | None, int | None]] = field(default_factory=list)
    geo_prompts: list[str] = field(default_factory=list)
    baseline: tuple[int, int, float] = (0, 0, 0.0)  # followers, weekly impressions, weekly growth
    deal_range: tuple[int, int] = (10_000, 40_000)
    review_ages: list[int] = field(default_factory=list)  # hours each client_review piece has waited


PROFILES: list[Profile] = [
    Profile(
        name="Ananya Rao",
        title="Founder & CEO",
        company="LedgerLoop",
        industry="Fintech",
        domain="ledgerloop.example",
        plan="scale",
        positioning="LedgerLoop automates accounts payable for mid-market finance teams, so CFOs close the books in days, not weeks.",
        brand_voice="Direct, numbers-first and practical. Speaks like a CFO who has done the job: no hype, concrete examples, one clear takeaway per post.",
        tone_tags=["direct", "data-driven", "pragmatic"],
        target_audience="CFOs and finance leaders at mid-market companies (200-2,000 employees) in India and Southeast Asia",
        content_pillars=["Finance automation", "The modern CFO", "Cash flow discipline", "Building a fintech in India"],
        topics_to_avoid="Competitor names, crypto, specific customer revenue figures, political commentary",
        goals=["Become a recognised voice for mid-market CFOs", "40 qualified demo requests per quarter", "Rank top 5 for 'AP automation India'"],
        channels=["linkedin", "x", "blog", "newsletter"],
        posting_cadence=4,
        steps_done=5,
        auto_approve_hours=48,
        keywords=[
            ("AP automation India", "commercial", 2400, 46, 4, 7),
            ("accounts payable automation", "commercial", 6600, 62, 11, 15),
            ("invoice processing software", "commercial", 5400, 58, 9, 8),
            ("month-end close checklist", "informational", 3600, 35, 3, 5),
            ("CFO dashboard metrics", "informational", 1900, 41, 6, 9),
            ("vendor payment automation", "transactional", 1300, 38, 5, 6),
            ("three-way matching", "informational", 2900, 30, 2, 4),
            ("GST invoice reconciliation", "informational", 4400, 44, 7, 12),
            ("cash flow forecasting template", "informational", 8100, 52, 14, 13),
            ("AP software for mid-market", "commercial", 720, 33, 3, None),
        ],
        geo_prompts=[
            "What is the best accounts payable automation software for mid-market companies in India?",
            "How can a CFO shorten the month-end close?",
            "Which fintech startups help finance teams automate vendor payments?",
        ],
        baseline=(4200, 16000, 0.06),
        deal_range=(15_000, 60_000),
        review_ages=[3, 9, 26, 60],
    ),
    Profile(
        name="Marcus Bell",
        title="Co-founder & CEO",
        company="Shiftwise",
        industry="HR tech",
        domain="shiftwise.example",
        plan="growth",
        positioning="Shiftwise is workforce scheduling for multi-site retailers and restaurants: fewer no-shows, happier hourly teams, lower overtime.",
        brand_voice="Warm, energetic and story-led. Champions frontline workers with real anecdotes from store floors, light humour, never preachy.",
        tone_tags=["warm", "story-led", "optimistic"],
        target_audience="COOs and HR leaders at multi-site retail and hospitality brands in the US and UK",
        content_pillars=["Frontline workforce", "Scheduling and labour costs", "Culture at scale", "Founder journey"],
        topics_to_avoid="Union politics, layoffs at named companies, wage-policy debates",
        goals=["Grow LinkedIn following to 10k", "25 enterprise pilots this year", "Own the 'frontline experience' conversation"],
        channels=["linkedin", "newsletter", "instagram"],
        posting_cadence=3,
        steps_done=5,
        keywords=[
            ("shift scheduling software", "commercial", 9900, 64, 12, 18),
            ("employee scheduling app", "commercial", 14800, 70, 21, 24),
            ("reduce overtime costs", "informational", 1600, 32, 4, 6),
            ("restaurant staff scheduling", "commercial", 3600, 48, 8, 11),
            ("retail workforce management", "commercial", 2900, 55, 15, 14),
            ("no-show policy for employees", "informational", 2400, 28, 5, 9),
            ("shift swap app", "transactional", 1300, 36, 6, 10),
            ("labor cost percentage restaurant", "informational", 4400, 40, 9, 7),
            ("frontline employee engagement", "informational", 1900, 45, 10, None),
        ],
        geo_prompts=[
            "What is the best shift scheduling software for restaurants?",
            "How do multi-site retailers reduce overtime costs?",
            "Which tools improve frontline employee retention?",
        ],
        baseline=(2600, 9000, 0.07),
        deal_range=(12_000, 45_000),
        review_ages=[5, 52, 75],
    ),
    Profile(
        name="Dr. Kavya Menon",
        title="Founder & CEO",
        company="CarePath Health",
        industry="Healthtech",
        domain="carepath.example",
        plan="scale",
        positioning="CarePath runs remote patient monitoring for chronic-care clinics, catching deterioration early and cutting readmissions.",
        brand_voice="Calm, evidence-based and empathetic. Clinician first, founder second. Cites research, explains simply, never overclaims outcomes.",
        tone_tags=["evidence-based", "empathetic", "clear"],
        target_audience="Hospital administrators, clinic owners and chief medical officers running chronic-care programmes",
        content_pillars=["Remote patient monitoring", "Clinical evidence", "Healthcare operations", "Women in health leadership"],
        topics_to_avoid="Medical advice to individuals, unverified outcome claims, patient-identifiable stories",
        goals=["Be the trusted clinical voice on RPM", "15 new clinic partners this half", "Get cited by AI assistants for RPM questions"],
        channels=["linkedin", "blog", "newsletter"],
        posting_cadence=3,
        steps_done=5,
        keywords=[
            ("remote patient monitoring", "commercial", 12100, 67, 14, 19),
            ("RPM for chronic care", "commercial", 1300, 39, 3, 5),
            ("reduce hospital readmissions", "informational", 5400, 51, 8, 12),
            ("RPM reimbursement", "informational", 3600, 47, 6, 6),
            ("heart failure remote monitoring", "informational", 1600, 42, 5, 8),
            ("care coordination software", "commercial", 2900, 58, 17, 16),
            ("chronic care management program", "commercial", 2400, 44, 9, 13),
            ("patient engagement platform", "commercial", 4400, 61, 22, 27),
            ("virtual ward", "informational", 6600, 49, 11, None),
            ("remote monitoring for diabetes", "informational", 3200, 37, 4, 7),
        ],
        geo_prompts=[
            "Which remote patient monitoring companies are best for chronic-care clinics?",
            "How can hospitals reduce readmissions for heart failure patients?",
            "What should a clinic look for in an RPM provider?",
        ],
        baseline=(6800, 22000, 0.05),
        deal_range=(25_000, 90_000),
        review_ages=[2, 20, 50],
    ),
    Profile(
        name="Rohan Mehta",
        title="Founder",
        company="Stackfold",
        industry="B2B SaaS",
        domain="stackfold.example",
        plan="growth",
        positioning="Stackfold shows engineering teams exactly where their cloud bill goes and fixes the waste automatically.",
        brand_voice="Technical but plain-spoken. Shows the numbers, shares code-level detail, a little dry wit.",
        tone_tags=["technical", "candid", "witty"],
        target_audience="CTOs and platform engineering leads at Series A-C SaaS companies",
        content_pillars=["Cloud cost engineering", "Platform teams", "Bootstrapping to Series A"],
        topics_to_avoid="Cloud-provider bashing, pricing of named customers",
        goals=["Launch founder-led content", "Drive 20 trials a month from content"],
        channels=["linkedin", "x", "blog"],
        posting_cadence=3,
        steps_done=4,
    ),
    Profile(
        name="Elena Petrova",
        title="CEO",
        company="Northwind Freight",
        industry="Logistics",
        domain="northwindfreight.example",
        plan="growth",
        positioning="Northwind Freight is a digital freight forwarder for European mid-market shippers, with live tracking and fixed-price quotes.",
        brand_voice="Confident, operational, plain English. Talks about real lanes, real delays and what fixed them.",
        tone_tags=["confident", "operational", "plain"],
        target_audience="Supply chain and logistics directors at European manufacturers and distributors",
        content_pillars=["Supply chain resilience", "Freight pricing", "Logistics tech"],
        topics_to_avoid="Geopolitics, competitor pricing",
        goals=["Build trust with enterprise shippers", "Generate 30 RFQs per quarter"],
        channels=["linkedin", "newsletter"],
        posting_cadence=2,
        steps_done=3,
    ),
    Profile(
        name="Vikram Iyer",
        title="Managing Partner",
        company="Banyan Ventures",
        industry="Venture capital",
        domain="banyan.example",
        plan="growth",
        positioning="Banyan Ventures backs pre-seed and seed B2B founders in India with a hands-on go-to-market bench.",
        brand_voice="Thoughtful, generous and founder-friendly. Shares frameworks and honest market reads, no portfolio bragging.",
        tone_tags=["thoughtful", "generous", "candid"],
        target_audience="Early-stage B2B founders in India and the Indian diaspora",
        content_pillars=["Fundraising", "Go-to-market for B2B", "Indian SaaS ecosystem", "Founder wellbeing"],
        topics_to_avoid="Portfolio company metrics, valuation gossip, deals not yet announced",
        goals=["Increase quality inbound deal flow", "Be top-of-mind for seed-stage B2B founders"],
        channels=["linkedin", "x", "newsletter"],
        posting_cadence=3,
        steps_done=2,
    ),
    Profile(
        name="Sophie Laurent",
        title="Founder & CEO",
        company="Verdant Grid",
        industry="Climate tech",
        domain="verdantgrid.example",
        plan="starter",
        positioning="Verdant Grid is software that helps utilities schedule battery storage to absorb more renewable energy.",
        brand_voice="Optimistic and precise. Mission-driven without being preachy; explains grid economics with simple analogies.",
        tone_tags=["optimistic", "precise", "mission-driven"],
        target_audience="Utility executives, grid operators and energy investors",
        content_pillars=["Grid-scale storage", "Energy transition economics", "Climate founders"],
        topics_to_avoid="Partisan politics, attacking fossil-fuel workers",
        goals=["Credibility with utility buyers", "Shape the Series A narrative"],
        channels=["linkedin", "blog"],
        posting_cadence=2,
        steps_done=1,
    ),
    Profile(
        name="Siddharth Kapoor",
        title="Co-founder & CEO",
        company="Clauseway",
        industry="Legal tech",
        domain="clauseway.example",
        plan="starter",
        positioning="Clauseway reviews commercial contracts in minutes and flags risky clauses for in-house legal teams.",
        brand_voice="Precise and a little playful. Demystifies legalese without dumbing it down.",
        tone_tags=["precise", "playful", "clear"],
        target_audience="General counsels and in-house legal teams at growth-stage companies",
        content_pillars=["Contract risk", "Legal operations", "AI in law"],
        topics_to_avoid="Advice on specific legal cases, criticising law firms by name",
        goals=["Launch thought leadership", "Book 10 GC demos a month"],
        channels=["linkedin"],
        posting_cadence=2,
        steps_done=0,
    ),
    Profile(
        name="Nisha Agarwal",
        title="Founder",
        company="Kiko Kids",
        industry="D2C",
        domain="kikokids.example",
        plan="growth",
        positioning="Kiko Kids makes organic-cotton kidswear designed in India and sold direct to parents.",
        brand_voice="Playful, warm and honest about the messy reality of building a D2C brand while parenting.",
        tone_tags=["playful", "warm", "honest"],
        target_audience="Millennial parents in Indian metros, and fellow D2C founders",
        content_pillars=["Building a D2C brand", "Sustainable fashion", "Parenting and work"],
        topics_to_avoid="Body image, comparisons with named brands",
        goals=["Grow the founder audience on Instagram and LinkedIn", "Drive repeat purchases"],
        channels=["instagram", "linkedin"],
        posting_cadence=4,
        steps_done=2,
    ),
    Profile(
        name="Daniel Okafor",
        title="CEO",
        company="Sentinel Shield",
        industry="Cybersecurity",
        domain="sentinelshield.example",
        plan="scale",
        positioning="Sentinel Shield is managed detection and response for mid-sized companies that can't staff a 24/7 security team.",
        brand_voice="Calm authority. Explains threats without fear-mongering; practical checklists over scare stories.",
        tone_tags=["calm", "authoritative", "practical"],
        target_audience="CIOs, IT directors and risk owners at mid-sized companies in the UK and Africa",
        content_pillars=["Practical security", "Incident response", "Security leadership"],
        topics_to_avoid="Naming breached companies, sharing exploit details",
        goals=["Board-level credibility", "25 MDR assessments per quarter"],
        channels=["linkedin", "blog", "newsletter"],
        posting_cadence=3,
        steps_done=4,
    ),
    Profile(
        name="Meera Pillai",
        title="Co-founder",
        company="Learnloft",
        industry="Edtech",
        domain="learnloft.example",
        plan="starter",
        positioning="Learnloft runs cohort-based upskilling programmes for engineering managers at Indian tech companies.",
        brand_voice="Encouraging and practical, a teacher at heart. Every post leaves the reader with one thing to try.",
        tone_tags=["encouraging", "practical", "clear"],
        target_audience="L&D heads and engineering leaders at Indian tech companies",
        content_pillars=["Manager development", "Learning that sticks", "Careers in tech"],
        topics_to_avoid="Ranking colleges, salary gossip",
        goals=["Fill 4 corporate cohorts", "Launch a newsletter"],
        channels=["linkedin", "newsletter"],
        posting_cadence=3,
        steps_done=1,
    ),
    Profile(
        name="James Whitaker",
        title="Founding Principal",
        company="Harbor & Hale",
        industry="Real estate",
        domain="harborhale.example",
        plan="starter",
        positioning="Harbor & Hale advises family offices on commercial real estate in coastal US markets.",
        brand_voice="Measured, discreet and long-term. Prefers one well-argued idea to a stream of hot takes.",
        tone_tags=["measured", "discreet", "insightful"],
        target_audience="Family office principals and private investors",
        content_pillars=["Commercial real estate cycles", "Coastal markets", "Long-term investing"],
        topics_to_avoid="Specific deal terms, client names, interest-rate predictions",
        goals=["Discreet visibility with family offices", "Speaking invitations"],
        channels=["linkedin", "newsletter"],
        posting_cadence=1,
        steps_done=0,
    ),
]

PROSPECTS = (
    ("Neha Gupta", "VP Finance", "Brightcart"),
    ("Tom Fischer", "CFO", "Alpenhaus Retail"),
    ("Aditi Shah", "Head of Operations", "UrbanNest"),
    ("Liam O'Connor", "Finance Director", "Greenway Foods"),
    ("Fatima Khan", "Controller", "Medilink Labs"),
    ("Rahul Verma", "COO", "QuickServe"),
    ("Grace Kim", "VP People", "Bluefin Hotels"),
    ("Carlos Mendes", "Head of HR", "Casa Verde Group"),
    ("Priyanka Das", "CMO", "Wellnest Clinics"),
    ("Ben Carter", "Director of Operations", "Harbourline"),
    ("Ishaan Malhotra", "Founder", "Tiffin Box"),
    ("Sara Lindqvist", "CFO", "Nordic Pantry"),
    ("Kenji Watanabe", "VP Engineering", "Kumo Systems"),
    ("Olivia Brooks", "Chief Nursing Officer", "Riverside Health"),
    ("Arnav Joshi", "Head of Finance", "PayrollPal"),
    ("Hannah Weiss", "Operations Lead", "Freshcrate"),
    ("Dev Patel", "Medical Director", "Sunrise Care"),
    ("Emily Zhang", "HR Director", "Lotus Retail"),
    ("Mohammed Ali", "Finance Manager", "Desert Rose Trading"),
    ("Chloe Martin", "COO", "Bistro Collective"),
    ("Ravi Krishnan", "CTO", "Finlytics"),
    ("Julia Novak", "Head of Clinical Ops", "Vita Clinics"),
    ("Ankit Bansal", "CFO", "Cartwheel Logistics"),
    ("Megan Riley", "VP Store Operations", "Peak Outfitters"),
)

CHANGE_NOTES = (
    "Tone is a bit too salesy. Can we make it more personal, like I'm talking to one CFO?",
    "Please remove the stat in the second line; we can't share that publicly yet.",
    "Love the idea, but let's hold it until after our launch next week and add the launch angle.",
)
CLIENT_COMMENTS = (
    "Looks good. Can we add a line about our customer community?",
    "Happy with this one. Could the hook be a little shorter?",
)
LEAD_NOTES = (
    "Engaged with three posts before reaching out.",
    "Asked for a case study from a similar company.",
    "Budget confirmed for next quarter.",
    "Intro via a mutual investor.",
    "",
)

# The sequence of actions that leads a piece to each status.
_PATHS = {
    "idea": [],
    "draft": [],
    "internal_review": ["submit"],
    "client_review": ["submit", "send_to_client"],
    "changes_requested": ["submit", "send_to_client", "request_changes"],
    "approved": ["submit", "send_to_client", "approve"],
    "scheduled": ["submit", "send_to_client", "approve", "schedule"],
    "published": ["submit", "send_to_client", "approve", "schedule", "publish"],
}
_TARGET = {
    "submit": "internal_review",
    "send_to_client": "client_review",
    "approve": "approved",
    "request_changes": "changes_requested",
    "schedule": "scheduled",
    "publish": "published",
}
_FORMAT_BY_CHANNEL = {
    "linkedin": "post",
    "x": "thread",
    "blog": "article",
    "newsletter": "article",
    "instagram": "carousel",
}
_IMPRESSION_RANGE = {
    "linkedin": (2500, 14000),
    "x": (900, 6000),
    "blog": (300, 2600),
    "newsletter": (1200, 4200),
    "instagram": (1500, 9000),
}


def reset_schema() -> None:
    from app import models  # noqa: F401  (registers tables)

    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


class _Seeder:
    def __init__(self, db: Session, now: datetime) -> None:
        self.db = db
        self.now = now
        self.today = now.date()
        self.rng = random.Random(42)

    # --- helpers ------------------------------------------------------------

    def activity(
        self, client: Client, user: User | None, kind: str, message: str, at: datetime
    ) -> None:
        self.db.add(
            Activity(
                client_id=client.id,
                user_id=user.id if user else None,
                kind=kind,
                message=message,
                created_at=at,
            )
        )

    def event(
        self,
        client: Client,
        piece: ContentPiece,
        user: User | None,
        action: str,
        from_status: str | None,
        to_status: str | None,
        at: datetime,
        note: str = "",
    ) -> None:
        self.db.add(
            ApprovalEvent(
                content_id=piece.id,
                user_id=user.id if user else None,
                action=action,
                from_status=from_status,
                to_status=to_status,
                note=note,
                created_at=at,
            )
        )
        actor = user.name if user else "System"
        self.activity(client, user, f"content.{action}", f"{actor} {ACTION_VERBS[action]} “{piece.title}”", at)

    # --- people -------------------------------------------------------------

    def team(self) -> list[User]:
        users = [
            User(email=email, name=name, role=role, password_hash=hash_password(password))
            for email, name, role, password in TEAM
        ]
        self.db.add_all(users)
        self.db.flush()
        return users

    def client(self, number: int, profile: Profile, manager: User) -> tuple[Client, User]:
        steps = {step: i < profile.steps_done for i, step in enumerate(ONBOARDING_STEPS)}
        live = profile.steps_done == len(ONBOARDING_STEPS)
        joined = self.now - timedelta(days=95 if live else 3 + 4 * profile.steps_done)
        client = Client(
            name=profile.name,
            title=profile.title,
            email=f"{profile.name.removeprefix('Dr. ').split()[0].lower()}@{profile.domain}",
            company=profile.company,
            industry=profile.industry,
            website=f"https://{profile.domain}",
            plan=profile.plan,
            status="active" if live else "onboarding",
            positioning=profile.positioning,
            brand_voice=profile.brand_voice,
            tone_tags=profile.tone_tags,
            target_audience=profile.target_audience,
            content_pillars=profile.content_pillars,
            topics_to_avoid=profile.topics_to_avoid,
            goals=profile.goals,
            channels=profile.channels,
            posting_cadence=profile.posting_cadence,
            auto_approve_hours=profile.auto_approve_hours,
            onboarding=steps,
            account_manager_id=manager.id,
            start_date=(self.today - timedelta(days=84)) if live else None,
            created_at=joined,
        )
        self.db.add(client)
        self.db.flush()

        login = User(
            email=f"client{number}@growthos.dev",
            name=profile.name,
            role="client",
            client_id=client.id,
            password_hash=hash_password(CLIENT_PASSWORD),
            created_at=joined,
        )
        self.db.add(login)
        self.db.flush()

        self.activity(client, manager, "client.created", f"{manager.name} added {client.name} ({client.company})", joined)
        for i, step in enumerate(ONBOARDING_STEPS[: profile.steps_done]):
            at = joined + timedelta(days=2 + 3 * i, hours=self.rng.randint(1, 8))
            self.activity(client, manager, "onboarding.step", f"Onboarding: “{ONBOARDING_LABELS[step]}” completed for {client.name}", at)
        if live:
            self.activity(client, manager, "client.live", f"{client.name} is live", joined + timedelta(days=11))
        return client, login

    # --- content ------------------------------------------------------------

    def piece(
        self,
        client: Client,
        status: str,
        changed_at: datetime,
        index: int,
        strategist: User,
        client_user: User,
        campaigns: dict[str, Campaign],
        *,
        channel: str | None = None,
        ai: bool = False,
    ) -> ContentPiece:
        channel = channel or client.channels[index % len(client.channels)]
        pillar = client.content_pillars[index % len(client.content_pillars)]
        draft = build_post(
            client,
            channel=channel,
            pillar=pillar,
            framework=FRAMEWORKS[index % len(FRAMEWORKS)],
            index=index,
            day=changed_at.date(),
        )
        campaign = None
        if campaigns:
            if channel == "blog":
                campaign = campaigns["performance"]
            elif channel == "linkedin":
                campaign = campaigns["personal_brand" if index % 2 else "content"]
            else:
                campaign = campaigns["content"]

        scheduled_for = None
        if status == "scheduled":
            # changed_at is the publish slot; the scheduling itself happened recently.
            scheduled_for = changed_at
            changed_at = self.now - timedelta(hours=self.rng.randint(6, 30))

        path = _PATHS[status]
        step = timedelta(hours=self.rng.randint(14, 30))
        created_at = changed_at - step * (len(path) + 1)
        piece = ContentPiece(
            client_id=client.id,
            campaign_id=campaign.id if campaign else None,
            title=draft.title,
            channel=channel,
            format=_FORMAT_BY_CHANNEL[channel],
            pillar=pillar,
            body=draft.body,
            hashtags=draft.hashtags,
            target_keyword="",
            status=status,
            status_changed_at=changed_at,
            ai_generated=ai,
            ai_source="template" if ai else "",
            created_by_id=strategist.id,
            created_at=created_at,
            updated_at=changed_at,
        )
        if status == "published":
            piece.published_at = changed_at
            piece.scheduled_at = changed_at
            low, high = _IMPRESSION_RANGE[channel]
            piece.impressions = self.rng.randint(low, high)
            piece.engagements = int(piece.impressions * self.rng.uniform(0.02, 0.06))
            piece.clicks = int(piece.impressions * self.rng.uniform(0.005, 0.02))
            piece.leads_generated = self.rng.choice((0, 0, 1, 1, 2, 3))
        elif status == "scheduled":
            piece.scheduled_at = scheduled_for
        self.db.add(piece)
        self.db.flush()

        initial = "idea" if status == "idea" else "draft"
        self.event(client, piece, strategist, "create", None, initial, created_at)
        current, at = initial, created_at
        for action in path:
            at = changed_at if action == path[-1] else at + step
            if status == "published" and action == "schedule":
                at = changed_at - timedelta(days=1)
            actor = client_user if action in ("approve", "request_changes") else strategist
            note = ""
            if action == "request_changes":
                note = CHANGE_NOTES[index % len(CHANGE_NOTES)]
            self.event(client, piece, actor, action, current, _TARGET[action], at, note)
            current = _TARGET[action]
        if status == "client_review" and index % 3 == 0:
            comment_at = min(self.now, changed_at + timedelta(hours=1))
            self.event(client, piece, client_user, "comment", status, status, comment_at,
                       CLIENT_COMMENTS[index % len(CLIENT_COMMENTS)])
        return piece

    def live_content(
        self,
        client: Client,
        profile: Profile,
        strategist: User,
        client_user: User,
        campaigns: dict[str, Campaign],
    ) -> list[ContentPiece]:
        def hours(h: int) -> datetime:
            return self.now - timedelta(hours=h)

        plan: list[tuple[str, datetime, dict]] = []
        for days_ago in (3, 8, 12, 17, 22, 29, 36, 43, 52):
            plan.append(("published", hours(days_ago * 24 + self.rng.randint(0, 10)), {}))
        plan += [
            ("scheduled", self.now + timedelta(days=2, hours=3), {}),
            ("scheduled", self.now + timedelta(days=6, hours=5), {}),
            ("approved", hours(20), {}),
            ("approved", hours(31), {}),
        ]
        plan += [("client_review", hours(age), {}) for age in profile.review_ages]
        plan += [
            ("changes_requested", hours(30), {}),
            ("internal_review", hours(6), {}),
            ("draft", hours(4), {"ai": True}),
            ("draft", hours(27), {}),
            ("idea", hours(50), {}),
        ]
        return [
            self.piece(client, status, at, i, strategist, client_user, campaigns, **extra)
            for i, (status, at, extra) in enumerate(plan)
        ]

    def campaigns(self, client: Client) -> dict[str, Campaign]:
        first = client.name.replace("Dr. ", "").split()[0]
        pillar = client.content_pillars[0]
        specs = {
            "content": (
                f"Thought leadership engine: {pillar}",
                f"Publish consistently on {pillar.lower()} to build category authority.",
                -56, 35, {"posts": 14, "impressions": 90000, "engagements": 3500},
            ),
            "personal_brand": (
                f"{first}'s founder voice on LinkedIn",
                f"{client.goals[0]}.",
                -84, 7, {"posts": 10, "impressions": 70000, "engagements": 2800},
            ),
            "lead_gen": (
                f"Demand capture: {client.content_pillars[1]}",
                "Turn content engagement into qualified meetings.",
                -42, 48, {"leads": 12, "meetings": 5},
            ),
            "performance": (
                "Search and AI-assistant visibility",
                "Rank for buying-intent keywords and get cited by AI assistants.",
                -70, 90, {"posts": 4, "impressions": 8000, "leads": 4},
            ),
        }
        result: dict[str, Campaign] = {}
        for kind, (name, objective, start, end, kpis) in specs.items():
            campaign = Campaign(
                client_id=client.id,
                name=name,
                type=kind,
                status="active",
                objective=objective,
                channels=[c for c in client.channels if c != "instagram"][:2] or client.channels[:1],
                start_date=self.today + timedelta(days=start),
                end_date=self.today + timedelta(days=end),
                kpi_targets=kpis,
                created_at=self.now + timedelta(days=start - 3),
            )
            self.db.add(campaign)
            result[kind] = campaign
        self.db.flush()
        return result

    # --- results ------------------------------------------------------------

    def snapshots(self, client: Client, profile: Profile) -> None:
        followers, impressions, growth = profile.baseline
        monday = self.today - timedelta(days=self.today.weekday())
        for week in range(12, 0, -1):
            i = 12 - week
            trend = (1 + growth) ** i
            weekly = int(impressions * trend * self.rng.uniform(0.88, 1.12))
            engagements = int(weekly * self.rng.uniform(0.032, 0.05))
            visits = int(weekly * self.rng.uniform(0.005, 0.008))
            leads = max(1, round(visits * 0.05 + self.rng.uniform(-1, 1.5)))
            followers += int(weekly * self.rng.uniform(0.003, 0.005))
            self.db.add(
                MetricSnapshot(
                    client_id=client.id,
                    week_start=monday - timedelta(weeks=week),
                    followers=followers,
                    impressions=weekly,
                    engagements=engagements,
                    profile_views=int(weekly * self.rng.uniform(0.01, 0.015)),
                    website_visits=visits,
                    leads=leads,
                    meetings=max(0, round(leads * self.rng.uniform(0.25, 0.45))),
                    ai_visibility=round(min(60.0, 6 + i * 2.1 + self.rng.uniform(-2, 2)), 1),
                )
            )

    def leads(
        self,
        client: Client,
        profile: Profile,
        published: list[ContentPiece],
        campaign: Campaign,
    ) -> None:
        stages = ("new", "new", "new", "contacted", "contacted", "engaged", "engaged",
                  "meeting_booked", "meeting_booked", "proposal", "won", "won", "lost")
        score_by_stage = {"new": 45, "contacted": 55, "engaged": 65, "meeting_booked": 75,
                          "proposal": 82, "won": 95, "lost": 30}
        people = self.rng.sample(PROSPECTS, len(stages))
        for i, (stage, (name, title, company)) in enumerate(zip(stages, people, strict=True)):
            created = self.now - timedelta(days=self.rng.randint(5, 60), hours=self.rng.randint(0, 20))
            from_content = i % 2 == 0 and bool(published)
            source = "content" if from_content else self.rng.choice(("inbound", "outbound", "referral"))
            changed = created + (self.now - created) * self.rng.uniform(0.3, 0.9)
            if stage == "won":
                changed = self.now - timedelta(days=self.rng.randint(2, 24))
                created = min(created, changed - timedelta(days=10))
            slug = name.lower().replace("'", "").replace(" ", ".")
            self.db.add(
                Lead(
                    client_id=client.id,
                    campaign_id=campaign.id if i % 3 != 2 else None,
                    content_id=published[i % len(published)].id if from_content else None,
                    name=name,
                    title=title,
                    company=company,
                    email=f"{slug}@{company.lower().replace(' ', '')}.example",
                    linkedin_url=f"https://www.linkedin.com/in/{slug.replace('.', '-')}",
                    source=source,
                    stage=stage,
                    score=min(100, score_by_stage[stage] + self.rng.randint(-5, 5)),
                    deal_value=round(self.rng.randint(*profile.deal_range), -3),
                    notes=LEAD_NOTES[i % len(LEAD_NOTES)],
                    created_at=created,
                    stage_changed_at=changed,
                    updated_at=changed,
                )
            )

    def keywords(self, client: Client, profile: Profile) -> None:
        for keyword, intent, volume, difficulty, current, previous in profile.keywords:
            if previous is None:
                trend = "new"
            elif current is not None and current < previous:
                trend = "up"
            elif current is not None and current > previous:
                trend = "down"
            else:
                trend = "flat"
            self.db.add(
                Keyword(
                    client_id=client.id,
                    keyword=keyword,
                    intent=intent,
                    search_volume=volume,
                    difficulty=difficulty,
                    current_rank=current,
                    previous_rank=previous,
                    trend=trend,
                    target_url=f"{client.website}/blog/{keyword.lower().replace(' ', '-')}",
                    updated_at=self.now - timedelta(days=self.rng.randint(1, 6)),
                )
            )

    def geo(self, client: Client, profile: Profile) -> None:
        likelihood = {"chatgpt": 0.55, "perplexity": 0.7, "gemini": 0.4, "claude": 0.5}
        for prompt in profile.geo_prompts:
            for engine_name in GEO_ENGINES:
                mentioned = self.rng.random() < likelihood[engine_name]
                position = self.rng.randint(1, 5) if mentioned else None
                excerpt = (
                    f"Simulated answer: lists {client.company} at position {position} among recommended providers."
                    if mentioned
                    else f"Simulated answer: recommends other providers; {client.company} is not mentioned."
                )
                self.db.add(
                    GeoCheck(
                        client_id=client.id,
                        prompt=prompt,
                        engine=engine_name,
                        mentioned=mentioned,
                        position=position,
                        method="simulated",
                        excerpt=excerpt,
                        checked_at=self.now - timedelta(days=self.rng.randint(1, 5)),
                    )
                )

    def onboarding_content(self, client: Client, strategist: User, client_user: User) -> None:
        plan = (("draft", 30), ("internal_review", 12), ("client_review", 10))
        for i, (status, age) in enumerate(plan):
            self.piece(client, status, self.now - timedelta(hours=age), i, strategist, client_user, {},
                       channel=client.channels[0], ai=i == 0)

    # --- entry point ----------------------------------------------------------

    def run(self) -> dict[str, int]:
        admin, priya, arjun = self.team()
        strategists = (priya, arjun)
        for number, profile in enumerate(PROFILES, start=1):
            manager = strategists[(number - 1) % 2]
            client, client_user = self.client(number, profile, manager)
            if profile.steps_done == len(ONBOARDING_STEPS):
                campaigns = self.campaigns(client)
                pieces = self.live_content(client, profile, manager, client_user, campaigns)
                published = [p for p in pieces if p.status == "published"]
                self.snapshots(client, profile)
                self.leads(client, profile, published, campaigns["lead_gen"])
                self.keywords(client, profile)
                self.geo(client, profile)
            elif profile.steps_done >= 3:
                self.onboarding_content(client, manager, client_user)
        self.db.commit()
        return {"team": len(TEAM), "clients": len(PROFILES)}


def seed(db: Session, now: datetime | None = None) -> dict[str, int]:
    """Load demo data into an empty schema. Returns a small summary."""
    return _Seeder(db, now or utcnow()).run()


def _print_credentials() -> None:
    rows = [(email, password, role) for email, _, role, password in TEAM]
    rows += [
        (f"client{i}@growthos.dev", CLIENT_PASSWORD, f"client: {p.name}, {p.company}"
         + (" (live)" if p.steps_done == len(ONBOARDING_STEPS) else f" (onboarding {p.steps_done}/5)"))
        for i, p in enumerate(PROFILES, start=1)
    ]
    width = max(len(r[0]) for r in rows)
    print("\nDemo credentials")
    print("-" * 72)
    for email, password, role in rows:
        print(f"{email:<{width}}  {password:<10}  {role}")
    print()


def main() -> None:
    reset_schema()
    with SessionLocal() as db:
        summary = seed(db)
    print(f"Seeded {summary['clients']} clients and {summary['team']} team users.")
    _print_credentials()


if __name__ == "__main__":
    main()
