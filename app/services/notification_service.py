import logging
from fastapi import BackgroundTasks
from sqlalchemy.orm import Session
from app.repositories.notification_repository import create_notification, get_notification_preference
from app.schemas.notification import NotificationCreate
from app.models.user import User
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import requests
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from app.models.task import Task


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

#load email configs fron .env
from dotenv import load_dotenv
SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL")

import os

load_dotenv() 

# Email configuration 
SMTP_SERVER = os.getenv("MAIL_SERVER")
SMTP_PORT = int(os.getenv("MAIL_PORT", 587))
SMTP_USERNAME = os.getenv("MAIL_USERNAME")
SMTP_PASSWORD = os.getenv("MAIL_PASSWORD")
SMTP_FROM = os.getenv("MAIL_FROM")

def send_email(to_email: str, subject: str, body: str):
    try:
        msg = MIMEMultipart()
        msg["From"] = SMTP_USERNAME
        msg["To"] = to_email
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain"))
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USERNAME, SMTP_PASSWORD)
            server.sendmail(SMTP_USERNAME, to_email, msg.as_string())
        logger.info(f"Email sent to {to_email}")
    except Exception as e:
        logger.error(f"Error sending email to {to_email}: {str(e)}")

def send_slack_message(message: str):
    try:
        payload = {"text": message}
        response = requests.post(SLACK_WEBHOOK_URL, json=payload)
        response.raise_for_status()
        logger.info("Slack message sent")
    except Exception as e:
        logger.error(f"Error sending Slack message: {str(e)}")

def trigger_notification(db: Session, user_id: int, notification_type: str, message: str, background_tasks: BackgroundTasks):
    try:
        notification = NotificationCreate(user_id=user_id, type=notification_type, message=message)
        db_notification = create_notification(db, notification)
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            logger.error(f"User {user_id} not found")
            return

        preference = get_notification_preference(db, user_id)
        if notification_type == "task_assigned" and preference.task_assigned_email:
            background_tasks.add_task(send_email, user.email, "New Task Assigned", message)
        if notification_type == "task_updated" and preference.task_updated_email:
            background_tasks.add_task(send_email, user.email, "Task Updated", message)
        if notification_type == "project_completed" and preference.project_completed_email:
            background_tasks.add_task(send_email, user.email, "Project Completed", message)
        if notification_type == "task_assigned" and preference.task_assigned_slack:
            background_tasks.add_task(send_slack_message, message)
        if notification_type == "task_updated" and preference.task_updated_slack:
            background_tasks.add_task(send_slack_message, message)
        if notification_type == "project_completed" and preference.project_completed_slack:
            background_tasks.add_task(send_slack_message, message)
        logger.info(f"Triggered notification for user {user_id}: {notification_type}")
        return db_notification
    except Exception as e:
        logger.error(f"Error triggering notification for user {user_id}: {str(e)}")

def send_daily_summary():
    from app.core.database import SessionLocal
    db = SessionLocal()
    try:
        users = db.query(User).all()
        for user in users:
            preference = get_notification_preference(db, user.id)
            if not preference or not preference.daily_summary_email:
                continue
            tasks = db.query(Task).filter(Task.owner_id == user.id, Task.updated_at >= datetime.utcnow().replace(hour=0, minute=0, second=0)).all()
            summary = f"Daily Summary for {user.username}:\n"
            for task in tasks:
                summary += f"- Task {task.title}: {'Completed' if task.is_completed else 'Pending'}\n"
            if tasks:
                send_email(user.email, "Daily Task Summary", summary)
        logger.info("Daily summaries sent")
    except Exception as e:
        logger.error(f"Error sending daily summaries: {str(e)}")
    finally:
        db.close()

# Initialize scheduler for daily summaries
scheduler = BackgroundScheduler()
scheduler.add_job(send_daily_summary, CronTrigger(hour=0, minute=0))
scheduler.start()