from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app import ai
from app.auth import get_current_user, require_team
from app.database import get_db
from app.models import Campaign, ContentPiece, Lead, User
from app.routers.common import load_client, load_content, load_owned
from app.schemas import GenerateContentIn, KeywordIdeasIn, OutreachIn, RepurposeIn, TopicsIn
from app.serializers import content_out
from app.services import record_event

router = APIRouter(prefix="/ai", tags=["ai"])

DEFAULT_FORMAT = {
    "linkedin": "post",
    "x": "thread",
    "blog": "article",
    "newsletter": "article",
    "instagram": "carousel",
}


def _save_draft(
    db: Session,
    user: User,
    *,
    client_id: int,
    source: str,
    channel: str,
    content_format: str,
    draft: dict,
    keyword: str = "",
    campaign_id: int | None = None,
    note: str,
) -> ContentPiece:
    """AI output always lands as a draft and goes through the approval layer."""
    piece = ContentPiece(
        client_id=client_id,
        campaign_id=campaign_id,
        title=draft["title"],
        channel=channel,
        format=content_format,
        pillar=draft.get("pillar", ""),
        body=draft["body"],
        hashtags=draft.get("hashtags", []),
        target_keyword=keyword,
        status="draft",
        ai_generated=True,
        ai_source=source,
        created_by_id=user.id,
    )
    db.add(piece)
    db.flush()
    record_event(db, piece, user, "create", None, "draft", f"{note} ({source})")
    return piece


@router.get("/status")
def ai_status(_: User = Depends(get_current_user)) -> dict:
    return ai.status()


@router.post("/generate-content")
def generate_content(
    body: GenerateContentIn, user: User = Depends(require_team), db: Session = Depends(get_db)
) -> dict:
    client = load_client(db, user, body.client_id)
    if body.campaign_id is not None:
        campaign = db.get(Campaign, body.campaign_id)
        if campaign is None or campaign.client_id != client.id:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Campaign does not belong to this client")
    drafts, source = ai.generate_content(
        client,
        channel=body.channel,
        content_format=body.format,
        pillar=body.pillar,
        topic=body.topic,
        keyword=body.keyword,
        count=body.count,
    )
    pieces = [
        _save_draft(
            db,
            user,
            client_id=client.id,
            source=source,
            channel=body.channel,
            content_format=body.format,
            draft=draft,
            keyword=body.keyword,
            campaign_id=body.campaign_id,
            note="AI draft generated",
        )
        for draft in drafts
    ]
    db.commit()
    return {"items": [content_out(p) for p in pieces], "source": source}


@router.post("/topics")
def topics(body: TopicsIn, user: User = Depends(require_team), db: Session = Depends(get_db)) -> dict:
    client = load_client(db, user, body.client_id)
    items, source = ai.trending_topics(client, body.count)
    return {"topics": items, "source": source}


@router.post("/keywords")
def keyword_ideas(
    body: KeywordIdeasIn, user: User = Depends(require_team), db: Session = Depends(get_db)
) -> dict:
    client = load_client(db, user, body.client_id)
    items, source = ai.suggest_keywords(client, body.seed, body.count)
    return {
        "keywords": items,
        "source": source,
        "note": "Search volume and difficulty are estimates until an SEO data provider is connected.",
    }


@router.post("/outreach")
def outreach(body: OutreachIn, user: User = Depends(require_team), db: Session = Depends(get_db)) -> dict:
    lead = load_owned(db, user, Lead, body.lead_id)
    client = load_client(db, user, lead.client_id)
    post = db.get(ContentPiece, lead.content_id) if lead.content_id else None
    message, source = ai.outreach_message(client, lead, body.kind, post)
    return {**message, "lead_id": lead.id, "source": source}


@router.post("/repurpose")
def repurpose(
    body: RepurposeIn, user: User = Depends(require_team), db: Session = Depends(get_db)
) -> dict:
    original = load_content(db, user, body.content_id)
    client = load_client(db, user, original.client_id)
    content_format = body.format or DEFAULT_FORMAT[body.channel]
    draft, source = ai.repurpose(client, original, body.channel, content_format)
    draft["pillar"] = original.pillar
    piece = _save_draft(
        db,
        user,
        client_id=client.id,
        source=source,
        channel=body.channel,
        content_format=content_format,
        draft=draft,
        keyword=original.target_keyword,
        campaign_id=original.campaign_id,
        note=f"Repurposed from #{original.id} ({original.channel})",
    )
    db.commit()
    return {"item": content_out(piece), "source": source}
