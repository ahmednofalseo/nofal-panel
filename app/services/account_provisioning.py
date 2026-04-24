from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlalchemy.orm import Session

from app.config import settings
from app.models.domain import Domain
from app.models.user import User
from app.services.account_manager import AccountManager
from app.services.ports import PortAllocatorService


@dataclass
class ProvisionResult:
    success: bool
    error: str | None = None
    details: dict[str, Any] | None = None


class AccountProvisioningService:
    """
    Enterprise wrapper for AccountManager that:
    - allocates ports in DB
    - creates Domain row for main domain
    - returns consistent structured output
    """

    @staticmethod
    def create_account(
        db: Session,
        user: User,
        *,
        plaintext_password: str,
        domain: str,
        ip_address: str,
        package: dict[str, Any],
    ) -> ProvisionResult:
        """
        Attach server resources to an existing panel ``User`` row (already flushed by the router).
        Must not insert a second user with the same username — that used to break provisioning.
        """
        # Allocate port for future instances/apps.
        allocated = PortAllocatorService.allocate_for_user(db, user.id, purpose="instance")

        # Server-side provisioning (Linux user, nginx, DNS, mail, MySQL FTP, …)
        res = AccountManager.create_account(
            username=user.username,
            domain=domain,
            password=plaintext_password,
            email=user.email,
            ip_address=ip_address,
            package=package,
        )
        if not res.get("success"):
            PortAllocatorService.release_user_ports(db, user.id)
            return ProvisionResult(
                success=False,
                error=str(res.get("error") or "provisioning failed"),
                details={"result": res},
            )

        pub = res.get("account_info", {}).get("public_html") or f"{settings.ACCOUNTS_HOME}/{user.username}/public_html"
        db.add(
            Domain(
                user_id=user.id,
                domain_name=domain.strip().lower(),
                domain_type="main",
                document_root=pub,
                ip_address=ip_address,
                config_file=f"{settings.NGINX_SITES_AVAILABLE}/{domain.strip()}.conf",
                is_active=True,
            )
        )

        return ProvisionResult(success=True, details={"allocated_port": allocated.port, "result": res})

    @staticmethod
    def terminate_account(db: Session, *, user: User) -> ProvisionResult:
        # Remove server resources
        AccountManager.terminate_account(user.username, user.primary_domain)
        PortAllocatorService.release_user_ports(db, user.id)
        return ProvisionResult(success=True)

