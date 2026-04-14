"""cPanel File Manager Router"""
import os
import shutil
from typing import List
from fastapi import APIRouter, Depends, Request, Form, UploadFile, File, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, FileResponse, JSONResponse
from sqlalchemy.orm import Session
from app.database import get_db
from app.auth import get_cpanel_user
from app.config import settings
from app.templating import templates

router = APIRouter(prefix="/cpanel", tags=["cpanel-files"])

ALLOWED_UPLOAD_EXTENSIONS = {
    # Web
    ".html", ".htm", ".css", ".js", ".map",
    ".php", ".phtml",
    # Data / configs (safe subset)
    ".txt", ".md", ".json", ".xml", ".csv", ".log", ".sql",
    ".ini", ".conf",
    # Images
    ".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".ico",
    # Archives
    ".zip", ".tar", ".gz", ".tgz", ".bz2", ".xz",
}

ALLOWED_DOTFILES = {".htaccess", ".user.ini", ".well-known"}


def get_user_home(username: str) -> str:
    return f"{settings.ACCOUNTS_HOME}/{username}"


def safe_path(username: str, path: str) -> str:
    """Ensure path is within user's home directory"""
    home = get_user_home(username)
    if not path:
        return home
    full_path = os.path.normpath(os.path.join(home, path.lstrip("/")))
    if not full_path.startswith(home):
        return home  # Prevent path traversal
    return full_path


def _safe_basename(name: str) -> str:
    name = (name or "").strip()
    return os.path.basename(name)


@router.get("/files", response_class=HTMLResponse)
async def file_manager(request: Request, path: str = "", db: Session = Depends(get_db), user=Depends(get_cpanel_user)):
    current_path = safe_path(user.username, path)
    home = get_user_home(user.username)
    relative_path = os.path.relpath(current_path, home)

    items = []
    if os.path.exists(current_path) and os.path.isdir(current_path):
        for item in sorted(os.listdir(current_path)):
            item_path = os.path.join(current_path, item)
            stat = os.stat(item_path)
            items.append({
                "name": item,
                "is_dir": os.path.isdir(item_path),
                "size": stat.st_size,
                "modified": stat.st_mtime,
                "perms": oct(stat.st_mode)[-3:],
                "path": os.path.relpath(item_path, home),
            })

    breadcrumbs = []
    parts = relative_path.split("/") if relative_path != "." else []
    for i, part in enumerate(parts):
        breadcrumbs.append({"name": part, "path": "/".join(parts[:i+1])})

    return templates.TemplateResponse("cpanel/files.html", {
        "request": request, "user": user,
        "items": items, "current_path": relative_path,
        "breadcrumbs": breadcrumbs,
        "home": home, "page": "files"
    })


@router.post("/files/upload")
async def upload_file(
    request: Request,
    path: str = Form(""),
    files: List[UploadFile] = File(...),
    user=Depends(get_cpanel_user)
):
    upload_dir = safe_path(user.username, path)
    for file in files:
        original = (file.filename or "").strip()
        filename = os.path.basename(original)
        if not filename or filename in (".", ".."):
            continue

        # Hidden files: only allow a small safe list
        if filename.startswith(".") and filename not in ALLOWED_DOTFILES and not filename.startswith(".well-known"):
            return RedirectResponse(
                url=f"/cpanel/files?path={path}&error=Hidden+files+blocked",
                status_code=302,
            )

        _, ext = os.path.splitext(filename.lower())
        if ext and ext not in ALLOWED_UPLOAD_EXTENSIONS and filename not in ALLOWED_DOTFILES:
            return RedirectResponse(
                url=f"/cpanel/files?path={path}&error=File+type+not+allowed",
                status_code=302,
            )

        file_path = os.path.join(upload_dir, filename)
        with open(file_path, "wb") as f:
            content = await file.read()
            f.write(content)
    return RedirectResponse(url=f"/cpanel/files?path={path}&success=Files+uploaded", status_code=302)


@router.post("/files/create-folder")
async def create_folder(
    path: str = Form(""),
    folder_name: str = Form(...),
    user=Depends(get_cpanel_user)
):
    parent = safe_path(user.username, path)
    folder = _safe_basename(folder_name)
    if not folder or folder in (".", ".."):
        return RedirectResponse(url=f"/cpanel/files?path={path}&error=Invalid+folder+name", status_code=302)
    if folder.startswith(".") and folder not in ALLOWED_DOTFILES and not folder.startswith(".well-known"):
        return RedirectResponse(url=f"/cpanel/files?path={path}&error=Hidden+folders+blocked", status_code=302)
    new_folder = os.path.join(parent, folder)
    os.makedirs(new_folder, exist_ok=True)
    return RedirectResponse(url=f"/cpanel/files?path={path}&success=Folder+created", status_code=302)


@router.post("/files/delete")
async def delete_file(
    path: str = Form(...),
    item_name: str = Form(...),
    user=Depends(get_cpanel_user)
):
    name = _safe_basename(item_name)
    item_path = safe_path(user.username, os.path.join(path, name))
    if os.path.exists(item_path):
        if os.path.isdir(item_path):
            shutil.rmtree(item_path)
        else:
            os.remove(item_path)
    return RedirectResponse(url=f"/cpanel/files?path={path}&success=Deleted", status_code=302)


@router.post("/files/rename")
async def rename_file(
    path: str = Form(""),
    old_name: str = Form(...),
    new_name: str = Form(...),
    user=Depends(get_cpanel_user)
):
    parent = safe_path(user.username, path)
    old_base = _safe_basename(old_name)
    new_base = _safe_basename(new_name)
    if not new_base or new_base in (".", ".."):
        return RedirectResponse(url=f"/cpanel/files?path={path}&error=Invalid+name", status_code=302)
    if new_base.startswith(".") and new_base not in ALLOWED_DOTFILES and not new_base.startswith(".well-known"):
        return RedirectResponse(url=f"/cpanel/files?path={path}&error=Hidden+files+blocked", status_code=302)
    old_path = os.path.join(parent, old_base)
    new_path = os.path.join(parent, new_base)
    if os.path.exists(old_path):
        os.rename(old_path, new_path)
    return RedirectResponse(url=f"/cpanel/files?path={path}&success=Renamed", status_code=302)


@router.post("/files/chmod")
async def change_permissions(
    path: str = Form(""),
    item_name: str = Form(...),
    permissions: str = Form("755"),
    user=Depends(get_cpanel_user)
):
    item_path = safe_path(user.username, os.path.join(path, item_name))
    if os.path.exists(item_path):
        os.chmod(item_path, int(permissions, 8))
    return RedirectResponse(url=f"/cpanel/files?path={path}&success=Permissions+changed", status_code=302)


@router.get("/files/download")
async def download_file(path: str, user=Depends(get_cpanel_user)):
    file_path = safe_path(user.username, path)
    if os.path.isfile(file_path):
        return FileResponse(file_path, filename=os.path.basename(file_path))
    raise HTTPException(status_code=404)


@router.get("/files/edit", response_class=HTMLResponse)
async def edit_file(request: Request, path: str, user=Depends(get_cpanel_user)):
    file_path = safe_path(user.username, path)
    content = ""
    if os.path.isfile(file_path):
        try:
            with open(file_path, "r") as f:
                content = f.read()
        except:
            content = "# Binary file - cannot edit"
    return templates.TemplateResponse("cpanel/file_editor.html", {
        "request": request, "user": user,
        "file_path": path, "content": content,
        "filename": os.path.basename(file_path), "page": "files"
    })


@router.post("/files/edit")
async def save_file(
    path: str = Form(...),
    content: str = Form(...),
    user=Depends(get_cpanel_user)
):
    file_path = safe_path(user.username, path)
    with open(file_path, "w") as f:
        f.write(content)
    parent = os.path.dirname(path)
    return RedirectResponse(url=f"/cpanel/files?path={parent}&success=File+saved", status_code=302)
