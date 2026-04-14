from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from app.config import settings
from app.models.domain import Domain
from app.models.user import User
from app.services.nginx import NginxService


_DOMAIN_RE = re.compile(r"^(?=.{1,253}$)(?!-)[A-Za-z0-9-]{1,63}(?<!-)(\.(?!-)[A-Za-z0-9-]{1,63}(?<!-))*\.?$")


class NginxDesiredState:
    @staticmethod
    def is_safe_domain(name: str) -> bool:
        name = (name or "").strip().lower().rstrip(".")
        return bool(_DOMAIN_RE.match(name))


class NginxReconciler:
    """
    Desired-state reconciliation for Nginx vhosts based on DB domains.
    - Ensures each active domain has an enabled, valid vhost config.
    - Runs `nginx -t` before reload.
    """

    @staticmethod
    def reconcile_domains(db: Session) -> dict[str, Any]:
        domains = (
            db.query(Domain)
            .filter(Domain.is_active == True)  # noqa: E712
            .order_by(Domain.domain_name.asc())
            .all()
        )

        created: list[str] = []
        skipped: list[str] = []
        errors: list[dict[str, str]] = []

        for d in domains:
            domain_name = (d.domain_name or "").strip().lower()
            if not NginxDesiredState.is_safe_domain(domain_name):
                skipped.append(domain_name)
                continue

            user = db.query(User).filter(User.id == d.user_id).first()
            if not user:
                skipped.append(domain_name)
                continue

            doc_root = (d.document_root or "").strip()
            if not doc_root:
                doc_root = f"{settings.ACCOUNTS_HOME}/{user.username}/public_html"

            config_path = Path(settings.NGINX_SITES_AVAILABLE) / f"{domain_name}.conf"
            enabled_path = Path(settings.NGINX_SITES_ENABLED) / f"{domain_name}.conf"

            if config_path.exists() and enabled_path.exists():
                continue

            res = NginxService.create_vhost(username=user.username, domain=domain_name, document_root=doc_root)
            if res.get("success"):
                created.append(domain_name)
                d.config_file = str(config_path)
            else:
                errors.append({"domain": domain_name, "error": str(res.get("error") or res.get("message") or "unknown")})

        if created:
            db.commit()

        test = NginxService.test_config()
        if not test.get("success"):
            return {
                "success": False,
                "created": created,
                "skipped": skipped,
                "errors": errors,
                "nginx_test": test,
            }

        reload_res = NginxService.reload()
        return {
            "success": bool(reload_res.get("success")),
            "created": created,
            "skipped": skipped,
            "errors": errors,
            "nginx_test": test,
            "nginx_reload": reload_res,
        }

