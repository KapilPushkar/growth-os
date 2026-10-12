import random

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app import ai
from app.analytics import geo_by_engine, geo_overview
from app.auth import get_current_user, require_team, scope_client_id
from app.database import get_db
from app.models import GeoCheck, Keyword, MetricSnapshot, User
from app.routers.common import load_client, load_owned
from app.schemas import ClientRef, GeoRunIn, KeywordBulk, KeywordCreate, KeywordItem
from app.serializers import geo_out, keyword_out
from app.services import log_activity, simulate_rank_refresh

keywords_router = APIRouter(prefix="/keywords", tags=["seo"])
geo_router = APIRouter(prefix="/geo", tags=["geo"])


def _is_tracked(db: Session, client_id: int, keyword: str) -> bool:
    return (
        db.scalar(
            select(Keyword.id).where(
                Keyword.client_id == client_id, func.lower(Keyword.keyword) == keyword.lower()
            )
        )
        is not None
    )


def _new_keyword(client_id: int, item: KeywordItem) -> Keyword:
    return Keyword(client_id=client_id, trend="new", **item.model_dump())


@keywords_router.get("")
def list_keywords(
    client_id: int | None = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[dict]:
    client_id = scope_client_id(user, client_id)
    query = select(Keyword).order_by(Keyword.search_volume.desc())
    if client_id is not None:
        query = query.where(Keyword.client_id == client_id)
    return [keyword_out(k) for k in db.scalars(query)]


@keywords_router.post("", status_code=status.HTTP_201_CREATED)
def create_keyword(
    body: KeywordCreate, user: User = Depends(require_team), db: Session = Depends(get_db)
) -> dict:
    load_client(db, user, body.client_id)
    if _is_tracked(db, body.client_id, body.keyword):
        raise HTTPException(status.HTTP_409_CONFLICT, f"“{body.keyword}” is already tracked")
    keyword = _new_keyword(body.client_id, KeywordItem(**body.model_dump(exclude={"client_id"})))
    db.add(keyword)
    db.commit()
    return keyword_out(keyword)


@keywords_router.post("/bulk", status_code=status.HTTP_201_CREATED)
def bulk_keywords(
    body: KeywordBulk, user: User = Depends(require_team), db: Session = Depends(get_db)
) -> dict:
    client = load_client(db, user, body.client_id)
    added: list[Keyword] = []
    skipped: list[str] = []
    seen: set[str] = set()
    for item in body.keywords:
        key = item.keyword.lower()
        if key in seen or _is_tracked(db, client.id, item.keyword):
            skipped.append(item.keyword)
            continue
        seen.add(key)
        keyword = _new_keyword(client.id, item)
        db.add(keyword)
        added.append(keyword)
    if added:
        log_activity(
            db,
            client.id,
            user,
            "seo.keywords",
            f"{user.name} started tracking {len(added)} keyword(s) for {client.name}",
        )
    db.commit()
    return {"added": [keyword_out(k) for k in added], "skipped": skipped}


@keywords_router.post("/refresh")
def refresh_ranks(
    body: ClientRef, user: User = Depends(require_team), db: Session = Depends(get_db)
) -> dict:
    client = load_client(db, user, body.client_id)
    keywords = list(db.scalars(select(Keyword).where(Keyword.client_id == client.id)))
    simulate_rank_refresh(keywords, random.Random())
    log_activity(
        db, client.id, user, "seo.refresh", f"Keyword ranks refreshed for {client.name} (simulated)"
    )
    db.commit()
    return {
        "items": [keyword_out(k) for k in keywords],
        "method": "simulated",
        "note": "Simulated rank refresh: no SEO data provider is connected yet.",
    }


@keywords_router.delete("/{keyword_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_keyword(
    keyword_id: int, user: User = Depends(require_team), db: Session = Depends(get_db)
) -> Response:
    db.delete(load_owned(db, user, Keyword, keyword_id))
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@geo_router.get("")
def list_geo(
    client_id: int | None = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    client_id = scope_client_id(user, client_id)
    if client_id is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "client_id is required")
    load_client(db, user, client_id)
    return geo_overview(db, client_id)


@geo_router.post("/run")
def run_geo(body: GeoRunIn, user: User = Depends(require_team), db: Session = Depends(get_db)) -> dict:
    client = load_client(db, user, body.client_id)
    latest = db.scalar(
        select(MetricSnapshot.ai_visibility)
        .where(MetricSnapshot.client_id == client.id)
        .order_by(MetricSnapshot.week_start.desc())
        .limit(1)
    )
    checks = []
    for engine in body.engines:
        result, _source = ai.geo_check(client, body.prompt, engine, latest or 0.0)
        check = GeoCheck(client_id=client.id, prompt=body.prompt, engine=engine, **result)
        db.add(check)
        checks.append(check)
    live = sum(1 for c in checks if c.method == "live")
    log_activity(
        db,
        client.id,
        user,
        "geo.run",
        f"GEO check run for {client.name} across {len(checks)} engine(s): "
        f"mentioned by {sum(1 for c in checks if c.mentioned)}",
    )
    db.commit()
    return {
        "checks": [geo_out(c) for c in checks],
        "by_engine": geo_by_engine(checks),
        "note": (
            f"{live} live and {len(checks) - live} simulated check(s). Engines are live only "
            "when the matching provider key is configured (claude: Anthropic, chatgpt: OpenAI)."
        ),
    }
