"""
ML Service - Integration layer between ML models and API
Handles predictions, training, and caching
"""

from sqlalchemy.orm import Session
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from app.ml.models import get_task_predictor, get_user_predictor
from app.models.user import User
from app.models.task import Task, TaskStatus
from app.models.project import Project, ProjectMember
from app.models.activity import CommitActivity
from app.models.dashboard import UserDashboard


class MLService:
    """Main ML service for all predictions and recommendations"""

    def __init__(self, db: Session):
        self.db = db
        self.task_predictor = get_task_predictor()
        self.user_predictor = get_user_predictor()

    # =========================================================================
    # TASK ASSIGNMENT PREDICTIONS
    # =========================================================================

    def predict_best_assignee(self, task_id: int) -> Dict:
        """
        Predict best person to assign a task
        Returns ranked list with confidence scores
        """
        task = self.db.query(Task).filter(Task.id == task_id).first()

        if not task:
            return {"error": "Task not found"}

        # Get all project members
        members = self.db.query(ProjectMember).filter(
            ProjectMember.project_id == task.project_id
        ).all()

        if not members:
            return {"error": "No team members found"}

        predictions = []

        for member in members:
            user = self.db.query(User).filter(User.id == member.user_id).first()
            if not user:
                continue

            # Prepare user data
            user_data = self._prepare_user_data(user.id, task.project_id)

            # Prepare task data
            task_data = self._prepare_task_data(task)

            # Calculate skill match
            user_data['skill_match_score'] = self._calculate_skill_match(
                user.skills or [], task
            )

            # Get prediction
            confidence, explanation = self.task_predictor.predict(user_data, task_data)

            predictions.append({
                "user_id": user.id,
                "name": f"{user.first_name} {user.last_name}",
                "avatar": user.profile_image,
                "role": member.role,
                "confidence_score": round(confidence, 1),
                "explanation": explanation,
                "metrics": {
                    "completion_rate": user_data.get('completion_rate', 0),
                    "current_workload": user_data.get('current_workload', 0),
                    "skill_match": user_data.get('skill_match_score', 0),
                    "recent_activity": user_data.get('commits_last_30d', 0)
                }
            })

        # Sort by confidence score
        predictions.sort(key=lambda x: x['confidence_score'], reverse=True)

        # Add ranking
        for idx, pred in enumerate(predictions):
            pred['rank'] = idx + 1

        return {
            "task_id": task_id,
            "task_title": task.title,
            "recommendations": predictions,
            "best_match": predictions[0] if predictions else None,
            "generated_at": datetime.utcnow().isoformat()
        }

    def _prepare_user_data(self, user_id: int, project_id: Optional[int] = None) -> Dict:
        """Prepare user data for ML model"""
        dashboard = self.db.query(UserDashboard).filter(
            UserDashboard.user_id == user_id
        ).first()

        thirty_days_ago = datetime.utcnow() - timedelta(days=30)

        # Get current workload
        active_tasks = self.db.query(Task).filter(
            Task.owner_id == user_id,
            Task.status.in_([TaskStatus.TODO, TaskStatus.IN_PROGRESS])
        ).count()

        # Get recent activity
        recent_commits = self.db.query(CommitActivity).filter(
            CommitActivity.user_id == user_id,
            CommitActivity.timestamp >= thirty_days_ago
        ).count()

        recent_completed_tasks = self.db.query(Task).filter(
            Task.owner_id == user_id,
            Task.status == TaskStatus.DONE,
            Task.completed_at >= thirty_days_ago
        ).count()

        return {
            'completion_rate': dashboard.tasks_completed / dashboard.tasks_total * 100 if dashboard and dashboard.tasks_total > 0 else 50,
            'avg_completion_time_hours': dashboard.avg_completion_time_hours if dashboard else 24,
            'current_workload': active_tasks,
            'commits_last_30d': recent_commits,
            'tasks_completed_last_30d': recent_completed_tasks
        }

    def _prepare_task_data(self, task: Task) -> Dict:
        """Prepare task data for ML model"""
        priority_map = {
            'LOW': 1,
            'MEDIUM': 2,
            'HIGH': 3,
            'URGENT': 4
        }

        return {
            'priority_score': priority_map.get(task.priority, 2)
        }

    def _calculate_skill_match(self, user_skills: List[str], task: Task) -> float:
        """Calculate how well user skills match task requirements"""
        if not user_skills:
            return 30.0  # Base score for no skills

        # Extract keywords from task title and description
        task_text = f"{task.title} {task.description or ''}".lower()

        matched_skills = sum(1 for skill in user_skills if skill.lower() in task_text)

        if not matched_skills:
            return 40.0  # Some base score

        # Score based on match percentage
        match_percentage = (matched_skills / len(user_skills)) * 100

        return min(100, 50 + match_percentage)

    # =========================================================================
    # USER PERFORMANCE ANALYSIS & PREDICTIONS
    # =========================================================================

    def analyze_user_performance(self, user_id: int, project_id: Optional[int] = None) -> Dict:
        """
        Complete user performance analysis with ML predictions
        Includes: skill gaps, improvement areas, upskilling roadmap
        """
        return self.user_predictor.analyze_user(user_id, self.db)

    def predict_user_performance_trend(self, user_id: int) -> Dict:
        """
        Predict user's performance over next 1-3 months
        """
        analysis = self.analyze_user_performance(user_id)

        if 'error' in analysis:
            return analysis

        return {
            "user_id": user_id,
            "predictions": analysis.get('predictions', {}),
            "key_factors": analysis.get('predictions', {}).get('key_factors', []),
            "confidence": "medium",
            "generated_at": datetime.utcnow().isoformat()
        }

    # =========================================================================
    # ORGANIZATION-LEVEL INSIGHTS
    # =========================================================================

    def analyze_team_health(self, project_id: int) -> Dict:
        """
        Analyze team health and identify issues
        - Overworked members
        - Underutilized members
        - Skill distribution gaps
        """
        project = self.db.query(Project).filter(Project.id == project_id).first()

        if not project:
            return {"error": "Project not found"}

        members = self.db.query(ProjectMember).filter(
            ProjectMember.project_id == project_id
        ).all()

        team_analysis = []
        overloaded = []
        underutilized = []
        at_risk = []

        for member in members:
            user = self.db.query(User).filter(User.id == member.user_id).first()
            if not user:
                continue

            # Get user metrics
            active_tasks = self.db.query(Task).filter(
                Task.owner_id == user.id,
                Task.project_id == project_id,
                Task.status.in_([TaskStatus.TODO, TaskStatus.IN_PROGRESS])
            ).count()

            completed_tasks = self.db.query(Task).filter(
                Task.owner_id == user.id,
                Task.project_id == project_id,
                Task.status == TaskStatus.DONE
            ).count()

            overdue_tasks = self.db.query(Task).filter(
                Task.owner_id == user.id,
                Task.project_id == project_id,
                Task.status != TaskStatus.DONE,
                Task.due_date < datetime.utcnow()
            ).count()

            member_data = {
                "user_id": user.id,
                "name": f"{user.first_name} {user.last_name}",
                "role": member.role,
                "active_tasks": active_tasks,
                "completed_tasks": completed_tasks,
                "overdue_tasks": overdue_tasks,
                "workload_status": "normal"
            }

            # Classify workload
            if active_tasks > 7 or overdue_tasks > 3:
                member_data["workload_status"] = "overloaded"
                overloaded.append(member_data)
            elif active_tasks < 2 and completed_tasks < 5:
                member_data["workload_status"] = "underutilized"
                underutilized.append(member_data)

            # Check if at risk
            if overdue_tasks > 5:
                at_risk.append({
                    "user": member_data["name"],
                    "reason": f"{overdue_tasks} overdue tasks - needs immediate support"
                })

            team_analysis.append(member_data)

        # Calculate team balance score
        workloads = [m["active_tasks"] for m in team_analysis]
        avg_workload = sum(workloads) / len(workloads) if workloads else 0
        workload_std = np.std(workloads) if workloads else 0

        balance_score = max(0, 100 - (workload_std * 10))

        return {
            "project_id": project_id,
            "team_size": len(team_analysis),
            "balance_score": round(balance_score, 1),
            "team_members": team_analysis,
            "issues": {
                "overloaded_members": overloaded,
                "underutilized_members": underutilized,
                "at_risk_members": at_risk
            },
            "recommendations": self._generate_team_recommendations(
                overloaded, underutilized, at_risk
            ),
            "generated_at": datetime.utcnow().isoformat()
        }

    def _generate_team_recommendations(self, overloaded, underutilized, at_risk) -> List[str]:
        """Generate actionable team recommendations"""
        recommendations = []

        if overloaded:
            recommendations.append(
                f"Redistribute {sum(m['active_tasks'] - 5 for m in overloaded)} tasks from overloaded members"
            )

        if underutilized:
            recommendations.append(
                f"Assign more tasks to {len(underutilized)} underutilized team members"
            )

        if at_risk:
            recommendations.append(
                f"Immediate intervention needed for {len(at_risk)} at-risk members - schedule 1-on-1s"
            )

        if not recommendations:
            recommendations.append("Team workload is well-balanced. Maintain current approach.")

        return recommendations

    # =========================================================================
    # TASK TIME PREDICTIONS
    # =========================================================================

    def predict_task_duration(self, task_id: int, user_id: int) -> Dict:
        """
        Predict how long a task will take for a specific user
        Based on historical completion times
        """
        task = self.db.query(Task).filter(Task.id == task_id).first()
        user = self.db.query(User).filter(User.id == user_id).first()

        if not task or not user:
            return {"error": "Task or user not found"}

        # Get historical data for similar tasks
        similar_tasks = self.db.query(Task).filter(
            Task.owner_id == user_id,
            Task.status == TaskStatus.DONE,
            Task.completed_at.isnot(None),
            Task.created_at.isnot(None)
        ).all()

        if not similar_tasks:
            # No historical data - use defaults
            return {
                "task_id": task_id,
                "user_id": user_id,
                "predicted_hours": task.estimated_hours or 8,
                "confidence": "low",
                "explanation": "No historical data available. Using task estimate."
            }

        # Calculate average completion time
        completion_times = [
            (t.completed_at - t.created_at).total_seconds() / 3600
            for t in similar_tasks
        ]

        avg_time = np.mean(completion_times)
        std_time = np.std(completion_times)

        # Adjust based on task priority
        priority_multiplier = {
            'LOW': 0.9,
            'MEDIUM': 1.0,
            'HIGH': 1.2,
            'URGENT': 1.5
        }

        multiplier = priority_multiplier.get(task.priority, 1.0)
        predicted_hours = avg_time * multiplier

        # Calculate confidence
        if len(similar_tasks) >= 10 and std_time < avg_time * 0.3:
            confidence = "high"
        elif len(similar_tasks) >= 5:
            confidence = "medium"
        else:
            confidence = "low"

        return {
            "task_id": task_id,
            "user_id": user_id,
            "predicted_hours": round(predicted_hours, 1),
            "range": {
                "min": round(predicted_hours - std_time, 1),
                "max": round(predicted_hours + std_time, 1)
            },
            "confidence": confidence,
            "explanation": f"Based on {len(similar_tasks)} similar completed tasks",
            "historical_average": round(avg_time, 1),
            "generated_at": datetime.utcnow().isoformat()
        }

    # =========================================================================
    # MODEL TRAINING
    # =========================================================================

    def train_task_assignment_model(self) -> Dict:
        """
        Train ML model on historical task assignments
        Should be run periodically (e.g., weekly)
        """
        # Get all completed tasks with assignments
        completed_tasks = self.db.query(Task).filter(
            Task.status == TaskStatus.DONE,
            Task.owner_id.isnot(None),
            Task.completed_at.isnot(None)
        ).all()

        if len(completed_tasks) < 20:
            return {
                "success": False,
                "message": f"Not enough training data. Need at least 20 completed tasks, found {len(completed_tasks)}",
                "training_examples": len(completed_tasks)
            }

        training_data = []

        for task in completed_tasks:
            user_data = self._prepare_user_data(task.owner_id, task.project_id)
            task_data = self._prepare_task_data(task)

            # Determine if assignment was successful
            # Success = completed on time with good quality
            was_successful = (
                task.completed_at and
                task.due_date and
                task.completed_at <= task.due_date
            )

            training_data.append((user_data, task_data, was_successful))

        # Train model
        success = self.task_predictor.train(training_data)

        if success:
            # Save model
            self.task_predictor.save()

            return {
                "success": True,
                "message": "Model trained successfully",
                "training_examples": len(training_data),
                "model_file": "ml/task_assignment_model.pkl"
            }
        else:
            return {
                "success": False,
                "message": "Training failed",
                "training_examples": len(training_data)
            }


def get_ml_service(db: Session) -> MLService:
    """Factory function"""
    return MLService(db)


# Import numpy for calculations
import numpy as np
