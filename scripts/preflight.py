from __future__ import annotations

import json
import os
import platform
import shutil
import socket
import subprocess
import sys
import time
from dataclasses import dataclass
from typing import Iterable


DEFAULT_INDEXES: list[str] = [
    "https://pypi.org/simple",
    "https://pypi.python.org/simple",
]


@dataclass(frozen=True)
class CheckResult:
    ok: bool
    name: str
    detail: str


def _run(cmd: list[str], timeout_s: int = 20) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, check=False, capture_output=True, text=True, timeout=timeout_s)


def _python_info() -> CheckResult:
    return CheckResult(
        ok=True,
        name="python",
        detail=f"{sys.version.split()[0]} ({platform.system()} {platform.release()})",
    )


def _pip_info(venv_python: str) -> CheckResult:
    p = _run([venv_python, "-m", "pip", "--version"])
    if p.returncode != 0:
        return CheckResult(False, "pip", p.stderr.strip() or "pip not available")
    return CheckResult(True, "pip", p.stdout.strip())


def _dns_check(host: str = "pypi.org") -> CheckResult:
    try:
        socket.getaddrinfo(host, 443)
        return CheckResult(True, "dns", f"resolved {host}")
    except Exception as exc:
        return CheckResult(False, "dns", f"failed to resolve {host}: {exc}")


def _tcp_check(host: str = "pypi.org", port: int = 443, timeout_s: int = 5) -> CheckResult:
    try:
        with socket.create_connection((host, port), timeout=timeout_s):
            return CheckResult(True, "tcp", f"connected {host}:{port}")
    except Exception as exc:
        return CheckResult(False, "tcp", f"cannot connect {host}:{port}: {exc}")


def _index_probe(venv_python: str, indexes: Iterable[str]) -> CheckResult:
    # Use pip to fetch just the index page for a well-known package.
    # This detects corporate mirrors/blocked internet early.
    for idx in indexes:
        p = _run(
            [
                venv_python,
                "-m",
                "pip",
                "download",
                "--no-deps",
                "--no-binary",
                ":all:",
                "--disable-pip-version-check",
                "--index-url",
                idx,
                "pip",
            ],
            timeout_s=25,
        )
        if p.returncode == 0:
            return CheckResult(True, "pypi", f"reachable index: {idx}")
    return CheckResult(False, "pypi", "no index reachable (check firewall/DNS/proxy/mirror)")


def _system_bins() -> list[CheckResult]:
    required = ["git", "nginx"]
    out: list[CheckResult] = []
    for b in required:
        ok = shutil.which(b) is not None
        out.append(CheckResult(ok, f"bin:{b}", "found" if ok else "missing"))
    return out


def main() -> int:
    venv_python = os.getenv("VENV_PYTHON") or sys.executable
    indexes = (os.getenv("PIP_INDEX_URL") or "").strip()
    extra = (os.getenv("PIP_EXTRA_INDEX_URL") or "").strip()
    idxs = []
    if indexes:
        idxs.append(indexes)
    if extra:
        idxs.append(extra)
    idxs.extend(DEFAULT_INDEXES)

    results: list[CheckResult] = []
    results.append(_python_info())
    results.append(_pip_info(venv_python))
    results.append(_dns_check())
    results.append(_tcp_check())
    results.append(_index_probe(venv_python, idxs))
    results.extend(_system_bins())

    ok = all(r.ok for r in results)
    payload = {
        "ok": ok,
        "ts": int(time.time()),
        "results": [r.__dict__ for r in results],
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if ok else 2


if __name__ == "__main__":
    raise SystemExit(main())

