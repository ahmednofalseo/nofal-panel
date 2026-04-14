from __future__ import annotations

import os
import shutil
import tarfile
import zipfile
from dataclasses import dataclass
from pathlib import Path

from app.config import settings


ALLOWED_UPLOAD_EXTENSIONS = {
    ".html", ".htm", ".css", ".js", ".map",
    ".php", ".phtml",
    ".txt", ".md", ".json", ".xml", ".csv", ".log", ".sql",
    ".ini", ".conf",
    ".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".ico",
    ".zip", ".tar", ".gz", ".tgz", ".bz2", ".xz",
}

ALLOWED_DOTFILES = {".htaccess", ".user.ini", ".well-known"}


@dataclass(frozen=True)
class FileItem:
    name: str
    path: str
    is_dir: bool
    size: int
    modified: float
    perms: str


class FileManagerService:
    @staticmethod
    def home(username: str) -> str:
        return f"{settings.ACCOUNTS_HOME}/{username}"

    @staticmethod
    def safe_path(username: str, rel_path: str) -> str:
        home = FileManagerService.home(username)
        if not rel_path:
            return home
        full_path = os.path.normpath(os.path.join(home, rel_path.lstrip("/")))
        if not full_path.startswith(home):
            return home
        return full_path

    @staticmethod
    def _safe_basename(name: str) -> str:
        name = (name or "").strip()
        return os.path.basename(name)

    @staticmethod
    def list_dir(username: str, rel_path: str) -> tuple[str, list[FileItem]]:
        current_path = FileManagerService.safe_path(username, rel_path)
        home = FileManagerService.home(username)
        relative_path = os.path.relpath(current_path, home)

        items: list[FileItem] = []
        if os.path.exists(current_path) and os.path.isdir(current_path):
            for item in sorted(os.listdir(current_path)):
                item_path = os.path.join(current_path, item)
                st = os.stat(item_path)
                items.append(
                    FileItem(
                        name=item,
                        is_dir=os.path.isdir(item_path),
                        size=st.st_size,
                        modified=st.st_mtime,
                        perms=oct(st.st_mode)[-3:],
                        path=os.path.relpath(item_path, home),
                    )
                )

        return relative_path, items

    @staticmethod
    def delete(username: str, parent_rel: str, name: str) -> None:
        base = FileManagerService._safe_basename(name)
        target = FileManagerService.safe_path(username, os.path.join(parent_rel, base))
        if os.path.isdir(target):
            shutil.rmtree(target)
        elif os.path.exists(target):
            os.remove(target)

    @staticmethod
    def bulk_delete(username: str, rel_paths: list[str]) -> int:
        deleted = 0
        for rp in rel_paths:
            target = FileManagerService.safe_path(username, rp)
            if not os.path.exists(target):
                continue
            if os.path.isdir(target):
                shutil.rmtree(target)
            else:
                os.remove(target)
            deleted += 1
        return deleted

    @staticmethod
    def move(username: str, src_rel: str, dest_dir_rel: str) -> None:
        src = FileManagerService.safe_path(username, src_rel)
        dest_dir = FileManagerService.safe_path(username, dest_dir_rel)
        os.makedirs(dest_dir, exist_ok=True)
        shutil.move(src, os.path.join(dest_dir, os.path.basename(src)))

    @staticmethod
    def copy(username: str, src_rel: str, dest_dir_rel: str) -> None:
        src = FileManagerService.safe_path(username, src_rel)
        dest_dir = FileManagerService.safe_path(username, dest_dir_rel)
        os.makedirs(dest_dir, exist_ok=True)
        dest = os.path.join(dest_dir, os.path.basename(src))
        if os.path.isdir(src):
            shutil.copytree(src, dest, dirs_exist_ok=True)
        else:
            shutil.copy2(src, dest)

    @staticmethod
    def make_zip(username: str, dest_rel: str, sources_rel: list[str]) -> None:
        dest_path = FileManagerService.safe_path(username, dest_rel)
        dest_dir = os.path.dirname(dest_path)
        os.makedirs(dest_dir, exist_ok=True)
        home = FileManagerService.home(username)
        with zipfile.ZipFile(dest_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            for rp in sources_rel:
                src = FileManagerService.safe_path(username, rp)
                if not os.path.exists(src):
                    continue
                if os.path.isdir(src):
                    for root, _, files in os.walk(src):
                        for f in files:
                            fp = os.path.join(root, f)
                            arc = os.path.relpath(fp, home)
                            zf.write(fp, arcname=arc)
                else:
                    zf.write(src, arcname=os.path.relpath(src, home))

    @staticmethod
    def extract_archive(username: str, archive_rel: str, dest_dir_rel: str) -> None:
        archive_path = FileManagerService.safe_path(username, archive_rel)
        dest_dir = FileManagerService.safe_path(username, dest_dir_rel)
        os.makedirs(dest_dir, exist_ok=True)

        p = Path(archive_path)
        lower = p.name.lower()
        if lower.endswith(".zip"):
            with zipfile.ZipFile(archive_path, "r") as zf:
                zf.extractall(dest_dir)
            return
        if lower.endswith((".tar", ".tar.gz", ".tgz", ".tar.bz2", ".tar.xz")):
            with tarfile.open(archive_path, "r:*") as tf:
                tf.extractall(dest_dir)
            return

        raise ValueError("Unsupported archive type")

