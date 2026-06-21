import os, json, time
from extensions.base import BaseExtension

TASKS_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "tasks.json")

class TasksExtension(BaseExtension):
    name = "tasks"
    display_name = "Task Manager"
    description = "Track tasks, deadlines, and to-do lists"
    version = "1.0.0"
    author = "GALACTOS"

    def get_config_schema(self):
        return {
            "notify_before_deadline": {"type": "number", "default": 60, "title": "Minutes before deadline to notify"},
            "auto_archive_done": {"type": "boolean", "default": False, "title": "Auto-archive completed tasks"}
        }

    def _load_tasks(self):
        if os.path.exists(TASKS_FILE):
            with open(TASKS_FILE, 'r') as f:
                return json.load(f)
        return []

    def _save_tasks(self, tasks):
        with open(TASKS_FILE, 'w') as f:
            json.dump(tasks, f, indent=2)

    def get_chat_tools(self):
        return [
            {
                "name": "task_add",
                "description": "Add a new task with optional deadline and priority",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "title": {"type": "string", "description": "Task title"},
                        "deadline": {"type": "string", "description": "Deadline (e.g. 2025-01-15 or tomorrow)"},
                        "priority": {"type": "string", "enum": ["low", "medium", "high"], "description": "Priority level"}
                    },
                    "required": ["title"]
                }
            },
            {
                "name": "task_list",
                "description": "List all tasks or filter by status",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "status": {"type": "string", "enum": ["pending", "done", "all"], "description": "Filter by status"}
                    }
                }
            },
            {
                "name": "task_complete",
                "description": "Mark a task as completed",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "task_id": {"type": "integer", "description": "Task ID to complete"}
                    },
                    "required": ["task_id"]
                }
            },
            {
                "name": "task_delete",
                "description": "Delete a task",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "task_id": {"type": "integer", "description": "Task ID to delete"}
                    },
                    "required": ["task_id"]
                }
            }
        ]

    def execute_tool(self, tool_name, params, user=None):
        tasks = self._load_tasks()
        if tool_name == "task_add":
            task = {
                "id": max([t.get("id", 0) for t in tasks], default=0) + 1,
                "title": params.get("title", ""),
                "deadline": params.get("deadline", ""),
                "priority": params.get("priority", "medium"),
                "status": "pending",
                "created": time.strftime("%Y-%m-%d %H:%M"),
                "user": user
            }
            tasks.append(task)
            self._save_tasks(tasks)
            return {"success": True, "message": f"Task #{task['id']} created: {task['title']}"}
        elif tool_name == "task_list":
            status = params.get("status", "all")
            user_tasks = [t for t in tasks if status == "all" or t.get("status") == status]
            if user:
                user_tasks = [t for t in user_tasks if t.get("user") == user]
            return {"tasks": user_tasks, "count": len(user_tasks)}
        elif tool_name == "task_complete":
            tid = params.get("task_id")
            for t in tasks:
                if t.get("id") == tid:
                    t["status"] = "done"
                    t["completed"] = time.strftime("%Y-%m-%d %H:%M")
                    self._save_tasks(tasks)
                    return {"success": True, "message": f"Task #{tid} completed"}
            return {"error": f"Task #{tid} not found"}
        elif tool_name == "task_delete":
            tid = params.get("task_id")
            tasks = [t for t in tasks if t.get("id") != tid]
            self._save_tasks(tasks)
            return {"success": True, "message": f"Task #{tid} deleted"}
        return {"error": "Unknown tool"}
