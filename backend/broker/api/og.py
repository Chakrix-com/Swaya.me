"""
Open Graph meta-tag endpoint for social media link previews.
Called by nginx when a social crawler (Facebook, WhatsApp, Telegram, etc.)
hits a /join/:code URL.  Returns a minimal HTML page with OG/Twitter tags
and immediately redirects the browser to the SPA join page.
"""
from fastapi import APIRouter
from fastapi.responses import HTMLResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Depends

from persistence.database_async import get_async_db
from persistence.models.core import Event
from persistence.models.quiz import Quiz, QuizSession, QuizSessionStatus

router = APIRouter(prefix="/og", tags=["og"])

_SITE = "https://www.swaya.me"
_OG_IMAGE = f"{_SITE}/og-image.png"
_OG_IMAGE_W = 1200
_OG_IMAGE_H = 630


def _html(
    title: str,
    description: str,
    url: str,
    image: str = _OG_IMAGE,
) -> str:
    esc = lambda s: s.replace("&", "&amp;").replace('"', "&quot;").replace("<", "&lt;")
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8"/>
  <title>{esc(title)}</title>

  <!-- Open Graph -->
  <meta property="og:type"        content="website"/>
  <meta property="og:url"         content="{esc(url)}"/>
  <meta property="og:title"       content="{esc(title)}"/>
  <meta property="og:description" content="{esc(description)}"/>
  <meta property="og:image"       content="{esc(image)}"/>
  <meta property="og:image:width" content="{_OG_IMAGE_W}"/>
  <meta property="og:image:height"content="{_OG_IMAGE_H}"/>
  <meta property="og:site_name"   content="Swaya.me"/>

  <!-- Twitter Card -->
  <meta name="twitter:card"        content="summary_large_image"/>
  <meta name="twitter:title"       content="{esc(title)}"/>
  <meta name="twitter:description" content="{esc(description)}"/>
  <meta name="twitter:image"       content="{esc(image)}"/>

  <!-- Redirect browsers immediately; bots stop at meta tags -->
  <meta http-equiv="refresh" content="0;url={esc(url)}"/>
</head>
<body>
  <p>Redirecting… <a href="{esc(url)}">Click here if not redirected.</a></p>
</body>
</html>"""


@router.get("/join/{join_code}", response_class=HTMLResponse)
async def og_join(join_code: str, db: AsyncSession = Depends(get_async_db)):
    """
    Return an OG-tag page for a /join/:code URL.
    Looks up the active session to get the quiz name; falls back to generic
    site tags if the join code is expired or unknown.
    """
    join_url = f"{_SITE}/join/{join_code}"

    # Try to find the quiz name from the active session
    quiz_name: str | None = None
    try:
        result = await db.execute(
            select(Event).filter(Event.join_code == join_code)
        )
        event = result.scalar_one_or_none()
        if event:
            result = await db.execute(
                select(Quiz)
                .join(QuizSession, QuizSession.quiz_id == Quiz.id)
                .filter(
                    Quiz.event_id == event.id,
                    QuizSession.status.in_(
                        [QuizSessionStatus.CREATED, QuizSessionStatus.ACTIVE]
                    ),
                )
                .order_by(QuizSession.id.desc())
            )
            quiz = result.scalars().first()
            if quiz:
                quiz_name = quiz.title
    except Exception:
        pass  # Fall back to generic tags

    if quiz_name:
        title = f"{quiz_name} — Join on Swaya.me"
        description = (
            f"You've been invited to join \"{quiz_name}\" — a live interactive quiz! "
            f"Enter code {join_code.upper()} at swaya.me/join or tap the link to join now."
        )
    else:
        title = "Join a Live Quiz on Swaya.me"
        description = (
            "You've been invited to join a live interactive quiz on Swaya.me. "
            "Tap the link to join now!"
        )

    return HTMLResponse(
        content=_html(title=title, description=description, url=join_url),
        headers={"Cache-Control": "no-store"},
    )
