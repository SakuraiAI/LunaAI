from __future__ import annotations

import os
import re
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path

from app.core.user_settings import UserWorkspaceSettings


@dataclass(slots=True)
class ActionResult:
    ok: bool
    status: str
    message: str
    detail: str = ""
    category: str = "system"
    action_key: str = ""
    workspace: str = ""

    def to_dict(self) -> dict[str, str | bool]:
        return asdict(self)


class DesktopActionTool:
    APP_PATH_FIELDS = {
        "unreal": "unreal_engine_path",
        "blender": "blender_path",
        "fl_studio": "fl_studio_path",
        "photoshop": "photoshop_path",
        "vscode": "vscode_path",
        "davinci": "davinci_resolve_path",
        "unity": "unity_path",
        "premiere": "premiere_pro_path",
        "after_effects": "after_effects_path",
        "figma": "figma_path",
        "substance": "substance_painter_path",
    }

    APP_DISPLAY_NAMES = {
        "unreal": "Unreal Engine 5",
        "blender": "Blender",
        "fl_studio": "FL Studio",
        "photoshop": "Photoshop",
        "vscode": "VS Code",
        "davinci": "DaVinci Resolve",
        "unity": "Unity",
        "premiere": "Premiere Pro",
        "after_effects": "After Effects",
        "figma": "Figma",
        "substance": "Substance 3D Painter",
    }

    ACTION_HINT_REGISTRY = {
        "create_scope_file": {"category": "file_change", "label": "Create scope file"},
        "create_execution_plan": {"category": "file_change", "label": "Create execution plan"},
        "create_project_scaffold": {"category": "file_change", "label": "Create project scaffold"},
        "open_workspace_in_tool": {"category": "app_launch", "label": "Open workspace in tool"},
        "refresh_review_notes": {"category": "file_change", "label": "Refresh review notes"},
        "observe_desktop_state": {"category": "observe", "label": "Observe desktop state"},
    }

    def __init__(self, workspace_root: Path | None = None) -> None:
        self.workspace_root = workspace_root or Path("data/projects/workspaces")
        self.workspace_root.mkdir(parents=True, exist_ok=True)

    def _result(
        self,
        *,
        ok: bool,
        status: str,
        message: str,
        detail: str = "",
        category: str = "system",
        action_key: str = "",
        workspace: str = "",
    ) -> dict[str, str | bool]:
        return ActionResult(
            ok=ok,
            status=status,
            message=message.strip(),
            detail=detail.strip(),
            category=category,
            action_key=action_key,
            workspace=workspace,
        ).to_dict()

    def list_registered_actions(self) -> list[dict[str, str]]:
        return [
            {"action_key": key, "category": value["category"], "label": value["label"]}
            for key, value in self.ACTION_HINT_REGISTRY.items()
        ]

    def describe_action_hint(self, action_hint: str) -> dict[str, str]:
        return dict(self.ACTION_HINT_REGISTRY.get(action_hint, {"category": "system", "label": action_hint or "Manual action"}))

    def _slugify(self, value: str) -> str:
        normalized = value.strip().lower()
        normalized = re.sub(r"[^a-z0-9]+", "-", normalized)
        normalized = normalized.strip("-")
        return normalized or "project"

    def get_project_workspace(self, project_name: str) -> Path:
        return self.workspace_root / self._slugify(project_name)

    def ensure_project_workspace(self, project_name: str) -> Path:
        workspace = self.get_project_workspace(project_name)
        workspace.mkdir(parents=True, exist_ok=True)
        return workspace

    def create_project_scaffold(self, project_name: str, brief: str = "") -> Path:
        workspace = self.ensure_project_workspace(project_name)
        for folder in ["docs", "src", "assets", "references"]:
            (workspace / folder).mkdir(parents=True, exist_ok=True)

        readme = workspace / "README.md"
        if not readme.exists():
            readme.write_text(
                f"# {project_name}\n\n{brief.strip() or 'Project created by Luna and the task agent.'}\n",
                encoding="utf-8",
            )

        notes = workspace / "docs" / "execution_notes.md"
        if not notes.exists():
            notes.write_text(
                "# Execution Notes\n\n- Initial scaffold created by Luna's task agent.\n",
                encoding="utf-8",
            )

        return workspace

    def create_execution_plan_file(self, project_name: str, next_step: str) -> Path:
        workspace = self.ensure_project_workspace(project_name)
        plan_file = workspace / "docs" / "execution_plan.md"
        plan_file.parent.mkdir(parents=True, exist_ok=True)
        plan_file.write_text(
            f"# Execution Plan\n\n## Next step\n\n{next_step.strip() or 'Define the next milestone.'}\n",
            encoding="utf-8",
        )
        return plan_file

    def create_scope_file(self, project_name: str, brief: str) -> Path:
        workspace = self.ensure_project_workspace(project_name)
        brief_file = workspace / "docs" / "project_scope.md"
        brief_file.parent.mkdir(parents=True, exist_ok=True)
        brief_file.write_text(
            f"# Project Scope\n\n{brief.strip() or 'Scope to be refined with Luna.'}\n",
            encoding="utf-8",
        )
        return brief_file

    def create_folder(self, path: Path) -> str:
        resolved = Path(path).expanduser()
        resolved.mkdir(parents=True, exist_ok=True)
        return f"Created folder {resolved}"

    def create_file(self, path: Path, content: str = "") -> str:
        resolved = Path(path).expanduser()
        resolved.parent.mkdir(parents=True, exist_ok=True)
        if resolved.exists():
            return f"File already exists: {resolved}"
        resolved.write_text(content, encoding="utf-8")
        return f"Created file {resolved}"

    def overwrite_file(self, path: Path, content: str) -> str:
        resolved = Path(path).expanduser()
        resolved.parent.mkdir(parents=True, exist_ok=True)
        resolved.write_text(content, encoding="utf-8")
        return f"Updated file {resolved}"

    def append_to_file(self, path: Path, content: str) -> str:
        resolved = Path(path).expanduser()
        resolved.parent.mkdir(parents=True, exist_ok=True)
        if resolved.exists():
            existing = resolved.read_text(encoding="utf-8", errors="ignore")
            prefix = "" if existing.endswith("\n") or not existing else "\n"
        else:
            prefix = ""
        with resolved.open("a", encoding="utf-8") as handle:
            handle.write(prefix + content)
        return f"Appended content to {resolved}"

    def create_files_batch(self, targets: dict[Path, str]) -> str:
        created: list[str] = []
        updated: list[str] = []

        for path, content in targets.items():
            resolved = Path(path).expanduser()
            resolved.parent.mkdir(parents=True, exist_ok=True)
            existed = resolved.exists()
            resolved.write_text(content, encoding="utf-8")
            if existed:
                updated.append(str(resolved))
            else:
                created.append(str(resolved))

        parts: list[str] = []
        if created:
            parts.append(f"Created {len(created)} files")
        if updated:
            parts.append(f"updated {len(updated)} files")
        if not parts:
            return "No files were created."
        return " and ".join(parts) + "."

    def create_python_project(self, project_name: str) -> Path:
        workspace = self.ensure_project_workspace(project_name)
        self.create_folder(workspace / "src")
        self.create_folder(workspace / "tests")
        self.create_files_batch(
            {
                workspace / "main.py": (
                    'def main() -> None:\n'
                    '    print("Hello from LunaAI")\n\n\n'
                    'if __name__ == "__main__":\n'
                    '    main()\n'
                ),
                workspace / "requirements.txt": "",
                workspace / "README.md": f"# {project_name}\n\nPython project scaffold created by Luna.\n",
                workspace / "src" / "__init__.py": "",
                workspace / "tests" / "test_smoke.py": "def test_smoke() -> None:\n    assert True\n",
            }
        )
        return workspace

    def create_web_project(self, project_name: str) -> Path:
        workspace = self.ensure_project_workspace(project_name)
        self.create_folder(workspace / "assets")
        self.create_files_batch(
            {
                workspace / "index.html": (
                    "<!doctype html>\n"
                    '<html lang="en">\n'
                    "<head>\n"
                    '  <meta charset="UTF-8">\n'
                    '  <meta name="viewport" content="width=device-width, initial-scale=1.0">\n'
                    "  <title>Luna Web Project</title>\n"
                    '  <link rel="stylesheet" href="styles.css">\n'
                    "</head>\n"
                    "<body>\n"
                    "  <main>\n"
                    "    <h1>Hello from LunaAI</h1>\n"
                    "    <p>Your web project is ready.</p>\n"
                    "  </main>\n"
                    '  <script src="script.js"></script>\n'
                    "</body>\n"
                    "</html>\n"
                ),
                workspace / "styles.css": (
                    "body {\n"
                    "  font-family: Arial, sans-serif;\n"
                    "  background: #111;\n"
                    "  color: #f5f5f5;\n"
                    "  margin: 0;\n"
                    "  min-height: 100vh;\n"
                    "  display: grid;\n"
                    "  place-items: center;\n"
                    "}\n"
                ),
                workspace / "script.js": "console.log('Luna web project ready');\n",
                workspace / "README.md": f"# {project_name}\n\nWeb project scaffold created by Luna.\n",
            }
        )
        return workspace

    def create_pyside_project(self, project_name: str) -> Path:
        workspace = self.ensure_project_workspace(project_name)
        self.create_folder(workspace / "app")
        self.create_folder(workspace / "app" / "ui")
        self.create_files_batch(
            {
                workspace / "main.py": (
                    "import sys\n"
                    "from PySide6.QtWidgets import QApplication, QLabel\n\n"
                    "app = QApplication(sys.argv)\n"
                    "label = QLabel('Hello from LunaAI')\n"
                    "label.resize(360, 120)\n"
                    "label.show()\n"
                    "sys.exit(app.exec())\n"
                ),
                workspace / "requirements.txt": "PySide6\n",
                workspace / "README.md": f"# {project_name}\n\nPySide6 project scaffold created by Luna.\n",
                workspace / "app" / "__init__.py": "",
                workspace / "app" / "ui" / "__init__.py": "",
            }
        )
        return workspace

    def open_path(self, path: Path) -> str:
        resolved = Path(path).expanduser()
        os.startfile(str(resolved))
        return f"Opened {resolved}"

    def _optional_open_detail(self, path: Path) -> str:
        try:
            opened_message = self.open_path(path)
            return opened_message
        except OSError as error:
            return f"Created successfully, but opening failed: {error}"

    def open_in_vscode(self, vscode_path: str, target: Path) -> str:
        if not vscode_path.strip():
            return self.open_path(target)
        subprocess.Popen([vscode_path, str(target)])
        return f"Opened {target} in VS Code"

    def _app_path_for(self, app_key: str, workspace_settings: UserWorkspaceSettings) -> str:
        field_name = self.APP_PATH_FIELDS.get(app_key, "")
        if not field_name:
            return ""
        return str(getattr(workspace_settings, field_name, "") or "").strip()

    def launch_connected_app(
        self,
        app_key: str,
        workspace_settings: UserWorkspaceSettings,
        project_name: str = "",
    ) -> dict[str, str | bool]:
        app_path = self._app_path_for(app_key, workspace_settings)
        app_name = self.APP_DISPLAY_NAMES.get(app_key, app_key)
        action_key = f"launch_{app_key}"
        if not app_path:
            return self._result(
                ok=False,
                status="failed",
                message=f"{app_name} nema nastavenou cestu.",
                detail="No app path is configured yet.",
                category="app_launch",
                action_key=action_key,
            )

        target_path = Path(app_path)
        if not target_path.exists():
            return self._result(
                ok=False,
                status="failed",
                message=f"Cesta k aplikaci {app_name} nebyla nalezena.",
                detail=f"Configured app path was not found: {app_path}",
                category="app_launch",
                action_key=action_key,
            )

        workspace = self.ensure_project_workspace(project_name) if project_name else None

        try:
            if app_key == "vscode":
                if workspace is not None:
                    subprocess.Popen([str(target_path), str(workspace)])
                    return self._result(
                        ok=True,
                        status="completed",
                        message=f"Opened {workspace} in VS Code.",
                        detail=f"VS Code launched with workspace {workspace}",
                        category="app_launch",
                        action_key=action_key,
                        workspace=str(workspace),
                    )
                subprocess.Popen([str(target_path)])
                return self._result(
                    ok=True,
                    status="completed",
                    message="Opened VS Code.",
                    detail="VS Code launched.",
                    category="app_launch",
                    action_key=action_key,
                )

            if target_path.is_dir():
                self.open_path(target_path)
                return self._result(
                    ok=True,
                    status="completed",
                    message=f"Opened {app_name}.",
                    detail=f"Opened directory target for {app_name}.",
                    category="app_launch",
                    action_key=action_key,
                )

            if target_path.suffix.lower() in {".lnk", ".url", ".exe"}:
                os.startfile(str(target_path))
            else:
                subprocess.Popen([str(target_path)])
        except OSError as error:
            return self._result(
                ok=False,
                status="failed",
                message=f"{app_name} se nepodarilo otevrit.",
                detail=f"Could not launch the app: {error}",
                category="app_launch",
                action_key=action_key,
                workspace=str(workspace or ""),
            )

        if workspace is not None:
            return self._result(
                ok=True,
                status="completed",
                message=f"Opened {app_name}. Project workspace is ready at {workspace}.",
                detail=f"{app_name} launched and workspace is ready.",
                category="app_launch",
                action_key=action_key,
                workspace=str(workspace),
            )
        return self._result(
            ok=True,
            status="completed",
            message=f"Opened {app_name}.",
            detail=f"{app_name} launched.",
            category="app_launch",
            action_key=action_key,
        )

    def run_task_action(
        self,
        *,
        project_name: str,
        brief: str,
        next_step: str,
        task: dict[str, object],
        workspace_settings: UserWorkspaceSettings,
    ) -> dict[str, str | bool]:
        task_title = str(task.get("title", "Task"))
        normalized = task_title.strip().lower()
        action_hint = str(task.get("action_hint", "")).strip().lower()
        handoff_note = str(task.get("handoff_note", "")).strip()
        workspace = self.ensure_project_workspace(project_name)
        action_meta = self.describe_action_hint(action_hint)
        category = action_meta.get("category", "system")

        if action_hint == "create_scope_file" or any(token in normalized for token in ["scope", "clarify the real target", "lock the first milestone"]):
            created = self.create_scope_file(project_name, brief)
            open_detail = self._optional_open_detail(created)
            message = handoff_note or f"Task agent prepared the project scope at {created}."
            return self._result(ok=True, status="completed", message=message, detail=f"Scope file prepared: {created}. {open_detail}", category=category, action_key=action_hint or "create_scope_file", workspace=str(workspace))

        if action_hint == "create_execution_plan" or any(token in normalized for token in ["execution path", "map the execution path", "implementation stack"]):
            created = self.create_execution_plan_file(project_name, next_step)
            open_detail = self._optional_open_detail(created)
            message = handoff_note or f"Task agent created the execution plan at {created}."
            return self._result(ok=True, status="completed", message=message, detail=f"Execution plan updated: {created}. {open_detail}", category=category, action_key=action_hint or "create_execution_plan", workspace=str(workspace))

        if action_hint == "create_project_scaffold" or any(token in normalized for token in ["workspace", "implementation structure", "scaffold", "prepare local workspace"]):
            created_workspace = self.create_project_scaffold(project_name, brief)
            message = handoff_note or f"Task agent created the project workspace structure in {created_workspace}."
            return self._result(ok=True, status="completed", message=message, detail=f"Workspace scaffold ready: {created_workspace}", category=category, action_key=action_hint or "create_project_scaffold", workspace=str(created_workspace))

        if action_hint == "open_workspace_in_tool" or any(token in normalized for token in ["working slice", "milestone", "build the first working slice"]):
            created_workspace = self.create_project_scaffold(project_name, brief)
            vscode_message = self.open_in_vscode(workspace_settings.vscode_path, created_workspace)
            message = handoff_note or f"Task agent prepared the workspace and {vscode_message.lower()}."
            return self._result(ok=True, status="in_progress", message=message, detail=f"Workspace opened for implementation: {created_workspace}", category=category, action_key=action_hint or "open_workspace_in_tool", workspace=str(created_workspace))

        if action_hint == "refresh_review_notes" or any(token in normalized for token in ["review quality", "review and harden", "next step"]):
            created = self.create_execution_plan_file(project_name, next_step)
            message = handoff_note or f"Task agent refreshed the review notes and next-step file at {created}."
            return self._result(ok=True, status="completed", message=message, detail=f"Review notes refreshed: {created}", category=category, action_key=action_hint or "refresh_review_notes", workspace=str(workspace))

        open_detail = self._optional_open_detail(workspace)
        return self._result(ok=True, status="in_progress", message=handoff_note or f"Task agent prepared the project workspace at {workspace} for the next manual step.", detail=f"Workspace ready: {workspace}. {open_detail}", category="path_open", action_key=action_hint or "open_workspace", workspace=str(workspace))
