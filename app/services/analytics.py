from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass

from app.config import settings


def _run(cmd: list[str], timeout_s: int = 60) -> tuple[int, str, str]:
    p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout_s)
    return p.returncode, p.stdout.strip(), p.stderr.strip()


@dataclass(frozen=True)
class AccountUsage:
    username: str
    disk_mb: int
    file_count: int


class AnalyticsService:
    @staticmethod
    def disk_usage_mb(username: str) -> int:
        path = os.path.join(settings.ACCOUNTS_HOME, username)
        rc, out, _ = _run(["du", "-sm", path])
        if rc != 0 or not out:
            return 0
        try:
            return int(out.split()[0])
        except Exception:
            return 0

    @staticmethod
    def file_count(username: str) -> int:
        path = os.path.join(settings.ACCOUNTS_HOME, username)
        # fast count using find
        rc, out, _ = _run(["bash", "-lc", f"find '{path}' -type f 2>/dev/null | wc -l"], timeout_s=120)
        if rc != 0 or not out:
            return 0
        try:
            return int(out.strip())
        except Exception:
            return 0

