"""
ML/AI Prediction Endpoints
Provides intelligent recommendations and predictions
"""

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import get_current_user_or_organization
from app.models.user import User
from app.models.organization import Organization
from app.services.ml_service import get_ml_service
from app.schemas.response_model import create_response


router = APIRouter()


# ==============================================================================
# TASK ASSIGNMENT PREDICTIONS
# ==============================================================================

@router.get("/predict-assignee/{task_id}")
def predict_task_assignee(
    task_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_or_organization)
):
    """
    🤖 AI-powered task assignment recommendation

    Returns ranked list of team members with confidence scores
    Use this when creating/reassigning tasks
    """
    ml_service = get_ml_service(db)
    predictions = ml_service.predict_best_assignee(task_id)

    return create_response(
        success=True,
        message="Task assignment predictions generated",
        data=predictions
    )


@router.get("/predict-task-duration/{task_id}/{user_id}")
def predict_task_duration(
    task_id: int,
    user_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_or_organization)
):
    """
    ⏱️ Predict how long a task will take for a specific user

    Based on historical completion times
    """
    ml_service = get_ml_service(db)
    prediction = ml_service.predict_task_duration(task_id, user_id)

    return create_response(
        success=True,
        message="Task duration predicted",
        data=prediction
    )


# ==============================================================================
# USER PERFORMANCE & PREDICTIONS
# ==============================================================================

@router.get("/user-analysis/{user_id}")
def get_user_ml_analysis(
    user_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_or_organization)
):
    """
    🎯 Complete ML-powered user analysis

    Returns:
    - Skill gaps and proficiency scores
    - Performance predictions (1 & 3 months)
    - Improvement areas with specific recommendations
    - Personalized upskilling roadmap
    - Task time analysis
    """
    # Authorization
    if isinstance(current_user, User):
        if current_user.id != user_id:
            # Check if same organization
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                raise HTTPException(status_code=404, detail="User not found")

            user_orgs = [org.id for org in current_user.organizations]
            target_orgs = [org.id for org in user.organizations]

            if not set(user_orgs).intersection(target_orgs):
                raise HTTPException(status_code=403, detail="Not authorized")

    ml_service = get_ml_service(db)
    analysis = ml_service.analyze_user_performance(user_id)

    return create_response(
        success=True,
        message="User ML analysis completed",
        data=analysis
    )


@router.get("/user-predictions/{user_id}")
def get_user_performance_predictions(
    user_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_or_organization)
):
    """
    📈 Predict user's performance trajectory

    Shows expected performance in 1 month and 3 months
    """
    ml_service = get_ml_service(db)
    predictions = ml_service.predict_user_performance_trend(user_id)

    return create_response(
        success=True,
        message="Performance predictions generated",
        data=predictions
    )


# ==============================================================================
# TEAM & ORGANIZATION INSIGHTS
# ==============================================================================

@router.get("/team-health/{project_id}")
def analyze_team_health(
    project_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_or_organization)
):
    """
    🏥 Team health analysis

    Identifies:
    - Overloaded members
    - Underutilized members
    - At-risk members
    - Workload balance score
    - Actionable recommendations
    """
    ml_service = get_ml_service(db)
    health = ml_service.analyze_team_health(project_id)

    return create_response(
        success=True,
        message="Team health analysis completed",
        data=health
    )


# ==============================================================================
# MODEL TRAINING (ADMIN)
# ==============================================================================

@router.post("/train-model")
def train_ml_model(
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_or_organization)
):
    """
    🔧 Train ML model on historical data

    Should be run weekly to improve predictions
    Requires at least 20 completed tasks
    """
    # Only organizations can trigger training
    if not isinstance(current_user, Organization):
        raise HTTPException(status_code=403, detail="Only organizations can train models")

    ml_service = get_ml_service(db)

    # Run training in background
    background_tasks.add_task(train_model_task, ml_service)

    return create_response(
        success=True,
        message="Model training started in background",
        data={"status": "training"}
    )


def train_model_task(ml_service):
    """Background task for model training"""
    try:
        result = ml_service.train_task_assignment_model()
        print(f"✅ Model training result: {result}")
    except Exception as e:
        print(f"❌ Model training failed: {e}")
