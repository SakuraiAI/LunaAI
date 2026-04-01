from __future__ import annotations

import ctypes
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path

try:
    import mss  # type: ignore
    import mss.tools  # type: ignore
except Exception:
    mss = None  # type: ignore

try:
    from PIL import ImageGrab  # type: ignore
except Exception:
    ImageGrab = None  # type: ignore


@dataclass(slots=True)
class DesktopObservation:
    ok: bool
    active_window_title: str = ""
    process_name: str = ""
    process_id: int = 0
    mouse_x: int = 0
    mouse_y: int = 0
    screen_width: int = 0
    screen_height: int = 0
    screenshot_path: str = ""
    app_label: str = ""
    app_key: str = ""
    inferred_activity: str = ""
    url_hint: str = ""
    detail: str = ""

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


class DesktopObserverTool:
    def __init__(self, capture_root: Path | None = None) -> None:
        self.capture_root = capture_root or Path("data/observations")
        self.capture_root.mkdir(parents=True, exist_ok=True)
        self._user32 = ctypes.windll.user32
        self._kernel32 = ctypes.windll.kernel32

    def _safe_text(self, value: object) -> str:
        text = str(value or "")
        text = text.replace("?", "-").replace("?", "-").replace("?", "...")
        return text.encode("cp1250", errors="ignore").decode("cp1250", errors="ignore") or text

    def _get_screen_size(self) -> tuple[int, int]:
        width = int(self._user32.GetSystemMetrics(0))
        height = int(self._user32.GetSystemMetrics(1))
        return width, height

    def _get_mouse_position(self) -> tuple[int, int]:
        class POINT(ctypes.Structure):
            _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]

        point = POINT()
        self._user32.GetCursorPos(ctypes.byref(point))
        return int(point.x), int(point.y)

    def _get_active_window(self) -> tuple[str, int, str]:
        hwnd = self._user32.GetForegroundWindow()
        if not hwnd:
            return "", 0, ""

        length = self._user32.GetWindowTextLengthW(hwnd)
        title_buffer = ctypes.create_unicode_buffer(length + 1)
        self._user32.GetWindowTextW(hwnd, title_buffer, length + 1)
        title = title_buffer.value.strip()

        pid = ctypes.c_ulong()
        self._user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        process_id = int(pid.value)
        process_name = self._get_process_name(process_id)
        return title, process_id, process_name

    def _get_process_name(self, process_id: int) -> str:
        if not process_id:
            return ""
        PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
        handle = self._kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, process_id)
        if not handle:
            return ""
        try:
            size = ctypes.c_ulong(32768)
            buffer = ctypes.create_unicode_buffer(size.value)
            ok = ctypes.windll.kernel32.QueryFullProcessImageNameW(handle, 0, buffer, ctypes.byref(size))
            if not ok:
                return ""
            return Path(buffer.value).name
        finally:
            self._kernel32.CloseHandle(handle)

    def _capture_with_mss(self, target_path: Path) -> bool:
        if mss is None:
            return False
        with mss.mss() as sct:  # type: ignore[attr-defined]
            monitor = sct.monitors[1] if len(sct.monitors) > 1 else sct.monitors[0]
            shot = sct.grab(monitor)
            mss.tools.to_png(shot.rgb, shot.size, output=str(target_path))  # type: ignore[attr-defined]
        return target_path.exists()

    def _capture_with_pil(self, target_path: Path) -> bool:
        if ImageGrab is None:
            return False
        image = ImageGrab.grab(all_screens=True)
        image.save(target_path)
        return target_path.exists()

    def capture_screenshot(self) -> tuple[str, str]:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        target_path = self.capture_root / f"desktop_{timestamp}.png"
        try:
            if self._capture_with_mss(target_path) or self._capture_with_pil(target_path):
                return str(target_path), "Screenshot captured successfully."
            return "", "No screenshot backend is available yet. Install mss or Pillow for image capture."
        except Exception as error:
            return "", f"Screenshot capture failed: {error}"

    def _infer_meaning(self, title: str, process_name: str) -> dict[str, str]:
        normalized_title = title.lower()
        normalized_process = process_name.lower()
        process = normalized_process.replace('.exe', '')

        cases = [
            (("code",), "VS Code", "vscode", "coding or editing project files"),
            (("blender",), "Blender", "blender", "working in a 3D scene or asset pipeline"),
            (("unrealeditor", "unreal", "epicgameslauncher"), "Unreal Engine", "unreal", "working on a game or real-time scene"),
            (("unity",), "Unity", "unity", "working in a game editor"),
            (("photoshop",), "Photoshop", "photoshop", "editing graphics or images"),
            (("resolve", "davinci"), "DaVinci Resolve", "davinci", "editing or reviewing video"),
            (("premiere pro", "adobe premiere pro", "premiere"), "Premiere Pro", "premiere", "editing video timelines"),
            (("afterfx", "after effects"), "After Effects", "after_effects", "working on motion graphics or compositing"),
            (("figma",), "Figma", "figma", "designing UI or reviewing layouts"),
            (("fl64", "fl studio"), "FL Studio", "fl_studio", "working on music production"),
            (("substance",), "Substance 3D Painter", "substance", "painting textures or materials"),
            (("explorer",), "File Explorer", "explorer", "browsing files or folders"),
            (("chrome", "msedge", "firefox", "opera"), "Web browser", "browser", "browsing the web"),
            (("discord",), "Discord", "discord", "chatting or reviewing messages"),
            (("notion",), "Notion", "notion", "reading or writing notes"),
            (("obs64", "obs"), "OBS Studio", "obs", "recording or streaming"),
        ]

        app_label = "Desktop app"
        app_key = process or "desktop"
        inferred_activity = "working in a desktop application"

        for keywords, label, key, activity in cases:
            if any(keyword in process or keyword in normalized_title for keyword in keywords):
                app_label = label
                app_key = key
                inferred_activity = activity
                break

        url_hint = ""
        if app_key == "browser":
            if "youtube" in normalized_title:
                inferred_activity = "watching or browsing YouTube"
                url_hint = "youtube"
            elif "github" in normalized_title:
                inferred_activity = "reading or editing something on GitHub"
                url_hint = "github"
            elif "chatgpt" in normalized_title or "openai" in normalized_title:
                inferred_activity = "using an AI chat or OpenAI page"
                url_hint = "openai"

        if app_key == "vscode" and any(token in normalized_title for token in [".py", ".ts", ".js", ".cpp", ".json", ".qml"]):
            inferred_activity = "editing source code or configuration files"

        if app_key == "explorer" and any(token in normalized_title for token in ["downloads", "desktop", "documents", "data", "projects"]):
            inferred_activity = "browsing project files or local folders"

        return {
            "app_label": app_label,
            "app_key": app_key,
            "inferred_activity": inferred_activity,
            "url_hint": url_hint,
        }

    def observe(self, include_screenshot: bool = False) -> dict[str, object]:
        width, height = self._get_screen_size()
        mouse_x, mouse_y = self._get_mouse_position()
        title, process_id, process_name = self._get_active_window()
        screenshot_path = ""
        detail = "Desktop observation captured."
        if include_screenshot:
            screenshot_path, detail = self.capture_screenshot()

        meaning = self._infer_meaning(title, process_name)
        result = DesktopObservation(
            ok=True,
            active_window_title=title,
            process_name=process_name,
            process_id=process_id,
            mouse_x=mouse_x,
            mouse_y=mouse_y,
            screen_width=width,
            screen_height=height,
            screenshot_path=screenshot_path,
            app_label=meaning["app_label"],
            app_key=meaning["app_key"],
            inferred_activity=meaning["inferred_activity"],
            url_hint=meaning["url_hint"],
            detail=detail,
        )
        return result.to_dict()



    def _signature(self, observation: dict[str, object]) -> tuple[str, str, str, str]:
        return (
            str(observation.get("active_window_title", "") or "").strip(),
            str(observation.get("process_name", "") or "").strip(),
            str(observation.get("app_key", "") or "").strip(),
            str(observation.get("inferred_activity", "") or "").strip(),
        )

    def diff(self, previous: dict[str, object] | None, current: dict[str, object]) -> dict[str, object]:
        if not previous:
            return {
                "changed": True,
                "summary": "No previous desktop snapshot was available, so Luna captured the current state as the new baseline.",
                "items": ["Initial desktop baseline captured."],
            }

        items: list[str] = []
        if str(previous.get("active_window_title", "")) != str(current.get("active_window_title", "")):
            items.append(
                "Active window changed from "
                + self._safe_text(previous.get("active_window_title") or "unknown")
                + " to "
                + self._safe_text(current.get("active_window_title") or "unknown")
                + "."
            )
        if str(previous.get("process_name", "")) != str(current.get("process_name", "")):
            items.append(
                "Process changed from "
                + self._safe_text(previous.get("process_name") or "unknown")
                + " to "
                + self._safe_text(current.get("process_name") or "unknown")
                + "."
            )
        if str(previous.get("app_label", "")) != str(current.get("app_label", "")):
            items.append(
                "App context changed from "
                + self._safe_text(previous.get("app_label") or "unknown")
                + " to "
                + self._safe_text(current.get("app_label") or "unknown")
                + "."
            )
        if str(previous.get("inferred_activity", "")) != str(current.get("inferred_activity", "")):
            items.append(
                "Activity changed from "
                + self._safe_text(previous.get("inferred_activity") or "unknown activity")
                + " to "
                + self._safe_text(current.get("inferred_activity") or "unknown activity")
                + "."
            )
        mouse_before = (int(previous.get("mouse_x", 0) or 0), int(previous.get("mouse_y", 0) or 0))
        mouse_now = (int(current.get("mouse_x", 0) or 0), int(current.get("mouse_y", 0) or 0))
        if mouse_before != mouse_now:
            dx = abs(mouse_before[0] - mouse_now[0])
            dy = abs(mouse_before[1] - mouse_now[1])
            if dx >= 120 or dy >= 120:
                items.append(f"Mouse moved from {mouse_before[0]}, {mouse_before[1]} to {mouse_now[0]}, {mouse_now[1]}.")

        changed = bool(items) or self._signature(previous) != self._signature(current)
        if not changed:
            summary = "The desktop still looks stable. Luna did not detect a meaningful change since the last observation."
        else:
            summary = "Desktop changes detected:\n- " + "\n- ".join(items)
        return {
            "changed": changed,
            "summary": summary,
            "items": items,
        }

    def summarize(self, observation: dict[str, object]) -> str:
        if not observation.get("ok"):
            return f"Observation failed. {observation.get('detail', '')}".strip()

        lines = [
            "Luna desktop observation:",
            f"Active window: {self._safe_text(observation.get('active_window_title') or 'unknown')}",
            f"App: {self._safe_text(observation.get('app_label') or 'unknown')}",
            f"Process: {self._safe_text(observation.get('process_name') or 'unknown')} (PID {observation.get('process_id') or 0})",
            f"Meaning: {self._safe_text(observation.get('inferred_activity') or 'unknown activity')}",
            f"Mouse position: {observation.get('mouse_x')}, {observation.get('mouse_y')}",
            f"Screen size: {observation.get('screen_width')}x{observation.get('screen_height')}",
        ]
        if observation.get("url_hint"):
            lines.append(f"Detected context: {self._safe_text(observation.get('url_hint'))}")
        if observation.get("screenshot_path"):
            lines.append(f"Screenshot: {self._safe_text(observation.get('screenshot_path'))}")
        if observation.get("detail"):
            lines.append(self._safe_text(observation.get("detail")))
        return "\n".join(lines)
