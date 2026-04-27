"""
Machine Learning Models for Predictions
Uses scikit-learn (FREE, no API keys needed)
Trains on collected system data
"""

import numpy as np
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.preprocessing import StandardScaler
import pickle
import os
from datetime import datetime, timedelta
from typing import Dict, List, Tuple
from sqlalchemy.orm import Session


class TaskAssignmentPredictor:
    """
    Predicts best user for a task based on historical data
    Features: user skills, past completion rate, current workload, task type
    """

    def __init__(self):
        self.model = RandomForestClassifier(n_estimators=100, random_state=42)
        self.scaler = StandardScaler()
        self.is_trained = False
        self.feature_names = [
            'user_completion_rate',
            'user_avg_completion_time',
            'user_current_workload',
            'skill_match_score',
            'user_commits_last_30d',
            'user_tasks_completed_last_30d',
            'task_priority_score'
        ]

    def prepare_features(self, user_data: Dict, task_data: Dict) -> np.array:
        """Convert user and task data to ML features"""
        features = [
            user_data.get('completion_rate', 0) / 100,  # Normalize to 0-1
            user_data.get('avg_completion_time_hours', 24) / 168,  # Normalize to 0-1 (168 hours = 1 week)
            user_data.get('current_workload', 0) / 10,  # Normalize
            user_data.get('skill_match_score', 0) / 100,
            user_data.get('commits_last_30d', 0) / 50,  # Normalize
            user_data.get('tasks_completed_last_30d', 0) / 20,
            task_data.get('priority_score', 2) / 4  # LOW=1, MEDIUM=2, HIGH=3, URGENT=4
        ]
        return np.array(features).reshape(1, -1)

    def train(self, training_data: List[Tuple[Dict, Dict, bool]]):
        """
        Train model on historical task assignments
        training_data: [(user_data, task_data, was_successful), ...]
        """
        if len(training_data) < 10:
            print("⚠️  Not enough training data. Need at least 10 historical assignments.")
            return False

        X = []
        y = []

        for user_data, task_data, was_successful in training_data:
            features = self.prepare_features(user_data, task_data)
            X.append(features[0])
            y.append(1 if was_successful else 0)

        X = np.array(X)
        y = np.array(y)

        # Scale features
        X_scaled = self.scaler.fit_transform(X)

        # Train model
        self.model.fit(X_scaled, y)
        self.is_trained = True

        print(f"✅ Task Assignment Model trained on {len(training_data)} examples")
        return True

    def predict(self, user_data: Dict, task_data: Dict) -> Tuple[float, str]:
        """
        Predict success probability for assigning task to user
        Returns: (confidence_score 0-100, explanation)
        """
        if not self.is_trained:
            # Fallback to rule-based
            return self._rule_based_prediction(user_data, task_data)

        features = self.prepare_features(user_data, task_data)
        features_scaled = self.scaler.transform(features)

        # Get probability
        proba = self.model.predict_proba(features_scaled)[0][1]  # Probability of success
        confidence = proba * 100

        # Generate explanation
        explanation = self._generate_explanation(user_data, task_data, confidence)

        return confidence, explanation

    def _rule_based_prediction(self, user_data: Dict, task_data: Dict) -> Tuple[float, str]:
        """Rule-based fallback when not enough training data"""
        score = 50.0  # Base score
        reasons = []

        # Check completion rate
        completion_rate = user_data.get('completion_rate', 0)
        if completion_rate >= 80:
            score += 20
            reasons.append("high task completion rate")
        elif completion_rate < 50:
            score -= 15
            reasons.append("below-average completion rate")

        # Check workload
        workload = user_data.get('current_workload', 0)
        if workload < 3:
            score += 15
            reasons.append("light current workload")
        elif workload > 7:
            score -= 20
            reasons.append("heavy workload")

        # Check skill match
        skill_match = user_data.get('skill_match_score', 0)
        if skill_match >= 80:
            score += 25
            reasons.append("excellent skill match")
        elif skill_match < 40:
            score -= 15
            reasons.append("limited relevant skills")

        # Check recent activity
        commits = user_data.get('commits_last_30d', 0)
        if commits >= 20:
            score += 10
            reasons.append("consistently active")
        elif commits < 5:
            score -= 10
            reasons.append("low recent activity")

        score = max(0, min(100, score))  # Clamp to 0-100

        explanation = f"Based on: {', '.join(reasons)}"

        return score, explanation

    def _generate_explanation(self, user_data: Dict, task_data: Dict, confidence: float) -> str:
        """Generate human-readable explanation"""
        if confidence >= 75:
            return f"Strong match: High completion rate ({user_data.get('completion_rate', 0):.0f}%), relevant skills, and manageable workload."
        elif confidence >= 50:
            return "Moderate match: Decent skills and availability, but may need support."
        else:
            return "Weak match: Consider assigning to someone with better skill match or lower workload."

    def save(self, filepath: str = "ml/task_assignment_model.pkl"):
        """Save trained model to disk"""
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, 'wb') as f:
            pickle.dump({
                'model': self.model,
                'scaler': self.scaler,
                'is_trained': self.is_trained
            }, f)
        print(f"✅ Model saved to {filepath}")

    def load(self, filepath: str = "ml/task_assignment_model.pkl"):
        """Load trained model from disk"""
        if not os.path.exists(filepath):
            print("⚠️  No saved model found. Will use rule-based predictions.")
            return False

        with open(filepath, 'rb') as f:
            data = pickle.load(f)
            self.model = data['model']
            self.scaler = data['scaler']
            self.is_trained = data['is_trained']

        print(f"✅ Model loaded from {filepath}")
        return True


class UserPerformancePredictor:
    """
    Predicts user performance trends and areas for improvement
    Features: task completion trends, code quality, collaboration
    """

    def __init__(self):
        self.model = RandomForestRegressor(n_estimators=100, random_state=42)
        self.scaler = StandardScaler()
        self.is_trained = False

    def analyze_user(self, user_id: int, db: Session) -> Dict:
        """
        Comprehensive user analysis with predictions
        Returns: skills gaps, improvement areas, predictions
        """
        from app.models.user import User
        from app.models.task import Task, TaskStatus
        from app.models.activity import CommitActivity
        from app.models.dashboard import UserDashboard

        user = db.query(User).filter(User.id == user_id).first()

        if not user:
            return {"error": "User not found"}

        dashboard = db.query(UserDashboard).filter(UserDashboard.user_id == user_id).first()

        # Gather data
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)

        recent_tasks = db.query(Task).filter(
            Task.owner_id == user_id,
            Task.created_at >= thirty_days_ago
        ).all()

        recent_commits = db.query(CommitActivity).filter(
            CommitActivity.user_id == user_id,
            CommitActivity.timestamp >= thirty_days_ago
        ).all()

        # Analyze task completion patterns
        completed_on_time = sum(
            1 for t in recent_tasks
            if t.status == TaskStatus.DONE and t.due_date and t.completed_at and t.completed_at <= t.due_date
        )

        completed_late = sum(
            1 for t in recent_tasks
            if t.status == TaskStatus.DONE and t.due_date and t.completed_at and t.completed_at > t.due_date
        )

        overdue = sum(
            1 for t in recent_tasks
            if t.status != TaskStatus.DONE and t.due_date and t.due_date < datetime.utcnow()
        )

        # Analyze code patterns
        commits_per_week = len(recent_commits) / 4
        avg_commit_size = np.mean([c.additions + c.deletions for c in recent_commits]) if recent_commits else 0

        # 1. SKILL GAP ANALYSIS
        skill_gaps = self._analyze_skill_gaps(user, recent_tasks, recent_commits)

        # 2. IMPROVEMENT AREAS
        improvement_areas = self._identify_improvement_areas(
            completed_on_time, completed_late, overdue, commits_per_week, dashboard
        )

        # 3. PERFORMANCE PREDICTIONS
        predictions = self._predict_performance_trends(
            completed_on_time, completed_late, commits_per_week, dashboard
        )

        # 4. UPSKILLING RECOMMENDATIONS
        upskill_recommendations = self._generate_upskill_recommendations(
            skill_gaps, improvement_areas, user.skills or []
        )

        # 5. TASK TIME ANALYSIS
        task_time_analysis = self._analyze_task_times(recent_tasks)

        return {
            "user_id": user_id,
            "user_name": f"{user.first_name} {user.last_name}",
            "skill_analysis": {
                "current_skills": user.skills or [],
                "skill_gaps": skill_gaps,
                "proficiency_scores": self._calculate_proficiency_scores(user, recent_commits)
            },
            "improvement_areas": improvement_areas,
            "predictions": predictions,
            "upskilling_roadmap": upskill_recommendations,
            "task_time_analysis": task_time_analysis,
            "generated_at": datetime.utcnow().isoformat()
        }

    def _analyze_skill_gaps(self, user, recent_tasks, recent_commits) -> List[Dict]:
        """Identify missing or weak skills"""
        gaps = []

        # Check if user has required skills for their tasks
        task_keywords = set()
        for task in recent_tasks:
            if task.description:
                desc_lower = task.description.lower()
                # Extract potential tech keywords
                tech_keywords = ['react', 'python', 'django', 'fastapi', 'sql', 'aws', 'docker', 'kubernetes']
                for keyword in tech_keywords:
                    if keyword in desc_lower:
                        task_keywords.add(keyword.capitalize())

        user_skills_lower = [s.lower() for s in (user.skills or [])]

        for keyword in task_keywords:
            if keyword.lower() not in user_skills_lower:
                gaps.append({
                    "skill": keyword,
                    "reason": "Required for tasks but not in profile",
                    "priority": "high",
                    "learning_resources": self._get_learning_resources(keyword)
                })

        # Check commit patterns for code quality issues
        if len(recent_commits) > 0:
            avg_commit_size = np.mean([c.additions + c.deletions for c in recent_commits])
            if avg_commit_size > 500:
                gaps.append({
                    "skill": "Code Modularity",
                    "reason": "Large commit sizes suggest need for better code organization",
                    "priority": "medium",
                    "learning_resources": ["https://refactoring.guru/", "Clean Code book"]
                })

        return gaps

    def _identify_improvement_areas(self, completed_on_time, completed_late, overdue, commits_per_week, dashboard) -> List[Dict]:
        """Identify specific areas needing improvement"""
        areas = []

        total_completed = completed_on_time + completed_late

        # Time management
        if overdue > 0 or (completed_late > completed_on_time and total_completed > 0):
            areas.append({
                "area": "Time Management",
                "severity": "high" if overdue > 3 else "medium",
                "details": f"{overdue} overdue tasks, {completed_late} completed late",
                "recommendations": [
                    "Break large tasks into smaller subtasks",
                    "Set internal deadlines 2 days before actual due date",
                    "Use time-blocking techniques for focused work"
                ]
            })

        # Code contribution consistency
        if commits_per_week < 2:
            areas.append({
                "area": "Code Contribution Frequency",
                "severity": "medium",
                "details": f"Only {commits_per_week:.1f} commits per week",
                "recommendations": [
                    "Aim for daily commits, even small improvements",
                    "Follow 'commit early, commit often' principle",
                    "Set up automated reminders for end-of-day commits"
                ]
            })

        # Collaboration
        if dashboard and dashboard.messages_sent < 30:  # Less than 1 per day
            areas.append({
                "area": "Team Communication",
                "severity": "low",
                "details": "Limited team interaction observed",
                "recommendations": [
                    "Participate more in daily standups",
                    "Ask questions in team channels",
                    "Share progress updates regularly"
                ]
            })

        return areas if areas else [{"area": "None", "details": "Performance is strong across all areas!"}]

    def _predict_performance_trends(self, completed_on_time, completed_late, commits_per_week, dashboard) -> Dict:
        """Predict future performance based on trends"""
        total_completed = completed_on_time + completed_late

        # Calculate current trajectory
        if total_completed > 0:
            on_time_rate = completed_on_time / total_completed
        else:
            on_time_rate = 0.5

        # Simple linear trend projection
        current_score = dashboard.productivity_score if dashboard else 50

        # Predict 1 month
        if on_time_rate >= 0.8 and commits_per_week >= 3:
            month_1_score = min(100, current_score + 10)
            month_1_outlook = "improving"
        elif on_time_rate < 0.5 or commits_per_week < 1:
            month_1_score = max(0, current_score - 10)
            month_1_outlook = "declining"
        else:
            month_1_score = current_score
            month_1_outlook = "stable"

        # Predict 3 months
        if on_time_rate >= 0.8 and commits_per_week >= 4:
            month_3_score = min(100, current_score + 25)
            month_3_outcome = "Likely promotion to senior role"
        elif on_time_rate < 0.5:
            month_3_score = max(0, current_score - 15)
            month_3_outcome = "May need additional support or training"
        else:
            month_3_score = current_score + 5
            month_3_outcome = "Steady growth expected"

        return {
            "current_score": round(current_score, 1),
            "1_month": {
                "predicted_score": round(month_1_score, 1),
                "outlook": month_1_outlook,
                "confidence": 75
            },
            "3_months": {
                "predicted_score": round(month_3_score, 1),
                "outcome": month_3_outcome,
                "confidence": 60
            },
            "key_factors": [
                f"On-time completion rate: {on_time_rate*100:.0f}%",
                f"Code contribution: {commits_per_week:.1f} commits/week"
            ]
        }

    def _generate_upskill_recommendations(self, skill_gaps, improvement_areas, current_skills) -> Dict:
        """Generate personalized learning roadmap"""
        roadmap = {
            "immediate": [],
            "short_term": [],
            "long_term": []
        }

        # Immediate (this week)
        for gap in skill_gaps[:2]:  # Top 2 gaps
            if gap['priority'] == 'high':
                roadmap["immediate"].append({
                    "skill": gap['skill'],
                    "action": f"Complete tutorial/course on {gap['skill']}",
                    "resources": gap['learning_resources'],
                    "estimated_time": "5-10 hours"
                })

        # Short-term (this month)
        for area in improvement_areas[:2]:
            if area['area'] != 'None':
                roadmap["short_term"].append({
                    "area": area['area'],
                    "actions": area['recommendations'],
                    "estimated_time": "2-4 weeks"
                })

        # Long-term (3-6 months)
        roadmap["long_term"].append({
            "goal": "Expand technical breadth",
            "actions": [
                "Learn complementary technology (e.g., if backend dev, learn frontend basics)",
                "Contribute to open-source projects",
                "Mentor junior developers"
            ],
            "estimated_time": "3-6 months"
        })

        return roadmap

    def _analyze_task_times(self, recent_tasks) -> Dict:
        """Analyze which tasks are taking too long"""
        slow_tasks = []

        for task in recent_tasks:
            if task.completed_at and task.created_at:
                duration_hours = (task.completed_at - task.created_at).total_seconds() / 3600

                # If task took more than estimated or > 40 hours
                if (task.estimated_hours and duration_hours > task.estimated_hours * 1.5) or duration_hours > 40:
                    slow_tasks.append({
                        "task_title": task.title,
                        "estimated_hours": task.estimated_hours or "Not set",
                        "actual_hours": round(duration_hours, 1),
                        "overrun_percentage": round(((duration_hours / task.estimated_hours) - 1) * 100, 1) if task.estimated_hours else "N/A",
                        "possible_reasons": self._diagnose_slow_task(task, duration_hours)
                    })

        return {
            "slow_tasks_count": len(slow_tasks),
            "slow_tasks": slow_tasks[:5],  # Top 5
            "recommendations": [
                "Break down complex tasks into smaller subtasks",
                "Set more realistic time estimates based on historical data",
                "Identify and remove blockers early"
            ] if slow_tasks else ["Task completion times are healthy!"]
        }

    def _diagnose_slow_task(self, task, duration_hours) -> List[str]:
        """Diagnose why a task took too long"""
        reasons = []

        if duration_hours > 80:
            reasons.append("Task may have been too complex - consider breaking down")

        if task.priority == "URGENT":
            reasons.append("Urgent priority may have caused stress - plan better")

        if not task.estimated_hours:
            reasons.append("No time estimate - harder to manage expectations")

        return reasons if reasons else ["Normal development time"]

    def _calculate_proficiency_scores(self, user, recent_commits) -> Dict:
        """Calculate proficiency in each skill"""
        scores = {}

        for skill in (user.skills or []):
            # Simple heuristic: count commits related to this skill
            related_commits = sum(
                1 for c in recent_commits
                if skill.lower() in c.message.lower()
            )

            # Score out of 100
            score = min(100, 50 + (related_commits * 5))

            scores[skill] = {
                "score": score,
                "level": "Expert" if score >= 80 else "Intermediate" if score >= 50 else "Beginner"
            }

        return scores

    def _get_learning_resources(self, skill: str) -> List[str]:
        """Get free learning resources for a skill"""
        resources = {
            "Python": ["https://www.learnpython.org/", "https://realpython.com/"],
            "JavaScript": ["https://javascript.info/", "https://www.freecodecamp.org/"],
            "React": ["https://react.dev/learn", "https://www.freecodecamp.org/news/react-beginner-handbook/"],
            "Django": ["https://docs.djangoproject.com/en/stable/intro/tutorial01/", "https://www.djangoproject.com/"],
            "FastAPI": ["https://fastapi.tiangolo.com/tutorial/", "https://testdriven.io/blog/fastapi-crud/"],
            "SQL": ["https://sqlbolt.com/", "https://www.w3schools.com/sql/"],
            "Docker": ["https://docs.docker.com/get-started/", "https://www.freecodecamp.org/news/the-docker-handbook/"],
            "AWS": ["https://aws.amazon.com/getting-started/", "https://www.freecodecamp.org/news/aws-certified-solutions-architect-associate-certification-guide/"]
        }

        return resources.get(skill, [f"https://www.google.com/search?q=learn+{skill.lower()}"])


# Singleton instances
_task_predictor = None
_user_predictor = None


def get_task_predictor() -> TaskAssignmentPredictor:
    """Get singleton task predictor instance"""
    global _task_predictor
    if _task_predictor is None:
        _task_predictor = TaskAssignmentPredictor()
        _task_predictor.load()  # Try to load saved model
    return _task_predictor


def get_user_predictor() -> UserPerformancePredictor:
    """Get singleton user predictor instance"""
    global _user_predictor
    if _user_predictor is None:
        _user_predictor = UserPerformancePredictor()
    return _user_predictor
