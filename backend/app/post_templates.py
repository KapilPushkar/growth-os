"""Deterministic post frameworks filled from a client's brand profile.

Used by the seed data and as the AI layer's offline fallback, so drafts read
like that client even with no LLM key configured. Output is stable for a
given client, day and request, which keeps demos repeatable.
"""

import random
import re
from dataclasses import dataclass
from datetime import date

from app.models import Client


@dataclass(frozen=True)
class Draft:
    framework: str
    title: str
    body: str
    hashtags: list[str]


@dataclass(frozen=True)
class _Core:
    hook: str
    intro: str
    lead_in: str
    points: list[str]
    outro: str
    close: str


FRAMEWORKS = (
    "contrarian",
    "lesson_learned",
    "playbook",
    "data_point",
    "behind_the_scenes",
    "question",
)

FRAMEWORK_LABELS = {
    "contrarian": "Contrarian take",
    "lesson_learned": "Lesson learned",
    "playbook": "Playbook",
    "data_point": "Data point",
    "behind_the_scenes": "Behind the scenes",
    "question": "Question",
}


def soften(phrase: str) -> str:
    """Lower-case the first letter unless the first word looks like an acronym."""
    phrase = phrase.strip()
    if len(phrase) > 1 and phrase[1].islower():
        return phrase[0].lower() + phrase[1:]
    return phrase


def short_audience(client: Client) -> str:
    text = client.target_audience or "operators"
    first = re.split(r"[(;.]| who | that ", text, maxsplit=1)[0]
    return soften(first.strip(" ,")) or "operators"


def first_name(client: Client) -> str:
    parts = [p for p in client.name.split() if not p.endswith(".")]
    return parts[0] if parts else client.name


def hashtag(phrase: str) -> str:
    words = re.findall(r"[A-Za-z0-9]+", phrase)[:3]
    return "#" + "".join(w if w.isupper() else w.capitalize() for w in words)


def _core(framework: str, topic: str, client: Client, rng: random.Random) -> _Core:
    audience = short_audience(client)
    company = client.company
    t = soften(topic)

    if framework == "contrarian":
        return _Core(
            hook=f"Unpopular opinion: {t} is not a tooling problem.",
            intro=(
                f"Most {audience} I speak with start by buying software. "
                "Six months later the dashboard looks great and nothing has changed."
            ),
            lead_in="What actually moves the needle:",
            points=[
                "One owner with the authority to say no",
                "One metric the whole team can recite from memory",
                "A weekly 20-minute review that never gets cancelled",
            ],
            outro=f"At {company} we learned this the expensive way. Tools amplify a process. They don't replace one.",
            close="Agree, or am I missing something?",
        )
    if framework == "lesson_learned":
        return _Core(
            hook=f"The most expensive mistake I've made with {t}:",
            intro=f"Early on at {company}, I assumed {audience} wanted more features. They wanted fewer decisions.",
            lead_in="We had to unlearn three things:",
            points=[
                "Speed beats completeness in the first conversation",
                "The buyer is rarely the user, so design for both",
                "Every 'quick exception' quietly becomes the process",
            ],
            outro="If I were starting again, I'd spend the first 90 days listening, not building.",
            close="What's a lesson you only learned the hard way?",
        )
    if framework == "playbook":
        return _Core(
            hook=f"A simple playbook for {t} that works for {audience}:",
            intro="No frameworks with acronyms. Four steps, in this order.",
            lead_in="The playbook:",
            points=[
                "Write down the one outcome that matters this quarter",
                "Map who touches it and where it stalls",
                "Fix the biggest stall first and measure for two weeks",
                "Only then automate what's left",
            ],
            outro=f"We run this with every new customer at {company}. It's boring. It works.",
            close="Save this for your next planning session.",
        )
    if framework == "data_point":
        share = rng.randint(58, 81)
        conversations = rng.choice((40, 60, 75, 120))
        return _Core(
            hook=(
                f"In {conversations} conversations with {audience} this year, "
                f"{share}% called {t} a top-3 priority. Fewer than 1 in 5 had a plan for it."
            ),
            intro="That gap is the opportunity.",
            lead_in="Three patterns in the teams that close it:",
            points=[
                "They track leading indicators, not just outcomes",
                "They give one person end-to-end ownership",
                "They review progress weekly, in 15 minutes",
            ],
            outro=f"Directional, not a study, but the pattern has held across every {company} customer cohort.",
            close="Which of these is hardest for your team?",
        )
    if framework == "behind_the_scenes":
        return _Core(
            hook=f"Behind the scenes at {company}: how we think about {t}.",
            intro=f"Every Monday our team asks one question: what would make this easier for {audience}?",
            lead_in="This week that meant:",
            points=[
                "Cutting a feature we loved but customers didn't use",
                "Rewriting onboarding in plain language",
                "Calling five customers instead of sending a survey",
            ],
            outro="None of it is glamorous. All of it compounds.",
            close="What's the Monday question at your company?",
        )
    return _Core(
        hook=f"A question for {audience}: what's the one thing about {t} you'd fix tomorrow if you could?",
        intro=f"I'm asking because the answers shape what we build at {company}.",
        lead_in="So far I've heard:",
        points=[
            "Too many handoffs",
            "No single source of truth",
            "We find out about problems too late",
        ],
        outro="Reply below or send me a message. I read every one.",
        close="",
    )


def _hashtags(client: Client, pillar: str, keyword: str, limit: int) -> list[str]:
    candidates = [hashtag(pillar), hashtag(client.industry or "Leadership")]
    if keyword:
        candidates.append(hashtag(keyword))
    candidates += ["#Leadership", "#Founders", "#Growth", "#Strategy", "#B2B"]
    unique = [tag for tag in dict.fromkeys(candidates) if len(tag) > 1]
    return unique[:limit]


def _render(channel: str, core: _Core, client: Client, title: str, keyword: str) -> str:
    points = core.points
    if channel == "x":
        tweets = [core.hook, core.intro, *points, f"{core.outro} {core.close}".strip()]
        total = len(tweets)
        return "\n\n".join(f"{i}/{total} {tweet}" for i, tweet in enumerate(tweets, start=1))
    if channel == "blog":
        keyword_line = f" If you're researching {keyword}, start here." if keyword else ""
        sections = "\n\n".join(
            f"## {point}\n\n{point}. In practice this is where most {short_audience(client)} "
            "lose momentum, and where the fastest wins usually are."
            for point in points
        )
        return (
            f"# {title}\n\n{core.hook} {core.intro}{keyword_line}\n\n{sections}\n\n"
            f"## The takeaway\n\n{core.outro} {core.close}".strip()
        )
    if channel == "newsletter":
        numbered = "\n".join(f"{i}. {point}" for i, point in enumerate(points, start=1))
        return (
            f"Subject: {title}\n\nHi there,\n\n{core.hook}\n\n{core.intro}\n\n"
            f"{core.lead_in}\n{numbered}\n\n{core.outro}\n\n{core.close}\n\n"
            f"Until next week,\n{first_name(client)}"
        ).replace("\n\n\n", "\n\n")
    if channel == "instagram":
        bullets = "\n".join(f"✅ {point}" for point in points)
        return f"{core.hook}\n\n{bullets}\n\n{core.outro}\n\n{core.close}".strip()
    # LinkedIn: hook, white space, arrow list, single-line close.
    arrows = "\n".join(f"→ {point}" for point in points)
    return f"{core.hook}\n\n{core.intro}\n\n{core.lead_in}\n{arrows}\n\n{core.outro}\n\n{core.close}".strip()


def build_post(
    client: Client,
    *,
    channel: str = "linkedin",
    pillar: str = "",
    topic: str = "",
    keyword: str = "",
    framework: str | None = None,
    index: int = 0,
    day: date | None = None,
) -> Draft:
    """Return a draft for one channel; the same inputs on the same day give the same draft."""
    day = day or date.today()
    pillars = client.content_pillars or [client.industry or "Leadership"]
    pillar = pillar or pillars[index % len(pillars)]
    topic = topic or pillar
    rng = random.Random(f"{client.id}:{day.isoformat()}:{channel}:{index}:{topic}")
    if framework not in FRAMEWORKS:
        framework = FRAMEWORKS[(day.toordinal() + index + client.id) % len(FRAMEWORKS)]

    core = _core(framework, topic, client, rng)
    title = f"{FRAMEWORK_LABELS[framework]}: {topic}"
    tag_limit = 8 if channel == "instagram" else 3
    return Draft(
        framework=framework,
        title=title,
        body=_render(channel, core, client, title, keyword),
        hashtags=_hashtags(client, pillar, keyword, tag_limit),
    )
