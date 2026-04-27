"""
Remote AI Chat using FREE Hugging Face Inference API
Works on deployed servers, no local setup needed
"""

import requests
from typing import Dict, Optional
from datetime import datetime


class RemoteAIChatService:
    """
    Uses Hugging Face's FREE Inference API
    No API key needed for public models
    Works remotely on any server
    """

    def __init__(self):
        self.conversation_history = {}
        # FREE models from Hugging Face
        self.general_model = "microsoft/DialoGPT-large"
        self.app_model = "facebook/blenderbot-400M-distill"
        self.api_url = "https://api-inference.huggingface.co/models"

    def chat_general(self, user_id: int, message: str, session_id: Optional[str] = None) -> Dict:
        """
        General AI chat using FREE Hugging Face models
        No API key required!
        """
        session_key = f"{user_id}_{session_id or 'default'}"

        if session_key not in self.conversation_history:
            self.conversation_history[session_key] = []

        # Prepare conversation context
        past_user_inputs = [msg["content"] for msg in self.conversation_history[session_key] if msg["role"] == "user"]
        generated_responses = [msg["content"] for msg in self.conversation_history[session_key] if msg["role"] == "assistant"]

        try:
            # Call Hugging Face API
            response = requests.post(
                f"{self.api_url}/{self.general_model}",
                headers={"Content-Type": "application/json"},
                json={
                    "inputs": {
                        "past_user_inputs": past_user_inputs[-5:],  # Last 5 messages
                        "generated_responses": generated_responses[-5:],
                        "text": message
                    },
                    "parameters": {
                        "max_length": 500,
                        "temperature": 0.8
                    }
                },
                timeout=30
            )

            if response.status_code == 200:
                result = response.json()

                # Extract response
                if isinstance(result, dict):
                    ai_response = result.get("generated_text", "I couldn't process that.")
                elif isinstance(result, list) and len(result) > 0:
                    ai_response = result[0].get("generated_text", "I couldn't process that.")
                else:
                    ai_response = str(result)

                # Clean up response
                ai_response = ai_response.strip()

            else:
                # Fallback to simple rule-based
                ai_response = self._fallback_general_response(message)

        except Exception as e:
            print(f"Hugging Face API error: {e}")
            ai_response = self._fallback_general_response(message)

        # Update history
        self.conversation_history[session_key].append({"role": "user", "content": message})
        self.conversation_history[session_key].append({"role": "assistant", "content": ai_response})

        # Keep only last 20 messages
        if len(self.conversation_history[session_key]) > 20:
            self.conversation_history[session_key] = self.conversation_history[session_key][-20:]

        return {
            "response": ai_response,
            "session_id": session_id or "default",
            "provider": "huggingface_free",
            "timestamp": datetime.utcnow().isoformat()
        }

    def _fallback_general_response(self, message: str) -> str:
        """Simple rule-based fallback"""
        message_lower = message.lower()

        # Programming help
        if any(word in message_lower for word in ["code", "programming", "debug", "error", "function"]):
            return """I can help with programming questions! For specific code issues, try:

1. Check your syntax and indentation
2. Review error messages carefully
3. Use print statements to debug
4. Search Stack Overflow for similar issues
5. Break down complex problems into smaller parts

What specific issue are you facing?"""

        # Career advice
        elif any(word in message_lower for word in ["career", "job", "interview", "resume"]):
            return """For career development:

1. **Skills**: Focus on in-demand technologies (Python, React, Cloud)
2. **Projects**: Build a strong portfolio with real-world projects
3. **Networking**: Engage on LinkedIn, GitHub, and developer communities
4. **Learning**: Stay updated with latest tech trends

What aspect of your career would you like to discuss?"""

        # Best practices
        elif any(word in message_lower for word in ["best practice", "how to", "should i"]):
            return """Here are some general best practices:

1. Write clean, readable code
2. Use version control (Git)
3. Write tests for your code
4. Document your work
5. Follow coding standards
6. Review others' code

What specific practice are you curious about?"""

        # Default
        else:
            return """I'm here to help! I can assist with:

🔧 Programming and technical questions
💼 Career advice for developers
📚 Best practices and design patterns
🐛 Debugging and troubleshooting
🎯 Project planning and architecture

What would you like to know about?"""


class RemoteAppChatService:
    """
    App-specific AI using FREE Hugging Face + Database context
    """

    def __init__(self, db):
        self.db = db
        self.conversation_history = {}

    def chat_app(self, user_id: int, message: str, session_id: Optional[str] = None) -> Dict:
        """
        App-specific chat with database context
        100% rule-based (no external API needed for app queries)
        """
        from app.models.user import User
        from app.models.task import Task
        from app.models.project import Project, ProjectMember
        from app.models.dashboard import UserDashboard
        from datetime import datetime, timedelta

        session_key = f"{user_id}_{session_id or 'default'}"

        if session_key not in self.conversation_history:
            self.conversation_history[session_key] = []

        message_lower = message.lower()

        # Get user
        user = self.db.query(User).filter(User.id == user_id).first()
        user_name = user.first_name if user else "there"

        # === TASK QUERIES ===
        if any(word in message_lower for word in ["task", "todo", "assignment"]):
            tasks = self.db.query(Task).filter(Task.owner_id == user_id).all()

            if "how many" in message_lower or "count" in message_lower:
                in_progress = sum(1 for t in tasks if t.status.value == "IN_PROGRESS")
                completed = sum(1 for t in tasks if t.status.value == "DONE")

                response = f"""Hi {user_name}! 📊 Here's your task summary:

**Total Tasks**: {len(tasks)}
**✅ Completed**: {completed}
**🔄 In Progress**: {in_progress}
**📝 To Do**: {len(tasks) - completed - in_progress}

View all tasks in your Dashboard → Tasks section."""

            elif "overdue" in message_lower:
                overdue_tasks = [
                    t for t in tasks
                    if t.due_date and t.due_date < datetime.utcnow() and t.status.value != "DONE"
                ]

                if overdue_tasks:
                    task_list = "\n".join([
                        f"• **{t.title}** (Due: {t.due_date.strftime('%b %d')})"
                        for t in overdue_tasks[:5]
                    ])
                    response = f"""⚠️ You have {len(overdue_tasks)} overdue tasks:

{task_list}

💡 **Tip**: Prioritize these tasks to improve your productivity score!"""
                else:
                    response = "🎉 Great news! You have no overdue tasks. Keep up the good work!"

            elif "today" in message_lower or "this week" in message_lower:
                week_end = datetime.utcnow() + timedelta(days=7)
                upcoming = [
                    t for t in tasks
                    if t.due_date and t.due_date <= week_end and t.status.value != "DONE"
                ]

                if upcoming:
                    task_list = "\n".join([
                        f"• **{t.title}** ({t.priority}) - Due: {t.due_date.strftime('%b %d')}"
                        for t in upcoming[:5]
                    ])
                    response = f"""📅 Tasks due this week:

{task_list}

Navigate to: Dashboard → Tasks → Filter by "Due This Week" """
                else:
                    response = "You're all caught up! No urgent tasks due this week. 🎯"

            else:
                response = """I can help you with tasks! Try asking:

• "How many tasks do I have?"
• "Show me overdue tasks"
• "What's due this week?"
• "What tasks am I working on?"

Or visit: Dashboard → Tasks"""

        # === PROJECT QUERIES ===
        elif "project" in message_lower:
            memberships = self.db.query(ProjectMember).filter(
                ProjectMember.user_id == user_id
            ).all()

            projects = []
            for m in memberships:
                project = self.db.query(Project).filter(Project.id == m.project_id).first()
                if project:
                    projects.append({"name": project.name, "role": m.role, "id": project.id})

            if projects:
                project_list = "\n".join([
                    f"• **{p['name']}** (Role: {p['role']})"
                    for p in projects
                ])

                response = f"""📁 You're working on {len(projects)} project(s):

{project_list}

View details: Dashboard → Projects → Click project name"""
            else:
                response = """You're not assigned to any projects yet.

Contact your manager or organization admin to be added to a project."""

        # === TEAM QUERIES ===
        elif "team" in message_lower or "member" in message_lower or "colleague" in message_lower:
            memberships = self.db.query(ProjectMember).filter(
                ProjectMember.user_id == user_id
            ).all()

            team_members = set()
            for m in memberships:
                project_members = self.db.query(ProjectMember).filter(
                    ProjectMember.project_id == m.project_id,
                    ProjectMember.user_id != user_id
                ).all()

                for pm in project_members:
                    member = self.db.query(User).filter(User.id == pm.user_id).first()
                    if member:
                        team_members.add(f"{member.first_name} {member.last_name} ({pm.role})")

            if team_members:
                team_list = "\n".join([f"• {member}" for member in list(team_members)[:10]])
                response = f"""👥 Your team members:

{team_list}

View full team: Dashboard → Team"""
            else:
                response = "You don't have any team members yet in your projects."

        # === DASHBOARD/METRICS QUERIES ===
        elif any(word in message_lower for word in ["score", "performance", "metrics", "dashboard"]):
            dashboard = self.db.query(UserDashboard).filter(
                UserDashboard.user_id == user_id
            ).first()

            if dashboard:
                response = f"""📊 Your Performance Metrics:

**Productivity Score**: {dashboard.productivity_score:.1f}/100
**Tasks Completed**: {dashboard.tasks_completed}
**Current Workload**: {dashboard.tasks_in_progress} tasks in progress
**Code Contributions**: {dashboard.commits_count} commits

🎯 **AI Insight**: {'Great work! Keep it up!' if dashboard.productivity_score >= 70 else 'Focus on completing tasks on time to improve your score.'}

View detailed analytics: Dashboard → Performance"""
            else:
                response = "Your dashboard is still loading. Check back in a few minutes!"

        # === NAVIGATION HELP ===
        elif any(word in message_lower for word in ["how do i", "where", "find", "navigate", "access"]):
            response = """🧭 **Navigation Guide**:

**📊 Dashboard**: Home → View metrics, tasks, and AI insights
**📁 Projects**: Sidebar → Projects → See all your projects
**✅ Tasks**: Sidebar → Tasks → Manage assignments
**👥 Team**: Sidebar → Team → View team members
**⚙️ Settings**: Top right → Profile icon → Settings

**Quick Actions**:
• Create task: Dashboard → "New Task" button
• View project: Projects → Click project name
• Update profile: Settings → Edit Profile

What specifically are you looking for?"""

        # === HELP/TROUBLESHOOTING ===
        elif any(word in message_lower for word in ["help", "error", "problem", "not working", "issue"]):
            response = """🔧 **Troubleshooting Help**:

**Common Issues**:
1. **Can't see tasks**: Check if you're assigned to a project
2. **Dashboard empty**: Refresh the page or wait for data sync
3. **Webhook not working**: Verify webhook URL in external tool
4. **Performance score 0**: Complete some tasks to generate metrics

**Need more help?**
📧 Contact: support@teamiq.com
📚 Documentation: /docs

What specific issue are you experiencing?"""

        # === DEFAULT ===
        else:
            response = f"""Hi {user_name}! 👋 I'm your TeamIQ Assistant. I can help with:

✅ **Tasks**: "Show me overdue tasks"
📁 **Projects**: "What projects am I on?"
👥 **Team**: "Who are my team members?"
📊 **Metrics**: "What's my productivity score?"
🧭 **Navigation**: "How do I create a task?"

What would you like to know?"""

        # Update history
        self.conversation_history[session_key].append({"role": "user", "content": message})
        self.conversation_history[session_key].append({"role": "assistant", "content": response})

        return {
            "response": response,
            "session_id": session_id or "default",
            "provider": "rule_based_app",
            "timestamp": datetime.utcnow().isoformat()
        }


# Singleton instances
_remote_general_chat = None

def get_remote_general_chat() -> RemoteAIChatService:
    """Get remote general AI chat"""
    global _remote_general_chat
    if _remote_general_chat is None:
        _remote_general_chat = RemoteAIChatService()
    return _remote_general_chat


def get_remote_app_chat(db) -> RemoteAppChatService:
    """Get remote app chat"""
    return RemoteAppChatService(db)
