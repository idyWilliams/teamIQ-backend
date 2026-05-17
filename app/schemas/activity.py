from pydantic import BaseModel
from datetime import datetime
from typing import Optional, Any, Dict, List
from enum import Enum

class ActivityType(str, Enum):
    MESSAGE = "message"
    REACTION = "reaction"
    MENTION = "mention"
    THREAD_REPLY = "thread_reply"
    COMMIT = "commit"
    PULL_REQUEST = "pull_request"
    CODE_REVIEW = "code_review"
    PR_COMMENT = "pr_comment"
    PR_MERGE = "pr_merge"
    TASK_CREATED = "task_created"
    TASK_UPDATED = "task_updated"
    TASK_COMPLETED = "task_completed"
    TASK_COMMENT = "task_comment"
    TASK_ASSIGNED = "task_assigned"
    FILE_UPLOAD = "file_upload"
    MEETING_ATTENDED = "meeting_attended"

class ActivityResponse(BaseModel):
    id: int
    user_id: int
    project_id: int
    type: str
    source: str
    action: str
    title: Optional[str] = None
    content: Optional[str] = None
    activity_metadata: Optional[Dict[str, Any]] = None
    external_id: Optional[str] = None
    external_url: Optional[str] = None
    channel_id: Optional[str] = None
    impact_score: float = 0.0
    complexity_score: float = 0.0
    timestamp: datetime
    synced_at: datetime

    class Config:
        from_attributes = True

class CommitActivityResponse(BaseModel):
    id: int
    user_id: int
    project_id: int
    commit_sha: Optional[str] = None
    message: str
    branch: Optional[str] = None
    repository: str
    files_changed: int = 0
    additions: int = 0
    deletions: int = 0
    files: Optional[List[Any]] = None
    external_url: Optional[str] = None
    source: str
    timestamp: datetime
    synced_at: datetime

    class Config:
        from_attributes = True

class PullRequestActivityResponse(BaseModel):
    id: int
    user_id: int
    project_id: int
    pr_number: int
    title: str
    description: Optional[str] = None
    state: str
    files_changed: int = 0
    commits_count: int = 0
    comments_count: int = 0
    reviews_count: int = 0
    external_id: Optional[str] = None
    external_url: Optional[str] = None
    source: str
    created_at: datetime
    merged_at: Optional[datetime] = None
    synced_at: datetime

    class Config:
        from_attributes = True
