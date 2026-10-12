"""AI layer: prompt builders, provider calls and template fallbacks.

Provider order: Anthropic (ANTHROPIC_API_KEY) -> OpenAI (OPENAI_API_KEY) ->
deterministic templates. Every public function returns ``(data, source)``
where source is "llm:anthropic", "llm:openai" or "template", and none of
them raise: any provider, network or parsing failure falls back to templates
built from the same brand profile.
"""

import json
import logging
import random
import re
from datetime import date
from typing import Any

import httpx

from app.config import settings
from app.models import Client, ContentPiece, Lead
from app.post_templates import (
    FRAMEWORK_LABELS,
    build_post,
    first_name,
    short_audience,
    soften,
)

logger = logging.getLogger(__name__)

ANTHROPIC_URL = "https://api.anthropic.com/v1/messages"
ANTHROPIC_VERSION = "2023-06-01"
# Re-runs a request on Anthropic's recommended model if a safety classifier
# declines it, instead of returning the refusal.
ANTHROPIC_FALLBACK_BETA = "server-side-fallback-2026-07-01"
OPENAI_URL = "https://api.openai.com/v1/chat/completions"
TEMPLATE = "template"

CHANNEL_RULES = {
    "linkedin": (
        "LinkedIn post, 120-220 words. Strong first line that works before 'see more'. "
        "Short paragraphs, white space, at most one list, end with a question or clear takeaway. "
        "3 relevant hashtags. No emojis unless the brand voice is playful."
    ),
    "x": (
        "X (Twitter) thread of 5-7 tweets, each under 270 characters, numbered '1/', '2/' ... "
        "The first tweet must stand alone as a hook. 1-2 hashtags max."
    ),
    "blog": (
        "Blog article outline-draft of 400-600 words in Markdown: H1 title, short intro, "
        "3-4 H2 sections with 2-3 sentences each, and a conclusion. Use the target keyword "
        "naturally in the title and first paragraph."
    ),
    "newsletter": (
        "Newsletter issue of 250-350 words: start with 'Subject: ...', a personal opening, "
        "3 numbered ideas, a sign-off with the founder's first name."
    ),
    "instagram": (
        "Instagram caption of 80-150 words with line breaks, a hook line, 3 short points, "
        "a call to action, and 5-8 hashtags."
    ),
}

GEO_ENGINE_PROVIDER = {"claude": "anthropic", "chatgpt": "openai"}


class AIError(Exception):
    """Any reason an LLM result could not be used."""


# --- Provider plumbing --------------------------------------------------------


def active_provider() -> str | None:
    if settings.anthropic_api_key:
        return "anthropic"
    if settings.openai_api_key:
        return "openai"
    return None


def status() -> dict[str, Any]:
    provider = active_provider()
    model = {
        "anthropic": settings.anthropic_model,
        "openai": settings.openai_model,
    }.get(provider or "")
    return {"provider": provider or "none", "model": model, "mode": "llm" if provider else TEMPLATE}


def _call_anthropic(system: str, prompt: str, max_tokens: int) -> str:
    response = httpx.post(
        ANTHROPIC_URL,
        headers={
            "x-api-key": settings.anthropic_api_key,
            "anthropic-version": ANTHROPIC_VERSION,
            "anthropic-beta": ANTHROPIC_FALLBACK_BETA,
            "content-type": "application/json",
        },
        json={
            "model": settings.anthropic_model,
            "max_tokens": max_tokens,
            "system": system,
            "messages": [{"role": "user", "content": prompt}],
            "output_config": {"effort": settings.ai_effort},
            "fallbacks": "default",
        },
        timeout=settings.ai_timeout_seconds,
    )
    response.raise_for_status()
    payload = response.json()
    if payload.get("stop_reason") == "refusal":
        raise AIError("Request declined by the model")
    # Thinking blocks may precede the answer; only text blocks carry it.
    text = "".join(
        block.get("text", "") for block in payload.get("content", []) if block.get("type") == "text"
    )
    if not text.strip():
        raise AIError("Empty response")
    return text


def _call_openai(system: str, prompt: str, max_tokens: int, json_mode: bool) -> str:
    body: dict[str, Any] = {
        "model": settings.openai_model,
        "max_tokens": max_tokens,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ],
    }
    if json_mode:
        body["response_format"] = {"type": "json_object"}
    response = httpx.post(
        OPENAI_URL,
        headers={"Authorization": f"Bearer {settings.openai_api_key}"},
        json=body,
        timeout=settings.ai_timeout_seconds,
    )
    response.raise_for_status()
    text = response.json()["choices"][0]["message"]["content"] or ""
    if not text.strip():
        raise AIError("Empty response")
    return text


def _complete(
    system: str,
    prompt: str,
    *,
    max_tokens: int = 4000,
    provider: str | None = None,
    json_mode: bool = True,
) -> tuple[str, str]:
    """Return (text, provider). Raises AIError when no provider is usable."""
    provider = provider or active_provider()
    try:
        if provider == "anthropic":
            # Thinking tokens count toward max_tokens, so leave headroom.
            return _call_anthropic(system, prompt, max_tokens + 4000), provider
        if provider == "openai":
            return _call_openai(system, prompt, max_tokens, json_mode), provider
    except (httpx.HTTPError, KeyError, IndexError, ValueError) as exc:
        raise AIError(f"{provider} request failed: {type(exc).__name__}") from exc
    raise AIError("No AI provider configured")


def parse_json(text: str) -> Any:
    """Parse the first JSON value in a reply, tolerating code fences and prose."""
    text = re.sub(r"```(?:json)?", "", text)
    starts = [i for i in (text.find("{"), text.find("[")) if i != -1]
    if not starts:
        raise AIError("No JSON found in reply")
    try:
        value, _ = json.JSONDecoder().raw_decode(text[min(starts) :])
    except json.JSONDecodeError as exc:
        raise AIError("Reply was not valid JSON") from exc
    return value


def _llm_json(system: str, prompt: str, max_tokens: int = 4000) -> tuple[Any, str]:
    text, provider = _complete(system, prompt, max_tokens=max_tokens)
    return parse_json(text), f"llm:{provider}"


def _as_list(value: Any, key: str) -> list:
    """Accept either {key: [...]} or a bare list."""
    if isinstance(value, dict):
        value = value.get(key)
    if not isinstance(value, list) or not value:
        raise AIError(f"Expected a non-empty '{key}' list")
    return value


def _text(value: Any, limit: int = 20000) -> str:
    return str(value or "").strip()[:limit]


def _str_list(value: Any, limit: int = 10) -> list[str]:
    if isinstance(value, str):
        value = re.split(r"[,\n]", value)
    if not isinstance(value, list):
        return []
    return [str(v).strip() for v in value if str(v).strip()][:limit]


# --- Prompt building ---------------------------------------------------------


def brand_brief(client: Client) -> str:
    """Every prompt starts here so output sounds like this client."""
    lines = [
        f"Client: {client.name}, {client.title} at {client.company} ({client.industry}).",
        f"Positioning: {client.positioning}",
        f"Brand voice: {client.brand_voice}",
        f"Tone: {', '.join(client.tone_tags or [])}",
        f"Target audience: {client.target_audience}",
        f"Content pillars: {'; '.join(client.content_pillars or [])}",
        f"Goals: {'; '.join(client.goals or [])}",
        f"Never mention or discuss: {client.topics_to_avoid or 'n/a'}",
        f"Channels: {', '.join(client.channels or [])}",
    ]
    return "\n".join(line for line in lines if not line.endswith(": "))


def _system(client: Client, role: str) -> str:
    return (
        f"You are {role} at a done-for-you growth agency, writing for one client.\n\n"
        f"BRAND BRIEF\n{brand_brief(client)}\n\n"
        "Write in the client's own voice (first person where it is a post). Be specific and "
        "concrete; avoid hype, cliches and invented statistics presented as fact. Respect the "
        "topics to avoid. Respond with JSON only, no commentary."
    )


# --- Content -----------------------------------------------------------------


def _template_drafts(
    client: Client, channel: str, pillar: str, topic: str, keyword: str, count: int
) -> list[dict[str, Any]]:
    drafts = []
    for i in range(count):
        draft = build_post(client, channel=channel, pillar=pillar, topic=topic, keyword=keyword, index=i)
        drafts.append(
            {
                "title": draft.title,
                "body": draft.body,
                "hashtags": draft.hashtags,
                "pillar": pillar or (client.content_pillars or [""])[i % max(1, len(client.content_pillars or []))],
            }
        )
    return drafts


def generate_content(
    client: Client,
    *,
    channel: str = "linkedin",
    content_format: str = "post",
    pillar: str = "",
    topic: str = "",
    keyword: str = "",
    count: int = 1,
) -> tuple[list[dict[str, Any]], str]:
    pillar = pillar or (client.content_pillars or [""])[0]
    prompt = (
        f"Write {count} distinct draft(s) for {client.name}.\n"
        f"Channel rules: {CHANNEL_RULES[channel]}\n"
        f"Format: {content_format}\n"
        f"Content pillar: {pillar}\n"
        f"Topic: {topic or pillar}\n"
        + (f"Target keyword: {keyword}\n" if keyword else "")
        + "Use a different angle for each draft (e.g. contrarian take, lesson learned, playbook, "
        "data point, behind the scenes, question).\n"
        'Return JSON: {"drafts": [{"title": "short internal title", "body": "the full post", '
        '"hashtags": ["#Tag"]}]}'
    )
    try:
        data, source = _llm_json(_system(client, "a senior ghostwriter"), prompt)
        drafts = [
            {
                "title": _text(item.get("title"), 200) or f"{pillar}: draft {i + 1}",
                "body": _text(item.get("body")),
                "hashtags": [t if t.startswith("#") else f"#{t}" for t in _str_list(item.get("hashtags"))],
                "pillar": pillar,
            }
            for i, item in enumerate(_as_list(data, "drafts")[:count])
            if isinstance(item, dict) and _text(item.get("body"))
        ]
        if not drafts:
            raise AIError("No usable drafts")
        return drafts, source
    except Exception as exc:  # any failure, including unexpected shapes, falls back
        logger.info("generate_content fell back to templates: %s", exc)
        return _template_drafts(client, channel, pillar, topic, keyword, count), TEMPLATE


def repurpose(
    client: Client, piece: ContentPiece, channel: str, content_format: str
) -> tuple[dict[str, Any], str]:
    prompt = (
        f"Repurpose this {piece.channel} piece into a {channel} {content_format}.\n"
        f"Channel rules: {CHANNEL_RULES[channel]}\n"
        "Keep the core idea and the client's voice; adapt structure and length to the channel.\n\n"
        f"ORIGINAL ({piece.channel}):\n{piece.body}\n\n"
        'Return JSON: {"title": "...", "body": "...", "hashtags": ["#Tag"]}'
    )
    try:
        data, source = _llm_json(_system(client, "a senior content strategist"), prompt)
        if not isinstance(data, dict) or not _text(data.get("body")):
            raise AIError("No usable body")
        return {
            "title": _text(data.get("title"), 200) or piece.title,
            "body": _text(data.get("body")),
            "hashtags": _str_list(data.get("hashtags")),
        }, source
    except Exception as exc:  # any failure, including unexpected shapes, falls back
        logger.info("repurpose fell back to templates: %s", exc)

    # Template: re-render the same framework and topic for the new channel.
    label, _, topic = piece.title.partition(": ")
    framework = {v: k for k, v in FRAMEWORK_LABELS.items()}.get(label)
    draft = build_post(
        client,
        channel=channel,
        pillar=piece.pillar,
        topic=topic or piece.pillar,
        keyword=piece.target_keyword,
        framework=framework,
    )
    return {"title": draft.title, "body": draft.body, "hashtags": draft.hashtags}, TEMPLATE


# --- Topics & keywords -------------------------------------------------------

_TOPIC_PATTERNS = (
    ("What changed in {pillar_lc} this year", "Why last year's playbook no longer works for {audience}", "Planning season: buyers are re-checking assumptions before next year's budgets."),
    ("The hidden cost of ignoring {pillar_lc}", "Put a number on doing nothing, using patterns {first} sees at {company}", "Year-end reviews put every line item under scrutiny."),
    ("AI and {pillar_lc}: hype vs reality", "A grounded take from someone actually shipping it at {company}", "AI launches dominate feeds; {audience} want practical, honest takes."),
    ("{pillar} benchmarks for next year", "The three numbers {audience} should track, and why", "Leaders are setting next year's targets right now."),
    ("A {pillar_lc} project that failed, and what fixed it", "An honest post-mortem in {first}'s own words", "Candid failure stories are out-performing polished wins."),
    ("What {audience} get wrong about {pillar_lc}", "A contrarian view grounded in customer conversations", "Contrarian posts are driving comment-heavy engagement this month."),
    ("How {company} approaches {pillar_lc}", "Behind-the-scenes look at the team's weekly ritual", "Audiences reward transparency from founders during uncertain markets."),
)


def _template_topics(client: Client, count: int) -> list[dict[str, Any]]:
    today = date.today()
    rng = random.Random(f"topics:{client.id}:{today.isoformat()}")
    pillars = client.content_pillars or [client.industry or "Leadership"]
    channels = client.channels or ["linkedin"]
    patterns = list(_TOPIC_PATTERNS)
    rng.shuffle(patterns)
    topics = []
    for i in range(count):
        pillar = pillars[i % len(pillars)]
        title, angle, why = patterns[i % len(patterns)]
        values = {
            "pillar": pillar,
            "pillar_lc": soften(pillar),
            "audience": short_audience(client),
            "company": client.company,
            "first": first_name(client),
        }
        score = rng.randint(55, 96)
        topics.append(
            {
                "topic": title.format(**values),
                "angle": angle.format(**values),
                "pillar": pillar,
                "why_now": why.format(**values),
                "channel": channels[i % len(channels)],
                "keywords": [soften(pillar), f"{soften(pillar)} strategy", f"{client.industry.lower()} trends"],
                "momentum": "breakout" if score > 88 else "rising" if score > 70 else "steady",
                "momentum_score": score,
            }
        )
    return topics


def trending_topics(client: Client, count: int = 6) -> tuple[list[dict[str, Any]], str]:
    prompt = (
        f"Today is {date.today().isoformat()}. Suggest {count} timely content topics for this client "
        "that their audience is likely discussing now. For each give the client's specific angle, "
        "the pillar it supports, why it matters now, the best channel, 2-3 keywords and momentum.\n"
        'Return JSON: {"topics": [{"topic": "...", "angle": "...", "pillar": "...", '
        '"why_now": "...", "channel": "linkedin|x|blog|newsletter|instagram", '
        '"keywords": ["..."], "momentum": "breakout|rising|steady", "momentum_score": 0-100}]}'
    )
    try:
        data, source = _llm_json(_system(client, "a content strategist tracking trends"), prompt)
        channels = client.channels or ["linkedin"]
        topics = []
        for item in _as_list(data, "topics")[:count]:
            if not isinstance(item, dict) or not _text(item.get("topic")):
                continue
            channel = _text(item.get("channel")).lower()
            momentum = _text(item.get("momentum")).lower()
            try:
                score = max(0, min(100, int(item.get("momentum_score", 70))))
            except (TypeError, ValueError):
                score = 70
            topics.append(
                {
                    "topic": _text(item.get("topic"), 200),
                    "angle": _text(item.get("angle"), 400),
                    "pillar": _text(item.get("pillar"), 120),
                    "why_now": _text(item.get("why_now"), 400),
                    "channel": channel if channel in channels else channels[0],
                    "keywords": _str_list(item.get("keywords"), 5),
                    "momentum": momentum if momentum in ("breakout", "rising", "steady") else "rising",
                    "momentum_score": score,
                }
            )
        if not topics:
            raise AIError("No usable topics")
        return topics, source
    except Exception as exc:  # any failure, including unexpected shapes, falls back
        logger.info("trending_topics fell back to templates: %s", exc)
        return _template_topics(client, count), TEMPLATE


_KEYWORD_PATTERNS = (
    ("{x} software", "commercial"),
    ("{x} best practices", "informational"),
    ("{x} for {segment}", "commercial"),
    ("how to measure {x}", "informational"),
    ("{x} tools", "commercial"),
    ("{x} checklist", "informational"),
    ("{x} examples", "informational"),
    ("{x} consultant", "transactional"),
    ("{x} strategy", "informational"),
    ("{x} pricing", "transactional"),
)


def keyword_stem(phrase: str) -> str:
    """Turn a pillar like 'The modern CFO' into a searchable stem: 'modern CFO'."""
    phrase = re.sub(r"^(the|a|an|building( a| an)?)\s+", "", phrase.strip(), flags=re.IGNORECASE)
    return " ".join(word if word.isupper() else word.lower() for word in phrase.split())


def _template_keywords(client: Client, seed: str, count: int) -> list[dict[str, Any]]:
    rng = random.Random(f"kw:{client.id}:{seed}:{date.today().isoformat()}")
    pillars = client.content_pillars or [client.industry or "growth"]
    stems = [keyword_stem(seed)] if seed else [keyword_stem(p) for p in pillars]
    segment = keyword_stem(re.split(r" and |, | at ", short_audience(client))[0])
    ideas, seen = [], set()
    for i in range(len(stems) * len(_KEYWORD_PATTERNS)):
        stem = stems[i % len(stems)]
        pattern, intent = _KEYWORD_PATTERNS[(i // len(stems) + i) % len(_KEYWORD_PATTERNS)]
        keyword = pattern.format(x=stem, segment=segment)
        if keyword in seen:
            continue
        seen.add(keyword)
        ideas.append(
            {
                "keyword": keyword,
                "intent": intent,
                "search_volume": rng.choice((320, 480, 720, 880, 1300, 1900, 2400, 3600, 5400)),
                "difficulty": rng.randint(18, 68),
                "rationale": f"{intent.capitalize()} query from {segment} researching {stem}.",
            }
        )
        if len(ideas) == count:
            break
    return ideas


def suggest_keywords(client: Client, seed: str = "", count: int = 8) -> tuple[list[dict[str, Any]], str]:
    prompt = (
        f"Suggest {count} SEO keywords this client should target"
        + (f", starting from the seed '{seed}'" if seed else "")
        + ". Prefer buying-intent and problem-aware queries their audience would type. "
        "Volumes and difficulty are estimates.\n"
        'Return JSON: {"keywords": [{"keyword": "...", "intent": '
        '"informational|commercial|transactional|navigational", "search_volume": 0, '
        '"difficulty": 0-100, "rationale": "..."}]}'
    )
    intents = ("informational", "commercial", "transactional", "navigational")
    try:
        data, source = _llm_json(_system(client, "an SEO strategist"), prompt)
        ideas = []
        for item in _as_list(data, "keywords")[:count]:
            if not isinstance(item, dict) or not _text(item.get("keyword")):
                continue
            intent = _text(item.get("intent")).lower()
            try:
                volume = max(0, int(item.get("search_volume", 0)))
                difficulty = max(0, min(100, int(item.get("difficulty", 40))))
            except (TypeError, ValueError):
                volume, difficulty = 0, 40
            ideas.append(
                {
                    "keyword": _text(item.get("keyword"), 160),
                    "intent": intent if intent in intents else "informational",
                    "search_volume": volume,
                    "difficulty": difficulty,
                    "rationale": _text(item.get("rationale"), 300),
                }
            )
        if not ideas:
            raise AIError("No usable keywords")
        return ideas, source
    except Exception as exc:  # any failure, including unexpected shapes, falls back
        logger.info("suggest_keywords fell back to templates: %s", exc)
        return _template_keywords(client, seed, count), TEMPLATE


# --- Outreach ----------------------------------------------------------------


def _template_outreach(client: Client, lead: Lead, kind: str, source_post: ContentPiece | None) -> dict[str, str]:
    lead_first = lead.name.split()[0]
    me = first_name(client)
    pillar = soften((client.content_pillars or [client.industry])[0])
    audience = short_audience(client)
    if source_post is not None:
        topic = source_post.title.partition(": ")[2] or source_post.pillar
        context = f"thanks for engaging with my post on {soften(topic)}"
    elif lead.source == "referral":
        context = "a mutual connection suggested we talk"
    else:
        context = f"I've been following what {lead.company or 'your team'} is doing"

    if kind == "connection_note":
        message = (
            f"Hi {lead_first}, {context}. I'm {me}, {client.title} at {client.company}; "
            f"we work with {audience} on {pillar}. Would be good to connect."
        )
        return {"kind": kind, "subject": "", "message": message[:300]}
    if kind == "follow_up":
        message = (
            f"Hi {lead_first},\n\nFollowing up on my earlier note. {context.capitalize()}, and it "
            f"made me think of how {lead.company or 'teams like yours'} might approach {pillar}.\n\n"
            f"We recently helped a team with a similar setup cut the time they spend on it "
            f"significantly. Happy to share what worked, no pitch.\n\nWorth a 15-minute chat next week?\n\n{me}"
        )
        return {"kind": kind, "subject": f"Quick follow-up on {pillar}", "message": message}
    message = (
        f"Hi {lead_first},\n\nThanks for the conversation so far. I'd love to show you how "
        f"{client.company} approaches {pillar} for {audience}, and hear what's on your plate this quarter.\n\n"
        "Would either of these work for a 30-minute call?\n"
        "• Tuesday, 10:00-10:30\n• Thursday, 15:00-15:30\n\n"
        f"If neither suits, send me a time that does.\n\nBest,\n{me}"
    )
    return {"kind": kind, "subject": f"{client.company} x {lead.company or lead.name}: 30 minutes?", "message": message}


def outreach_message(
    client: Client, lead: Lead, kind: str, source_post: ContentPiece | None = None
) -> tuple[dict[str, str], str]:
    purpose = {
        "connection_note": "a LinkedIn connection note under 300 characters, no subject",
        "follow_up": "a short follow-up message (80-120 words) with a soft call to action",
        "meeting_request": "a meeting request (80-120 words) proposing two time slots",
    }[kind]
    prompt = (
        f"Write {purpose} from {client.name} to this lead.\n"
        f"Lead: {lead.name}, {lead.title} at {lead.company}. Stage: {lead.stage}. "
        f"Source: {lead.source}. Notes: {lead.notes or 'none'}.\n"
        + (f"They engaged with this post: {source_post.title}\n" if source_post else "")
        + "Sound human and specific, not salesy.\n"
        'Return JSON: {"subject": "... or empty", "message": "..."}'
    )
    try:
        data, source = _llm_json(_system(client, "a B2B outreach specialist"), prompt, max_tokens=1200)
        if not isinstance(data, dict) or not _text(data.get("message")):
            raise AIError("No usable message")
        message = _text(data.get("message"), 3000)
        if kind == "connection_note":
            message = message[:300]
        return {"kind": kind, "subject": _text(data.get("subject"), 200), "message": message}, source
    except Exception as exc:  # any failure, including unexpected shapes, falls back
        logger.info("outreach_message fell back to templates: %s", exc)
        return _template_outreach(client, lead, kind, source_post), TEMPLATE


# --- Report summary ----------------------------------------------------------


def _kpi(report: dict[str, Any], key: str) -> dict[str, Any]:
    return next((k for k in report.get("kpis", []) if k["key"] == key), {"current": 0, "change_pct": None})


def _template_summary(client: Client, report: dict[str, Any]) -> dict[str, Any]:
    impressions = _kpi(report, "impressions")
    leads = _kpi(report, "leads")
    visibility = _kpi(report, "ai_visibility")
    highlights = report.get("highlights", {})
    days = report.get("period", {}).get("days", 30)

    def trend(kpi: dict) -> str:
        change = kpi.get("change_pct")
        if change is None:
            return ""
        return f" ({'up' if change >= 0 else 'down'} {abs(change):.0f}% on the previous period)"

    parts = [
        f"Over the last {days} days, {client.name}'s content reached {int(impressions['current']):,} "
        f"impressions{trend(impressions)} across {highlights.get('posts_published', 0)} published pieces.",
        f"That attention produced {int(leads['current'])} leads{trend(leads)}, "
        f"{highlights.get('meetings_booked', 0)} meetings and {highlights.get('deals_won', 0)} won deal(s)"
        + (f" worth ${highlights.get('won_value', 0):,.0f}." if highlights.get("won_value") else "."),
    ]
    top = (report.get("top_content") or [None])[0]
    if top:
        parts.append(
            f"The strongest piece was “{top['title']}” with {top['metrics']['engagements']:,} engagements."
        )
    parts.append(f"AI-assistant visibility averaged {visibility['current']}%{trend(visibility)}.")

    steps = []
    if top:
        steps.append(f"Double down on the {top['pillar'] or 'top-performing'} pillar: two more posts in the format that won this month.")
    movers = report.get("keyword_movers") or []
    if movers:
        steps.append(f"Publish a deeper article on “{movers[0]['keyword']}” to push it further up the rankings.")
    if (visibility.get("current") or 0) < 40:
        steps.append("Raise AI-assistant visibility: answer the top buyer questions on the website and earn citations from industry lists.")
    steps += [
        "Turn this month's engaged leads into meetings with a personal follow-up sequence from the founder.",
        f"Batch-approve next month's calendar early so {client.name} keeps a steady posting cadence.",
        "Repurpose the best-performing post into a newsletter issue and a short thread.",
    ]
    return {"summary": " ".join(parts), "next_steps": steps[:3]}


def report_summary(client: Client, report: dict[str, Any]) -> tuple[dict[str, Any], str]:
    facts = {
        "period_days": report.get("period", {}).get("days"),
        "kpis": [
            {"metric": k["label"], "current": k["current"], "previous": k["previous"], "change_pct": k["change_pct"]}
            for k in report.get("kpis", [])
        ],
        "highlights": report.get("highlights"),
        "top_content": [
            {"title": p["title"], "channel": p["channel"], **p["metrics"]} for p in report.get("top_content", [])[:3]
        ],
        "keyword_movers": [
            {"keyword": k["keyword"], "from": k["previous_rank"], "to": k["current_rank"]}
            for k in report.get("keyword_movers", [])[:5]
        ],
    }
    prompt = (
        "Write the executive summary for this client's monthly report, addressed to the founder: "
        "3-5 sentences, plain English, lead with business outcomes, cite the numbers given and "
        "nothing else. Then give exactly 3 specific next steps for next month.\n\n"
        f"DATA\n{json.dumps(facts, default=str)}\n\n"
        'Return JSON: {"summary": "...", "next_steps": ["...", "...", "..."]}'
    )
    try:
        data, source = _llm_json(_system(client, "the account strategist"), prompt, max_tokens=1500)
        if not isinstance(data, dict) or not _text(data.get("summary")):
            raise AIError("No usable summary")
        steps = _str_list(data.get("next_steps"), 3)
        if len(steps) < 3:
            raise AIError("Expected 3 next steps")
        return {"summary": _text(data.get("summary"), 2000), "next_steps": steps}, source
    except Exception as exc:  # any failure, including unexpected shapes, falls back
        logger.info("report_summary fell back to templates: %s", exc)
        return _template_summary(client, report), TEMPLATE


# --- GEO (AI-assistant visibility) ---------------------------------------------


def _mention(answer: str, client: Client) -> tuple[bool, int | None]:
    """Is the client named, and at which list position (1-based) if any?"""
    names = [n.lower() for n in (client.company, client.name.removeprefix("Dr. ")) if n]
    lowered = answer.lower()
    if not any(name in lowered for name in names):
        return False, None
    items = [line for line in answer.splitlines() if re.match(r"^\s*(\d+[.)]|[-*•])\s+", line)]
    for position, line in enumerate(items, start=1):
        if any(name in line.lower() for name in names):
            return True, position
    return True, None


def geo_check(
    client: Client, prompt: str, engine: str, visibility: float
) -> tuple[dict[str, Any], str]:
    """Ask an assistant the buyer's question and see whether the client is named.

    Live only when the engine matches the configured provider (claude ->
    Anthropic, chatgpt -> OpenAI); otherwise simulated, weighted by the
    client's current AI-visibility so results track the trend.
    """
    provider = GEO_ENGINE_PROVIDER.get(engine)
    configured = {"anthropic": settings.anthropic_api_key, "openai": settings.openai_api_key}
    if provider and configured.get(provider):
        try:
            answer, used = _complete(
                "You are a helpful assistant. Answer the user's question directly. When they ask "
                "for recommendations, give a short numbered list of specific companies or products.",
                prompt,
                max_tokens=900,
                provider=provider,
                json_mode=False,
            )
            mentioned, position = _mention(answer, client)
            return {
                "mentioned": mentioned,
                "position": position,
                "method": "live",
                "excerpt": answer.strip()[:600],
            }, f"llm:{used}"
        except Exception as exc:  # fall back to simulation on any failure
            logger.info("geo_check live call failed, simulating: %s", exc)

    rng = random.Random(f"geo:{client.id}:{engine}:{prompt}:{date.today().isoformat()}")
    engine_bias = {"perplexity": 1.25, "chatgpt": 1.0, "claude": 1.0, "gemini": 0.8}.get(engine, 1.0)
    chance = min(0.9, max(0.05, visibility / 100 * engine_bias * 1.6))
    mentioned = rng.random() < chance
    position = rng.randint(1, 6) if mentioned else None
    excerpt = (
        f"Simulated answer: lists {client.company} at position {position} among recommended options."
        if mentioned
        else f"Simulated answer: recommends other providers; {client.company} is not mentioned."
    )
    return {"mentioned": mentioned, "position": position, "method": "simulated", "excerpt": excerpt}, TEMPLATE

