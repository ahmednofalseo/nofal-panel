"""مثيل Jinja2 واحد بمسارات مطلقة + مرشحات مشتركة."""
from urllib.parse import quote

from markupsafe import Markup, escape
from starlette.requests import Request
from fastapi.templating import Jinja2Templates

from app.paths import TEMPLATES_DIR
from app.security import CSRF_COOKIE_NAME

templates = Jinja2Templates(directory=TEMPLATES_DIR)
templates.env.filters["urlq"] = lambda s: quote(str(s), safe="")


def csrf_hidden(request: Request) -> Markup:
    """Hidden input for POST forms; token must match CSRF cookie on submit.

    When the browser has no CSRF cookie yet, ``runtime_notice_middleware`` puts a
    fresh token on ``request.state`` and sets the cookie on the same response so
    the hidden field and cookie stay in sync (avoids empty form + 403 on POST).
    """
    if request is None:
        return Markup("")
    token = request.cookies.get(CSRF_COOKIE_NAME) or getattr(request.state, "csrf_token", None)
    if not token:
        return Markup("")
    return Markup(f'<input type="hidden" name="csrf_token" value="{escape(token)}">')


templates.env.globals["CSRF_COOKIE_NAME"] = CSRF_COOKIE_NAME
templates.env.globals["csrf_hidden"] = csrf_hidden
