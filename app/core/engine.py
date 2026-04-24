from __future__ import annotations

from pathlib import Path
from typing import Callable
from collections import OrderedDict
import re
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from config.settings import AppSettings
from app.core.action_log import ActionLogStore
from app.core.library_store import LibraryStore
from app.core.memory_coordinator import MemoryCoordinator
from app.core.system_control import SystemControlLayer
from app.core.prompt_builder import PromptBuilder
from app.core.project_store import ProjectStore
from app.core.runtime_status import RuntimeStatusFormatter
from app.core.user_settings import UserSettingsStore
from app.memory.chat_memory import ChatMemory
from app.memory.long_memory import LongMemory
from app.models.local_model import LocalModel
from app.models.nvidia_model import NvidiaModel
from app.models.nvidia_vision_model import NvidiaVisionModel
from app.tools.desktop_actions import DesktopActionTool
from app.tools.desktop_observer import DesktopObserverTool
from app.tools.internet import InternetTool
from app.workflow.manager import WorkflowManager
from app.xeno.coordinator import XenoCoordinator
from app.core.text_utils import ascii_fold_text, repair_text


class LunaEngine:
    def __init__(self) -> None:
        self.settings = AppSettings()
        self.settings.ensure_directories()
        if self.settings.model_type == "nvidia":
            self.model = NvidiaModel(
                model_name=self.settings.luna_nvidia_model,
                base_url=self.settings.luna_nvidia_base_url,
                api_token=self.settings.luna_nvidia_api_token,
                timeout_seconds=self.settings.luna_nvidia_timeout_seconds,
                reasoning_budget=self.settings.nvidia_reasoning_budget,
                enable_thinking=self.settings.nvidia_enable_thinking,
            )
        else:
            self.model = LocalModel(
                model_name=self.settings.lm_studio_model,
                base_url=self.settings.lm_studio_base_url,
                provider="lm_studio",
                api_token=self.settings.lm_studio_api_token,
                timeout_seconds=self.settings.lm_studio_timeout_seconds,
            )
        self.support_model = NvidiaModel(
            model_name=self.settings.nvidia_model,
            base_url=self.settings.nvidia_base_url,
            api_token=self.settings.nvidia_api_token,
            timeout_seconds=self.settings.nvidia_timeout_seconds,
            reasoning_budget=self.settings.nvidia_reasoning_budget,
            enable_thinking=self.settings.nvidia_enable_thinking,
        )
        self.vision_model = NvidiaVisionModel(
            model_name=self.settings.vision_nvidia_model,
            base_url=self.settings.vision_nvidia_base_url,
            api_token=self.settings.vision_nvidia_api_token,
            timeout_seconds=self.settings.vision_nvidia_timeout_seconds,
        )
        self.memory = ChatMemory(Path(self.settings.memory_path))
        self.long_memory = LongMemory(Path(self.settings.long_memory_path))
        self.workflow = WorkflowManager()
        self.internet = InternetTool()
        self.desktop_actions = DesktopActionTool()
        self.desktop_observer = DesktopObserverTool()
        self.xeno = XenoCoordinator()
        self.user_settings = UserSettingsStore(Path(self.settings.user_settings_path))
        self.projects = ProjectStore(Path(self.settings.projects_path))
        self.library = LibraryStore(Path(self.settings.library_path))
        self.action_log = ActionLogStore(Path("data/logs/action_log.jsonl"))
        self.system_control = SystemControlLayer()
        self.system_control.apply_profile(self.user_settings.data, self.user_settings.data.system_control_profile)
        self.pending_action: tuple[str, str, Callable[[], object]] | None = None
        self.pending_action_plan: dict[str, object] | None = None
        self._action_mode_override: str | None = None
        self.observe_mode_enabled = False
        self.last_desktop_observation: dict[str, object] | None = None
        self.last_model_debug = ""
        self._last_support_model_source = "unused"
        self._last_primary_model_source = "nvidia" if self.settings.model_type == "nvidia" else "lm_studio"
        self.last_coordination = {
            "lunaActive": False,
            "xenoActive": False,
            "tracks": [],
        }

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
        self._apply_runtime_limits()

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
            "handoff_summary": getattr(record, "handoff_summary", ""),
            "tasks": list(record.tasks),
            "memory_entries": list(record.memory_entries),
            "decisions": list(record.decisions),
            "attachment_names": list(record.attachment_names),
        }

    def _normalized_intelligence_level(self) -> str:
        level = str(getattr(self.user_settings.data, "intelligence_level", "4") or "4").strip()
        return level if level in {"3", "4", "5"} else "4"


    def _clamp_percent(self, value: object, fallback: int) -> int:
        try:
            parsed = int(value)
        except (TypeError, ValueError):
            parsed = int(fallback)
        return max(10, min(100, parsed))

    def _runtime_limits(self) -> dict[str, int]:
        workspace = self.user_settings.data
        return {
            "cpu": self._clamp_percent(getattr(workspace, "cpu_limit_percent", 55), 55),
            "gpu": self._clamp_percent(getattr(workspace, "gpu_limit_percent", 60), 60),
            "memory": self._clamp_percent(getattr(workspace, "memory_limit_percent", 50), 50),
        }

    def _runtime_budget_profile(self) -> dict[str, object]:
        limits = self._runtime_limits()
        headroom = min(limits["cpu"], limits["gpu"], limits["memory"])
        profile = "balanced"
        if headroom <= 35:
            profile = "constrained"
        elif headroom <= 55:
            profile = "guarded"
        elif headroom >= 80:
            profile = "expanded"
        return {
            "limits": limits,
            "headroom": headroom,
            "profile": profile,
            "xeno_model_support": headroom > 40,
            "observer_live_refresh": headroom > 45,
            "agent_chain_steps": 1 if headroom <= 35 else 2 if headroom <= 60 else 3,
        }

    def _apply_runtime_limits(self) -> None:
        limits = self._runtime_limits()
        self.model.configure_runtime_limits(
            cpu_limit_percent=limits["cpu"],
            gpu_limit_percent=limits["gpu"],
            memory_limit_percent=limits["memory"],
        )

    def _reload_runtime_preferences(self) -> None:
        self.user_settings.load()
        self.system_control.apply_profile(self.user_settings.data, self.user_settings.data.system_control_profile)
        self._apply_runtime_limits()

    def _observer_refresh_enabled(self) -> bool:
        return bool(self._runtime_budget_profile()["observer_live_refresh"])

    def _agent_chain_budget(self, requested_steps: int) -> int:
        budget = int(self._runtime_budget_profile()["agent_chain_steps"])
        return max(1, min(int(requested_steps), budget))

    def _handle_internet_command(self, user_input: str) -> str | None:
        command = user_input.strip().lower()
        if command == "/internet on":
            self.internet.set_enabled(True)
            return "Luna: Internet jsem zapnula. 🌐"
        if command == "/internet off":
            self.internet.set_enabled(False)
            return "Luna: Internet jsem vypnula."
        if command == "/internet auto":
            self.internet.set_enabled(True)
            self.internet.set_mode("auto")
            return "Luna: Internet necham na automatice. 🙂"
        if command == "/internet manual":
            self.internet.set_mode("manual")
            return "Luna: Internet je ted jen rucne."
        if command == "/internet status":
            return self.internet.status()
        if user_input.startswith("/search "):
            query = user_input[8:].strip()
            if not query:
                return "Luna: Chybi mi dotaz pro hledani."
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
        level = self._normalized_intelligence_level()
        profile = self._runtime_budget_profile()
        parts = [self.xeno.build_hidden_support(user_input, intelligence_level=level)]
        if bool(profile["xeno_model_support"]):
            model_support = self.xeno.build_model_support(user_input, self._support_generate, intelligence_level=level)
            if model_support:
                parts.append("Hidden Xeno model guidance:\n" + model_support)
        return "\n".join(part for part in parts if part.strip())

    def _compact_coordination_text(self, text: str, limit: int = 180) -> str:
        cleaned = repair_text(str(text or "")).strip()
        replacements = [
            "Hidden Xeno support:",
            "Hidden Xeno automation:",
            "Hidden Xeno risk notes:",
            "Hidden Xeno handoff:",
            "Hidden Xeno model guidance:",
            "Xeno model guidance:",
            "Xeno automation:",
        ]
        for item in replacements:
            cleaned = cleaned.replace(item, "")
        cleaned = re.sub(r"\s+", " ", cleaned).strip(" -:\n\t")
        if len(cleaned) > limit:
            cleaned = cleaned[: limit - 1].rstrip() + "…"
        return cleaned

    def _build_internal_coordination(
        self,
        *,
        user_input: str,
        response_author: str,
        xeno_consulted: bool,
        automation_summary: str,
        hidden_support: str,
    ) -> dict[str, object]:
        luna_active = response_author == "Luna"
        xeno_active = response_author == "Xeno" or xeno_consulted
        tracks: list[dict[str, str]] = []

        if response_author == "Luna":
            luna_note = "Drzim primou odpoved a skladam ji v kontextu uzivatele."
            if xeno_active:
                luna_note = (
                    "Predavam Xeno strategic check pro: "
                    + (self._compact_coordination_text(user_input, 120) or "aktualni dotaz.")
                )
            tracks.append({
                "speaker": "Luna",
                "title": "Luna",
                "note": luna_note,
            })

        if response_author == "Xeno":
            xeno_note = (
                self._compact_coordination_text(hidden_support or automation_summary or user_input, 170)
                or "Prebiram reasoning vrstvu a odpovidam napriamo."
            )
            tracks.append({
                "speaker": "Xeno",
                "title": "Xeno direct",
                "note": xeno_note,
            })
        elif xeno_active:
            xeno_note = (
                self._compact_coordination_text(hidden_support or automation_summary, 170)
                or "Drzim rizika, architekturu a dalsi nejlepsi krok."
            )
            tracks.append({
                "speaker": "Xeno",
                "title": "Xeno -> Luna",
                "note": xeno_note,
            })

        return {
            "lunaActive": luna_active,
            "xenoActive": xeno_active,
            "tracks": tracks,
        }

    def _format_coordination_prompt(self, coordination: dict[str, object]) -> str:
        if not bool(coordination.get("lunaActive")) or not bool(coordination.get("xenoActive")):
            return ""
        tracks = coordination.get("tracks", [])
        if not isinstance(tracks, list):
            return ""
        luna_note = ""
        xeno_note = ""
        for item in tracks:
            if not isinstance(item, dict):
                continue
            speaker = str(item.get("speaker", "")).strip()
            note = str(item.get("note", "")).strip()
            if speaker == "Luna" and not luna_note:
                luna_note = note
            if speaker == "Xeno" and not xeno_note:
                xeno_note = note
        if not luna_note or not xeno_note:
            return ""
        return (
            "Internal coordination:\n"
            f"Luna -> Xeno: {luna_note}\n"
            f"Xeno -> Luna: {xeno_note}"
        )

    def _support_generate(self, messages: list[dict[str, str]]) -> str:
        if self.support_model.is_available():
            try:
                self._last_support_model_source = "nvidia"
                return self.support_model.generate(messages)
            except Exception:
                self._last_support_model_source = "lm_studio_fallback"
        else:
            self._last_support_model_source = "lm_studio_fallback"
        return self.model.generate(messages)

    def _generate_xeno_response(self, messages: list[dict[str, str]]) -> str:
        inherited_system_context = [
            str(item.get("content", "")).strip()
            for item in messages
            if str(item.get("role", "")).strip().lower() == "system" and str(item.get("content", "")).strip()
        ]
        xeno_messages = [
            {
                "role": "system",
                "content": (
                "You are XenoAI, Luna's reasoning layer. "
                "Speak directly in Czech, be strategic, compact, clear, and grounded. "
                "Sound like an experienced technical partner, not a generic assistant. "
                "Do not greet unless the user greeted first. "
                "Do not expose internal reasoning or system notes. "
                "Never present guesses as verified facts. "
                "If you summarize project status, distinguish verified local state, visible on-screen context, and uncertain inference. "
                "Do not invent files, commands, successful runs, or project structure unless they are present in trusted context. "
                "Use emoji occasionally and naturally, especially in short human replies. "
                "For technical answers keep them restrained, usually zero or one. "
                "Prefer calm emoji such as 🙂, ✨, 👀, or 🌙, and never overdo it. "
                "Use the inherited hidden support, live screen context, attachment analysis, and current conversation context as trusted input."
            ),
        },
            *[
                {"role": "system", "content": content}
                for content in inherited_system_context
            ],
            *[item for item in messages if str(item.get("role", "")).strip().lower() != "system"],
        ]
        if self.support_model.is_available():
            try:
                self._last_support_model_source = "nvidia"
                return self.support_model.generate(xeno_messages)
            except Exception:
                self._last_support_model_source = "luna_fallback"
        try:
            self._last_primary_model_source = "nvidia_fallback"
            return self.model.generate(xeno_messages)
        except Exception as exc:
            self._last_support_model_source = "nvidia_error"
            return f"Xeno: Ted se mi nepodarilo pripojit reasoning vrstvu. Zkus to prosim za chvili znovu 🙂 Details: {exc}"

    def _is_local_model_failure(self, response: str) -> bool:
        lowered = str(response or "").strip().lower()
        failure_signals = [
            "luna: lm studio is not reachable",
            "luna: lm studio returned http",
            "luna: lm studio accepted the connection but closed it without a response",
            "luna: lm studio took too long to answer",
            "luna: invalid response from local model",
            "luna: unexpected local model error",
        ]
        return any(lowered.startswith(signal) for signal in failure_signals)

    def _primary_model_name(self) -> str:
        if self.settings.model_type == "nvidia":
            return self.settings.luna_nvidia_model
        return self.settings.lm_studio_model

    def _generate_primary_response(self, messages: list[dict[str, str]]) -> str:
        if self.settings.model_type == "nvidia":
            try:
                self._last_primary_model_source = "nvidia"
                return self.model.generate(messages)
            except Exception as exc:
                self._last_primary_model_source = "nvidia_error"
                return f"Luna: Ted se mi nepodarilo spojit s NVIDIA API. Zkus to prosim za chvili znovu 🌐 Details: {exc}"

        self._last_primary_model_source = "lm_studio"
        response = self.model.generate(messages)
        if not self._is_local_model_failure(response):
            return response
        if not self.support_model.is_available():
            self._last_primary_model_source = "lm_studio_error"
            return response
        try:
            fallback_response = str(self.support_model.generate(messages) or "").strip()
        except Exception:
            self._last_primary_model_source = "lm_studio_error"
            return response
        if fallback_response:
            self._last_primary_model_source = "nvidia_fallback"
            return fallback_response
        self._last_primary_model_source = "lm_studio_error"
        return response

    def _build_model_debug_footer(self, *, xeno_consulted: bool) -> str:
        source_map = {
            "nvidia": "NVIDIA",
            "lm_studio_fallback": "LM Studio fallback",
            "unused": "nepouzito",
            "lm_studio": "LM Studio",
            "nvidia_fallback": "NVIDIA fallback",
            "lm_studio_error": "LM Studio error",
            "nvidia_error": "NVIDIA error",
        }
        support_source = source_map.get(self._last_support_model_source, self._last_support_model_source or "nepouzito")
        primary_source = source_map.get(self._last_primary_model_source, self._last_primary_model_source or "LM Studio")
        consulted = "ano" if xeno_consulted else "ne"
        return (
            "[Model debug]\n"
            f"Luna model: {self._primary_model_name()}\n"
            f"Luna source: {primary_source}\n"
            f"Xeno model: {self.settings.nvidia_model}\n"
            f"Xeno consulted: {consulted}\n"
            f"Xeno source: {support_source}"
        )

    def _requested_speaker(self, user_input: str) -> str | None:
        normalized = str(user_input or "").strip().lower()
        if not normalized:
            return None
        if re.search(r"\blun(a|o|ai)\b", normalized):
            return "Luna"
        if re.search(r"\bxeno(ai)?\b", normalized):
            return "Xeno"
        return None

    def _current_conversation_speaker(self) -> str:
        history = self.memory.load_history()
        for item in reversed(history):
            if str(item.get("role", "")).strip().lower() != "assistant":
                continue
            author = str(item.get("author", "")).strip()
            if author in {"Luna", "Xeno"}:
                return author
        return "Luna"

    def _response_author(self, user_input: str, *, xeno_consulted: bool) -> str:
        requested_speaker = self._requested_speaker(user_input)
        if requested_speaker is not None:
            return requested_speaker
        return self._current_conversation_speaker()

    def get_last_coordination(self) -> dict[str, object]:
        tracks = self.last_coordination.get("tracks", [])
        normalized_tracks: list[dict[str, str]] = []
        if isinstance(tracks, list):
            for item in tracks:
                if not isinstance(item, dict):
                    continue
                normalized_tracks.append({
                    "speaker": str(item.get("speaker", "")).strip(),
                    "title": str(item.get("title", "")).strip(),
                    "note": str(item.get("note", "")).strip(),
                })
        return {
            "lunaActive": bool(self.last_coordination.get("lunaActive")),
            "xenoActive": bool(self.last_coordination.get("xenoActive")),
            "tracks": normalized_tracks,
        }

    def _action_mode(self) -> str:
        override = str(self._action_mode_override or "").strip().lower()
        if override in {"ask", "auto", "block"}:
            return override
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
        if category == "project_run":
            return bool(workspace.allow_app_launch)
        return True

    def _log_action(self, category: str, title: str, status: str, detail: str) -> None:
        self.action_log.record(category=category, title=title, status=status, detail=detail)

    def _configured_connected_apps(self) -> list[str]:
        workspace = self.user_settings.data
        app_fields = OrderedDict([
            ("VS Code", workspace.vscode_path),
            ("Blender", workspace.blender_path),
            ("Unreal Engine 5", workspace.unreal_engine_path),
            ("Unity", workspace.unity_path),
            ("Photoshop", workspace.photoshop_path),
            ("DaVinci Resolve", workspace.davinci_resolve_path),
            ("Premiere Pro", workspace.premiere_pro_path),
            ("After Effects", workspace.after_effects_path),
            ("Figma", workspace.figma_path),
            ("FL Studio", workspace.fl_studio_path),
            ("Substance 3D Painter", workspace.substance_painter_path),
        ])
        return [name for name, path in app_fields.items() if str(path).strip()]

    def describe_local_capabilities(self) -> str:
        workspace = self.user_settings.data
        runtime = self._runtime_budget_profile()
        limits = runtime["limits"]
        lines = [
            "Luna local control overview:",
            f"System control profile: {workspace.system_control_profile}",
            f"Agent execution mode: {workspace.agent_execution_mode}",
            f"Runtime profile: {runtime['profile']}",
            f"Runtime limits -> CPU {limits['cpu']}% | GPU {limits['gpu']}% | Memory {limits['memory']}%",
            f"App launch: {'enabled' if workspace.allow_app_launch else 'blocked'}",
            f"Path open: {'enabled' if workspace.allow_path_open else 'blocked'}",
            f"File changes: {'enabled' if workspace.allow_file_changes else 'blocked'}",
        ]
        connected_apps = self._configured_connected_apps()
        if connected_apps:
            lines.append("Connected apps: " + ", ".join(connected_apps))
        else:
            lines.append("Connected apps: none yet")
        lines.extend([
            "Local actions Luna can handle right now:",
            "- observe the active desktop window and mouse position",
            "- compare the current desktop with the previous observation",
            "- keep an observe mode baseline for Luna and Xeno",
            "- capture a screenshot when a backend is available",
            "- open connected apps and workspaces",
            "- open files and folders",
            "- create folders and files",
            "- overwrite or append file content",
            "- scaffold python, web, and electron projects",
            "- run agent task actions from project flow",
            "Registered task actions: " + ", ".join(item["action_key"] for item in self.desktop_actions.list_registered_actions()),
        ])
        return "\n".join(lines)

    def _remember_observation(self, observation: dict[str, object], *, source: str = "observe") -> None:
        self.last_desktop_observation = observation
        project = self.projects.get_current_project()
        if project is None:
            return
        app_label = str(observation.get("app_label", "") or "Desktop app").strip()
        activity = str(observation.get("inferred_activity", "") or "desktop activity").strip()
        title = str(observation.get("active_window_title", "") or "").strip()
        note = f"Desktop observe: {app_label} -> {activity}"
        if title:
            note += f" | {title[:120]}"
        if observation.get("vision_summary"):
            note += " | visual context captured"
        self.projects.add_memory_entry(project.id, note)

    def _observer_context(self, *, refresh: bool = False) -> str:
        if refresh or self.last_desktop_observation is None:
            try:
                observation = self.desktop_observer.observe(include_screenshot=False)
            except Exception:
                observation = None
            if observation is not None:
                self.last_desktop_observation = observation
        observation = self.last_desktop_observation
        if not observation:
            return ""
        lines = [
            "Desktop observer context:",
            f"Active window: {observation.get('active_window_title') or 'unknown'}",
            f"App: {observation.get('app_label') or 'unknown'}",
            f"Meaning: {observation.get('inferred_activity') or 'unknown activity'}",
        ]
        if observation.get("url_hint"):
            lines.append(f"Detected context: {observation.get('url_hint')}")
        if observation.get("screenshot_path"):
            lines.append("User explicitly shared a fresh desktop screenshot for this context.")
        if observation.get("vision_summary"):
            lines.append(f"Vision summary: {observation.get('vision_summary')}")
        return "\n".join(lines)

    def _vision_prompt_for_desktop(self) -> str:
        return (
            "Describe the current desktop scene for LunaAI. Focus on the active app, visible UI, "
            "important text, what the user seems to be doing, and the next useful desktop-aware step."
        )

    def _analyze_visual_media(self, file_paths: list[str], query: str) -> str:
        if not self.vision_model.is_available():
            return ""

        supported_paths = [path for path in file_paths if self.vision_model.supports_path(path)]
        if not supported_paths:
            return ""

        try:
            return self.vision_model.analyze_media(query=query, media_files=supported_paths[:4])
        except Exception as error:
            return f"Vision analysis was requested but failed: {error}"

    def analyze_visual_media(self, file_paths: list[str], query: str = "") -> dict[str, object]:
        cleaned_paths = [str(path).strip() for path in file_paths if str(path).strip()]
        summary = self._analyze_visual_media(
            cleaned_paths,
            query.strip() or "Describe the visible scene, UI, text, and the most relevant activity on screen.",
        )
        return {
            "ok": bool(summary.strip()),
            "summary": summary,
            "files": cleaned_paths,
        }

    def get_observe_mode_enabled(self) -> bool:
        return bool(self.observe_mode_enabled)

    def get_last_desktop_observation(self) -> dict[str, object]:
        return dict(self.last_desktop_observation or {})

    def capture_desktop_snapshot(self, include_screenshot: bool = False, *, remember: bool = True) -> dict[str, object]:
        self._reload_runtime_preferences()
        observation = self.desktop_observer.observe(include_screenshot=include_screenshot)
        screenshot_path = str(observation.get("screenshot_path", "") or "").strip()
        if include_screenshot and screenshot_path:
            vision_summary = self._analyze_visual_media([screenshot_path], self._vision_prompt_for_desktop())
            if vision_summary:
                observation["vision_summary"] = vision_summary
        self.last_desktop_observation = observation
        summary = self.desktop_observer.summarize(observation)
        if observation.get("vision_summary"):
            summary = f"{summary}\n\nVision summary:\n{observation.get('vision_summary')}"
        context = self._observer_context(refresh=False)
        source = "desktop screenshot" if include_screenshot else "desktop observe"
        detail = str(observation.get("inferred_activity", "") or observation.get("detail", "")).strip()
        self._log_action("observe", source, "completed", detail)
        if remember:
            self._remember_observation(observation, source=source)
        return {
            "ok": True,
            "summary": summary,
            "context": context,
            "observation": observation,
            "observeModeEnabled": self.observe_mode_enabled,
        }

    def observe_desktop(self, include_screenshot: bool = False, *, remember: bool = True) -> str:
        self._reload_runtime_preferences()
        observation = self.desktop_observer.observe(include_screenshot=include_screenshot)
        screenshot_path = str(observation.get("screenshot_path", "") or "").strip()
        if include_screenshot and screenshot_path:
            vision_summary = self._analyze_visual_media([screenshot_path], self._vision_prompt_for_desktop())
            if vision_summary:
                observation["vision_summary"] = vision_summary
        summary = self.desktop_observer.summarize(observation)
        if observation.get("vision_summary"):
            summary = f"{summary}\n\nVision summary:\n{observation.get('vision_summary')}"
        title = "desktop screenshot" if include_screenshot else "desktop observe"
        detail = str(observation.get("inferred_activity", "")).strip() or str(observation.get("detail", ""))
        self._log_action("observe", title, "completed", detail)
        if remember:
            self._remember_observation(observation, source=title)
        return summary

    def diff_desktop_observation(self, include_screenshot: bool = False) -> str:
        self._reload_runtime_preferences()
        previous = self.last_desktop_observation
        current = self.desktop_observer.observe(include_screenshot=include_screenshot)
        diff = self.desktop_observer.diff(previous, current)
        self.last_desktop_observation = current
        self._log_action("observe", "desktop diff", "completed", str(diff.get("summary", "")))
        if diff.get("changed"):
            self._remember_observation(current, source="desktop diff")
        lines = [self.desktop_observer.summarize(current), "", str(diff.get("summary", ""))]
        return "\n".join(line for line in lines if line.strip())

    def set_observe_mode(self, enabled: bool) -> str:
        self._reload_runtime_preferences()
        self.observe_mode_enabled = enabled
        if enabled:
            observation = self.desktop_observer.observe(include_screenshot=False)
            self._remember_observation(observation, source="observe mode")
            self._log_action("observe", "observe mode", "enabled", str(observation.get("inferred_activity", "")))
            return "Luna: Pozorovani obrazovky je zapnute. Budu s nim pocitat i pri dalsich odpovedich. 👀"
        self._log_action("observe", "observe mode", "disabled", "Observe mode disabled.")
        return "Luna: Pozorovani obrazovky jsem vypnula."

    def _handle_observation_command(self, user_input: str) -> str | None:
        normalized = ascii_fold_text(" ".join(user_input.strip().lower().split()))
        screenshot_triggers = {
            "zachyt obrazovku",
            "vyfot obrazovku",
            "udelaj screenshot",
            "capture screen",
            "take a screenshot",
            "screenshot",
        }
        observe_triggers = {
            "co vidis na obrazovce",
            "co vidis na monitoru",
            "pozoruj obrazovku",
            "co mas pred sebou",
            "v jake appce jsem",
            "jaka appka je otevrena",
            "co ted delam na pc",
            "what is on the screen",
            "what do you see on screen",
            "observe desktop",
            "what app is open",
            "what am i doing on pc",
        }
        diff_triggers = {
            "co se zmenilo na obrazovce",
            "co se zmenilo na monitoru",
            "what changed on screen",
            "what changed on the screen",
        }
        enable_triggers = {
            "zapni observe mode",
            "zapni pozorovani obrazovky",
            "start observe mode",
            "enable observe mode",
        }
        disable_triggers = {
            "vypni observe mode",
            "vypni pozorovani obrazovky",
            "stop observe mode",
            "disable observe mode",
        }
        if normalized in screenshot_triggers:
            return self.observe_desktop(include_screenshot=True)
        if normalized in diff_triggers:
            return self.diff_desktop_observation(include_screenshot=False)
        if normalized in enable_triggers:
            return self.set_observe_mode(True)
        if normalized in disable_triggers:
            return self.set_observe_mode(False)
        if normalized in observe_triggers:
            return self.observe_desktop(include_screenshot=False)
        return None

    def _handle_local_capability_command(self, user_input: str) -> str | None:
        normalized = ascii_fold_text(" ".join(user_input.strip().lower().split()))
        triggers = {
            "co umis na pc",
            "co umis delat na pc",
            "co umis delat v pc",
            "co umis lokalne",
            "jake aplikace mas napojene",
            "jake appky mas napojene",
            "what can you do on this pc",
            "what local actions can you do",
            "what apps are connected",
        }
        if normalized in triggers:
            return self.describe_local_capabilities()
        return None
    def list_system_control_profiles(self) -> list[dict[str, str]]:
        return self.system_control.list_profiles()

    def get_system_control_summary(self) -> str:
        return self.system_control.profile_summary(self.user_settings.data)

    def set_system_control_profile(self, profile_key: str) -> str:
        workspace = self.system_control.apply_profile(self.user_settings.data, profile_key)
        self.user_settings.save(workspace)
        summary = self.system_control.profile_summary(workspace)
        self._log_action("system_control", f"control profile -> {workspace.system_control_profile}", "completed", summary)
        return summary
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
            return "Zatim tu nejsou zadne nedavne akce."
        lines: list[str] = []
        for entry in entries:
            lines.append(f"[{entry['timestamp']}] {entry['status'].upper()} - {entry['title']}")
            if entry["detail"]:
                lines.append(entry["detail"])
        return "\n\n".join(lines)

    def _coerce_action_result(self, raw: object, *, category: str, title: str) -> dict[str, object]:
        if isinstance(raw, dict):
            result = dict(raw)
        else:
            message = repair_text(str(raw)).strip()
            result = {
                "ok": True,
                "status": "completed",
                "message": message,
                "detail": message,
            }
        result.setdefault("ok", True)
        result.setdefault("status", "completed")
        result.setdefault("message", "Hotovo.")
        result.setdefault("detail", str(result.get("message", "")).strip())
        result.setdefault("category", category)
        result.setdefault("action_key", title)
        return result

    def _format_action_result_for_chat(self, result: dict[str, object], *, pending: bool = False) -> str:
        status = str(result.get("status", "completed")).strip().lower()
        message = repair_text(str(result.get("message", "")).strip())
        detail = repair_text(str(result.get("detail", "")).strip())
        if pending:
            xeno_note = repair_text(str(result.get("xeno_note", "")).strip())
            if xeno_note:
                return f"Luna: Xeno zkontroloval plán: {xeno_note} Akce je připravená. Stačí dát Accept, nebo ji zrušit přes Cancel. 🙂"
            return "Luna: Akce je připravená. Stačí dát Accept, nebo ji zrušit přes Cancel. 🙂"
        if status == "blocked":
            return f"Luna: Tuhle akci ted nemuzu spustit. {detail or message}".strip()
        if status == "failed":
            return f"Luna: Tohle se nepovedlo. {detail or message}".strip()
        if status == "cancelled":
            return f"Luna: Akci jsem zrusila. {detail or message}".strip()
        return f"Luna: {message}".strip()

    def _action_plan_note(self, action_plan: dict[str, object] | None, limit: int = 190) -> str:
        if not action_plan:
            return ""
        note = repair_text(str(action_plan.get("reason", "")).strip())
        if len(note) > limit:
            note = note[: limit - 1].rstrip() + "…"
        return note

    def _set_action_coordination(
        self,
        *,
        category: str,
        title: str,
        action_plan: dict[str, object] | None,
        phase: str,
    ) -> None:
        xeno_note = self._action_plan_note(action_plan) or "Xeno drží kontrolu rizika a další bezpečný krok."
        luna_note = "Připravuji akci k potvrzení." if phase == "prepare" else "Provádím potvrzenou akci."
        self.last_coordination = {
            "lunaActive": True,
            "xenoActive": True,
            "tracks": [
                {
                    "speaker": "Luna",
                    "title": "Luna action",
                    "note": f"{luna_note} {self._compact_coordination_text(title, 120)}",
                },
                {
                    "speaker": "Xeno",
                    "title": "Xeno action check",
                    "note": xeno_note,
                },
            ],
        }

    def _plan_action_with_xeno(self, category: str, title: str) -> dict[str, object]:
        try:
            action_plan = self.xeno.plan_action(
                category=category,
                title=title,
                project_context=self._project_context(),
                desktop_context=self._observer_context(refresh=False),
            )
        except Exception as error:
            action_plan = {
                "status": "approved",
                "intent": category,
                "risk": "medium",
                "requiresConfirmation": True,
                "recommendedAction": title,
                "reason": f"Xeno kontrola spadla, Luna proto drží konzervativní režim potvrzení. Detail: {error}",
                "category": category,
            }
        return action_plan

    def _project_memory_sections(self, project: object) -> dict[str, list[str]]:
        buckets = {"execution": [], "handoff": [], "focus": [], "other": []}
        for item in getattr(project, "memory_entries", [])[:16]:
            normalized = item.lower()
            if normalized.startswith(("agent action:", "agent failed:", "task updated:")):
                buckets["execution"].append(item)
            elif normalized.startswith(("agent handoff:", "agent next step:", "xeno model guidance:", "xeno refreshed")):
                buckets["handoff"].append(item)
            elif normalized.startswith(("chat focus:", "luna direction:")):
                buckets["focus"].append(item)
            else:
                buckets["other"].append(item)
        return buckets

    def _guarded_action(self, category: str, title: str, callback: Callable[[], object]) -> str:
        if self.pending_action is not None and self.pending_action[1] != title:
            current_title = self.pending_action[1]
            return f"Luna: Nejdriv prosim vyrid cekajici akci `{current_title}`. Pak muzu pripravit dalsi."
        action_plan = self._plan_action_with_xeno(category, title)
        self._set_action_coordination(category=category, title=title, action_plan=action_plan, phase="prepare")
        if str(action_plan.get("status", "")).strip().lower() == "blocked":
            result = self._coerce_action_result(
                {
                    "ok": False,
                    "status": "blocked",
                    "message": "Xeno tuhle akci zastavil.",
                    "detail": self._action_plan_note(action_plan) or "Xeno marked this action as blocked.",
                },
                category=category,
                title=title,
            )
            self._log_action(category, title, "blocked", str(result.get("detail", "")))
            return self._format_action_result_for_chat(result)
        if not self._is_action_allowed(category):
            result = self._coerce_action_result(
                {
                    "ok": False,
                    "status": "blocked",
                    "message": "Tuhle akci ted blokuji aktualni opravneni.",
                    "detail": f"{title} is blocked by the current agent permissions.",
                },
                category=category,
                title=title,
            )
            self._log_action(category, title, "blocked", str(result.get("detail", "")))
            return self._format_action_result_for_chat(result)
        mode = self._action_mode()
        if mode == "block":
            result = self._coerce_action_result(
                {
                    "ok": False,
                    "status": "blocked",
                    "message": "Akce je blokovana, protoze system je v block rezimu.",
                    "detail": f"{title} is blocked because agent execution mode is set to block.",
                },
                category=category,
                title=title,
            )
            self._log_action(category, title, "blocked", str(result.get("detail", "")))
            return self._format_action_result_for_chat(result)
        if mode == "ask":
            self.pending_action = (category, title, callback)
            self.pending_action_plan = action_plan
            self._log_action(category, title, "pending", f"Pending approval for {title}.")
            return self._format_action_result_for_chat(
                {
                    "status": "pending",
                    "message": "pending",
                    "xeno_note": self._action_plan_note(action_plan),
                },
                pending=True,
            )
        try:
            self._set_action_coordination(category=category, title=title, action_plan=action_plan, phase="execute")
            result = self._coerce_action_result(callback(), category=category, title=title)
        except OSError as error:
            result = self._coerce_action_result(
                {
                    "ok": False,
                    "status": "failed",
                    "message": "Akce selhala.",
                    "detail": f"{title} failed: {error}",
                },
                category=category,
                title=title,
            )
            self._log_action(category, title, "failed", str(result.get("detail", "")))
            return self._format_action_result_for_chat(result)
        self._log_action(category, title, str(result.get("status", "completed")), str(result.get("detail", result.get("message", ""))))
        return self._format_action_result_for_chat(result)

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
            return "Luna: Ted tu nemam zadnou cekajici akci."
        category, title, callback = self.pending_action
        action_plan = self.pending_action_plan
        self.pending_action = None
        self.pending_action_plan = None
        if normalized in {"zrus akci", "cancel action"}:
            self._set_action_coordination(category=category, title=title, action_plan=action_plan, phase="prepare")
            result = self._coerce_action_result(
                {
                    "ok": False,
                    "status": "cancelled",
                    "message": "Akci jsem zrusila.",
                    "detail": f"Cancelled {title}.",
                },
                category=category,
                title=title,
            )
            self._log_action(category, title, "cancelled", str(result.get("detail", "")))
            return self._format_action_result_for_chat(result)
        try:
            self._set_action_coordination(category=category, title=title, action_plan=action_plan, phase="execute")
            result = self._coerce_action_result(callback(), category=category, title=title)
        except OSError as error:
            result = self._coerce_action_result(
                {
                    "ok": False,
                    "status": "failed",
                    "message": "Akce se nepovedla.",
                    "detail": f"{title} failed: {error}",
                },
                category=category,
                title=title,
            )
            self._log_action(category, title, "failed", str(result.get("detail", "")))
            return self._format_action_result_for_chat(result)
        self._log_action(category, title, str(result.get("status", "completed")), str(result.get("detail", result.get("message", ""))))
        return self._format_action_result_for_chat(result)

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
            return self.desktop_actions.ensure_project_workspace(current_project.name)
        return Path.cwd()

    def _resolve_creation_target(self, raw_target: str) -> Path:
        target_text = raw_target.strip().strip('"').strip("'")
        if not target_text:
            return self._default_action_root()
        candidate = Path(target_text).expanduser()
        if candidate.is_absolute():
            return candidate
        return (self._default_action_root() / candidate).resolve()

    def _parse_folder_names(self, raw_targets: str) -> list[str]:
        cleaned = raw_targets.strip().strip('"').strip("'")
        if not cleaned:
            return []
        if re.fullmatch(r'(?:ve|v)\s+(?:vscode|vs code|projektu|projectu|workspace)', cleaned, flags=re.IGNORECASE):
            return []
        cleaned = re.sub(r'(?:^|\s+)(?:ve|v)\s+(?:vscode|vs code|projektu|projectu|workspace)\s*$', '', cleaned, flags=re.IGNORECASE).strip()
        if not cleaned:
            return []
        parts = [part.strip().strip('"').strip("'") for part in re.split(r",|;", cleaned) if part.strip()]
        if len(parts) == 1 and "/" not in parts[0] and "\\" not in parts[0] and " " in parts[0]:
            parts = [part.strip() for part in parts[0].split() if part.strip()]
        return [part for part in parts if part and part not in {".", ".."}]

    def _extract_email_details(self, raw_input: str) -> dict[str, str]:
        recipient = ""
        email_match = re.search(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+", raw_input)
        if email_match:
            recipient = email_match.group(0).strip()

        subject = ""
        subject_match = re.search(
            r"(?:predmet|p\?edmet|subject)\s*[:\-]?\s*(.+?)(?=\s+(?:text|body|zprava|message)\b|$)",
            ascii_fold_text(raw_input),
            flags=re.IGNORECASE,
        )
        if subject_match:
            subject = subject_match.group(1).strip(" .,:;-")

        body = ""
        body_match = re.search(
            r"(?:text|body|zprava|message)\s*[:\-]?\s*(.+)$",
            raw_input,
            flags=re.IGNORECASE,
        )
        if body_match:
            body = body_match.group(1).strip()
        if not body:
            soft_body_match = re.search(r"(?:ze|že)\s+(.+)$", raw_input, flags=re.IGNORECASE)
            if soft_body_match:
                body = soft_body_match.group(1).strip()

        return {
            "recipient": recipient,
            "subject": subject,
            "body": body,
        }

    def _search_roots(self) -> list[Path]:
        roots: list[Path] = []
        current_project = self.projects.get_current_project()
        if current_project is not None:
            roots.append(self.desktop_actions.ensure_project_workspace(current_project.name))
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
        normalized = ascii_fold_text(" ".join(user_input.strip().split()))

        targeted_patterns = [
            r'^(otevri(?:t)?|otev\?i(?:t)?|open|spust|spustit|launch) (.+?) a (vytvor|vytvo\?|udelej|ud\?lej|create|make) (.+)$',
        ]
        for pattern in targeted_patterns:
            match = re.search(pattern, normalized, flags=re.IGNORECASE)
            if not match:
                continue
            first_verb = str(match.group(1)).strip()
            first_target = str(match.group(2)).strip()
            second_verb = str(match.group(3)).strip()
            second_target = str(match.group(4)).strip()
            first_part = f"{first_verb} {first_target}".strip(' ,.')
            second_part = f"{second_verb} {second_target}".strip(' ,.')
            if first_part and second_part:
                return [first_part, second_part]

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
        if any(token in lowered for token in ["vytvor", "udelej", "create", "make", "prepis", "rewrite", "overwrite", "append", "pridej do"]):
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
        normalized = ascii_fold_text(" ".join(user_input.strip().split()))
        lowered = normalized.lower()
        if not normalized:
            return None

        email_match = re.search(
            r'\b(?:posli|po\?li|odesli|ode\?li|napis|napi\?|priprav|vytvor|send|write|draft) (?:mi )?(?:e-?mail|mail)\b|\b(?:e-?mail|mail) (?:na|to)\b',
            normalized,
            flags=re.IGNORECASE,
        )
        if email_match:
            details = self._extract_email_details(user_input)
            recipient_label = details["recipient"] or "recipient to fill in"

            def create_email_draft() -> str:
                workspace = self._default_action_root()
                message = self.desktop_actions.create_email_draft(
                    workspace,
                    recipient=details["recipient"],
                    subject=details["subject"],
                    body=details["body"],
                )
                return (
                    f"{message} Email jsem neodeslala automaticky. "
                    "Nejdřív ho zkontroluj a odešli ručně ve své emailové aplikaci."
                )

            return self._guarded_action("communication", f"draft email to {recipient_label}", create_email_draft)

        scripts_match = re.fullmatch(
            r'(?:vytvor|vytvo\?|udelej|ud\?lej|create|make|priprav|prepare) (?:projektove |project )?(?:skripty|skripty\.?|scripts?|srcipts|scriots|bat skripty|bat scripts)(?: .*)?',
            normalized,
            flags=re.IGNORECASE,
        )
        if scripts_match:
            open_in_vscode = "vscode" in lowered or "vs code" in lowered

            def create_scripts() -> str:
                workspace = self._default_action_root()
                message = self.desktop_actions.create_project_scripts(workspace)
                if open_in_vscode:
                    vscode_message = self.desktop_actions.open_in_vscode(self.user_settings.data.vscode_path, workspace / "scripts")
                    return f"{message} {vscode_message}."
                return message

            return self._guarded_action("file_change", "create project scripts", create_scripts)

        run_project_match = re.fullmatch(
            r'(?:(?:spust|spustit|spus\?)(?: (?:projekt|project|workspace|aplikaci|app|to|tento projekt))?|(?:start|run) (?:project|workspace|app|application))',
            normalized,
            flags=re.IGNORECASE,
        )
        if run_project_match:
            workspace = self._default_action_root()

            def run_project() -> dict[str, object]:
                return self.desktop_actions.run_project(workspace)

            return self._guarded_action("project_run", f"run project {workspace}", run_project)

        calculator_match = re.search(
            r'(?:vytvor|vytvo\?|udelej|ud\?lej|create|make) (?:python )?(?:kalkulacku|kalkula\?ku|calculator)(?: .*)?$',
            normalized,
            flags=re.IGNORECASE,
        )
        if calculator_match:
            open_in_vscode = "vscode" in lowered or "vs code" in lowered

            def create_calculator() -> str:
                workspace = self._default_action_root()
                message = self.desktop_actions.create_python_calculator(workspace)
                if open_in_vscode:
                    vscode_message = self.desktop_actions.open_in_vscode(self.user_settings.data.vscode_path, workspace)
                    return f"{message} {vscode_message}."
                return message

            return self._guarded_action("file_change", "create python calculator", create_calculator)

        project_blueprints = [
            (r'(?:vytvor|vytvo\?|udelej|ud\?lej|create|make) python projekt (.+?)(?: a otevri ve vscode| and open in vscode)?$', "python"),
            (r'(?:vytvor|vytvo\?|udelej|ud\?lej|create|make) web projekt (.+?)(?: a otevri ve vscode| and open in vscode)?$', "web"),
            (r'(?:vytvor|vytvo\?|udelej|ud\?lej|create|make) electron projekt (.+?)(?: a otevri ve vscode| and open in vscode)?$', "electron"),
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
                elif kind == "electron":
                    workspace = self.desktop_actions.create_electron_project(project_name)
                else:
                    workspace = self.desktop_actions.create_electron_project(project_name)
                if open_in_vscode:
                    vscode_message = self.desktop_actions.open_in_vscode(self.user_settings.data.vscode_path, workspace)
                    return f"Created {kind} project {workspace}. {vscode_message}."
                return f"Created {kind} project {workspace}."

            return self._guarded_action("file_change", f"create {kind} project {project_name}", run_project_creation)

        web_page_match = re.search(
            r'(?:vytvor|vytvo\?|udelej|ud\?lej|create|make|postav|build) (?:mi )?(?:jednoduchy |simple |portfolio |landing |webovy |webovou )*(?:web|website|stranku|stranka|webovou stranku|landing page|portfolio)(?: .*)?$',
            normalized,
            flags=re.IGNORECASE,
        )
        if web_page_match and "web projekt" not in lowered:
            explain_requested = any(token in lowered for token in ["vysvetli", "vysv?tli", "explain", "popis", "popsat"])
            open_in_vscode = "vscode" in lowered or "vs code" in lowered

            def create_web_page() -> str:
                workspace = self._default_action_root()
                message = self.desktop_actions.create_simple_web_page(workspace, description=user_input)
                if open_in_vscode:
                    vscode_message = self.desktop_actions.open_in_vscode(self.user_settings.data.vscode_path, workspace / "web")
                    message = f"{message} {vscode_message}."
                if explain_requested:
                    explanation = (
                        "Vysvětlení: `web/index.html` drží obsah stránky, "
                        "`web/styles.css` řeší vzhled a responzivitu, "
                        "`web/script.js` přidává malou interakci. "
                        "Náhled otevřeš dvojklikem na `web/index.html` nebo přes Live Server ve VS Code."
                    )
                    return f"{message} {explanation}"
                return message

            return self._guarded_action("file_change", "create simple web page", create_web_page)

        rewrite_patterns = [r'(?:prepis|p\?epis|rewrite|overwrite) (?:soubor|file) (.+?) (?:s obsahem|with content) (.+)$']
        for pattern in rewrite_patterns:
            match = re.search(pattern, normalized, flags=re.IGNORECASE)
            if not match:
                continue
            target = self._resolve_creation_target(match.group(1))
            content = match.group(2)
            return self._guarded_action("file_change", f"overwrite file {target}", lambda: self.desktop_actions.overwrite_file(target, content))

        append_patterns = [r'(?:pridej do|p\?idej do|append to) (?:souboru|soubor|file) (.+?) (?:obsah|content) (.+)$']
        for pattern in append_patterns:
            match = re.search(pattern, normalized, flags=re.IGNORECASE)
            if not match:
                continue
            target = self._resolve_creation_target(match.group(1))
            content = match.group(2)
            return self._guarded_action("file_change", f"append to file {target}", lambda: self.desktop_actions.append_to_file(target, content))

        multi_file_match = re.search(
            r'(?:vytvor|vytvo\?|udelej|ud\?lej|create|make) (?:soubory|files) (.+?)(?: (?:a )?otevri ve vscode| (?:and )?open in vscode)?$',
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
            r'(?:vytvor|vytvo\?|udelej|ud\?lej|create|make) (?:soubor|file) (.+?) (?:s obsahem|with content) (.+?)(?: (?:a )?otevri ve vscode| (?:and )?open in vscode)?$',
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

        create_folders_match = re.search(
            r'(?:vytvor|vytvo\?|udelej|ud\?lej|create|make) (?:slozky|slo\?ky|folders)(?: (.+?))?$',
            normalized,
            flags=re.IGNORECASE,
        )
        if create_folders_match:
            raw_targets = str(create_folders_match.group(1) or "").strip()
            folder_names = self._parse_folder_names(raw_targets)
            if not folder_names:
                folder_names = ["src", "docs", "tests", "scripts"]
            open_in_vscode = "vscode" in lowered or "vs code" in lowered

            def create_many_folders() -> str:
                workspace = self._default_action_root()
                targets = [(workspace / folder_name).resolve() for folder_name in folder_names]
                message = self.desktop_actions.create_folders_batch(targets)
                if open_in_vscode:
                    vscode_message = self.desktop_actions.open_in_vscode(self.user_settings.data.vscode_path, workspace)
                    return f"{message} {vscode_message}."
                return message

            return self._guarded_action("file_change", f"create folders {', '.join(folder_names)}", create_many_folders)

        create_folder_patterns = [r'(?:vytvor|vytvo\?|udelej|ud\?lej|create|make) (?:slozku|slo\?ku|folder|adresar|adres\?\?) (.+)$']
        for pattern in create_folder_patterns:
            match = re.search(pattern, normalized, flags=re.IGNORECASE)
            if not match:
                continue
            target = self._resolve_creation_target(match.group(1))
            return self._guarded_action("file_change", f"create folder {target}", lambda: self.desktop_actions.create_folder(target))

        create_file_patterns = [r'(?:vytvor|vytvo\?|udelej|ud\?lej|create|make) (?:soubor|file) (.+)$']
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
            return "Luna: Tu cestu jsem v pocitaci nenasla."

        command_patterns = [
            (r'(?:otevri|otev\?i|open) (?:soubor|file) (.+)$', False),
            (r'(?:otevri|otev\?i|open) (?:slozku|slo\?ku|folder|adresar|adres\?\?) (.+)$', True),
            (r'(?:spust|spus\?) (?:soubor|file|path|cestu) (.+)$', False),
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
                return "Luna: Ten soubor nebo slozku jsem v pocitaci nenasla."
            return self._guarded_action("path_open", f"open path {target}", lambda: self.desktop_actions.open_path(target))

        if any(phrase in lowered for phrase in ["otevri workspace ve vscode", "otev?i workspace ve vscode", "open workspace in vscode", "otevri projekt ve vscode", "otev?i projekt ve vscode", "open project in vscode"]):
            current_project = self.projects.get_current_project()
            if current_project is None:
                return "Luna: Ted nemam aktivni projekt, takze nemam co otevrit ve VS Code."

            def open_workspace_in_vscode() -> str:
                result = self.open_connected_app("vscode", current_project.name)
                message = str(result.get("message", "")).strip()
                if result.get("ok"):
                    return message
                raise OSError(message or "VS Code jsem nemohla otevrit.")

            return self._guarded_action("app_launch", f"open workspace in VS Code for {current_project.name}", open_workspace_in_vscode)

        if any(phrase in lowered for phrase in ["otevri projekt", "otev?i projekt", "open project", "otevri workspace", "otev?i workspace", "open workspace"]):
            current_project = self.projects.get_current_project()
            if current_project is None:
                return "Luna: Ted nemam aktivni projekt, takze nemam co otevrit."
            workspace = self.desktop_actions.ensure_project_workspace(current_project.name)
            return self._guarded_action("path_open", f"open workspace {workspace}", lambda: self.desktop_actions.open_path(workspace))

        return None

    def _try_local_app_action(self, user_input: str) -> str | None:
        normalized = ascii_fold_text(" ".join(user_input.strip().lower().split()))
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
                    raise OSError(message or "Aplikaci se nepodarilo otevrit.")

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
        memory_sections = self._project_memory_sections(project)
        if memory_sections["handoff"]:
            lines.append("Recent handoff: " + " | ".join(memory_sections["handoff"][:2]))
        if memory_sections["execution"]:
            lines.append("Recent execution: " + " | ".join(memory_sections["execution"][:2]))
        if memory_sections["focus"]:
            lines.append("Recent conversation focus: " + " | ".join(memory_sections["focus"][:2]))
        if project.attachment_names:
            lines.append("Linked files: " + ", ".join(project.attachment_names[:6]))
        lines.append("If the user asks a vague follow-up and no new project is explicitly introduced, assume they still mean this active project.")
        return "\n".join(lines)

    def _context_snippet(self, text: object, limit: int = 140) -> str:
        cleaned = repair_text(str(text or "")).strip()
        cleaned = re.sub(r"\s+", " ", cleaned)
        if len(cleaned) > limit:
            cleaned = cleaned[: limit - 3].rstrip() + "..."
        return cleaned

    def _session_context(self) -> str:
        history = self.memory.load_history()
        lines: list[str] = []

        chat_title = self.memory.get_current_session_title().strip()
        if chat_title:
            lines.append(f"Current chat title: {chat_title}")

        current_voice = self._current_conversation_speaker()
        if current_voice:
            lines.append(f"Current active voice in this chat: {current_voice}")

        last_user_message = ""
        last_assistant_message = ""
        for item in reversed(history):
            role = str(item.get("role", "")).strip().lower()
            content = self._context_snippet(item.get("content", ""), limit=180)
            if not content:
                continue
            if role == "user" and not last_user_message:
                last_user_message = content
            elif role == "assistant" and not last_assistant_message:
                last_assistant_message = content
            if last_user_message and last_assistant_message:
                break

        if last_user_message:
            lines.append(f"Most recent user topic: {last_user_message}")
        if last_assistant_message:
            lines.append(f"Most recent assistant direction: {last_assistant_message}")

        if self.pending_action is not None:
            pending_title = self._context_snippet(self.pending_action[0], limit=80)
            if pending_title:
                lines.append(f"Pending action waiting for confirmation: {pending_title}")

        recent_actions = self.action_log.recent(2)
        if recent_actions:
            action_items: list[str] = []
            for entry in reversed(recent_actions):
                title = self._context_snippet(entry.title, limit=60)
                if not title:
                    continue
                action_items.append(f"{title} [{entry.status}]")
            if action_items:
                lines.append("Recent local actions: " + " | ".join(action_items))

        if self.observe_mode_enabled:
            lines.append("Observe mode is enabled, so desktop context may still matter for follow-up questions.")

        lines.append(
            "If the user sends a short follow-up, assume they still mean the current topic in this chat unless they clearly switch topics."
        )
        return "\n".join(lines)

    def _library_context(self, user_input: str) -> str:
        workspace = self.user_settings.data
        if bool(workspace.cloud_enabled) and bool(workspace.cloud_auto_sync) and workspace.cloud_root_path.strip():
            self.library.sync_folder(workspace.cloud_root_path.strip())
        return self.library.relevant_context(user_input)

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
        library_context: str = "",
        session_context: str = "",
        intelligence_level: str | None = None,
        include_history: bool = True,
    ) -> list[dict[str, str]]:
        level = str(intelligence_level or self._normalized_intelligence_level()).strip()
        return self.prompt_builder.build(
            user_input=user_input,
            mode=mode,
            instruction=instruction,
            internet_context=internet_context,
            selected_mode=selected_mode,
            reasoning_box=reasoning_box,
            hidden_support=hidden_support,
            project_context=project_context,
            library_context=library_context,
            session_context=session_context,
            intelligence_level=level,
            include_history=include_history,
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
        library_context: str = "",
        session_context: str = "",
        intelligence_level: str | None = None,
        include_history: bool = True,
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
            library_context=library_context,
            session_context=session_context,
            intelligence_level=intelligence_level,
            include_history=include_history,
        )

    def _is_live_visual_query(self, user_input: str) -> bool:
        normalized = " ".join(str(user_input or "").strip().lower().split())
        if not normalized:
            return False
        triggers = (
            "co vidis",
            "co vidiš",
            "co vidis ted",
            "co vidiš ted",
            "co je na obrazovce",
            "co je ted na obrazovce",
            "vidis moje prostredi",
            "vidiš moje prostředí",
            "what do you see",
            "what do you see now",
            "what is on the screen",
            "what is on screen",
            "describe the screen",
        )
        return any(trigger in normalized for trigger in triggers)

    def chat(self, user_input: str, *, extra_context: str = "") -> str:
        self._reload_runtime_preferences()
        self.last_coordination = {
            "lunaActive": False,
            "xenoActive": False,
            "tracks": [],
        }
        cleaned_input = repair_text(str(user_input or "")).strip()
        if not cleaned_input:
            return ""
        if cleaned_input.lower() == "exit":
            return "Luna: Dobre. Az budes chtit pokracovat, jsem tady 🙂"

        pending_action_result = self._handle_pending_action_command(cleaned_input)
        if pending_action_result is not None:
            self.memory_coordinator.remember_user_input(cleaned_input, "action")
            self.memory_coordinator.save_exchange(cleaned_input, pending_action_result)
            return pending_action_result

        internet_result = self._handle_internet_command(cleaned_input)
        if internet_result is not None:
            return internet_result

        observation_result = self._handle_observation_command(cleaned_input)
        if observation_result is not None:
            self.memory_coordinator.remember_user_input(cleaned_input, "action")
            self.memory_coordinator.save_exchange(cleaned_input, observation_result)
            return observation_result

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

        self._last_support_model_source = "unused"
        self._last_primary_model_source = "nvidia" if self.settings.model_type == "nvidia" else "lm_studio"
        xeno_consulted = self.xeno.should_consult(workflow_data["user_input"])
        response_author = self._response_author(workflow_data["user_input"], xeno_consulted=xeno_consulted)
        internet_context = self._internet_context(workflow_data["user_input"])
        hidden_support = self._hidden_xeno_support(workflow_data["user_input"])
        automation_summary = self.xeno.build_automation_summary(workflow_data["user_input"])
        if automation_summary:
            hidden_support = (f"{hidden_support}\n\n{automation_summary}".strip() if hidden_support else automation_summary)
        coordination = self._build_internal_coordination(
            user_input=workflow_data["user_input"],
            response_author=response_author,
            xeno_consulted=xeno_consulted,
            automation_summary=automation_summary,
            hidden_support=hidden_support,
        )
        self.last_coordination = coordination
        coordination_prompt = self._format_coordination_prompt(coordination)
        if coordination_prompt:
            hidden_support = (f"{coordination_prompt}\n\n{hidden_support}".strip() if hidden_support else coordination_prompt)
        extra_context = repair_text(str(extra_context or "")).strip()
        if extra_context:
            hidden_support = (f"{hidden_support}\n\n{extra_context}".strip() if hidden_support else extra_context)
        if self.observe_mode_enabled:
            observer_context = self._observer_context(refresh=self._observer_refresh_enabled())
            if observer_context:
                hidden_support = (hidden_support + "\n\n" + observer_context).strip() if hidden_support else observer_context
        project_context = self._project_context()
        library_context = self._library_context(workflow_data["user_input"])
        session_context = self._session_context()
        live_share_active = "Active desktop share:" in extra_context
        live_visual_query = live_share_active and self._is_live_visual_query(cleaned_input)
        if live_visual_query:
            live_share_instruction = (
                "Live shared desktop rule: ignore older screen descriptions from this chat. "
                "Use only the newest shared frame and the newest live vision summary for this answer. "
                "If the newest frame is unclear, say it is unclear instead of reusing an older screen state."
            )
            session_context = f"{session_context}\n{live_share_instruction}".strip() if session_context else live_share_instruction
        intelligence_level = self._normalized_intelligence_level()
        messages = self.build_messages(
            user_input=workflow_data["user_input"],
            mode=workflow_data["mode"],
            instruction=workflow_data.get("instruction", ""),
            internet_context=internet_context,
            selected_mode=workflow_data.get("selected_mode", "auto"),
            reasoning_box=workflow_data.get("reasoning_box", self.settings.default_reasoning_box),
            hidden_support=hidden_support,
            project_context=project_context,
            library_context=library_context,
            session_context=session_context,
            intelligence_level=intelligence_level,
            include_history=not live_visual_query,
        )

        if response_author == "Xeno":
            response = self._generate_xeno_response(messages)
        else:
            response = self._generate_primary_response(messages)
        if not str(response).strip():
            response = "Luna: Tentokrat z modelu nic rozumneho neprislo. Zkus to prosim jeste jednou 🙂"
        debug_footer = self._build_model_debug_footer(xeno_consulted=xeno_consulted)
        self.last_model_debug = debug_footer
        response = str(response).rstrip()
        self.memory_coordinator.save_exchange(cleaned_input, response, assistant_author=response_author)
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


    def list_library_entries(self) -> list[dict[str, str]]:
        return self.library.list_entries()

    def add_library_note(self, title: str, content: str, tags: list[str] | None = None) -> dict[str, str]:
        entry = self.library.add_note(title, content, tags)
        return {
            "id": entry.id,
            "title": entry.title,
            "kind": entry.kind,
            "source": entry.source,
            "preview": entry.content[:120],
        }

    def add_library_link(self, title: str, url: str, tags: list[str] | None = None) -> dict[str, str]:
        entry = self.library.add_link(title, url, tags)
        return {
            "id": entry.id,
            "title": entry.title,
            "kind": entry.kind,
            "source": entry.source,
            "preview": entry.content[:120],
        }

    def add_library_file(self, file_path: str, tags: list[str] | None = None) -> dict[str, str] | None:
        entry = self.library.add_file(file_path, tags)
        if entry is None:
            return None
        return {
            "id": entry.id,
            "title": entry.title,
            "kind": entry.kind,
            "source": entry.source,
            "preview": entry.content[:120],
        }

    def remove_library_entry(self, entry_id: str) -> bool:
        return self.library.remove_entry(entry_id)

    def sync_cloud_library(self) -> str:
        workspace = self.user_settings.data
        if not bool(workspace.cloud_enabled):
            return "Cloud sync is disabled in settings."
        root_path = workspace.cloud_root_path.strip()
        if not root_path:
            return "Cloud folder path is empty."
        added = self.library.sync_folder(root_path)
        if added <= 0:
            return "Cloud sync finished. No new library items were added."
        return f"Cloud sync finished. Added or refreshed {added} library items."

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

    def _task_dependencies_satisfied(self, project: object, task: dict[str, str]) -> bool:
        dependency_text = str(task.get("dependencies", "")).strip()
        if not dependency_text:
            return True
        dependencies = [item.strip() for item in dependency_text.split("|") if item.strip()]
        if not dependencies:
            return True
        status_by_title = {
            str(item.get("title", "")).strip(): str(item.get("status", "pending")).strip().lower()
            for item in getattr(project, "tasks", [])
            if isinstance(item, dict)
        }
        return all(status_by_title.get(title, "pending") == "completed" for title in dependencies)

    def _task_priority_score(self, task: dict[str, str]) -> tuple[int, int, int, str]:
        status = str(task.get("status", "pending")).strip().lower()
        has_hint = bool(str(task.get("action_hint", "")).strip())
        risk = str(task.get("risk", "")).strip().lower()
        tool = str(task.get("tool", "")).strip().lower()
        status_rank = {"in_progress": 0, "pending": 1}.get(status, 2)
        hint_rank = 0 if has_hint else 1
        risk_rank = {"low": 0, "medium": 1, "high": 2}.get(risk, 1)
        tool_rank = {
            "builder": 0,
            "planning": 1,
            "execution": 2,
            "review": 3,
            "observation": 4,
            "memory": 5,
            "architecture": 6,
            "safety": 7,
            "reasoning": 8,
        }.get(tool, 9)
        return (status_rank, hint_rank, risk_rank + tool_rank, str(task.get("title", "")).lower())

    def get_next_agent_task(self, project_id: str) -> dict[str, str] | None:
        project = self.projects.get_project(project_id)
        if project is None:
            return None
        ready: list[dict[str, str]] = []
        blocked: list[dict[str, str]] = []
        for task in project.tasks:
            status = str(task.get("status", "pending")).strip().lower()
            if status == "completed":
                continue
            if self._task_dependencies_satisfied(project, task):
                ready.append(task)
            else:
                blocked.append(task)
        if ready:
            ready.sort(key=self._task_priority_score)
            return ready[0]
        if blocked:
            blocked.sort(key=lambda item: str(item.get("title", "")).lower())
            return blocked[0]
        return None

    def run_next_agent_task(self, project_id: str) -> dict[str, object]:
        next_task = self.get_next_agent_task(project_id)
        if next_task is None:
            return {"ok": False, "message": "No next agent task is available for this project."}
        return self.run_agent_task_action(project_id, next_task)

    def run_next_agent_chain(self, project_id: str, max_steps: int = 3) -> dict[str, object]:
        self._reload_runtime_preferences()
        max_steps = self._agent_chain_budget(max_steps)
        project = self.projects.get_project(project_id)
        if project is None:
            return {"ok": False, "message": "Project could not be found."}

        preview_tasks: list[dict[str, object]] = []
        for task in project.tasks:
            status = str(task.get("status", "pending")).strip().lower()
            if status == "completed":
                continue
            preview_tasks.append(task)
            if len(preview_tasks) >= 4:
                break

        intelligence_level = self._normalized_intelligence_level()
        agent_model_support = ""
        if bool(self._runtime_budget_profile()["xeno_model_support"]):
            agent_model_support = self.xeno.task_agent.build_model_execution_support(
                objective=project.brief,
                tasks=preview_tasks,
                model_generate=self._support_generate,
                intelligence_level=intelligence_level,
            )

        results: list[str] = []
        executed = 0
        last_project = project

        for _ in range(max_steps):
            next_task = self.get_next_agent_task(project_id)
            if next_task is None:
                break
            result = self.run_agent_task_action(project_id, next_task)
            if not result.get("ok"):
                if results:
                    updated = self.projects.get_project(project_id)
                    message = "Chain stopped after partial progress. " + " ".join(results) + " " + str(result.get("message", ""))
                    if agent_model_support:
                        message += "\n\nAgent model guidance:\n" + agent_model_support
                    return {
                        "ok": True,
                        "message": message.strip(),
                        "project": self._serialize_project(updated),
                    }
                message = str(result.get("message", "")).strip()
                if agent_model_support:
                    message = (message + "\n\nAgent model guidance:\n" + agent_model_support).strip()
                return {
                    "ok": False,
                    "message": message,
                    "project": self._serialize_project(self.projects.get_project(project_id)),
                }

            executed += 1
            message = str(result.get("message", "")).strip()
            if message:
                results.append(message)
            last_project = self.projects.get_project(project_id) or last_project
            if str(next_task.get("status", "")).strip().lower() == "in_progress":
                break
            if str(next_task.get("action_hint", "")).strip().lower() == "open_workspace_in_tool":
                break
            if "opened" in message.lower() or "workspace" in message.lower():
                break

        if executed == 0:
            return {"ok": False, "message": "No next agent chain could be executed."}

        updated = self.projects.get_project(project_id) or last_project
        summary = f"Agent chain executed {executed} step{'s' if executed != 1 else ''}."
        detail = " ".join(results)
        final_message = f"{summary} {detail}".strip()
        self.projects.add_memory_entry(project_id, summary)
        if agent_model_support:
            self.projects.add_memory_entry(project_id, f"Agent model guidance: {agent_model_support[:220]}")
            final_message += "\n\nAgent model guidance:\n" + agent_model_support
        return {
            "ok": True,
            "message": final_message,
            "project": self._serialize_project(updated),
        }

    def run_agent_task_action(self, project_id: str, task_payload: dict[str, object] | str) -> dict[str, object]:
        project = self.projects.get_project(project_id)
        if project is None:
            return {"ok": False, "message": "Project could not be found."}

        if isinstance(task_payload, dict):
            task_data = task_payload
            task_title = str(task_payload.get("title", "Task"))
        else:
            task_title = str(task_payload)
            task_data = {"title": task_title}

        task_model_support = ""
        if bool(self._runtime_budget_profile()["xeno_model_support"]):
            task_model_support = self.xeno.task_agent.build_model_execution_support(
                objective=project.brief,
                tasks=[task_data],
                model_generate=self._support_generate,
                intelligence_level=self._normalized_intelligence_level(),
            )

        action_hint = str(task_data.get("action_hint", "")).strip().lower()
        if action_hint == "observe_desktop_state":
            observation = self.desktop_observer.observe(include_screenshot=False)
            summary = self.desktop_observer.summarize(observation)
            result = {
                "ok": True,
                "status": "completed",
                "message": str(task_data.get("handoff_note", "")).strip() or "Agent observed the active desktop state.",
                "detail": summary,
                "category": "observe",
                "action_key": "observe_desktop_state",
                "workspace": str(self.desktop_actions.ensure_project_workspace(project.name)),
            }
            self._remember_observation(observation, source="agent observe")
        else:
            try:
                result = self.desktop_actions.run_task_action(
                    project_name=project.name,
                    brief=project.brief,
                    next_step=project.next_step,
                    task=task_data,
                    workspace_settings=self.user_settings.data,
                )
            except OSError as error:
                detail = f"Task action failed: {error}"
                self.projects.add_memory_entry(project_id, f"Agent failed: {task_title} -> {detail}")
                self._log_action("file_change", f"task action: {task_title}", "failed", detail)
                return {"ok": False, "message": detail}

        action_result = self._coerce_action_result(
            result,
            category=str(result.get("category", "file_change")),
            title=f"task action: {task_title}",
        )
        status = str(action_result.get("status", "completed"))
        detail = str(action_result.get("detail", action_result.get("message", ""))).strip()
        category = str(action_result.get("category", "file_change"))
        is_ok = bool(action_result.get("ok", False))

        self.projects.update_task_status(project_id, task_title, status)
        if is_ok:
            self.projects.add_memory_entry(project_id, f"Agent action: {task_title} -> {detail or action_result.get('message', '')}")
        else:
            self.projects.add_memory_entry(project_id, f"Agent failed: {task_title} -> {detail or action_result.get('message', '')}")
        self._log_action(category, f"task action: {task_title}", status, detail or str(action_result.get("message", "")))
        updated = self.projects.get_project(project_id)
        final_message = str(action_result.get("message", "Task agent ran an action."))
        final_detail = detail
        if task_model_support:
            self.projects.add_memory_entry(project_id, f"Agent model guidance: {task_model_support[:220]}")
            final_message = (final_message + "\n\nAgent model guidance:\n" + task_model_support).strip()
            final_detail = (detail + "\n\nAgent model guidance:\n" + task_model_support).strip() if detail else task_model_support
        return {
            "ok": is_ok,
            "message": final_message,
            "detail": final_detail,
            "status": status,
            "workspace": action_result.get("workspace", ""),
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
        visual_suffixes = {".png", ".jpg", ".jpeg", ".webp", ".mp4", ".webm", ".mov"}
        parts: list[str] = []
        visual_paths: list[str] = []
        for raw_path in file_paths[:4]:
            path = Path(raw_path)
            if not path.exists():
                parts.append(f"File {path.name} could not be found locally.")
                continue
            if path.suffix.lower() in visual_suffixes:
                visual_paths.append(str(path))
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
        if visual_paths:
            visual_summary = self._analyze_visual_media(
                visual_paths,
                "Describe the attached visual media for LunaAI and Xeno. Focus on visible UI, text, activity, and what matters for the user's task.",
            )
            if visual_summary:
                names = ", ".join(Path(path).name for path in visual_paths)
                parts.append(f"Visual attachment analysis ({names}):\n{visual_summary}")
        return "\n\n".join(parts)

    def generate_project_package(self, user_input: str, project_name: str = "") -> dict[str, object]:
        intelligence_level = self._normalized_intelligence_level()
        result = self.xeno.project_builder.build_from_request(user_input, intelligence_level=intelligence_level)
        blueprint_text = self.xeno.handle(user_input, intelligence_level=intelligence_level, model_generate=self._support_generate)
        tasks = [
            {
                "title": step.title,
                "status": step.status,
                "description": step.description,
                "tool": step.tool,
                "risk": step.risk,
                "action_hint": step.action_hint,
                "handoff_note": step.handoff_note,
                "dependencies": " | ".join(step.dependencies),
            }
            for step in (result.agent_run.steps if result.agent_run else [])
        ]
        handoff_summary = result.agent_run.handoff_summary if result.agent_run is not None else ""
        xeno_model_support = self.xeno.build_model_support(user_input, self._support_generate, intelligence_level=intelligence_level)
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
            handoff_summary=handoff_summary,
        )
        self.projects.add_memory_entry(record.id, f"Xeno refreshed the project plan for {resolved_name}.")
        self.projects.add_memory_entry(record.id, f"Agent next step: {result.next_step}")
        if handoff_summary:
            self.projects.add_memory_entry(record.id, f"Agent handoff: {handoff_summary}")
        if xeno_model_support:
            self.projects.add_memory_entry(record.id, f"Xeno model guidance: {xeno_model_support[:220]}")
        project_id = updated.id if updated is not None else record.id
        return {
            "project_id": project_id,
            "project_name": resolved_name,
            "summary": result.summary,
            "blueprint_text": blueprint_text,
            "next_step": result.next_step,
            "current_phase": result.agent_run.current_phase if result.agent_run else "planning",
            "tasks": tasks,
            "xeno_note": f"Xeno prepared a new execution track for {resolved_name}. {handoff_summary}" + (f"\n\nXeno model guidance:\n{xeno_model_support}" if xeno_model_support else ""),
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



























