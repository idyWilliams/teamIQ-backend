"""
Dual AI Chat Service
1. General Assistant - Answers any questions (tech, solutions, etc.)
2. App Assistant - Answers questions about the app using database context
"""

from typing import Dict, List, Optional
from sqlalchemy.orm import Session
from datetime import datetime
import json
import requests


class GeneralAIChatService:
    """
    General purpose AI assistant
    Can discuss anything: tech problems, solutions, general questions
    Uses Ollama (FREE) or OpenAI
    """

    def __init__(self):
        self.conversation_history = {}
        self.ollama_url = "http://localhost:11434/api/generate"
        self.use_ollama = True  # Set to False to use OpenAI instead

    def chat(self, user_id: int, message: str, session_id: Optional[str] = None) -> Dict:
        """
        General chat - answers any question
        NOT limited to app functionality
        """
        # Get or create conversation history
        session_key = f"{user_id}_{session_id or 'default'}"

        if session_key not in self.conversation_history:
            self.conversation_history[session_key] = []

        # Add user message to history
        self.conversation_history[session_key].append({
            "role": "user",
            "content": message
        })

        # Prepare context
        system_prompt = """You are a helpful AI assistant. You can answer questions about:
- Programming and software development
- Technical problems and debugging
- Best practices and design patterns
- General knowledge
- Career advice for developers
- Technology recommendations

Be concise, accurate, and helpful. Provide code examples when relevant."""

        if self.use_ollama:
            response = self._chat_with_ollama(system_prompt, message)
        else:
            response = self._chat_with_openai(system_prompt, message, session_key)

        # Add assistant response to history
        self.conversation_history[session_key].append({
            "role": "assistant",
            "content": response
        })

        # Keep only last 10 messages to save memory
        if len(self.conversation_history[session_key]) > 20:
            self.conversation_history[session_key] = self.conversation_history[session_key][-20:]

        return {
            "response": response,
            "session_id": session_id or "default",
            "message_count": len(self.conversation_history[session_key]),
            "timestamp": datetime.utcnow().isoformat()
        }

    def _chat_with_ollama(self, system_prompt: str, message: str) -> str:
        """
        Chat using Ollama (FREE, runs locally)
        Requires: ollama installed and running
        """
        try:
            payload = {
                "model": "llama2",  # or "mistral", "codellama"
                "prompt": f"{system_prompt}\n\nUser: {message}\n\nAssistant:",
                "stream": False
            }

            response = requests.post(
                self.ollama_url,
                json=payload,
                timeout=30
            )

            if response.status_code == 200:
                return response.json().get("response", "I couldn't generate a response.")
            else:
                return "⚠️ Ollama service unavailable. Please ensure Ollama is running."

        except requests.exceptions.ConnectionError:
            return """⚠️ Ollama is not running.

To use FREE AI chat:
1. Install Ollama: https://ollama.ai/download
2. Run: ollama pull llama2
3. Start Ollama service
4. Try again!

Alternatively, configure OpenAI API key for cloud AI."""

        except Exception as e:
            return f"Error: {str(e)}"

    def _chat_with_openai(self, system_prompt: str, message: str, session_key: str) -> str:
        """
        Chat using OpenAI (requires API key)
        Fallback option if Ollama not available
        """
        try:
            import openai
            from app.core.config import settings

            openai.api_key = settings.OPENAI_API_KEY

            messages = [{"role": "system", "content": system_prompt}]
            messages.extend(self.conversation_history[session_key])

            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=messages,
                max_tokens=500,
                temperature=0.7
            )

            return response.choices[0].message.content

        except Exception as e:
            return f"OpenAI error: {str(e)}"

    def clear_history(self, user_id: int, session_id: Optional[str] = None):
        """Clear conversation history"""
        session_key = f"{user_id}_{session_id or 'default'}"
        if session_key in self.conversation_history:
            del self.conversation_history[session_key]


class AppAIChatService:
    """
    App-specific AI assistant
    Answers questions about YOUR app using database context
    Can query data and provide specific answers
    """

    def __init__(self, db: Session):
        self.db = db
        self.conversation_history = {}
        self.use_ollama = True

    def chat(self, user_id: int, message: str, session_id: Optional[str] = None) -> Dict:
        """
        App-specific chat - answers questions about the app
        Uses database context for accurate answers
        """
        session_key = f"{user_id}_{session_id or 'default'}"

        if session_key not in self.conversation_history:
            self.conversation_history[session_key] = []

        # Add user message
        self.conversation_history[session_key].append({
            "role": "user",
            "content": message
        })

        # 1. Determine intent and gather context
        intent = self._classify_intent(message)
        context = self._gather_context(user_id, intent, message)

        # 2. Generate response with context
        system_prompt = self._build_app_system_prompt(user_id, context)

        response = self._generate_response(system_prompt, message, context)

        # Add assistant response
        self.conversation_history[session_key].append({
            "role": "assistant",
            "content": response
        })

        return {
            "response": response,
            "intent": intent,
            "context_used": context.get("summary", ""),
            "session_id": session_id or "default",
            "timestamp": datetime.utcnow().isoformat()
        }

    def _classify_intent(self, message: str) -> str:
        """Classify what user is asking about"""
        message_lower = message.lower()

        intents = {
            "tasks": ["task", "issue", "ticket", "assignment", "todo"],
            "projects": ["project", "workspace", "repository"],
            "team": ["team", "member", "colleague", "user", "developer"],
            "dashboard": ["dashboard", "metrics", "stats", "performance", "score"],
            "navigation": ["how to", "where", "find", "navigate", "access"],
            "integration": ["webhook", "integration", "sync", "connect"],
            "troubleshooting": ["error", "problem", "issue", "not working", "fix", "bug"]
        }

        for intent, keywords in intents.items():
            if any(keyword in message_lower for keyword in keywords):
                return intent

        return "general"

    def _gather_context(self, user_id: int, intent: str, message: str) -> Dict:
        """Gather relevant database context based on intent"""
        from app.models.user import User
        from app.models.task import Task
        from app.models.project import Project, ProjectMember
        from app.models.dashboard import UserDashboard

        context = {"summary": "", "data": {}}

        user = self.db.query(User).filter(User.id == user_id).first()

        if intent == "tasks":
            # Get user's tasks
            tasks = self.db.query(Task).filter(Task.owner_id == user_id).limit(10).all()

            context["summary"] = f"User has {len(tasks)} tasks"
            context["data"] = {
                "tasks": [
                    {
                        "id": t.id,
                        "title": t.title,
                        "status": t.status.value,
                        "priority": t.priority,
                        "due_date": t.due_date.isoformat() if t.due_date else None
                    }
                    for t in tasks[:5]
                ]
            }

        elif intent == "projects":
            # Get user's projects
            memberships = self.db.query(ProjectMember).filter(
                ProjectMember.user_id == user_id
            ).all()

            projects = []
            for membership in memberships:
                project = self.db.query(Project).filter(Project.id == membership.project_id).first()
                if project:
                    projects.append({
                        "id": project.id,
                        "name": project.name,
                        "role": membership.role,
                        "status": project.status
                    })

            context["summary"] = f"User is in {len(projects)} projects"
            context["data"] = {"projects": projects}

        elif intent == "team":
            # Get team members from user's projects
            memberships = self.db.query(ProjectMember).filter(
                ProjectMember.user_id == user_id
            ).all()

            team_members = set()
            for membership in memberships:
                project_members = self.db.query(ProjectMember).filter(
                    ProjectMember.project_id == membership.project_id
                ).all()

                for pm in project_members:
                    if pm.user_id != user_id:
                        member = self.db.query(User).filter(User.id == pm.user_id).first()
                        if member:
                            team_members.add(f"{member.first_name} {member.last_name} ({pm.role})")

            context["summary"] = f"User works with {len(team_members)} team members"
            context["data"] = {"team_members": list(team_members)[:10]}

        elif intent == "dashboard":
            # Get dashboard metrics
            dashboard = self.db.query(UserDashboard).filter(
                UserDashboard.user_id == user_id
            ).first()

            if dashboard:
                context["summary"] = f"User productivity score: {dashboard.productivity_score:.1f}"
                context["data"] = {
                    "productivity_score": round(dashboard.productivity_score, 1),
                    "tasks_completed": dashboard.tasks_completed,
                    "tasks_in_progress": dashboard.tasks_in_progress,
                    "commits_count": dashboard.commits_count
                }

        elif intent == "navigation":
            # Provide navigation help
            context["summary"] = "Navigation help requested"
            context["data"] = {
                "common_pages": [
                    {"page": "Dashboard", "path": "/dashboard"},
                    {"page": "Projects", "path": "/projects"},
                    {"page": "Tasks", "path": "/tasks"},
                    {"page": "Team", "path": "/team"},
                    {"page": "Settings", "path": "/settings"}
                ]
            }

        return context

    def _build_app_system_prompt(self, user_id: int, context: Dict) -> str:
        """Build system prompt with app context"""
        from app.models.user import User

        user = self.db.query(User).filter(User.id == user_id).first()
        user_name = f"{user.first_name} {user.last_name}" if user else "User"

        return f"""You are TeamIQ Assistant, an AI helper for the TeamIQ intern management platform.

Current User: {user_name} (ID: {user_id})

Context: {context.get('summary', 'No specific context')}

Available Data:
{json.dumps(context.get('data', {}), indent=2)}

Your capabilities:
1. Answer questions about the user's tasks, projects, and team
2. Help navigate the app
3. Provide metrics and insights from their dashboard
4. Troubleshoot common issues
5. Explain how features work

Be conversational, helpful, and specific. Reference actual data when answering.
If you don't have enough data, suggest where the user can find it in the app."""

    def _generate_response(self, system_prompt: str, message: str, context: Dict) -> str:
        """Generate response using Ollama or OpenAI"""
        full_prompt = f"{system_prompt}\n\nUser Question: {message}\n\nAssistant:"

        try:
            if self.use_ollama:
                payload = {
                    "model": "llama2",
                    "prompt": full_prompt,
                    "stream": False
                }

                response = requests.post(
                    "http://localhost:11434/api/generate",
                    json=payload,
                    timeout=30
                )

                if response.status_code == 200:
                    return response.json().get("response", "I couldn't generate a response.")
                else:
                    return self._fallback_response(message, context)
            else:
                return self._fallback_response(message, context)

        except Exception as e:
            return self._fallback_response(message, context)

    def _fallback_response(self, message: str, context: Dict) -> str:
        """Rule-based fallback when AI unavailable"""
        message_lower = message.lower()
        data = context.get('data', {})

        # Tasks questions
        if 'task' in message_lower:
            if 'how many' in message_lower:
                tasks = data.get('tasks', [])
                return f"You currently have {len(tasks)} tasks. {len([t for t in tasks if t['status'] == 'IN_PROGRESS'])} are in progress."
            elif 'overdue' in message_lower:
                return "You can find overdue tasks in your Dashboard under 'Tasks' section, filtered by 'Overdue'."

        # Projects questions
        elif 'project' in message_lower:
            projects = data.get('projects', [])
            if projects:
                project_list = ", ".join([p['name'] for p in projects[:3]])
                return f"You're working on {len(projects)} projects: {project_list}. View all in the Projects page."
            else:
                return "You're not assigned to any projects yet. Contact your manager to get added."

        # Dashboard questions
        elif 'score' in message_lower or 'performance' in message_lower:
            score = data.get('productivity_score')
            if score:
                return f"Your productivity score is {score}/100. Check your Dashboard for detailed metrics and AI insights."
            else:
                return "Visit your Dashboard to see your productivity score and performance metrics."

        # Navigation questions
        elif 'how to' in message_lower or 'where' in message_lower:
            return """Here's how to navigate TeamIQ:

📊 **Dashboard**: View your metrics, tasks, and AI insights
📁 **Projects**: See all your projects and project details
✅ **Tasks**: Manage your tasks and assignments
👥 **Team**: View team members and their activity
⚙️ **Settings**: Update your profile and preferences

What specifically are you looking for?"""

        # Default
        return f"I'm here to help! You can ask me about:\n- Your tasks and assignments\n- Project information\n- Team members\n- How to navigate the app\n- Your performance metrics\n\nWhat would you like to know?"


# Singleton instances
_general_chat = None
_app_chat_sessions = {}


def get_general_chat() -> GeneralAIChatService:
    """Get general AI chat service"""
    global _general_chat
    if _general_chat is None:
        _general_chat = GeneralAIChatService()
    return _general_chat


def get_app_chat(db: Session) -> AppAIChatService:
    """Get app-specific chat service"""
    return AppAIChatService(db)
