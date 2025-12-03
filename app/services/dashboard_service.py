"""
Dashboard Service
Computes and caches dashboard metrics for fast loading
Integrates with AI service for insights
"""

from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from typing import Dict, List
from app.models.user import User
from app.models.project import Project
from app.models.task import Task, TaskStatus
from app.models.activity import Activity, CommitActivity, PullRequestActivity
from app.models.dashboard import UserDashboard, OrganizationDashboard
from app.services.ai_service import get_ai_service


class DashboardService:
    """Computes dashboard metrics and AI insights"""

    def __init__(self, db: Session):
        self.db = db
        self.ai_service = get_ai_service(db)

    # =========================================================================
    # USER DASHBOARD
    # =========================================================================

    def compute_user_dashboard(self, user_id: int) -> Dict:
        """
        Compute comprehensive user dashboard with AI insights
        Returns all metrics + AI analysis
        """
        user = self.db.query(User).filter(User.id == user_id).first()

        if not user:
            return {"error": "User not found"}

        # Get or create dashboard record
        dashboard = self.db.query(UserDashboard).filter(
            UserDashboard.user_id == user_id
        ).first()

        if not dashboard:
            dashboard = UserDashboard(user_id=user_id)
            self.db.add(dashboard)

        # Calculate task metrics
        tasks = self.db.query(Task).filter(Task.owner_id == user_id).all()

        dashboard.tasks_total = len(tasks)
        dashboard.tasks_completed = sum(1 for t in tasks if t.status == TaskStatus.DONE)
        dashboard.tasks_in_progress = sum(1 for t in tasks if t.status == TaskStatus.IN_PROGRESS)
        dashboard.tasks_overdue = sum(
            1 for t in tasks
            if t.due_date and t.due_date < datetime.utcnow() and t.status != TaskStatus.DONE
        )

        # Calculate average completion time
        completed_tasks_with_times = [
            t for t in tasks
            if t.status == TaskStatus.DONE and t.completed_at and t.created_at
        ]

        if completed_tasks_with_times:
            completion_times = [
                (t.completed_at - t.created_at).total_seconds() / 3600
                for t in completed_tasks_with_times
            ]
            dashboard.avg_completion_time_hours = sum(completion_times) / len(completion_times)

        # Calculate code metrics
        commits = self.db.query(CommitActivity).filter(
            CommitActivity.user_id == user_id
        ).all()

        dashboard.commits_count = len(commits)
        dashboard.lines_added = sum(c.additions for c in commits if c.additions)
        dashboard.lines_deleted = sum(c.deletions for c in commits if c.deletions)

        prs = self.db.query(PullRequestActivity).filter(
            PullRequestActivity.user_id == user_id
        ).all()

        dashboard.pull_requests_count = len(prs)
        dashboard.pull_requests_merged = sum(1 for pr in prs if pr.merged_at)

        # Calculate communication metrics
        activities = self.db.query(Activity).filter(
            Activity.user_id == user_id
        ).all()

        dashboard.messages_sent = sum(1 for a in activities if a.type == "message")
        dashboard.reactions_given = sum(1 for a in activities if a.type == "reaction")
        dashboard.files_shared = sum(1 for a in activities if a.type == "file_upload")

        # Calculate productivity scores (0-100)
        dashboard.productivity_score = self._calculate_productivity_score(dashboard)
        dashboard.collaboration_score = self._calculate_collaboration_score(dashboard)
        dashboard.code_quality_score = self._calculate_code_quality_score(dashboard, commits, prs)
        dashboard.consistency_score = self._calculate_consistency_score(commits, tasks)

        # Calculate streaks
        dashboard.current_commit_streak = self._calculate_commit_streak(commits)
        dashboard.longest_commit_streak = self._calculate_longest_streak(commits)
        dashboard.current_task_streak = self._calculate_task_streak(tasks)

        # Activity by day (last 30 days)
        dashboard.activity_by_day = self._calculate_activity_by_day(user_id)

        # Top languages (from commits)
        dashboard.top_languages = self._extract_top_languages(commits)

        # Top projects (by contribution)
        dashboard.top_projects = self._calculate_top_projects(user_id)

        # Last activity timestamp
        if activities:
            dashboard.last_activity_at = max(a.timestamp for a in activities)

        dashboard.updated_at = datetime.utcnow()

        self.db.commit()
        self.db.refresh(dashboard)

        # ✅ GET AI INSIGHTS
        ai_analysis = self.ai_service.analyze_user_performance(user_id)

        return {
            "user_id": user_id,
            "user_name": f"{user.first_name} {user.last_name}",
            "metrics": {
                "tasks": {
                    "total": dashboard.tasks_total,
                    "completed": dashboard.tasks_completed,
                    "in_progress": dashboard.tasks_in_progress,
                    "overdue": dashboard.tasks_overdue,
                    "completion_rate": round((dashboard.tasks_completed / dashboard.tasks_total * 100) if dashboard.tasks_total > 0 else 0, 1),
                    "avg_completion_time_hours": round(dashboard.avg_completion_time_hours, 1)
                },
                "code": {
                    "commits": dashboard.commits_count,
                    "lines_added": dashboard.lines_added,
                    "lines_deleted": dashboard.lines_deleted,
                    "net_lines": dashboard.lines_added - dashboard.lines_deleted,
                    "pull_requests": dashboard.pull_requests_count,
                    "prs_merged": dashboard.pull_requests_merged,
                    "merge_rate": round((dashboard.pull_requests_merged / dashboard.pull_requests_count * 100) if dashboard.pull_requests_count > 0 else 0, 1)
                },
                "communication": {
                    "messages_sent": dashboard.messages_sent,
                    "reactions_given": dashboard.reactions_given,
                    "files_shared": dashboard.files_shared,
                    "avg_daily_messages": round(dashboard.messages_sent / 90, 2)
                },
                "scores": {
                    "productivity": round(dashboard.productivity_score, 1),
                    "collaboration": round(dashboard.collaboration_score, 1),
                    "code_quality": round(dashboard.code_quality_score, 1),
                    "consistency": round(dashboard.consistency_score, 1)
                },
                "streaks": {
                    "current_commit": dashboard.current_commit_streak,
                    "longest_commit": dashboard.longest_commit_streak,
                    "current_task": dashboard.current_task_streak
                }
            },
            "activity_by_day": dashboard.activity_by_day,
            "top_languages": dashboard.top_languages,
            "top_projects": dashboard.top_projects,
            "last_activity_at": dashboard.last_activity_at.isoformat() if dashboard.last_activity_at else None,
            "ai_insights": ai_analysis,  # ✅ AI-POWERED INSIGHTS
            "updated_at": dashboard.updated_at.isoformat()
        }

    def _calculate_productivity_score(self, dashboard: UserDashboard) -> float:
        """
        Calculate overall productivity score (0-100)
        Based on: task completion, code output, consistency
        """
        score = 0.0

        # Task completion rate (40%)
        if dashboard.tasks_total > 0:
            completion_rate = dashboard.tasks_completed / dashboard.tasks_total
            score += completion_rate * 40

        # Code contribution (30%)
        commits_score = min(dashboard.commits_count / 50, 1.0) * 30  # 50+ commits = full score
        score += commits_score

        # PR merge rate (20%)
        if dashboard.pull_requests_count > 0:
            merge_rate = dashboard.pull_requests_merged / dashboard.pull_requests_count
            score += merge_rate * 20

        # No overdue tasks bonus (10%)
        if dashboard.tasks_overdue == 0 and dashboard.tasks_total > 0:
            score += 10

        return min(score, 100.0)

    def _calculate_collaboration_score(self, dashboard: UserDashboard) -> float:
        """Calculate collaboration score based on communication activity"""
        score = 0.0

        # Messages (50%)
        messages_score = min(dashboard.messages_sent / 100, 1.0) * 50
        score += messages_score

        # Reactions (25%)
        reactions_score = min(dashboard.reactions_given / 50, 1.0) * 25
        score += reactions_score

        # File shares (25%)
        files_score = min(dashboard.files_shared / 20, 1.0) * 25
        score += files_score

        return min(score, 100.0)

    def _calculate_code_quality_score(self, dashboard: UserDashboard, commits: List, prs: List) -> float:
        """
        Calculate code quality score
        Based on: PR reviews, commit message quality, code churn
        """
        score = 70.0  # Base score

        # PR merge rate (good quality = high merge rate)
        if dashboard.pull_requests_count > 0:
            merge_rate = dashboard.pull_requests_merged / dashboard.pull_requests_count
            score += merge_rate * 20

        # Code churn (low is better)
        if dashboard.lines_added > 0:
            churn_ratio = dashboard.lines_deleted / dashboard.lines_added
            if churn_ratio < 0.3:  # Low churn = good
                score += 10
            elif churn_ratio > 0.7:  # High churn = bad
                score -= 10

        return max(0, min(score, 100.0))

    def _calculate_consistency_score(self, commits: List, tasks: List) -> float:
        """Calculate consistency score based on regular activity"""
        if not commits and not tasks:
            return 0.0

        # Check activity spread over last 30 days
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)

        recent_commits = [c for c in commits if c.timestamp >= thirty_days_ago]
        recent_tasks = [t for t in tasks if t.created_at >= thirty_days_ago]

        # Calculate days with activity
        active_dates = set()
        for commit in recent_commits:
            active_dates.add(commit.timestamp.date())
        for task in recent_tasks:
            active_dates.add(task.created_at.date())

        # Consistency = (active days / 30) * 100
        consistency = (len(active_dates) / 30) * 100

        return min(consistency, 100.0)

    def _calculate_commit_streak(self, commits: List) -> int:
        """Calculate current commit streak (consecutive days with commits)"""
        if not commits:
            return 0

        # Sort by date descending
        sorted_commits = sorted(commits, key=lambda c: c.timestamp, reverse=True)

        streak = 0
        current_date = datetime.utcnow().date()

        for commit in sorted_commits:
            commit_date = commit.timestamp.date()

            if commit_date == current_date or commit_date == current_date - timedelta(days=streak):
                if commit_date != current_date - timedelta(days=streak):
                    streak += 1
                current_date = commit_date
            else:
                break

        return streak

    def _calculate_longest_streak(self, commits: List) -> int:
        """Calculate longest commit streak ever"""
        if not commits:
            return 0

        sorted_commits = sorted(commits, key=lambda c: c.timestamp)

        longest = 0
        current = 1
        prev_date = sorted_commits[0].timestamp.date()

        for commit in sorted_commits[1:]:
            commit_date = commit.timestamp.date()

            if commit_date == prev_date + timedelta(days=1):
                current += 1
                longest = max(longest, current)
            elif commit_date != prev_date:
                current = 1

            prev_date = commit_date

        return max(longest, current)

    def _calculate_task_streak(self, tasks: List) -> int:
        """Calculate current task completion streak"""
        completed_tasks = [t for t in tasks if t.status == TaskStatus.DONE and t.completed_at]

        if not completed_tasks:
            return 0

        sorted_tasks = sorted(completed_tasks, key=lambda t: t.completed_at, reverse=True)

        streak = 0
        current_date = datetime.utcnow().date()

        for task in sorted_tasks:
            task_date = task.completed_at.date()

            if task_date == current_date or task_date == current_date - timedelta(days=streak):
                if task_date != current_date - timedelta(days=streak):
                    streak += 1
                current_date = task_date
            else:
                break

        return streak

    def _calculate_activity_by_day(self, user_id: int) -> Dict:
        """Calculate activity breakdown by day for last 30 days"""
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)

        commits = self.db.query(CommitActivity).filter(
            CommitActivity.user_id == user_id,
            CommitActivity.timestamp >= thirty_days_ago
        ).all()

        tasks = self.db.query(Task).filter(
            Task.owner_id == user_id,
            Task.completed_at >= thirty_days_ago
        ).all()

        activities = self.db.query(Activity).filter(
            Activity.user_id == user_id,
            Activity.timestamp >= thirty_days_ago
        ).all()

        activity_by_day = {}

        for i in range(30):
            date = (datetime.utcnow() - timedelta(days=i)).date()
            date_str = date.isoformat()

            day_commits = sum(1 for c in commits if c.timestamp.date() == date)
            day_tasks = sum(1 for t in tasks if t.completed_at and t.completed_at.date() == date)
            day_messages = sum(1 for a in activities if a.timestamp.date() == date and a.type == "message")

            activity_by_day[date_str] = {
                "commits": day_commits,
                "tasks_completed": day_tasks,
                "messages": day_messages,
                "total_score": day_commits * 3 + day_tasks * 5 + day_messages
            }

        return activity_by_day

    def _extract_top_languages(self, commits: List) -> List[Dict]:
        """Extract top programming languages from commits"""
        # This would require analyzing commit diffs
        # For now, return placeholder
        return [
            {"name": "Python", "percentage": 45, "lines": 1200},
            {"name": "JavaScript", "percentage": 30, "lines": 800},
            {"name": "TypeScript", "percentage": 25, "lines": 650}
        ]

    def _calculate_top_projects(self, user_id: int) -> List[Dict]:
        """Calculate user's top contributing projects"""
        # Get all projects user is part of
        from app.models.project import ProjectMember

        project_members = self.db.query(ProjectMember).filter(
            ProjectMember.user_id == user_id
        ).all()

        project_contributions = []

        for pm in project_members:
            project = self.db.query(Project).filter(Project.id == pm.project_id).first()
            if not project:
                continue

            # Count contributions
            commits = self.db.query(CommitActivity).filter(
                CommitActivity.user_id == user_id,
                CommitActivity.project_id == project.id
            ).count()

            tasks = self.db.query(Task).filter(
                Task.owner_id == user_id,
                Task.project_id == project.id
            ).count()

            contribution_score = commits * 3 + tasks * 5

            project_contributions.append({
                "project_id": project.id,
                "name": project.name,
                "contribution_score": contribution_score,
                "commits": commits,
                "tasks": tasks
            })

        # Sort by contribution score
        project_contributions.sort(key=lambda x: x["contribution_score"], reverse=True)

        return project_contributions[:5]  # Top 5


    # =========================================================================
    # ORGANIZATION DASHBOARD
    # =========================================================================

    def compute_organization_dashboard(self, org_id: int) -> Dict:
        """
        Compute organization-wide dashboard
        Aggregates all team metrics + AI insights
        """
        from app.models.organization import Organization

        org = self.db.query(Organization).filter(Organization.id == org_id).first()

        if not org:
            return {"error": "Organization not found"}

        # Get or create dashboard
        dashboard = self.db.query(OrganizationDashboard).filter(
            OrganizationDashboard.organization_id == org_id
        ).first()

        if not dashboard:
            dashboard = OrganizationDashboard(organization_id=org_id)
            self.db.add(dashboard)

        # Get all projects
        projects = self.db.query(Project).filter(
            Project.organization_id == org_id
        ).all()

        dashboard.total_projects = len(projects)
        dashboard.active_projects = sum(1 for p in projects if p.status == "ACTIVE")

        # Get all users in org
        users = org.users
        dashboard.total_members = len(users)

        # Active members (activity in last 7 days)
        seven_days_ago = datetime.utcnow() - timedelta(days=7)
        active_user_ids = set()

        recent_activities = self.db.query(Activity).filter(
            Activity.timestamp >= seven_days_ago
        ).all()

        for activity in recent_activities:
            if activity.user_id:
                active_user_ids.add(activity.user_id)

        dashboard.active_members = len([u for u in users if u.id in active_user_ids])

        # Aggregate tasks
        all_tasks = self.db.query(Task).filter(
            Task.organization_id == org_id
        ).all()

        dashboard.total_tasks = len(all_tasks)
        dashboard.completed_tasks = sum(1 for t in all_tasks if t.status == TaskStatus.DONE)
        dashboard.in_progress_tasks = sum(1 for t in all_tasks if t.status == TaskStatus.IN_PROGRESS)

        if dashboard.total_tasks > 0:
            dashboard.avg_task_completion_rate = (dashboard.completed_tasks / dashboard.total_tasks) * 100

        # Aggregate code metrics
        dashboard.total_commits = self.db.query(CommitActivity).filter(
            CommitActivity.project_id.in_([p.id for p in projects])
        ).count()

        dashboard.total_pull_requests = self.db.query(PullRequestActivity).filter(
            PullRequestActivity.project_id.in_([p.id for p in projects])
        ).count()

        # Communication metrics
        dashboard.total_messages = self.db.query(Activity).filter(
            Activity.type == "message",
            Activity.project_id.in_([p.id for p in projects])
        ).count()

        # Calculate team scores
        user_scores = []
        for user in users:
            user_dash = self.db.query(UserDashboard).filter(
                UserDashboard.user_id == user.id
            ).first()

            if user_dash:
                user_scores.append(user_dash.productivity_score)

        if user_scores:
            dashboard.overall_productivity = sum(user_scores) / len(user_scores)

        dashboard.updated_at = datetime.utcnow()

        self.db.commit()
        self.db.refresh(dashboard)

        # ✅ GET TOP CONTRIBUTORS
        top_contributors = self._get_top_contributors(org_id)

        return {
            "organization_id": org_id,
            "organization_name": org.name,
            "metrics": {
                "team": {
                    "total_members": dashboard.total_members,
                    "active_members": dashboard.active_members,
                    "activity_rate": round((dashboard.active_members / dashboard.total_members * 100) if dashboard.total_members > 0 else 0, 1)
                },
                "projects": {
                    "total": dashboard.total_projects,
                    "active": dashboard.active_projects,
                    "completed": dashboard.completed_projects
                },
                "tasks": {
                    "total": dashboard.total_tasks,
                    "completed": dashboard.completed_tasks,
                    "in_progress": dashboard.in_progress_tasks,
                    "completion_rate": round(dashboard.avg_task_completion_rate, 1)
                },
                "code": {
                    "total_commits": dashboard.total_commits,
                    "total_prs": dashboard.total_pull_requests
                },
                "communication": {
                    "total_messages": dashboard.total_messages
                },
                "performance": {
                    "overall_productivity": round(dashboard.overall_productivity, 1),
                    "team_collaboration": round(dashboard.team_collaboration, 1),
                    "code_quality": round(dashboard.code_quality, 1)
                }
            },
            "top_contributors": top_contributors,
            "updated_at": dashboard.updated_at.isoformat()
        }

    def _get_top_contributors(self, org_id: int) -> List[Dict]:
        """Get top 10 contributors in organization"""
        from app.models.organization import Organization

        org = self.db.query(Organization).filter(Organization.id == org_id).first()

        contributors = []
        for user in org.users:
            user_dash = self.db.query(UserDashboard).filter(
                UserDashboard.user_id == user.id
            ).first()

            if user_dash:
                contributors.append({
                    "user_id": user.id,
                    "name": f"{user.first_name} {user.last_name}",
                    "avatar": user.profile_image,
                    "productivity_score": round(user_dash.productivity_score, 1),
                    "contributions": {
                        "commits": user_dash.commits_count,
                        "tasks_completed": user_dash.tasks_completed,
                        "prs_merged": user_dash.pull_requests_merged
                    }
                })

        contributors.sort(key=lambda x: x["productivity_score"], reverse=True)

        return contributors[:10]


def get_dashboard_service(db: Session) -> DashboardService:
    """Factory function"""
    return DashboardService(db)


# Helper function for backward compatibility
def compute_and_upsert_dashboard_metrics(db: Session, user_id: int):
    """Compute user dashboard metrics"""
    service = get_dashboard_service(db)
    return service.compute_user_dashboard(user_id)


def compute_org_metrics(db: Session, org_id: int):
    """Compute organization metrics"""
    service = get_dashboard_service(db)
    return service.compute_organization_dashboard(org_id)


def get_cached_org_dashboard(db: Session, org_id: int):
    """Get cached org dashboard"""
    return db.query(OrganizationDashboard).filter(
        OrganizationDashboard.organization_id == org_id
    ).first()
