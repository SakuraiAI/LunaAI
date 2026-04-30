from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.core.text_utils import ascii_fold_text


@dataclass(frozen=True, slots=True)
class ToolSpec:
    name: str
    category: str
    description: str
    args_schema: dict[str, str]
    returns: str
    risk: str = "low"
    requires_confirmation: bool = True
    aliases: tuple[str, ...] = field(default_factory=tuple)

    def compact(self) -> str:
        args = ", ".join(f"{name}: {kind}" for name, kind in self.args_schema.items()) or "none"
        confirmation = "confirm" if self.requires_confirmation else "auto-safe"
        return f"{self.name}({args}) -> {self.returns} [{self.category}, {self.risk}, {confirmation}]"

    def to_payload(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "category": self.category,
            "description": self.description,
            "argsSchema": dict(self.args_schema),
            "returns": self.returns,
            "risk": self.risk,
            "requiresConfirmation": self.requires_confirmation,
            "aliases": list(self.aliases),
        }


class AgentToolRegistry:
    """LangChain-inspired local tool catalog for LunaAI.

    LangChain tools are callable functions with clear names, descriptions,
    input schemas, outputs, and runtime context. LunaAI already has the actual
    execution functions in DesktopActionTool and LunaEngine; this registry gives
    those abilities a structured tool layer without adding a new dependency.
    """

    def __init__(self) -> None:
        self._tools = self._build_tools()

    def list_tools(self) -> list[ToolSpec]:
        return list(self._tools)

    def names(self) -> list[str]:
        return [tool.name for tool in self._tools]

    def get(self, name: str) -> ToolSpec | None:
        normalized = ascii_fold_text(name).lower().strip()
        for tool in self._tools:
            if ascii_fold_text(tool.name).lower() == normalized:
                return tool
        return None

    def match(self, *, category: str = "", title: str = "", user_input: str = "") -> ToolSpec | None:
        haystack = ascii_fold_text(f"{category} {title} {user_input}").lower()
        if not haystack.strip():
            return None

        for tool in self._tools:
            if tool.category and tool.category in haystack:
                if any(alias in haystack for alias in tool.aliases):
                    return tool

        scored: list[tuple[int, ToolSpec]] = []
        for tool in self._tools:
            score = 0
            for alias in tool.aliases:
                if alias and alias in haystack:
                    score += max(1, len(alias.split()))
            if tool.name.replace("_", " ") in haystack:
                score += 3
            if score:
                scored.append((score, tool))
        if not scored:
            return None
        scored.sort(key=lambda item: item[0], reverse=True)
        return scored[0][1]

    def summary_for_prompt(self, focus: str = "") -> str:
        focus_text = ascii_fold_text(focus).lower().strip()
        tools = self._tools
        if focus_text:
            focused = [
                tool
                for tool in tools
                if focus_text in tool.category
                or focus_text in tool.name
                or any(focus_text in alias for alias in tool.aliases)
            ]
            if focused:
                tools = focused
        return "Available local tools:\n" + "\n".join(f"- {tool.compact()}" for tool in tools[:12])

    def format_for_chat(self) -> str:
        lines = ["LunaAI agent tools:"]
        for tool in self._tools:
            confirmation = "needs confirmation" if tool.requires_confirmation else "can run automatically"
            lines.append(f"- {tool.name}: {tool.description} ({tool.risk}, {confirmation})")
        return "\n".join(lines)

    def to_bridge_payload(self) -> list[dict[str, Any]]:
        return [tool.to_payload() for tool in self._tools]

    def _build_tools(self) -> list[ToolSpec]:
        return [
            ToolSpec(
                name="observe_desktop",
                category="observe",
                description="Capture current desktop state and active window context.",
                args_schema={"include_screenshot": "bool"},
                returns="desktop observation summary",
                risk="low",
                requires_confirmation=False,
                aliases=("observe", "screen", "desktop", "co vidis", "obrazovka"),
            ),
            ToolSpec(
                name="analyze_visual_context",
                category="live_vision",
                description="Use the latest shared desktop frame or attached image/video as visual context for Luna and Xeno.",
                args_schema={"query": "string", "source": "latest_frame|attachment|screenshot"},
                returns="short visual description for the next assistant response",
                risk="low",
                requires_confirmation=False,
                aliases=("vision", "visual", "frame", "obrazek", "video", "co vidis ted", "share"),
            ),
            ToolSpec(
                name="open_app",
                category="app_launch",
                description="Open a configured desktop application such as VS Code, Blender, or Chrome.",
                args_schema={"app": "string", "target": "optional path or project name"},
                returns="launch result with verification",
                risk="medium",
                requires_confirmation=True,
                aliases=("open app", "otevri", "spust", "launch", "vscode", "blender", "chrome", "unreal"),
            ),
            ToolSpec(
                name="open_url",
                category="app_launch",
                description="Open a URL in the browser.",
                args_schema={"url": "string", "prefer_chrome": "bool"},
                returns="browser navigation result",
                risk="low",
                requires_confirmation=True,
                aliases=("open url", "http", "https", "website", "stranku", "unrealengine.com"),
            ),
            ToolSpec(
                name="search_web",
                category="app_launch",
                description="Open a web search for a user query.",
                args_schema={"query": "string", "prefer_chrome": "bool"},
                returns="browser search result",
                risk="low",
                requires_confirmation=True,
                aliases=("search", "vyhledej", "najdi na webu", "google"),
            ),
            ToolSpec(
                name="open_path",
                category="path_open",
                description="Open a local file or folder.",
                args_schema={"path": "string"},
                returns="opened path result",
                risk="low",
                requires_confirmation=True,
                aliases=("open path", "open folder", "otevri slozku", "otevri soubor", "workspace"),
            ),
            ToolSpec(
                name="read_file",
                category="file_read",
                description="Read a local text file.",
                args_schema={"path": "string"},
                returns="file contents",
                risk="low",
                requires_confirmation=False,
                aliases=("read file", "precti soubor", "obsah souboru"),
            ),
            ToolSpec(
                name="list_folder",
                category="file_read",
                description="List files and folders in a local directory.",
                args_schema={"path": "string"},
                returns="folder listing",
                risk="low",
                requires_confirmation=False,
                aliases=("list folder", "vypis slozku", "obsah slozky"),
            ),
            ToolSpec(
                name="find_path",
                category="file_read",
                description="Find a file or folder inside bounded local search roots.",
                args_schema={"query": "string", "prefer_directory": "optional bool"},
                returns="matching paths",
                risk="low",
                requires_confirmation=False,
                aliases=("find file", "find folder", "najdi soubor", "najdi slozku"),
            ),
            ToolSpec(
                name="create_file_or_folder",
                category="file_change",
                description="Create files, folders, scripts, calculator, or a simple web page in the project workspace.",
                args_schema={"target": "string", "content": "optional string"},
                returns="file creation result",
                risk="medium",
                requires_confirmation=True,
                aliases=("create", "make", "vytvor", "udelej", "scripts", "calculator", "web", "slozku", "soubor"),
            ),
            ToolSpec(
                name="run_project",
                category="project_run",
                description="Run the active project or static web server.",
                args_schema={"workspace": "optional path", "port": "optional int"},
                returns="started process result",
                risk="medium",
                requires_confirmation=True,
                aliases=("run project", "spust projekt", "spust web", "localhost"),
            ),
            ToolSpec(
                name="draft_email",
                category="communication",
                description="Create a local email draft; never sends email automatically.",
                args_schema={"recipient": "optional string", "subject": "optional string", "body": "optional string"},
                returns="email draft path",
                risk="medium",
                requires_confirmation=True,
                aliases=("email", "mail", "posli email", "napis email", "draft"),
            ),
            ToolSpec(
                name="system_input",
                category="system_input",
                description="Press shortcuts, type text, or click exact coordinates in the active window.",
                args_schema={"kind": "shortcut|type_text|mouse_click", "value": "string"},
                returns="input result with verification",
                risk="medium",
                requires_confirmation=True,
                aliases=("click", "klikni", "press", "stiskni", "type text", "napis text", "shortcut"),
            ),
            ToolSpec(
                name="agent_trace_status",
                category="diagnostic",
                description="Show recent route, Xeno, action, and verification trace records.",
                args_schema={"limit": "optional int"},
                returns="recent agent trace",
                risk="low",
                requires_confirmation=False,
                aliases=("agent status", "agent trace", "stav agenta", "trace agenta"),
            ),
        ]
