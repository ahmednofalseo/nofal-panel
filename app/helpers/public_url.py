"""Build public browser URLs for split admin/user deployments behind TLS termination."""

from __future__ import annotations

from starlette.requests import Request


def public_panel_url(request: Request, port: int) -> str:
    """
    Build scheme://host[:port] for cross-panel redirects.

    Omits :443 for HTTPS and :80 for HTTP so redirects stay on the same URL the user
    already hit (e.g. https://1.2.3.4/ without forcing :2020 when ADMIN_PUBLIC_PORT=443).
    """
    scheme = (request.headers.get("x-forwarded-proto") or request.url.scheme or "https").split(",")[0].strip()
    host = (request.headers.get("x-forwarded-host") or request.url.hostname or "").split(",")[0].strip()
    if not host:
        return "/"
    if (scheme == "https" and port == 443) or (scheme == "http" and port == 80):
        return f"{scheme}://{host}"
    return f"{scheme}://{host}:{port}"


def public_panel_path(request: Request, port: int, path: str) -> str:
    """
    Absolute URL to a path on the panel bound to ``port``.

    When ADMIN_PUBLIC_PORT and USER_PUBLIC_PORT are both 443, ``public_panel_url`` is only
    the origin (e.g. https://x/) — redirecting there would loop. Append real routes here.
    """
    base = public_panel_url(request, port).rstrip("/")
    if not path.startswith("/"):
        path = "/" + path
    if base == "/":
        return path
    return f"{base}{path}"
