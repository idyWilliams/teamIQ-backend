import sys
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

load_dotenv()

# Assume standard connection
DATABASE_URL = os.getenv("DATABASE_URL")
if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)
session = Session()

from app.models.task import Task
from app.models.activity import CommitActivity, PullRequestActivity, Activity

project_id = 9
tasks = session.query(Task).filter(Task.project_id == project_id).count()
commits = session.query(CommitActivity).filter(CommitActivity.project_id == project_id).count()
prs = session.query(PullRequestActivity).filter(PullRequestActivity.project_id == project_id).count()
activities = session.query(Activity).filter(Activity.project_id == project_id).count()

print(f"Project 9 Stats -> Tasks: {tasks}, Commits: {commits}, PRs: {prs}, Activities: {activities}")
