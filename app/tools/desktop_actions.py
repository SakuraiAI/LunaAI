from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path

from app.core.user_settings import UserWorkspaceSettings


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

    def __init__(self, workspace_root: Path | None = None) -> None:
        self.workspace_root = workspace_root or Path("data/projects/workspaces")
        self.workspace_root.mkdir(parents=True, exist_ok=True)

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

    def open_path(self, path: Path) -> str:
        os.startfile(str(path))
        return f"Opened {path}"

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
        if not app_path:
            return {"ok": False, "message": "No app path is configured yet."}

        target_path = Path(app_path)
        if not target_path.exists():
            return {"ok": False, "message": f"Configured app path was not found: {app_path}"}

        workspace = self.ensure_project_workspace(project_name) if project_name else None
        app_name = self.APP_DISPLAY_NAMES.get(app_key, app_key)

        try:
            if app_key == "vscode":
                target = workspace if workspace is not None else Path.cwd()
                subprocess.Popen([str(target_path), str(target)])
                return {"ok": True, "message": f"Opened {target} in VS Code."}

            if target_path.is_dir():
                self.open_path(target_path)
                return {"ok": True, "message": f"Opened {app_name}."}

            if target_path.suffix.lower() in {".lnk", ".url"}:
                os.startfile(str(target_path))
            else:
                subprocess.Popen([str(target_path)])
        except OSError as error:
            return {"ok": False, "message": f"Could not launch the app: {error}"}

        if workspace is not None:
            return {
                "ok": True,
                "message": f"Opened {app_name}. Project workspace is ready at {workspace}.",
            }
        return {"ok": True, "message": f"Opened {app_name}."}

    def run_task_action(
        self,
        *,
        project_name: str,
        brief: str,
        next_step: str,
        task_title: str,
        workspace_settings: UserWorkspaceSettings,
    ) -> dict[str, str]:
        normalized = task_title.strip().lower()
        workspace = self.ensure_project_workspace(project_name)

        if "align the scope" in normalized or "scope" in normalized:
            created = self.create_scope_file(project_name, brief)
            self.open_path(created)
            return {
                "status": "completed",
                "message": f"Task agent prepared the project scope at {created} and opened it for review.",
                "workspace": str(workspace),
            }

        if "execution path" in normalized or "design the execution path" in normalized:
            created = self.create_execution_plan_file(project_name, next_step)
            self.open_path(created)
            return {
                "status": "completed",
                "message": f"Task agent created an execution plan at {created} and opened it.",
                "workspace": str(workspace),
            }

        if (
            "implementation structure" in normalized
            or "scaffold" in normalized
            or "prepare implementation structure" in normalized
        ):
            created_workspace = self.create_project_scaffold(project_name, brief)
            return {
                "status": "completed",
                "message": f"Task agent created the project workspace structure in {created_workspace}.",
                "workspace": str(created_workspace),
            }

        if "ship the first milestone" in normalized or "milestone" in normalized:
            created_workspace = self.create_project_scaffold(project_name, brief)
            message = self.open_in_vscode(workspace_settings.vscode_path, created_workspace)
            return {
                "status": "in_progress",
                "message": f"Task agent prepared the workspace and {message.lower()}.",
                "workspace": str(created_workspace),
            }

        self.open_path(workspace)
        return {
            "status": "in_progress",
            "message": f"Task agent opened the project workspace at {workspace} for the next manual step.",
            "workspace": str(workspace),
        }
