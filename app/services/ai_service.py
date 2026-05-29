"""
AI Service for Generating Insights and Predictions
Uses OpenAI GPT-4 for analysis
"""

from typing import Dict, Optional, List
from openai import OpenAI
import json
from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session
from app.core.config import settings
from app.models.user import User
from app.models.project import Project, ProjectMember
from app.models.task import Task
from app.models.activity import Activity, CommitActivity


class AIInsightsService:
    """
    Generates AI-powered insights using the latest OpenAI API.
    Analyzes project telemetry, team behavior, and uploaded documents.
    """

    def __init__(self, db: Session):
        self.db = db
        self.client = OpenAI(api_key=settings.OPENAI_API_KEY)

    # =========================================================================
    # PROJECT AI SUMMARY
    # =========================================================================

    def generate_project_summary(self, project_id: int) -> Dict:
        """
        Generate AI summary for project overview page
        """
        project = self.db.query(Project).filter(Project.id == project_id).first()

        if not project:
            return {"error": "Project not found"}

        # Gather project data
        tasks = self.db.query(Task).filter(Task.project_id == project_id).all()
        activities = self.db.query(Activity).filter(
            Activity.project_id == project_id,
            Activity.timestamp >= datetime.now(timezone.utc) - timedelta(days=30)
        ).all()

        commits = self.db.query(CommitActivity).filter(
            CommitActivity.project_id == project_id,
            CommitActivity.timestamp >= datetime.now(timezone.utc) - timedelta(days=30)
        ).all()

        # Calculate metrics
        total_tasks = len(tasks)
        completed_tasks = sum(1 for t in tasks if t.status == "DONE")
        in_progress_tasks = sum(1 for t in tasks if t.status == "IN_PROGRESS")
        
        # Velocity calculation
        start_date = project.start_date.replace(tzinfo=timezone.utc) if project.start_date else datetime.now(timezone.utc) - timedelta(days=30)
        weeks_elapsed = (datetime.now(timezone.utc) - start_date).days / 7
        velocity = completed_tasks / weeks_elapsed if weeks_elapsed > 0 else 0

        # Incorporate Document Knowledge
        document_context = ""
        if project.linked_documents:
            document_context = "\n### Project Documents Context:\n"
            for doc in project.linked_documents:
                if isinstance(doc, dict) and "extracted_text" in doc:
                    # Only take a snippet of each doc to avoid token limits
                    text_snippet = doc["extracted_text"][:2000]
                    document_context += f"- Document '{doc.get('name')}': {text_snippet}...\n"

        context = f"""
Project: {project.name}
Type: {project.project_type}
Industry: {project.industry}
Methodology: {project.methodology}
Description: {project.description}

Current Status:
- Total Tasks: {total_tasks}
- Completed: {completed_tasks}
- In Progress: {in_progress_tasks}
- Velocity: {velocity:.1f} tasks/week

Activity (Last 30 days):
- Commits: {len(commits)}
- Team Activities: {len(activities)}
{document_context}
"""

        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert project manager. Analyze the provided project data and documents to give a high-level summary."
                    },
                    {"role": "user", "content": context}
                ]
            )

            ai_summary = response.choices[0].message.content.strip()

            return {
                "summary": ai_summary,
                "metrics": {
                    "total_tasks": total_tasks,
                    "completed_tasks": completed_tasks,
                    "velocity": round(velocity, 2)
                },
                "generated_at": datetime.now(timezone.utc).isoformat()
            }

        except Exception as e:
            print(f"AI Summary Error: {e}")
            return {"error": str(e)}

    # =========================================================================
    # USER PERFORMANCE ANALYSIS
    # =========================================================================

    def analyze_user_performance(self, user_id: int, project_id: Optional[int] = None) -> Dict:
        """
        Deep AI analysis of individual user performance
        """
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            return {"error": "User not found"}

        start_date = datetime.now(timezone.utc) - timedelta(days=90)
        
        query_tasks = self.db.query(Task).filter(Task.owner_id == user_id)
        if project_id:
            query_tasks = query_tasks.filter(Task.project_id == project_id)
        tasks = query_tasks.filter(Task.created_at >= start_date).all()

        query_commits = self.db.query(CommitActivity).filter(CommitActivity.user_id == user_id)
        if project_id:
            query_commits = query_commits.filter(CommitActivity.project_id == project_id)
        commits = query_commits.filter(CommitActivity.timestamp >= start_date).all()

        context = f"""
User: {user.first_name} {user.last_name}
Role: {user.role}
Tasks: {len(tasks)} (Completed: {sum(1 for t in tasks if t.status == 'DONE')})
Commits: {len(commits)}
Skills: {', '.join(user.skills) if user.skills else 'N/A'}
"""

        try:
            response = self.client.chat.completions.create(
                model="gpt-4o",
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": "You are an expert HR analyst. Analyze the performance data and return a JSON report with strengths, improvements, working_style, and recommendations."},
                    {"role": "user", "content": context}
                ]
            )
            return json.loads(response.choices[0].message.content)
        except Exception as e:
            return {"error": str(e)}

    # =========================================================================
    # TEAM OPTIMIZATION
    # =========================================================================

    def generate_team_optimization_insights(self, project_id: int) -> Dict:
        """
        AI-powered team optimization recommendations
        """
        project = self.db.query(Project).filter(Project.id == project_id).first()
        if not project: return {"error": "Project not found"}

        members = self.db.query(ProjectMember).filter(ProjectMember.project_id == project_id).all()
        team_data = []
        for m in members:
            u = self.db.query(User).filter(User.id == m.user_id).first()
            if u:
                t_count = self.db.query(Task).filter(Task.owner_id == u.id, Task.project_id == project_id).count()
                team_data.append(f"{u.first_name}: {t_count} tasks")

        context = f"Project: {project.name}\nTeam workloads:\n" + "\n".join(team_data)

        try:
            response = self.client.chat.completions.create(
                model="gpt-4o",
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": "Analyze team workload balance and return JSON with balance_score, issues, and recommendations."},
                    {"role": "user", "content": context}
                ]
            )
            return json.loads(response.choices[0].message.content)
        except Exception as e:
            return {"error": str(e)}

    # =========================================================================
    # INTELLIGENT TASK ASSIGNMENT
    # =========================================================================

    def suggest_task_assignment(self, task_id: int) -> Dict:
        """
        AI suggests best team member for a specific task
        """
        task = self.db.query(Task).filter(Task.id == task_id).first()
        if not task: return {"error": "Task not found"}

        members = self.db.query(ProjectMember).filter(ProjectMember.project_id == task.project_id).all()
        candidates = []
        for m in members:
            u = self.db.query(User).filter(User.id == m.user_id).first()
            if u:
                candidates.append(f"Name: {u.first_name}, Role: {m.role}, Skills: {u.skills}")

        context = f"Task: {task.title}\nDescription: {task.description}\nCandidates:\n" + "\n".join(candidates)

        try:
            response = self.client.chat.completions.create(
                model="gpt-4o",
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": "Suggest the best candidate for the task. Return JSON with recommended_assignee and reasoning."},
                    {"role": "user", "content": context}
                ]
            )
            return json.loads(response.choices[0].message.content)
        except Exception as e:
            return {"error": str(e)}

    # =========================================================================
    # INTELLIGENCE SUMMARY (Enhanced with Documents)
    # =========================================================================

    def generate_intelligence_summary(self, project_id: int, project_data: Dict) -> Dict:
        """
        Generate a high-signal Project Intelligence Summary.
        Now enhanced with document-based deductions.
        """
        project = self.db.query(Project).filter(Project.id == project_id).first()
        
        doc_knowledge = ""
        if project and project.linked_documents:
            doc_knowledge = "\n## DOCUMENT KNOWLEDGE BASE\n"
            for doc in project.linked_documents:
                if isinstance(doc, dict) and "extracted_text" in doc:
                    doc_knowledge += f"### Insights from '{doc.get('name')}':\n{doc['extracted_text'][:3000]}\n---\n"

        prompt = f"""
# Role
You are an expert Engineering Manager / Project Director. Your goal is to transform project telemetry AND internal document knowledge into a high-signal "Project Intelligence Summary".

# Context
Telemetry Data: {project_data}
{doc_knowledge}

# Instructions
Analyze both the telemetry (velocity, PRs, tasks) AND the document content (requirements, strategy, research) to generate a report.
If the documents contain specific goals, constraints, or technical details, use them to validate if the current progress (telemetry) aligns with the original vision.

## Structure
- ## Quick Pulse: One punchy sentence on current momentum and alignment with document-stated goals.
- ## Document-Telemetry Gap: If the documents mention specific requirements that aren't reflected in the task list or activity, flag it here.
- ## Critical Path: Single most significant bottleneck.
- ## Strategic Wins: Bulleted list of impactful recent activities.
- ## Director Advice: 2-3 pieces of actionable strategic advice.

## Style
- Professional, data-driven, active voice.
- Use Markdown.
"""

        try:
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=1500,
                temperature=0.7
            )

            ai_summary = response.choices[0].message.content.strip()

            return {
                "summary": ai_summary,
                "project_id": project_id,
                "generated_at": datetime.now(timezone.utc).isoformat()
            }

        except Exception as e:
            print(f"Intelligence Summary Error: {e}")
            return {"summary": "Unable to generate summary.", "error": str(e)}


def get_ai_service(db: Session) -> AIInsightsService:
    """Factory function"""
    return AIInsightsService(db)
