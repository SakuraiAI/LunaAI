from __future__ import annotations

from pathlib import Path
from typing import Callable
import re
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from config.settings import AppSettings
from app.core.action_log import ActionLogStore
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
        self.action_log = ActionLogStore(Path("data/logs/action_log.jsonl"))
        self.pending_action: tuple[str, str, Callable[[], str]] | None = None

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

    def _action_mode(self) -> str:
        mode = str(self.user_settings.data.agent_execution_mode or "ask").strip().lower()
        if mode not in {"ask", "auto", "block"}:
            return "ask"
        return mode

    def _is_action_allowed(self, category: str) -> bool:
        workspace = self.user_settings.data
        if category == "app_launch":
            return bool(workspace.allow_app_launch)
        if category == "path_open":
            return bool(workspace.allow_path_open)
        if category == "file_change":
            return bool(workspace.allow_file_changes)
        return True

    def _log_action(self, category: str, title: str, status: str, detail: str) -> None:
        self.action_log.record(category=category, title=title, status=status, detail=detail)

    def list_recent_actions(self, limit: int = 8) -> list[dict[str, str]]:
        return [
            {
                "timestamp": entry.timestamp,
                "category": entry.category,
                "title": entry.title,
                "status": entry.status,
                "detail": entry.detail,
            }
            for entry in self.action_log.recent(limit)
        ]

    def format_recent_actions(self, limit: int = 8) -> str:
        entries = self.list_recent_actions(limit)
        if not entries:
            return "No recent agent actions yet."
        lines: list[str] = []
        for entry in entries:
            lines.append(f"[{entry['timestamp']}] {entry['status'].upper()} - {entry['title']}")
            if entry["detail"]:
                lines.append(entry["detail"])
        return "\n\n".join(lines)

    def _guarded_action(self, category: str, title: str, callback: Callable[[], str]) -> str:
        if not self._is_action_allowed(category):
            detail = f"{title} is blocked by the current agent permissions."
            self._log_action(category, title, "blocked", detail)
            return f"Luna: {detail}"
        mode = self._action_mode()
        if mode == "block":
            detail = f"{title} is blocked because agent execution mode is set to block."
            self._log_action(category, title, "blocked", detail)
            return f"Luna: {detail}"
        if mode == "ask":
            self.pending_action = (category, title, callback)
            detail = f"Pending approval for {title}."
            self._log_action(category, title, "pending", detail)
            return "Luna: Mam akci pripravenou. Napis `potvrd akci`, pokud ji mam opravdu provest, nebo `zrus akci`, pokud ji mam zahodit."
        try:
            message = callback()
        except OSError as error:
            detail = f"{title} failed: {error}"
            self._log_action(category, title, "failed", detail)
            return f"Luna: {detail}"
        self._log_action(category, title, "completed", message)
        return f"Luna: {message}"

    def has_pending_action(self) -> bool:
        return self.pending_action is not None

    def get_pending_action_title(self) -> str:
        if self.pending_action is None:
            return ""
        return self.pending_action[1]

    def confirm_pending_action(self) -> str:
        return self.chat("potvrd akci")

    def cancel_pending_action(self) -> str:
        return self.chat("zrus akci")

    def _handle_pending_action_command(self, user_input: str) -> str | None:
        normalized = " ".join(user_input.strip().lower().split())
        if normalized not in {"potvrd akci", "confirm action", "zrus akci", "cancel action"}:
            return None
        if self.pending_action is None:
            return "Luna: Ted nemam zadnou cekajici akci k potvrzeni."
        category, title, callback = self.pending_action
        self.pending_action = None
        if normalized in {"zrus akci", "cancel action"}:
            detail = f"Cancelled {title}."
            self._log_action(category, title, "cancelled", detail)
            return f"Luna: {detail}"
        try:
            message = callback()
        except OSError as error:
            detail = f"{title} failed: {error}"
            self._log_action(category, title, "failed", detail)
            return f"Luna: {detail}"
        self._log_action(category, title, "completed", message)
        return f"Luna: {message}"

    def _resolve_local_target(self, raw_target: str) -> Path | None:
        target_text = raw_target.strip().strip('"').strip("'")
        if not target_text:
            return None
        candidate = Path(target_text).expanduser()
        if candidate.exists():
            return candidate
        workspace_candidate = (Path.cwd() / target_text).resolve()
        if workspace_candidate.exists():
            return workspace_candidate
        return None

    def _default_action_root(self) -> Path:
        current_project = self.projects.get_current_project()
        if current_project is not None:
            return self.desktop_actions.ensure_project_workspace(str(current_project.get("name", "")))
        return Path.cwd()

    def _resolve_creation_target(self, raw_target: str) -> Path:
        target_text = raw_target.strip().strip('"').strip("'")
        if not target_text:
            return self._default_action_root()
        candidate = Path(target_text).expanduser()
        if candidate.is_absolute():
            return candidate
        return (self._default_action_root() / candidate).resolve()

    def _search_roots(self) -> list[Path]:
        roots: list[Path] = []
        current_project = self.projects.get_current_project()
        if current_project is not None:
            roots.append(self.desktop_actions.ensure_project_workspace(str(current_project.get("name", ""))))
        cwd = Path.cwd()
        if cwd not in roots:
            roots.append(cwd)
        return roots

    def _find_named_target(self, target_name: str, *, prefer_directory: bool | None = None) -> Path | None:
        clean_name = target_name.strip().strip('"').strip("'")
        if not clean_name:
            return None
        lower_name = clean_name.lower()
        for root in self._search_roots():
            if not root.exists():
                continue
            try:
                for path in root.rglob("*"):
                    if path.name.lower() != lower_name:
                        continue
                    if prefer_directory is True and not path.is_dir():
                        continue
                    if prefer_directory is False and not path.is_file():
                        continue
                    return path
            except OSError:
                continue
        return None

    def _split_action_chain(self, user_input: str) -> list[str]:
        normalized = " ".join(user_input.strip().split())
        separators = [
            r"\s+a pak\s+",
            r"\s+potom\s+",
            r"\s+and then\s+",
            r"\s+then\s+",
        ]
        for separator in separators:
            if re.search(separator, normalized, flags=re.IGNORECASE):
                parts = [part.strip(" ,.") for part in re.split(separator, normalized, flags=re.IGNORECASE) if part.strip(" ,.")]
                if len(parts) > 1:
                    return parts
        return [normalized]

    def _chain_action_category(self, parts: list[str]) -> str:
        lowered = " ".join(parts).lower()
        if any(token in lowered for token in ["vytvor", "create", "make", "prepis", "rewrite", "overwrite", "append", "pridej do"]):
            return "file_change"
        if any(token in lowered for token in ["vscode", "vs code", "blender", "unreal", "unity", "photoshop", "davinci", "premiere", "after effects", "figma", "fl studio", "substance"]):
            return "app_launch"
        return "path_open"

    def _execute_chained_action_part(self, user_input: str) -> str | None:
        original_mode = self.user_settings.data.agent_execution_mode
        self.user_settings.data.agent_execution_mode = "auto"
        try:
            result = self._try_local_path_action(user_input)
            if result is None:
                result = self._try_local_app_action(user_input)
        finally:
            self.user_settings.data.agent_execution_mode = original_mode

        if result is None:
            return None

        cleaned = result.removeprefix("Luna: ").strip()
        if not cleaned:
            return None
        if any(token in cleaned.lower() for token in ["blocked", "nemohla", "nenasla", "chybi", "failed"]):
            raise OSError(cleaned)
        return cleaned

    def _try_local_action(self, user_input: str) -> str | None:
        parts = self._split_action_chain(user_input)
        if len(parts) > 1:
            category = self._chain_action_category(parts)
            title = " -> ".join(parts)

            def run_chain() -> str:
                messages: list[str] = []
                for part in parts:
                    result = self._execute_chained_action_part(part)
                    if result is None:
                        raise OSError(f'Neumim provest tento krok: "{part}"')
                    clean_result = result.rstrip(".")
                    if clean_result and clean_result not in messages:
                        messages.append(clean_result)
                return ". ".join(messages) + "."

            return self._guarded_action(category, f"chain action: {title}", run_chain)

        local_path_result = self._try_local_path_action(user_input)
        if local_path_result is not None:
            return local_path_result
        return self._try_local_app_action(user_input)

    def _try_local_path_action(self, user_input: str) -> str | None:
        normalized = " ".join(user_input.strip().split())
        lowered = normalized.lower()
        if not normalized:
            return None

        project_blueprints = [
            (r'(?:vytvor|vytvo?|create|make) python projekt (.+?)(?: a otevri ve vscode| and open in vscode)?$', "python"),
            (r'(?:vytvor|vytvo?|create|make) web projekt (.+?)(?: a otevri ve vscode| and open in vscode)?$', "web"),
            (r'(?:vytvor|vytvo?|create|make) pyside projekt (.+?)(?: a otevri ve vscode| and open in vscode)?$', "pyside"),
        ]
        for pattern, kind in project_blueprints:
            match = re.search(pattern, normalized, flags=re.IGNORECASE)
            if not match:
                continue
            project_name = match.group(1).strip().strip('"').strip("'")
            if not project_name:
                return "Luna: Chybi nazev projektu."
            open_in_vscode = "vscode" in lowered

            def run_project_creation() -> str:
                if kind == "python":
                    workspace = self.desktop_actions.create_python_project(project_name)
                elif kind == "web":
                    workspace = self.desktop_actions.create_web_project(project_name)
                else:
                    workspace = self.desktop_actions.create_pyside_project(project_name)
                if open_in_vscode:
                    vscode_message = self.desktop_actions.open_in_vscode(self.user_settings.data.vscode_path, workspace)
                    return f"Created {kind} project {workspace}. {vscode_message}."
                return f"Created {kind} project {workspace}."

            return self._guarded_action("file_change", f"create {kind} project {project_name}", run_project_creation)

        rewrite_patterns = [r'(?:prepis|p?epi?|rewrite|overwrite) (?:soubor|file) (.+?) (?:s obsahem|with content) (.+)$']
        for pattern in rewrite_patterns:
            match = re.search(pattern, normalized, flags=re.IGNORECASE)
            if not match:
                continue
            target = self._resolve_creation_target(match.group(1))
            content = match.group(2)
            return self._guarded_action("file_change", f"overwrite file {target}", lambda: self.desktop_actions.overwrite_file(target, content))

        append_patterns = [r'(?:pridej do|p?idej do|append to) (?:souboru|soubor|file) (.+?) (?:obsah|content) (.+)$']
        for pattern in append_patterns:
            match = re.search(pattern, normalized, flags=re.IGNORECASE)
            if not match:
                continue
            target = self._resolve_creation_target(match.group(1))
            content = match.group(2)
            return self._guarded_action("file_change", f"append to file {target}", lambda: self.desktop_actions.append_to_file(target, content))

        multi_file_match = re.search(
            r'(?:vytvor|vytvo?|create|make) (?:soubory|files) (.+?)(?: (?:a )?otevri ve vscode| (?:and )?open in vscode)?$',
            normalized,
            flags=re.IGNORECASE,
        )
        if multi_file_match:
            raw_targets = multi_file_match.group(1)
            open_in_vscode = "vscode" in lowered
            parts = [part.strip().strip('"').strip("'") for part in re.split(r",|;", raw_targets) if part.strip()]
            if not parts:
                return "Luna: Chybi seznam souboru."
            targets = {self._resolve_creation_target(part): "" for part in parts}

            def create_many_files() -> str:
                message = self.desktop_actions.create_files_batch(targets)
                if open_in_vscode:
                    first_target = next(iter(targets.keys()))
                    vscode_message = self.desktop_actions.open_in_vscode(self.user_settings.data.vscode_path, first_target)
                    return f"{message} {vscode_message}."
                return message

            return self._guarded_action("file_change", f"create files {', '.join(parts)}", create_many_files)
        rich_file_match = re.search(
            r'(?:vytvor|vytvo?|create|make) (?:soubor|file) (.+?) (?:s obsahem|with content) (.+?)(?: (?:a )?otevri ve vscode| (?:and )?open in vscode)?$',
            normalized,
            flags=re.IGNORECASE,
        )
        if rich_file_match:
            target = self._resolve_creation_target(rich_file_match.group(1))
            content = rich_file_match.group(2)
            open_in_vscode = "vscode" in lowered

            def create_rich_file() -> str:
                message = self.desktop_actions.create_file(target, content)
                if open_in_vscode:
                    vscode_message = self.desktop_actions.open_in_vscode(self.user_settings.data.vscode_path, target)
                    return f"{message}. {vscode_message}."
                return message

            return self._guarded_action("file_change", f"create file {target}", create_rich_file)

        create_folder_patterns = [r'(?:vytvor|vytvo?|create|make) (?:slozku|slo?ku|folder|adresar|adres??) (.+)$']
        for pattern in create_folder_patterns:
            match = re.search(pattern, normalized, flags=re.IGNORECASE)
            if not match:
                continue
            target = self._resolve_creation_target(match.group(1))
            return self._guarded_action("file_change", f"create folder {target}", lambda: self.desktop_actions.create_folder(target))

        create_file_patterns = [r'(?:vytvor|vytvo?|create|make) (?:soubor|file) (.+)$']
        for pattern in create_file_patterns:
            match = re.search(pattern, normalized, flags=re.IGNORECASE)
            if not match:
                continue
            raw_target = match.group(1)
            open_in_vscode = "vscode" in raw_target.lower()
            if open_in_vscode:
                raw_target = re.sub(r'(?:a )?otevri ve vscode|(?:and )?open in vscode', '', raw_target, flags=re.IGNORECASE).strip()
            target = self._resolve_creation_target(raw_target)

            def create_file_action() -> str:
                message = self.desktop_actions.create_file(target)
                if open_in_vscode:
                    vscode_message = self.desktop_actions.open_in_vscode(self.user_settings.data.vscode_path, target)
                    return f"{message}. {vscode_message}."
                return message

            return self._guarded_action("file_change", f"create file {target}", create_file_action)

        direct_path_match = re.search(r'([A-Za-z]:[\\/][^"]+)', normalized)
        if direct_path_match and any(token in lowered for token in ["otevri", "otev?i", "open", "spust", "spus?"]):
            target = self._resolve_local_target(direct_path_match.group(1))
            if target is not None:
                return self._guarded_action("path_open", f"open path {target}", lambda: self.desktop_actions.open_path(target))
            return "Luna: Tu cestu jsem na pocitaci nenasla."

        command_patterns = [
            (r'(?:otevri|otev?i|open) (?:soubor|file) (.+)$', False),
            (r'(?:otevri|otev?i|open) (?:slozku|slo?ku|folder|adresar|adres??) (.+)$', True),
            (r'(?:spust|spus?) (?:soubor|file|path|cestu) (.+)$', False),
        ]
        for pattern, prefer_directory in command_patterns:
            match = re.search(pattern, normalized, flags=re.IGNORECASE)
            if not match:
                continue
            raw_target = match.group(1)
            target = self._resolve_local_target(raw_target)
            if target is None:
                target = self._find_named_target(raw_target, prefer_directory=prefer_directory)
            if target is None:
                return "Luna: Ten soubor nebo slozku jsem na pocitaci nenasla."
            return self._guarded_action("path_open", f"open path {target}", lambda: self.desktop_actions.open_path(target))

        if any(phrase in lowered for phrase in ["otevri workspace ve vscode", "otev?i workspace ve vscode", "open workspace in vscode", "otevri projekt ve vscode", "otev?i projekt ve vscode", "open project in vscode"]):
            current_project = self.projects.get_current_project()
            if current_project is None:
                return "Luna: Ted nemam aktivni projekt, takze nemam jaky workspace otevrit ve VS Code."

            def open_workspace_in_vscode() -> str:
                result = self.open_connected_app("vscode", str(current_project.get("name", "")))
                message = str(result.get("message", "")).strip()
                if result.get("ok"):
                    return message
                raise OSError(message or "VS Code jsem nemohla otevrit.")

            return self._guarded_action("app_launch", f"open workspace in VS Code for {current_project.get('name', '')}", open_workspace_in_vscode)

        if any(phrase in lowered for phrase in ["otevri projekt", "otev?i projekt", "open project", "otevri workspace", "otev?i workspace", "open workspace"]):
            current_project = self.projects.get_current_project()
            if current_project is None:
                return "Luna: Ted nemam aktivni projekt, takze nemam jaky workspace otevrit."
            workspace = self.desktop_actions.ensure_project_workspace(str(current_project.get("name", "")))
            return self._guarded_action("path_open", f"open workspace {workspace}", lambda: self.desktop_actions.open_path(workspace))

        return None

    def _try_local_app_action(self, user_input: str) -> str | None:
        normalized = " ".join(user_input.strip().lower().split())
        if not normalized:
            return None

        app_aliases = {
            "vscode": ["vscode", "vs code", "visual studio code", "code.exe"],
            "blender": ["blender"],
            "unreal": ["unreal", "unreal engine", "unreal engine 5", "ue5"],
            "unity": ["unity"],
            "photoshop": ["photoshop"],
            "davinci": ["davinci", "davinci resolve"],
            "premiere": ["premiere", "premiere pro"],
            "after_effects": ["after effects", "aftereffects"],
            "figma": ["figma"],
            "fl_studio": ["fl studio"],
            "substance": ["substance", "substance painter", "substance 3d painter"],
        }
        open_markers = [
            "otevri", "otevrit", "otev?", "otev?e", "otevrel", "otevrela",
            "spust", "spustit", "zapni", "zapnout",
            "open", "launch", "start",
        ]
        if not any(marker in normalized for marker in open_markers):
            return None

        for app_key, aliases in app_aliases.items():
            if any(alias in normalized for alias in aliases):
                project_name = ""
                if app_key != "vscode":
                    current_project = self.projects.get_current_project()
                    project_name = current_project.name if current_project is not None else ""

                def launch_app() -> str:
                    result = self.open_connected_app(app_key, project_name, log_result=False)
                    message = str(result.get("message", "")).strip()
                    if result.get("ok"):
                        return message
                    raise OSError(message or "App could not be opened.")

                return self._guarded_action("app_launch", f"open {app_key}", launch_app)

        return None

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
        lines.append("If the user asks a vague follow-up and no new project is explicitly introduced, assume they still mean this active project.")
        return "\n".join(lines)

    def _remember_project_chat_focus(self, user_input: str, response: str) -> None:
        project = self.projects.get_current_project()
        if project is None:
            return
        cleaned_input = " ".join(user_input.strip().split())
        if not cleaned_input or cleaned_input.startswith("/"):
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

        pending_action_result = self._handle_pending_action_command(cleaned_input)
        if pending_action_result is not None:
            self.memory_coordinator.remember_user_input(cleaned_input, "action")
            self.memory_coordinator.save_exchange(cleaned_input, pending_action_result)
            return pending_action_result

        internet_result = self._handle_internet_command(cleaned_input)
        if internet_result is not None:
            return internet_result

        local_action_result = self._try_local_action(cleaned_input)
        if local_action_result is not None:
            self.memory_coordinator.remember_user_input(cleaned_input, "action")
            self.memory_coordinator.save_exchange(cleaned_input, local_action_result)
            self._remember_project_chat_focus(cleaned_input, local_action_result)
            return local_action_result

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
        self._log_action("file_change", f"task action: {task_title}", result.get("status", "completed"), result.get("message", "Task agent ran an action."))
        updated = self.projects.get_project(project_id)
        return {
            "ok": True,
            "message": result.get("message", "Task agent ran an action."),
            "workspace": result.get("workspace", ""),
            "project": self._serialize_project(updated),
        }

    def open_connected_app(self, app_key: str, project_name: str = "", log_result: bool = True) -> dict[str, str | bool]:
        result = self.desktop_actions.launch_connected_app(
            app_key=app_key,
            workspace_settings=self.user_settings.data,
            project_name=project_name,
        )
        status = "completed" if result.get("ok") else "failed"
        self._log_action("app_launch", f"open {app_key}", status, str(result.get("message", "")))
        return result

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
        tasks = [{"title": step.title, "status": step.status, "description": step.description} for step in (result.agent_run.steps if result.agent_run else [])]
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



