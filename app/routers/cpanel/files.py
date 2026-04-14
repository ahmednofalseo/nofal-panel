"""cPanel File Manager Router"""
import os
from typing import List
from fastapi import APIRouter, Depends, Request, Form, UploadFile, File, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, FileResponse, JSONResponse
from sqlalchemy.orm import Session
from app.database import get_db
from app.auth import get_cpanel_user
from app.config import settings
from app.models.activity_log import ActivityLog
from app.services.file_manager import FileManagerService, ALLOWED_DOTFILES, ALLOWED_UPLOAD_EXTENSIONS
from app.templating import templates

router = APIRouter(prefix="/cpanel", tags=["cpanel-files"])

def get_user_home(username: str) -> str:
    return FileManagerService.home(username)


@router.get("/files", response_class=HTMLResponse)
async def file_manager(request: Request, path: str = "", db: Session = Depends(get_db), user=Depends(get_cpanel_user)):
    home = get_user_home(user.username)
    relative_path, items_ = FileManagerService.list_dir(user.username, path)
    items = [it.__dict__ for it in items_]

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
    db: Session = Depends(get_db),
    user=Depends(get_cpanel_user)
):
    upload_dir = FileManagerService.safe_path(user.username, path)
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
    if db:
        db.add(ActivityLog(user_id=user.id, action="FILES_UPLOAD", description=f"Uploaded {len(files)} file(s) to {path or '/'}", status="success"))
        db.commit()
    return RedirectResponse(url=f"/cpanel/files?path={path}&success=Files+uploaded", status_code=302)


@router.post("/files/create-folder")
async def create_folder(
    path: str = Form(""),
    folder_name: str = Form(...),
    db: Session = Depends(get_db),
    user=Depends(get_cpanel_user)
):
    parent = FileManagerService.safe_path(user.username, path)
    folder = FileManagerService._safe_basename(folder_name)
    if not folder or folder in (".", ".."):
        return RedirectResponse(url=f"/cpanel/files?path={path}&error=Invalid+folder+name", status_code=302)
    if folder.startswith(".") and folder not in ALLOWED_DOTFILES and not folder.startswith(".well-known"):
        return RedirectResponse(url=f"/cpanel/files?path={path}&error=Hidden+folders+blocked", status_code=302)
    new_folder = os.path.join(parent, folder)
    os.makedirs(new_folder, exist_ok=True)
    db.add(ActivityLog(user_id=user.id, action="FILES_MKDIR", description=f"mkdir {os.path.join(path, folder)}", status="success"))
    db.commit()
    return RedirectResponse(url=f"/cpanel/files?path={path}&success=Folder+created", status_code=302)


@router.post("/files/delete")
async def delete_file(
    path: str = Form(...),
    item_name: str = Form(...),
    db: Session = Depends(get_db),
    user=Depends(get_cpanel_user)
):
    FileManagerService.delete(user.username, path, item_name)
    db.add(ActivityLog(user_id=user.id, action="FILES_DELETE", description=f"delete {os.path.join(path, item_name)}", status="success"))
    db.commit()
    return RedirectResponse(url=f"/cpanel/files?path={path}&success=Deleted", status_code=302)


@router.post("/files/bulk-delete")
async def bulk_delete(
    paths: str = Form(""),
    items: str = Form(""),
    db: Session = Depends(get_db),
    user=Depends(get_cpanel_user),
):
    # items is a comma-separated list of rel paths
    rels = [p.strip() for p in (items or "").split(",") if p.strip()]
    deleted = FileManagerService.bulk_delete(user.username, rels)
    db.add(ActivityLog(user_id=user.id, action="FILES_BULK_DELETE", description=f"bulk delete {deleted} item(s) under {paths or '/'}", status="success"))
    db.commit()
    return RedirectResponse(url=f"/cpanel/files?path={paths}&success=Deleted+{deleted}+items", status_code=302)


@router.post("/files/rename")
async def rename_file(
    path: str = Form(""),
    old_name: str = Form(...),
    new_name: str = Form(...),
    db: Session = Depends(get_db),
    user=Depends(get_cpanel_user)
):
    parent = FileManagerService.safe_path(user.username, path)
    old_base = FileManagerService._safe_basename(old_name)
    new_base = FileManagerService._safe_basename(new_name)
    if not new_base or new_base in (".", ".."):
        return RedirectResponse(url=f"/cpanel/files?path={path}&error=Invalid+name", status_code=302)
    if new_base.startswith(".") and new_base not in ALLOWED_DOTFILES and not new_base.startswith(".well-known"):
        return RedirectResponse(url=f"/cpanel/files?path={path}&error=Hidden+files+blocked", status_code=302)
    old_path = os.path.join(parent, old_base)
    new_path = os.path.join(parent, new_base)
    if os.path.exists(old_path):
        os.rename(old_path, new_path)
    db.add(ActivityLog(user_id=user.id, action="FILES_RENAME", description=f"rename {old_base} -> {new_base} in {path or '/'}", status="success"))
    db.commit()
    return RedirectResponse(url=f"/cpanel/files?path={path}&success=Renamed", status_code=302)


@router.post("/files/chmod")
async def change_permissions(
    path: str = Form(""),
    item_name: str = Form(...),
    permissions: str = Form("755"),
    db: Session = Depends(get_db),
    user=Depends(get_cpanel_user)
):
    item_path = FileManagerService.safe_path(user.username, os.path.join(path, item_name))
    if os.path.exists(item_path):
        os.chmod(item_path, int(permissions, 8))
    db.add(ActivityLog(user_id=user.id, action="FILES_CHMOD", description=f"chmod {permissions} {os.path.join(path, item_name)}", status="success"))
    db.commit()
    return RedirectResponse(url=f"/cpanel/files?path={path}&success=Permissions+changed", status_code=302)


@router.get("/files/download")
async def download_file(path: str, user=Depends(get_cpanel_user)):
    file_path = FileManagerService.safe_path(user.username, path)
    if os.path.isfile(file_path):
        return FileResponse(file_path, filename=os.path.basename(file_path))
    raise HTTPException(status_code=404)


@router.get("/files/edit", response_class=HTMLResponse)
async def edit_file(request: Request, path: str, user=Depends(get_cpanel_user)):
    file_path = FileManagerService.safe_path(user.username, path)
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
    db: Session = Depends(get_db),
    user=Depends(get_cpanel_user)
):
    file_path = FileManagerService.safe_path(user.username, path)
    with open(file_path, "w") as f:
        f.write(content)
    parent = os.path.dirname(path)
    db.add(ActivityLog(user_id=user.id, action="FILES_SAVE", description=f"save {path}", status="success"))
    db.commit()
    return RedirectResponse(url=f"/cpanel/files?path={parent}&success=File+saved", status_code=302)


@router.post("/files/move")
async def move_item(
    src: str = Form(...),
    dest_dir: str = Form(...),
    current: str = Form(""),
    db: Session = Depends(get_db),
    user=Depends(get_cpanel_user),
):
    FileManagerService.move(user.username, src, dest_dir)
    db.add(ActivityLog(user_id=user.id, action="FILES_MOVE", description=f"move {src} -> {dest_dir}", status="success"))
    db.commit()
    return RedirectResponse(url=f"/cpanel/files?path={current}&success=Moved", status_code=302)


@router.post("/files/copy")
async def copy_item(
    src: str = Form(...),
    dest_dir: str = Form(...),
    current: str = Form(""),
    db: Session = Depends(get_db),
    user=Depends(get_cpanel_user),
):
    FileManagerService.copy(user.username, src, dest_dir)
    db.add(ActivityLog(user_id=user.id, action="FILES_COPY", description=f"copy {src} -> {dest_dir}", status="success"))
    db.commit()
    return RedirectResponse(url=f"/cpanel/files?path={current}&success=Copied", status_code=302)


@router.post("/files/zip")
async def zip_items(
    dest_zip: str = Form(...),
    items: str = Form(...),
    current: str = Form(""),
    db: Session = Depends(get_db),
    user=Depends(get_cpanel_user),
):
    rels = [p.strip() for p in (items or "").split(",") if p.strip()]
    FileManagerService.make_zip(user.username, dest_zip, rels)
    db.add(ActivityLog(user_id=user.id, action="FILES_ZIP", description=f"zip {len(rels)} item(s) -> {dest_zip}", status="success"))
    db.commit()
    return RedirectResponse(url=f"/cpanel/files?path={current}&success=Archive+created", status_code=302)


@router.post("/files/unzip")
async def unzip_item(
    archive: str = Form(...),
    dest_dir: str = Form(""),
    current: str = Form(""),
    db: Session = Depends(get_db),
    user=Depends(get_cpanel_user),
):
    dest_dir = dest_dir or os.path.dirname(archive)
    FileManagerService.extract_archive(user.username, archive, dest_dir)
    db.add(ActivityLog(user_id=user.id, action="FILES_UNZIP", description=f"extract {archive} -> {dest_dir}", status="success"))
    db.commit()
    return RedirectResponse(url=f"/cpanel/files?path={current}&success=Archive+extracted", status_code=302)
