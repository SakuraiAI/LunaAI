from __future__ import annotations

from dataclasses import dataclass

from app.core.user_settings import UserWorkspaceSettings


@dataclass(frozen=True, slots=True)
class ControlProfile:
    key: str
    label: str
    description: str
    agent_mode: str
    allow_app_launch: bool
    allow_path_open: bool
    allow_file_changes: bool


class SystemControlLayer:
    PROFILES: dict[str, ControlProfile] = {
        "observe": ControlProfile(
            key="observe",
            label="Observe",
            description="Luna can inspect context and reason, but local execution stays blocked.",
            agent_mode="block",
            allow_app_launch=False,
            allow_path_open=False,
            allow_file_changes=False,
        ),
        "assist": ControlProfile(
            key="assist",
            label="Assist",
            description="Luna can prepare and suggest actions, but every local step needs confirmation.",
            agent_mode="ask",
            allow_app_launch=True,
            allow_path_open=True,
            allow_file_changes=True,
        ),
        "operator": ControlProfile(
            key="operator",
            label="Operator",
            description="Luna can move fast and execute local actions immediately under the current workspace rules.",
            agent_mode="auto",
            allow_app_launch=True,
            allow_path_open=True,
            allow_file_changes=True,
        ),
    }

    def normalize_profile(self, profile_key: str) -> str:
        key = (profile_key or "operator").strip().lower()
        return key if key in self.PROFILES else "operator"

    def apply_profile(self, workspace: UserWorkspaceSettings, profile_key: str) -> UserWorkspaceSettings:
        profile = self.PROFILES[self.normalize_profile(profile_key)]
        workspace.system_control_profile = profile.key
        workspace.agent_execution_mode = profile.agent_mode
        workspace.allow_app_launch = profile.allow_app_launch
        workspace.allow_path_open = profile.allow_path_open
        workspace.allow_file_changes = profile.allow_file_changes
        return workspace

    def profile_summary(self, workspace: UserWorkspaceSettings) -> str:
        profile = self.PROFILES[self.normalize_profile(workspace.system_control_profile)]
        action_mode = str(workspace.agent_execution_mode or profile.agent_mode).strip().lower()
        capability_lines = [
            f"Profile: {profile.label}",
            profile.description,
            f"Execution mode: {action_mode}",
            f"App launch: {'enabled' if workspace.allow_app_launch else 'blocked'}",
            f"Path open: {'enabled' if workspace.allow_path_open else 'blocked'}",
            f"File changes: {'enabled' if workspace.allow_file_changes else 'blocked'}",
        ]
        return "\n".join(capability_lines)

    def list_profiles(self) -> list[dict[str, str]]:
        return [
            {
                "key": profile.key,
                "label": profile.label,
                "description": profile.description,
            }
            for profile in self.PROFILES.values()
        ]
