"""
AI Chat Endpoints
Two assistants: General AI + App-Specific AI
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from app.core.database import get_db
from app.core.security import get_current_user_or_organization
from app.models.user import User
from app.services.chat_service import get_app_chat, get_general_chat
from app.schemas.response_model import create_response


router = APIRouter()


class ChatMessage(BaseModel):
    message: str
    session_id: Optional[str] = None


# ==============================================================================
# GENERAL AI ASSISTANT
# ==============================================================================

@router.post("/general")
def chat_with_general_ai(
    chat_msg: ChatMessage,
    current_user = Depends(get_current_user_or_organization)
):
    """
    🤖 General AI Assistant

    Ask anything:
    - Programming help
    - Technical solutions
    - Best practices
    - Career advice
    - General knowledge

    NOT limited to this app - can discuss anything!
    """
    if not isinstance(current_user, User):
        raise HTTPException(status_code=403, detail="Only users can chat")

    chat_service = get_general_chat()
    response = chat_service.chat_general(  # ✅ UPDATED METHOD NAME
        user_id=current_user.id,
        message=chat_msg.message,
        session_id=chat_msg.session_id
    )

    return create_response(
        success=True,
        message="Response generated",
        data=response
    )


@router.delete("/general/history")
def clear_general_chat_history(
    session_id: Optional[str] = None,
    current_user = Depends(get_current_user_or_organization)
):
    """Clear conversation history"""
    if not isinstance(current_user, User):
        raise HTTPException(status_code=403, detail="Only users can chat")

    chat_service = get_general_chat()
    chat_service.clear_history(current_user.id, "general", session_id)  # ✅ ADDED chat_type

    return create_response(
        success=True,
        message="Chat history cleared"
    )


# ==============================================================================
# APP-SPECIFIC AI ASSISTANT
# ==============================================================================

@router.post("/app")
def chat_with_app_ai(
    chat_msg: ChatMessage,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_or_organization)
):
    """
    🎯 TeamIQ App Assistant

    Ask about YOUR app:
    - "How many tasks do I have?"
    - "What projects am I on?"
    - "Who's on my team?"
    - "What's my productivity score?"
    - "How do I create a task?"
    - "Where can I find project settings?"

    Uses real data from the database!
    """
    if not isinstance(current_user, User):
        raise HTTPException(status_code=403, detail="Only users can chat")

    chat_service = get_app_chat(db)
    response = chat_service.chat_app(
        user_id=current_user.id,
        message=chat_msg.message,
        session_id=chat_msg.session_id
    )

    return create_response(
        success=True,
        message="Response generated",
        data=response
    )


# ==============================================================================
# SUGGESTED QUESTIONS
# ==============================================================================

@router.get("/app/suggestions")
def get_app_chat_suggestions(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_or_organization)
):
    """
    Get suggested questions user can ask
    Personalized based on their data
    """
    if not isinstance(current_user, User):
        raise HTTPException(status_code=403, detail="Only users can access")

    from app.models.task import Task
    from app.models.dashboard import UserDashboard

    # Get user context
    tasks_count = db.query(Task).filter(Task.owner_id == current_user.id).count()
    dashboard = db.query(UserDashboard).filter(
        UserDashboard.user_id == current_user.id
    ).first()

    suggestions = [
        "What tasks am I working on?",
        "Show me my overdue tasks",
        "What's my productivity score?",
        "Who are my team members?",
        "How do I create a new task?",
        "Where can I view project details?"
    ]

    # Personalize based on data
    if tasks_count > 5:
        suggestions.insert(0, f"I have {tasks_count} tasks - which should I prioritize?")

    if dashboard and dashboard.productivity_score < 60:
        suggestions.insert(0, "How can I improve my productivity score?")

    return create_response(
        success=True,
        message="Suggestions generated",
        data={"suggestions": suggestions[:6]}
    )
