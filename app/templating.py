"""مثيل Jinja2 واحد بمسارات مطلقة + مرشحات مشتركة."""
from urllib.parse import quote

from fastapi.templating import Jinja2Templates

from app.paths import TEMPLATES_DIR

templates = Jinja2Templates(directory=TEMPLATES_DIR)
templates.env.filters["urlq"] = lambda s: quote(str(s), safe="")

# Used by base layout JS to inject a CSRF hidden field into POST forms.
templates.env.globals["CSRF_COOKIE_NAME"] = "csrf_token"
