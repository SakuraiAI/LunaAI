from dataclasses import asdict, dataclass
import json
from pathlib import Path


@dataclass(slots=True)
class UserWorkspaceSettings:
    unreal_engine_path: str = ""
    blender_path: str = ""
    fl_studio_path: str = ""
    photoshop_path: str = ""
    vscode_path: str = ""
    davinci_resolve_path: str = ""
    unity_path: str = ""
    premiere_pro_path: str = ""
    after_effects_path: str = ""
    figma_path: str = ""
    substance_painter_path: str = ""
    github_username: str = ""
    github_token: str = ""
    google_email: str = ""
    profile_display_name: str = ""
    profile_image_path: str = ""
    agent_execution_mode: str = "ask"
    allow_app_launch: bool = True
    allow_path_open: bool = True
    allow_file_changes: bool = True
    cloud_enabled: bool = False
    cloud_provider: str = "local_folder"
    cloud_root_path: str = ""
    cloud_account_email: str = ""
    cloud_auto_sync: bool = False


class UserSettingsStore:
    def __init__(self, storage_path: Path) -> None:
        self.storage_path = storage_path
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        self.data = UserWorkspaceSettings()
        self.load()

    def load(self) -> UserWorkspaceSettings:
        if not self.storage_path.exists():
            return self.data

        try:
            payload = json.loads(self.storage_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return self.data

        if not isinstance(payload, dict):
            return self.data

        for field_name, field_info in self.data.__dataclass_fields__.items():
            value = payload.get(field_name)
            current = getattr(self.data, field_name)
            if isinstance(current, bool):
                if isinstance(value, bool):
                    setattr(self.data, field_name, value)
                continue
            if isinstance(current, str) and isinstance(value, str):
                setattr(self.data, field_name, value)

        return self.data

    def save(self, data: UserWorkspaceSettings | None = None) -> None:
        if data is not None:
            self.data = data

        self.storage_path.write_text(
            json.dumps(asdict(self.data), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
