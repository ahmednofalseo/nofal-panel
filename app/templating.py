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
    """Hidden input for POST forms when CSRF cookie exists (works without JS)."""
    if request is None:
        return Markup("")
    token = request.cookies.get(CSRF_COOKIE_NAME)
    if not token:
        return Markup("")
    return Markup(f'<input type="hidden" name="csrf_token" value="{escape(token)}">')


templates.env.globals["CSRF_COOKIE_NAME"] = CSRF_COOKIE_NAME
templates.env.globals["csrf_hidden"] = csrf_hidden
