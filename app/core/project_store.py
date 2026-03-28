from dataclasses import asdict, dataclass, field
import json
from pathlib import Path
from uuid import uuid4


@dataclass(slots=True)
class ProjectRecord:
    id: str
    name: str
    brief: str
    blueprint_text: str = ""
    next_step: str = ""
    current_phase: str = "draft"
    tasks: list[dict[str, str]] = field(default_factory=list)
    memory_entries: list[str] = field(default_factory=list)
    decisions: list[str] = field(default_factory=list)
    attachment_names: list[str] = field(default_factory=list)


class ProjectStore:
    def __init__(self, storage_path: Path) -> None:
        self.storage_path = storage_path
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        self.projects: list[ProjectRecord] = []
        self.current_project_id: str = ""
        self.load()

    def load(self) -> list[ProjectRecord]:
        if not self.storage_path.exists():
            return self.projects

        try:
            payload = json.loads(self.storage_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return self.projects

        if not isinstance(payload, dict):
            return self.projects

        self.current_project_id = payload.get("current_project_id", "") if isinstance(payload.get("current_project_id"), str) else ""
        raw_projects = payload.get("projects", [])
        if isinstance(raw_projects, list):
            self.projects = []
            for item in raw_projects:
                if not isinstance(item, dict):
                    continue
                project_id = item.get("id")
                name = item.get("name")
                brief = item.get("brief")
                if not all(isinstance(value, str) for value in (project_id, name, brief)):
                    continue

                tasks = self._normalize_tasks(item.get("tasks", []))
                memory_entries = self._normalize_string_list(item.get("memory_entries", []))
                decisions = self._normalize_string_list(item.get("decisions", []))
                attachment_names = self._normalize_string_list(item.get("attachment_names", []))

                self.projects.append(
                    ProjectRecord(
                        id=project_id,
                        name=name,
                        brief=brief,
                        blueprint_text=item.get("blueprint_text", "") if isinstance(item.get("blueprint_text"), str) else "",
                        next_step=item.get("next_step", "") if isinstance(item.get("next_step"), str) else "",
                        current_phase=item.get("current_phase", "draft") if isinstance(item.get("current_phase"), str) else "draft",
                        tasks=tasks,
                        memory_entries=memory_entries,
                        decisions=decisions,
                        attachment_names=attachment_names,
                    )
                )
        return self.projects

    def _normalize_tasks(self, raw_tasks: object) -> list[dict[str, str]]:
        tasks: list[dict[str, str]] = []
        if not isinstance(raw_tasks, list):
            return tasks
        for task in raw_tasks:
            if not isinstance(task, dict):
                continue
            title = task.get("title", "")
            status = task.get("status", "pending")
            description = task.get("description", "")
            if isinstance(title, str) and isinstance(status, str) and isinstance(description, str):
                tasks.append({
                    "title": title,
                    "status": status,
                    "description": description,
                })
        return tasks

    def _normalize_string_list(self, raw_values: object) -> list[str]:
        if not isinstance(raw_values, list):
            return []
        return [value.strip() for value in raw_values if isinstance(value, str) and value.strip()]

    def save(self) -> None:
        payload = {
            "current_project_id": self.current_project_id,
            "projects": [asdict(project) for project in self.projects],
        }
        self.storage_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def list_projects(self) -> list[dict[str, str]]:
        return [
            {
                "id": project.id,
                "name": project.name,
                "current_phase": project.current_phase,
                "task_count": str(len(project.tasks)),
                "memory_count": str(len(project.memory_entries)),
            }
            for project in self.projects
        ]

    def create_project(self, name: str, brief: str) -> ProjectRecord:
        record = ProjectRecord(
            id=uuid4().hex[:12],
            name=name.strip() or "New Project",
            brief=brief,
        )
        self.projects.insert(0, record)
        self.current_project_id = record.id
        self.save()
        return record

    def update_project(
        self,
        project_id: str,
        *,
        name: str | None = None,
        brief: str | None = None,
        blueprint_text: str | None = None,
        next_step: str | None = None,
        current_phase: str | None = None,
        tasks: list[dict[str, str]] | None = None,
        memory_entries: list[str] | None = None,
        decisions: list[str] | None = None,
        attachment_names: list[str] | None = None,
    ) -> ProjectRecord | None:
        project = self.get_project(project_id)
        if project is None:
            return None

        if name is not None:
            project.name = name.strip() or project.name
        if brief is not None:
            project.brief = brief
        if blueprint_text is not None:
            project.blueprint_text = blueprint_text
        if next_step is not None:
            project.next_step = next_step
        if current_phase is not None:
            project.current_phase = current_phase
        if tasks is not None:
            project.tasks = tasks
        if memory_entries is not None:
            project.memory_entries = memory_entries
        if decisions is not None:
            project.decisions = decisions
        if attachment_names is not None:
            project.attachment_names = attachment_names
        self.current_project_id = project.id
        self.save()
        return project

    def update_task_status(self, project_id: str, task_title: str, status: str) -> ProjectRecord | None:
        project = self.get_project(project_id)
        if project is None:
            return None
        for task in project.tasks:
            if task.get("title") == task_title:
                task["status"] = status
                break
        self.save()
        return project

    def add_memory_entry(self, project_id: str, entry: str) -> ProjectRecord | None:
        project = self.get_project(project_id)
        if project is None:
            return None
        clean_entry = entry.strip()
        if not clean_entry:
            return project
        project.memory_entries.insert(0, clean_entry)
        project.memory_entries = project.memory_entries[:24]
        self.save()
        return project

    def add_attachment_names(self, project_id: str, names: list[str]) -> ProjectRecord | None:
        project = self.get_project(project_id)
        if project is None:
            return None
        for name in names:
            clean_name = name.strip()
            if clean_name and clean_name not in project.attachment_names:
                project.attachment_names.append(clean_name)
        self.save()
        return project

    def get_project(self, project_id: str) -> ProjectRecord | None:
        for project in self.projects:
            if project.id == project_id:
                return project
        return None

    def get_current_project(self) -> ProjectRecord | None:
        if self.current_project_id:
            return self.get_project(self.current_project_id)
        return self.projects[0] if self.projects else None

    def set_current_project(self, project_id: str) -> ProjectRecord | None:
        project = self.get_project(project_id)
        if project is None:
            return None
        self.current_project_id = project.id
        self.save()
        return project
