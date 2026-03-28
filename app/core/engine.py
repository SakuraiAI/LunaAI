from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from config.settings import AppSettings
from app.core.memory_coordinator import MemoryCoordinator
from app.core.prompt_builder import PromptBuilder
from app.core.project_store import ProjectStore
from app.core.runtime_status import RuntimeStatusFormatter
from app.core.user_settings import UserSettingsStore
from app.memory.chat_memory import ChatMemory
from app.memory.long_memory import LongMemory
from app.models.local_model import LocalModel
from app.tools.desktop_actions import DesktopActionTool
from app.tools.internet import InternetTool
from app.workflow.manager import WorkflowManager
from app.xeno.coordinator import XenoCoordinator


class LunaEngine:
    def __init__(self) -> None:
        self.settings = AppSettings()
        self.settings.ensure_directories()
        self.model = LocalModel(
            model_name=self.settings.lm_studio_model,
            base_url=self.settings.lm_studio_base_url,
            provider="lm_studio",
            api_token=self.settings.lm_studio_api_token,
            timeout_seconds=self.settings.lm_studio_timeout_seconds,
        )
        self.memory = ChatMemory(Path(self.settings.memory_path))
        self.long_memory = LongMemory(Path(self.settings.long_memory_path))
        self.workflow = WorkflowManager()
        self.internet = InternetTool()
        self.desktop_actions = DesktopActionTool()
        self.xeno = XenoCoordinator()
        self.user_settings = UserSettingsStore(Path(self.settings.user_settings_path))
        self.projects = ProjectStore(Path(self.settings.projects_path))

        try:
            timezone = ZoneInfo("Europe/Prague")
            timezone_name = "Europe/Prague"
        except ZoneInfoNotFoundError:
            timezone = None
            timezone_name = "local system time"

        self.prompt_builder = PromptBuilder(
            memory=self.memory,
            long_memory=self.long_memory,
            internet=self.internet,
            timezone=timezone,
            timezone_name=timezone_name,
        )
        self.memory_coordinator = MemoryCoordinator(
            chat_memory=self.memory,
            long_memory=self.long_memory,
            review_interval=self.settings.memory_review_interval,
        )
        self.runtime_status = RuntimeStatusFormatter(
            settings=self.settings,
            internet=self.internet,
        )

    def _serialize_project(self, record: object) -> dict[str, object] | None:
        if record is None:
            return None
        return {
            "id": record.id,
            "name": record.name,
            "brief": record.brief,
            "blueprint_text": record.blueprint_text,
            "next_step": record.next_step,
            "current_phase": record.current_phase,
            "tasks": list(record.tasks),
            "memory_entries": list(record.memory_entries),
            "decisions": list(record.decisions),
            "attachment_names": list(record.attachment_names),
        }

    def _handle_internet_command(self, user_input: str) -> str | None:
        command = user_input.strip().lower()

        if command == "/internet on":
            self.internet.set_enabled(True)
            return "Luna: Internet access enabled."

        if command == "/internet off":
            self.internet.set_enabled(False)
            return "Luna: Internet access disabled."

        if command == "/internet auto":
            self.internet.set_enabled(True)
            self.internet.set_mode("auto")
            return "Luna: Internet mode set to auto."

        if command == "/internet manual":
            self.internet.set_mode("manual")
            return "Luna: Internet mode set to manual."

        if command == "/internet status":
            return self.internet.status()

        if user_input.startswith("/search "):
            query = user_input[8:].strip()
            if not query:
                return "Luna: Please provide a search query."
            return self.internet.search(query)

        return None

    def _internet_context(self, user_input: str) -> str:
        if not self.internet.should_search(user_input):
            return ""

        result = self.internet.search(user_input)
        if result.startswith("Luna:"):
            return result[5:].strip()
        return result

    def _hidden_xeno_support(self, user_input: str) -> str:
        if not self.xeno.should_consult(user_input):
            return ""
        return self.xeno.build_hidden_support(user_input)

    def _project_context(self) -> str:
        project = self.projects.get_current_project()
        if project is None:
            return ""

        lines = [
            f"Project name: {project.name}",
            f"Current phase: {project.current_phase}",
            f"Project brief: {project.brief}",
        ]
        if project.next_step:
            lines.append(f"Next step: {project.next_step}")
        if project.tasks:
            top_tasks = []
            for task in project.tasks[:4]:
                title = task.get("title", "Task")
                status = task.get("status", "pending")
                top_tasks.append(f"{title} [{status}]")
            lines.append("Tracked tasks: " + ", ".join(top_tasks))
        if project.memory_entries:
            lines.append("Recent project memory: " + " | ".join(project.memory_entries[:4]))
        if project.attachment_names:
            lines.append("Linked files: " + ", ".join(project.attachment_names[:6]))
        lines.append(
            "If the user asks a vague follow-up and no new project is explicitly introduced, assume they still mean this active project."
        )
        return "\n".join(lines)

    def _remember_project_chat_focus(self, user_input: str, response: str) -> None:
        project = self.projects.get_current_project()
        if project is None:
            return
        cleaned_input = " ".join(user_input.strip().split())
        if not cleaned_input:
            return
        if cleaned_input.startswith("/"):
            return
        note = cleaned_input[:140]
        if len(cleaned_input) > 140:
            note += "..."
        self.projects.add_memory_entry(project.id, f"Chat focus: {note}")
        if response:
            cleaned_response = response.removeprefix("Luna: ").strip()
            if cleaned_response:
                short_response = cleaned_response[:160]
                if len(cleaned_response) > 160:
                    short_response += "..."
                self.projects.add_memory_entry(project.id, f"Luna direction: {short_response}")

    def get_runtime_status(self) -> str:
        return self.runtime_status.format()

    def get_memory_insights(self) -> str:
        return self.memory_coordinator.memory_insights()

    def build_prompt(
        self,
        user_input: str,
        mode: str,
        instruction: str = "",
        internet_context: str = "",
        selected_mode: str = "auto",
        reasoning_box: str = "black_box",
        hidden_support: str = "",
        project_context: str = "",
    ) -> list[dict[str, str]]:
        return self.prompt_builder.build(
            user_input=user_input,
            mode=mode,
            instruction=instruction,
            internet_context=internet_context,
            selected_mode=selected_mode,
            reasoning_box=reasoning_box,
            hidden_support=hidden_support,
            project_context=project_context,
        )

    def build_messages(
        self,
        user_input: str,
        mode: str,
        instruction: str = "",
        internet_context: str = "",
        selected_mode: str = "auto",
        reasoning_box: str = "black_box",
        hidden_support: str = "",
        project_context: str = "",
    ) -> list[dict[str, str]]:
        return self.build_prompt(
            user_input=user_input,
            mode=mode,
            instruction=instruction,
            internet_context=internet_context,
            selected_mode=selected_mode,
            reasoning_box=reasoning_box,
            hidden_support=hidden_support,
            project_context=project_context,
        )

    def chat(self, user_input: str) -> str:
        cleaned_input = user_input.strip()
        if not cleaned_input:
            return ""

        if cleaned_input.lower() == "exit":
            return "Luna: Goodbye."

        internet_result = self._handle_internet_command(cleaned_input)
        if internet_result is not None:
            return internet_result

        workflow_data = self.workflow.process(cleaned_input, self.memory.load_history())
        if workflow_data["system_message"]:
            return f"Luna: {workflow_data['system_message']}"

        selected_mode = workflow_data.get("selected_mode", workflow_data.get("mode", "auto"))
        self.memory_coordinator.remember_user_input(cleaned_input, selected_mode)

        internet_context = self._internet_context(workflow_data["user_input"])
        hidden_support = self._hidden_xeno_support(workflow_data["user_input"])
        project_context = self._project_context()
        messages = self.build_messages(
            user_input=workflow_data["user_input"],
            mode=workflow_data["mode"],
            instruction=workflow_data.get("instruction", ""),
            internet_context=internet_context,
            selected_mode=workflow_data.get("selected_mode", "auto"),
            reasoning_box=workflow_data.get("reasoning_box", self.settings.default_reasoning_box),
            hidden_support=hidden_support,
            project_context=project_context,
        )

        response = self.model.generate(messages)
        self.memory_coordinator.save_exchange(cleaned_input, response)
        self._remember_project_chat_focus(cleaned_input, response)
        return response

    def process_message(self, user_input: str) -> str:
        return self.chat(user_input)

    def list_chats(self) -> list[dict[str, str]]:
        return self.memory.list_sessions()

    def create_new_chat(self, title: str = "New chat") -> str:
        return self.memory.create_session(title)

    def switch_chat(self, session_id: str) -> list[dict[str, str]]:
        return self.memory.switch_session(session_id)

    def delete_chat(self, session_id: str) -> str:
        return self.memory.delete_session(session_id)

    def rename_chat(self, session_id: str, title: str) -> str:
        return self.memory.rename_session(session_id, title)

    def get_current_chat_id(self) -> str:
        return self.memory.get_current_session_id()

    def get_current_chat_title(self) -> str:
        return self.memory.get_current_session_title()

    def list_projects(self) -> list[dict[str, str]]:
        return self.projects.list_projects()

    def create_project(self, name: str, brief: str) -> dict[str, object]:
        record = self.projects.create_project(name, brief)
        self.projects.add_memory_entry(record.id, "Project created and waiting for the first Xeno blueprint.")
        return self._serialize_project(self.projects.get_project(record.id)) or {}

    def get_project(self, project_id: str) -> dict[str, object] | None:
        return self._serialize_project(self.projects.get_project(project_id))

    def get_current_project(self) -> dict[str, object] | None:
        return self._serialize_project(self.projects.get_current_project())

    def set_current_project(self, project_id: str) -> dict[str, object] | None:
        return self._serialize_project(self.projects.set_current_project(project_id))

    def update_project_task_status(self, project_id: str, task_title: str, status: str) -> dict[str, object] | None:
        updated = self.projects.update_task_status(project_id, task_title, status)
        if updated is not None:
            self.projects.add_memory_entry(project_id, f"Task updated: {task_title} -> {status.replace('_', ' ')}")
        return self._serialize_project(self.projects.get_project(project_id))

    def run_agent_task_action(self, project_id: str, task_title: str) -> dict[str, object]:
        project = self.projects.get_project(project_id)
        if project is None:
            return {"ok": False, "message": "Project could not be found."}

        result = self.desktop_actions.run_task_action(
            project_name=project.name,
            brief=project.brief,
            next_step=project.next_step,
            task_title=task_title,
            workspace_settings=self.user_settings.data,
        )
        self.projects.update_task_status(project_id, task_title, result.get("status", "completed"))
        self.projects.add_memory_entry(project_id, result.get("message", "Task agent ran an action."))
        updated = self.projects.get_project(project_id)
        return {
            "ok": True,
            "message": result.get("message", "Task agent ran an action."),
            "workspace": result.get("workspace", ""),
            "project": self._serialize_project(updated),
        }

    def open_connected_app(self, app_key: str, project_name: str = "") -> dict[str, str | bool]:
        return self.desktop_actions.launch_connected_app(
            app_key=app_key,
            workspace_settings=self.user_settings.data,
            project_name=project_name,
        )

    def add_project_memory(self, project_id: str, note: str) -> dict[str, object] | None:
        updated = self.projects.add_memory_entry(project_id, note)
        return self._serialize_project(updated)

    def attach_files_to_project(self, project_id: str, file_paths: list[str]) -> dict[str, object] | None:
        names = [Path(file_path).name for file_path in file_paths if Path(file_path).name]
        self.projects.add_attachment_names(project_id, names)
        if names:
            self.projects.add_memory_entry(project_id, f"New attachments linked: {', '.join(names)}")
        return self._serialize_project(self.projects.get_project(project_id))

    def read_attachment_context(self, file_paths: list[str]) -> str:
        if not file_paths:
            return ""

        allowed_suffixes = {".txt", ".md", ".py", ".json", ".yaml", ".yml", ".csv", ".log", ".ini", ".toml", ".js", ".ts", ".tsx", ".jsx", ".html", ".css"}
        parts: list[str] = []
        for raw_path in file_paths[:4]:
            path = Path(raw_path)
            if not path.exists():
                parts.append(f"File {path.name} could not be found locally.")
                continue
            if path.suffix.lower() not in allowed_suffixes:
                parts.append(f"File {path.name} attached as a binary or unsupported format.")
                continue
            try:
                content = path.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                parts.append(f"File {path.name} is attached but could not be read.")
                continue
            snippet = content[:4000].strip()
            if not snippet:
                parts.append(f"File {path.name} is attached but empty.")
                continue
            parts.append(f"Attached file: {path.name}\n{snippet}")
        return "\n\n".join(parts)

    def generate_project_package(self, user_input: str, project_name: str = "") -> dict[str, object]:
        result = self.xeno.project_builder.build_from_request(user_input)
        blueprint_text = self.xeno.handle(user_input)
        tasks = [
            {
                "title": step.title,
                "status": step.status,
                "description": step.description,
            }
            for step in (result.agent_run.steps if result.agent_run else [])
        ]
        resolved_name = project_name.strip() or result.blueprint.project_name
        current = self.projects.get_current_project()
        if current is None:
            record = self.projects.create_project(resolved_name, user_input)
        else:
            record = current
        updated = self.projects.update_project(
            record.id,
            name=resolved_name,
            brief=user_input,
            blueprint_text=blueprint_text,
            next_step=result.next_step,
            current_phase=result.agent_run.current_phase if result.agent_run else "planning",
            tasks=tasks,
        )
        self.projects.add_memory_entry(record.id, f"Xeno refreshed the project plan for {resolved_name}.")
        self.projects.add_memory_entry(record.id, f"Agent next step: {result.next_step}")
        project_id = updated.id if updated is not None else record.id
        return {
            "project_id": project_id,
            "project_name": resolved_name,
            "summary": result.summary,
            "blueprint_text": blueprint_text,
            "next_step": result.next_step,
            "current_phase": result.agent_run.current_phase if result.agent_run else "planning",
            "tasks": tasks,
            "xeno_note": f"Xeno prepared a new execution track for {resolved_name}.",
        }

    def generate_project_blueprint(self, user_input: str) -> str:
        return self.generate_project_package(user_input).get("blueprint_text", "")

    def describe_xeno(self) -> str:
        return self.xeno.describe()

    def clear_history(self) -> None:
        self.memory_coordinator.clear_all()

    def run(self) -> None:
        print("LunaAI launched. Type 'exit' to quit.")
        print("Luna is ready. Just write naturally and it will choose the right style automatically.")

        while True:
            user_input = input("Ty: ").strip()
            if not user_input:
                continue

            response = self.chat(user_input)
            if not response:
                continue

            print(response)
            if user_input.lower() == "exit":
                break

