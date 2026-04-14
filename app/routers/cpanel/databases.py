"""
cPanel Databases Router - MySQL Database Management
"""
from fastapi import APIRouter, Depends, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from app.database import get_db
from app.auth import get_cpanel_user
from app.models.db_account import DatabaseAccount
from app.services.mysql_service import MySQLService
from app.templating import templates

router = APIRouter(prefix="/cpanel", tags=["cpanel-databases"])


@router.get("/databases", response_class=HTMLResponse)
async def databases_page(request: Request, db: Session = Depends(get_db), user=Depends(get_cpanel_user)):
    databases = db.query(DatabaseAccount).filter(DatabaseAccount.user_id == user.id).all()
    mysql_status = MySQLService.get_server_status()
    return templates.TemplateResponse("cpanel/databases.html", {
        "request": request, "user": user,
        "databases": databases,
        "db_count": len(databases),
        "mysql_status": mysql_status,
        "page": "databases"
    })


@router.post("/databases/create")
async def create_database(
    request: Request,
    db_name_suffix: str = Form(...),
    db_user_suffix: str = Form(...),
    db_password: str = Form(...),
    db: Session = Depends(get_db),
    user=Depends(get_cpanel_user)
):
    db_count = db.query(DatabaseAccount).filter(DatabaseAccount.user_id == user.id).count()
    if user.db_limit > 0 and db_count >= user.db_limit:
        return RedirectResponse(url="/cpanel/databases?error=Database+limit+reached", status_code=302)

    full_db_name = f"{user.username}_{db_name_suffix}"
    full_db_user = f"{user.username}_{db_user_suffix}"

    # Create on MySQL server
    result = MySQLService.create_db_with_user(full_db_name, full_db_user, db_password)

    if result["success"]:
        db_account = DatabaseAccount(
            user_id=user.id,
            db_name=full_db_name,
            db_user=full_db_user,
            db_password_hint=db_password[:3] + "***",
        )
        db.add(db_account)
        db.commit()
        return RedirectResponse(url="/cpanel/databases?success=Database+created", status_code=302)

    return RedirectResponse(url=f"/cpanel/databases?error={result.get('error', 'Failed')}", status_code=302)


@router.post("/databases/{db_id}/delete")
async def delete_database(db_id: int, db: Session = Depends(get_db), user=Depends(get_cpanel_user)):
    database = db.query(DatabaseAccount).filter(DatabaseAccount.id == db_id, DatabaseAccount.user_id == user.id).first()
    if database:
        MySQLService.revoke_privileges(database.db_name, database.db_user)
        MySQLService.drop_database(database.db_name)
        MySQLService.drop_user(database.db_user)
        db.delete(database)
        db.commit()
    return RedirectResponse(url="/cpanel/databases?success=Database+deleted", status_code=302)


@router.post("/databases/{db_id}/change-password")
async def change_db_password(
    db_id: int,
    new_password: str = Form(...),
    db: Session = Depends(get_db),
    user=Depends(get_cpanel_user)
):
    database = db.query(DatabaseAccount).filter(DatabaseAccount.id == db_id, DatabaseAccount.user_id == user.id).first()
    if database:
        MySQLService.change_user_password(database.db_user, new_password)
        database.db_password_hint = new_password[:3] + "***"
        db.commit()
    return RedirectResponse(url="/cpanel/databases?success=Password+changed", status_code=302)
