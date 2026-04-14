"""cPanel Cron Jobs Router"""
from fastapi import APIRouter, Depends, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
import subprocess
from app.database import get_db
from app.auth import get_cpanel_user
from app.models.cron_job import CronJob

router = APIRouter(prefix="/cpanel", tags=["cpanel-cron"])
templates = Jinja2Templates(directory="app/templates")


def update_system_crontab(username: str, jobs: list):
    """Update crontab for a system user"""
    cron_lines = "\n".join([
        f"{j.minute} {j.hour} {j.day_of_month} {j.month} {j.day_of_week} {j.command}"
        for j in jobs if j.is_active
    ])
    proc = subprocess.run(
        f"echo '{cron_lines}' | crontab -u {username} -",
        shell=True, capture_output=True
    )
    return proc.returncode == 0


@router.get("/cron", response_class=HTMLResponse)
async def cron_page(request: Request, db: Session = Depends(get_db), user=Depends(get_cpanel_user)):
    jobs = db.query(CronJob).filter(CronJob.user_id == user.id).all()
    return templates.TemplateResponse("cpanel/cron.html", {
        "request": request, "user": user, "jobs": jobs, "page": "cron"
    })


@router.post("/cron/create")
async def create_cron(
    name: str = Form(""),
    command: str = Form(...),
    minute: str = Form("*"),
    hour: str = Form("*"),
    day_of_month: str = Form("*"),
    month: str = Form("*"),
    day_of_week: str = Form("*"),
    email_output: str = Form(""),
    db: Session = Depends(get_db),
    user=Depends(get_cpanel_user)
):
    job = CronJob(
        user_id=user.id, name=name, command=command,
        minute=minute, hour=hour,
        day_of_month=day_of_month, month=month,
        day_of_week=day_of_week, email_output=email_output
    )
    db.add(job)
    db.flush()

    # Update system crontab
    all_jobs = db.query(CronJob).filter(CronJob.user_id == user.id, CronJob.is_active == True).all()
    update_system_crontab(user.username, all_jobs)
    db.commit()

    return RedirectResponse(url="/cpanel/cron?success=Cron+job+created", status_code=302)


@router.post("/cron/{job_id}/delete")
async def delete_cron(job_id: int, db: Session = Depends(get_db), user=Depends(get_cpanel_user)):
    job = db.query(CronJob).filter(CronJob.id == job_id, CronJob.user_id == user.id).first()
    if job:
        db.delete(job)
        db.flush()
        all_jobs = db.query(CronJob).filter(CronJob.user_id == user.id, CronJob.is_active == True).all()
        update_system_crontab(user.username, all_jobs)
        db.commit()
    return RedirectResponse(url="/cpanel/cron?success=Cron+job+deleted", status_code=302)


@router.post("/cron/{job_id}/toggle")
async def toggle_cron(job_id: int, db: Session = Depends(get_db), user=Depends(get_cpanel_user)):
    job = db.query(CronJob).filter(CronJob.id == job_id, CronJob.user_id == user.id).first()
    if job:
        job.is_active = not job.is_active
        all_jobs = db.query(CronJob).filter(CronJob.user_id == user.id).all()
        active_jobs = [j for j in all_jobs if j.is_active]
        update_system_crontab(user.username, active_jobs)
        db.commit()
    return RedirectResponse(url="/cpanel/cron?success=Updated", status_code=302)
