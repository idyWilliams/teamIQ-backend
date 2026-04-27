"""
AI Service for Generating Insights and Predictions
Uses OpenAI GPT or Anthropic Claude for analysis
"""

from typing import Dict, Optional
import openai
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from app.core.config import settings
from app.models.user import User
from app.models.project import Project
from app.models.task import Task
from app.models.activity import Activity, CommitActivity


class AIInsightsService:
    """
    Generates AI-powered insights using GPT-4
    Analyzes user behavior, productivity patterns, and team dynamics
    """

    def __init__(self, db: Session):
        self.db = db
        openai.api_key = settings.OPENAI_API_KEY

    # =========================================================================
    # PROJECT AI SUMMARY
    # =========================================================================

    def generate_project_summary(self, project_id: int) -> Dict:
        """
        Generate AI summary for project overview page
        Analyzes: tasks, commits, team activity, timeline
        """
        project = self.db.query(Project).filter(Project.id == project_id).first()

        if not project:
            return {"error": "Project not found"}

        # Gather project data
        tasks = self.db.query(Task).filter(Task.project_id == project_id).all()
        activities = self.db.query(Activity).filter(
            Activity.project_id == project_id,
            Activity.timestamp >= datetime.utcnow() - timedelta(days=30)
        ).all()

        commits = self.db.query(CommitActivity).filter(
            CommitActivity.project_id == project_id,
            CommitActivity.timestamp >= datetime.utcnow() - timedelta(days=30)
        ).all()

        # Calculate metrics
        total_tasks = len(tasks)
        completed_tasks = sum(1 for t in tasks if t.status.value == "DONE")
        in_progress_tasks = sum(1 for t in tasks if t.status.value == "IN_PROGRESS")
        overdue_tasks = sum(1 for t in tasks if t.due_date and t.due_date < datetime.utcnow() and t.status.value != "DONE")

        total_commits = len(commits)
        total_activities = len(activities)

        # Calculate velocity (tasks completed per week)
        weeks_elapsed = (datetime.utcnow() - project.start_date).days / 7 if project.start_date else 4
        velocity = completed_tasks / weeks_elapsed if weeks_elapsed > 0 else 0

        # Prepare context for AI
        context = f"""
Project: {project.name}
Description: {project.description}
Timeline: {project.start_date} to {project.end_date}
Duration: {weeks_elapsed:.1f} weeks elapsed

Current Status:
- Total Tasks: {total_tasks}
- Completed: {completed_tasks} ({(completed_tasks/total_tasks*100) if total_tasks > 0 else 0:.1f}%)
- In Progress: {in_progress_tasks}
- Overdue: {overdue_tasks}
- Velocity: {velocity:.1f} tasks/week

Activity (Last 30 days):
- Commits: {total_commits}
- Team Activities: {total_activities}

Technology Stack: {', '.join(project.stacks) if project.stacks else 'Not specified'}
"""

        # Call GPT-4 for summary
        try:
            response = openai.ChatCompletion.create(
                model="gpt-4",
                messages=[
                    {
                        "role": "system",
                        "content": """You are an expert project manager and data analyst.
Generate a concise, insightful project summary in 2-3 sentences that highlights:
1. Current project health (on track, at risk, or behind)
2. Key achievements or concerns
3. Actionable recommendation

Be direct, data-driven, and professional. Use metrics provided."""
                    },
                    {
                        "role": "user",
                        "content": context
                    }
                ],
                max_tokens=150,
                temperature=0.7
            )

            ai_summary = response.choices[0].message.content.strip()

            return {
                "summary": ai_summary,
                "metrics": {
                    "total_tasks": total_tasks,
                    "completed_tasks": completed_tasks,
                    "completion_rate": round((completed_tasks/total_tasks*100) if total_tasks > 0 else 0, 1),
                    "overdue_tasks": overdue_tasks,
                    "velocity": round(velocity, 2),
                    "total_commits": total_commits,
                    "team_activity_score": total_activities
                },
                "health_status": self._calculate_project_health(
                    completed_tasks, total_tasks, overdue_tasks, velocity
                ),
                "generated_at": datetime.utcnow().isoformat()
            }

        except Exception as e:
            print(f"AI Summary Error: {e}")
            return {
                "summary": "Unable to generate AI summary at this time. Project metrics are available below.",
                "error": str(e)
            }

    def _calculate_project_health(self, completed: int, total: int, overdue: int, velocity: float) -> str:
        """Calculate overall project health status"""
        if total == 0:
            return "just_started"

        completion_rate = (completed / total) * 100

        if overdue > 5 or (completion_rate < 30 and velocity < 2):
            return "at_risk"
        elif completion_rate > 70 and overdue < 2:
            return "on_track"
        elif completion_rate >= 50:
            return "healthy"
        else:
            return "needs_attention"

    # =========================================================================
    # USER PERFORMANCE ANALYSIS
    # =========================================================================

    def analyze_user_performance(self, user_id: int, project_id: Optional[int] = None) -> Dict:
        """
        Deep AI analysis of individual user performance
        Provides: strengths, weaknesses, predictions, recommendations
        """
        user = self.db.query(User).filter(User.id == user_id).first()

        if not user:
            return {"error": "User not found"}

        # Gather user data (last 90 days)
        start_date = datetime.utcnow() - timedelta(days=90)

        query_tasks = self.db.query(Task).filter(Task.owner_id == user_id)
        if project_id:
            query_tasks = query_tasks.filter(Task.project_id == project_id)

        tasks = query_tasks.filter(Task.created_at >= start_date).all()

        query_commits = self.db.query(CommitActivity).filter(CommitActivity.user_id == user_id)
        if project_id:
            query_commits = query_commits.filter(CommitActivity.project_id == project_id)

        commits = query_commits.filter(CommitActivity.timestamp >= start_date).all()

        query_activities = self.db.query(Activity).filter(Activity.user_id == user_id)
        if project_id:
            query_activities = query_activities.filter(Activity.project_id == project_id)

        activities = query_activities.filter(Activity.timestamp >= start_date).all()

        # Calculate detailed metrics
        completed_tasks = [t for t in tasks if t.status.value == "DONE"]
        overdue_tasks = [t for t in tasks if t.due_date and t.due_date < datetime.utcnow() and t.status.value != "DONE"]

        # Task completion patterns
        task_completion_times = []
        for task in completed_tasks:
            if task.completed_at and task.created_at:
                completion_time = (task.completed_at - task.created_at).total_seconds() / 3600  # hours
                task_completion_times.append(completion_time)

        avg_completion_time = sum(task_completion_times) / len(task_completion_times) if task_completion_times else 0

        # Commit patterns (lines of code, frequency)
        total_lines_added = sum(c.additions for c in commits if c.additions)
        total_lines_deleted = sum(c.deletions for c in commits if c.deletions)
        commits_per_week = len(commits) / 12  # 90 days / 7 days

        # Activity patterns
        messages_sent = len([a for a in activities if a.type == "message"])
        reactions_given = len([a for a in activities if a.type == "reaction"])

        # Working hours analysis (commit timestamps)
        commit_hours = [c.timestamp.hour for c in commits if c.timestamp]
        peak_hours = max(set(commit_hours), key=commit_hours.count) if commit_hours else None

        # Prepare context for AI analysis
        context = f"""
User: {user.first_name} {user.last_name}
Role: {user.role}
Analysis Period: Last 90 days

Task Performance:
- Total Tasks: {len(tasks)}
- Completed: {len(completed_tasks)}
- Completion Rate: {(len(completed_tasks)/len(tasks)*100) if len(tasks) > 0 else 0:.1f}%
- Overdue: {len(overdue_tasks)}
- Average Completion Time: {avg_completion_time:.1f} hours

Code Contribution:
- Total Commits: {len(commits)}
- Commits per Week: {commits_per_week:.1f}
- Lines Added: {total_lines_added}
- Lines Deleted: {total_lines_deleted}
- Most Active Hour: {peak_hours}:00 UTC

Collaboration:
- Messages Sent: {messages_sent}
- Reactions Given: {reactions_given}
- Team Engagement Score: {(messages_sent + reactions_given) / 90:.2f} per day

Technology Stack: {', '.join(user.skills) if user.skills else 'Not specified'}
"""

        # Call GPT-4 for analysis
        try:
            response = openai.ChatCompletion.create(
                model="gpt-4",
                messages=[
                    {
                        "role": "system",
                        "content": """You are an expert HR analyst and technical lead. Analyze this developer's performance data and provide:

1. STRENGTHS (2-3 bullet points)
2. AREAS FOR IMPROVEMENT (2-3 bullet points)
3. WORKING STYLE (1-2 sentences describing patterns)
4. PREDICTIONS (What will happen if current trends continue)
5. RECOMMENDATIONS (Specific, actionable advice for growth)

Format as JSON:
{
  "strengths": ["...", "..."],
  "improvements": ["...", "..."],
  "working_style": "...",
  "predictions": {
    "3_months": "...",
    "6_months": "..."
  },
  "recommendations": {
    "immediate": ["...", "..."],
    "long_term": ["...", "..."]
  },
  "task_fit": {
    "best_suited_for": ["...", "..."],
    "avoid_assigning": ["...", "..."]
  }
}

Be honest but constructive. Use data to support conclusions."""
                    },
                    {
                        "role": "user",
                        "content": context
                    }
                ],
                max_tokens=800,
                temperature=0.7
            )

            import json
            ai_analysis = json.loads(response.choices[0].message.content.strip())

            return {
                "user_id": user_id,
                "user_name": f"{user.first_name} {user.last_name}",
                "analysis": ai_analysis,
                "raw_metrics": {
                    "tasks_completed": len(completed_tasks),
                    "completion_rate": round((len(completed_tasks)/len(tasks)*100) if len(tasks) > 0 else 0, 1),
                    "avg_completion_time_hours": round(avg_completion_time, 1),
                    "commits_per_week": round(commits_per_week, 1),
                    "lines_of_code": total_lines_added - total_lines_deleted,
                    "collaboration_score": round((messages_sent + reactions_given) / 90, 2)
                },
                "generated_at": datetime.utcnow().isoformat()
            }

        except Exception as e:
            print(f"AI Analysis Error: {e}")
            return {
                "error": str(e),
                "fallback": "AI analysis temporarily unavailable"
            }

    # =========================================================================
    # TEAM OPTIMIZATION
    # =========================================================================

    def generate_team_optimization_insights(self, project_id: int) -> Dict:
        """
        AI-powered team optimization recommendations
        Analyzes: workload balance, collaboration patterns, bottlenecks
        """
        project = self.db.query(Project).filter(Project.id == project_id).first()

        if not project:
            return {"error": "Project not found"}

        # Get all project members
        from app.models.project import ProjectMember
        members = self.db.query(ProjectMember).filter(
            ProjectMember.project_id == project_id
        ).all()

        team_data = []
        for member in members:
            user = self.db.query(User).filter(User.id == member.user_id).first()
            if not user:
                continue

            tasks = self.db.query(Task).filter(
                Task.owner_id == user.id,
                Task.project_id == project_id
            ).all()

            completed = sum(1 for t in tasks if t.status.value == "DONE")
            in_progress = sum(1 for t in tasks if t.status.value == "IN_PROGRESS")
            overdue = sum(1 for t in tasks if t.due_date and t.due_date < datetime.utcnow() and t.status.value != "DONE")

            team_data.append({
                "name": f"{user.first_name} {user.last_name}",
                "role": member.role,
                "tasks_total": len(tasks),
                "tasks_completed": completed,
                "tasks_in_progress": in_progress,
                "tasks_overdue": overdue
            })

        # Prepare context
        context = f"""
Project: {project.name}
Team Size: {len(team_data)}

Team Member Workloads:
{chr(10).join([f"- {m['name']} ({m['role']}): {m['tasks_total']} tasks ({m['tasks_completed']} done, {m['tasks_in_progress']} in progress, {m['tasks_overdue']} overdue)" for m in team_data])}
"""

        # Call GPT-4
        try:
            response = openai.ChatCompletion.create(
                model="gpt-4",
                messages=[
                    {
                        "role": "system",
                        "content": """You are an expert project manager specializing in team optimization. Analyze this team and provide:

1. WORKLOAD BALANCE ASSESSMENT
2. BOTTLENECKS (who's overloaded, who's underutilized)
3. COLLABORATION RECOMMENDATIONS
4. TASK REDISTRIBUTION SUGGESTIONS

Format as JSON:
{
  "balance_score": 0-100,
  "issues": ["...", "..."],
  "overloaded_members": ["name: reason"],
  "underutilized_members": ["name: reason"],
  "recommendations": ["...", "..."],
  "suggested_reassignments": [
    {"from": "Person A", "to": "Person B", "task_type": "...", "reason": "..."}
  ]
}

Be specific and actionable."""
                    },
                    {
                        "role": "user",
                        "content": context
                    }
                ],
                max_tokens=600,
                temperature=0.7
            )

            import json
            optimization = json.loads(response.choices[0].message.content.strip())

            return {
                "project_id": project_id,
                "team_size": len(team_data),
                "optimization": optimization,
                "team_metrics": team_data,
                "generated_at": datetime.utcnow().isoformat()
            }

        except Exception as e:
            print(f"Team Optimization Error: {e}")
            return {"error": str(e)}

    # =========================================================================
    # INTELLIGENT TASK ASSIGNMENT
    # =========================================================================

    def suggest_task_assignment(self, task_id: int) -> Dict:
        """
        AI suggests best team member for a specific task
        Based on: skills, workload, past performance, availability
        """
        task = self.db.query(Task).filter(Task.id == task_id).first()

        if not task:
            return {"error": "Task not found"}

        # Get project team members
        from app.models.project import ProjectMember
        members = self.db.query(ProjectMember).filter(
            ProjectMember.project_id == task.project_id
        ).all()

        candidates = []
        for member in members:
            user = self.db.query(User).filter(User.id == member.user_id).first()
            if not user:
                continue

            # Current workload
            active_tasks = self.db.query(Task).filter(
                Task.owner_id == user.id,
                Task.status.in_(["TODO", "IN_PROGRESS"])
            ).count()

            candidates.append({
                "user_id": user.id,
                "name": f"{user.first_name} {user.last_name}",
                "role": member.role,
                "skills": user.skills or [],
                "current_workload": active_tasks
            })

        # Prepare context
        context = f"""
Task to Assign:
- Title: {task.title}
- Description: {task.description}
- Priority: {task.priority}
- Estimated Hours: {task.estimated_hours or 'Not specified'}

Available Team Members:
{chr(10).join([f"- {c['name']} ({c['role']}): {c['current_workload']} active tasks, Skills: {', '.join(c['skills'])}" for c in candidates])}
"""

        try:
            response = openai.ChatCompletion.create(
                model="gpt-4",
                messages=[
                    {
                        "role": "system",
                        "content": """You are an expert at task assignment optimization. Recommend the best person for this task.

Format as JSON:
{
  "recommended_assignee": "Name",
  "confidence": 0-100,
  "reasoning": "...",
  "alternative_assignees": [
    {"name": "...", "reason": "..."}
  ]
}"""
                    },
                    {
                        "role": "user",
                        "content": context
                    }
                ],
                max_tokens=300,
                temperature=0.6
            )

            import json
            suggestion = json.loads(response.choices[0].message.content.strip())

            return {
                "task_id": task_id,
                "suggestion": suggestion,
                "candidates": candidates,
                "generated_at": datetime.utcnow().isoformat()
            }

        except Exception as e:
            print(f"Task Assignment Error: {e}")
            return {"error": str(e)}


def get_ai_service(db: Session) -> AIInsightsService:
    """Factory function"""
    return AIInsightsService(db)
