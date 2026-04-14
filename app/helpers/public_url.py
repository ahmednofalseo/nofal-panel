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
