"""
مسارات مطلقة لمشروع اللوحة — تعمل مهما كان cwd (systemd، docker، إلخ).
"""
from pathlib import Path

# app/paths.py → parent = app/, parent.parent = جذر المشروع (يحتوي static/ و app/)
PROJECT_ROOT: Path = Path(__file__).resolve().parent.parent

TEMPLATES_DIR: str = str(PROJECT_ROOT / "app" / "templates")
STATIC_DIR: str = str(PROJECT_ROOT / "static")
