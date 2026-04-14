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
        *,
        username: str,
        email: str,
        password: str,
        domain: str,
        ip_address: str,
        package: dict[str, Any],
        first_name: str = "",
        last_name: str = "",
        company: str = "",
    ) -> ProvisionResult:
        # DB record
        new_user = User(
            username=username,
            email=email,
            hashed_password="",  # must be set by caller (router) to keep auth logic centralized
            role="user",
            first_name=first_name,
            last_name=last_name,
            company=company,
            primary_domain=domain,
            ip_address=ip_address,
            server_user=username,
            package_id=package.get("package_id"),
            disk_quota_mb=package.get("disk_quota_mb", 1024),
            bandwidth_limit_mb=package.get("bandwidth_limit_mb", 10240),
            email_limit=package.get("email_limit", 10),
            db_limit=package.get("db_limit", 5),
            ftp_limit=package.get("ftp_limit", 5),
            subdomain_limit=package.get("subdomain_limit", 10),
            addon_domain_limit=package.get("addon_domain_limit", 2),
        )
        db.add(new_user)
        db.flush()

        # Allocate port for future instances/apps.
        allocated = PortAllocatorService.allocate_for_user(db, new_user.id, purpose="instance")

        # Server-side provisioning
        res = AccountManager.create_account(
            username=username,
            domain=domain,
            password=password,
            email=email,
            ip_address=ip_address,
            package=package,
        )
        if not res.get("success"):
            PortAllocatorService.release_user_ports(db, new_user.id)
            db.delete(new_user)
            db.flush()
            return ProvisionResult(success=False, error=str(res.get("error") or "provisioning failed"), details=res)

        pub = res.get("account_info", {}).get("public_html") or f"{settings.ACCOUNTS_HOME}/{username}/public_html"
        db.add(
            Domain(
                user_id=new_user.id,
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

