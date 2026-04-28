from typing import Callable

from app.xeno.project_builder import ProjectBuilder
from app.xeno.planner import XenoPlanner
from app.xeno.task_agent import TaskAgent


class XenoCoordinator:
    def __init__(
        self,
        planner: XenoPlanner | None = None,
        project_builder: ProjectBuilder | None = None,
        task_agent: TaskAgent | None = None,
    ) -> None:
        self.planner = planner or XenoPlanner()
        self.task_agent = task_agent or TaskAgent()
        self.project_builder = project_builder or ProjectBuilder(self.planner, self.task_agent)

    def describe(self) -> str:
        return (
            "Xeno is Luna's sister system inside the same platform. "
            "She focuses on planning, architecture, research structure, execution strategy, and turning requests into agent-ready action tracks."
        )

    def classify_request(self, user_input: str) -> dict[str, object]:
        normalized = user_input.strip()
        normalized_lower = normalized.lower()
        if not normalized:
            return {
                "consult": False,
                "project_request": False,
                "action_request": False,
                "reasoning_request": False,
                "automation_mode": "none",
            }

        project_request = self.planner.is_project_builder_request(normalized)
        action_request = self.task_agent.can_handle(normalized)
        reasoning_signals = [
            "xeno",
            "luna a xeno",
            "obe ai",
            "obě ai",
            "promt",
            "prompt",
            "kontext",
            "context",
            "ucili",
            "učili",
            "pamatuj",
            "memory",
            "napoj",
            "propoj",
            "ovladani pc",
            "ovládání pc",
            "agent",
            "architektura",
            "analyzuj",
            "strategie",
            "strategy",
            "risk",
            "riziko",
        ]
        reasoning_request = any(signal in normalized_lower for signal in reasoning_signals)
        consult = project_request or action_request or reasoning_request
        automation_mode = "balanced"
        if project_request and action_request:
            automation_mode = "hybrid"
        elif project_request:
            automation_mode = "planning"
        elif action_request:
            automation_mode = "execution"
        elif reasoning_request:
            automation_mode = "reasoning"

        return {
            "consult": consult,
            "project_request": project_request,
            "action_request": action_request,
            "reasoning_request": reasoning_request,
            "automation_mode": automation_mode,
        }

    def should_consult(self, user_input: str) -> bool:
        return bool(self.classify_request(user_input)["consult"])

    def _clean_model_support(self, text: str) -> str:
        cleaned = str(text or "").strip()
        if cleaned.startswith("Luna:"):
            cleaned = cleaned.removeprefix("Luna:").strip()
        if cleaned.startswith("Xeno:"):
            cleaned = cleaned.removeprefix("Xeno:").strip()
        return cleaned

    def build_automation_summary(self, user_input: str) -> str:
        summary = self.classify_request(user_input)
        if not summary["consult"]:
            return ""
        parts: list[str] = [f"Automation mode: {summary['automation_mode']}"]
        if summary["project_request"]:
            parts.append("Project planning track active")
        if summary["action_request"]:
            parts.append("Task-agent execution track active")
        if summary.get("reasoning_request"):
            parts.append("Xeno reasoning/context track active")
        return " | ".join(parts)

    def _action_intent(self, category: str, title: str) -> str:
        normalized = f"{category} {title}".strip().lower()
        if category == "system_input" and "mouse click" in normalized:
            return "mouse_click"
        if category == "system_input" and "type text" in normalized:
            return "type_text"
        if category == "system_input" and "press shortcut" in normalized:
            return "press_shortcut"
        if category == "system_input":
            return "system_input"
        if "run project" in normalized or category == "project_run":
            return "run_project"
        if "calculator" in normalized or "kalkulack" in normalized:
            return "create_calculator"
        if "script" in normalized or "skript" in normalized:
            return "create_scripts"
        if "email" in normalized or "mail" in normalized:
            return "draft_email"
        if "web" in normalized or "website" in normalized or "landing" in normalized:
            return "create_web_page"
        if "create folders" in normalized:
            return "create_folders"
        if "create file" in normalized or "overwrite file" in normalized or "append to file" in normalized:
            return "edit_files"
        if "workspace" in normalized and "vscode" in normalized:
            return "open_workspace_in_vscode"
        if category == "file_read" and "list folder" in normalized:
            return "list_folder"
        if category == "file_read" and "read file" in normalized:
            return "read_file"
        if category == "file_read" and "find" in normalized:
            return "find_file_or_folder"
        if "open url" in normalized:
            return "open_url"
        if "search web" in normalized:
            return "search_web"
        if category == "app_launch":
            return "open_app"
        if category == "path_open":
            return "open_path"
        if title.startswith("chain action:"):
            return "multi_step_action"
        return category or "local_action"

    def plan_action(
        self,
        *,
        category: str,
        title: str,
        user_input: str = "",
        project_context: str = "",
        desktop_context: str = "",
    ) -> dict[str, object]:
        """Deterministic Xeno action check before Luna prepares or executes local actions."""
        normalized = f"{category} {title} {user_input}".strip().lower()
        blocked_markers = [
            "delete ",
            "remove ",
            "rm ",
            "rmdir",
            "format ",
            "registry",
            "regedit",
            "smaz",
            "vymaz",
        ]
        if any(marker in normalized for marker in blocked_markers):
            return {
                "status": "blocked",
                "intent": self._action_intent(category, title),
                "risk": "high",
                "requiresConfirmation": True,
                "recommendedAction": "block",
                "reason": "Xeno zastavil akci, protoze vypada jako mazani nebo rizikovy systemovy zasah.",
                "category": category,
            }

        risk_by_category = {
            "observe": "low",
            "path_open": "low",
            "file_read": "low",
            "app_launch": "medium",
            "project_run": "medium",
            "file_change": "medium",
            "communication": "medium",
            "system_input": "medium",
            "system": "medium",
        }
        intent = self._action_intent(category, title)
        risk = risk_by_category.get(category, "medium")
        requires_confirmation = category in {"app_launch", "path_open", "project_run", "file_change", "communication", "system_input", "system"}

        reason_map = {
            "list_folder": "Xeno ověřil záměr: výpis složky je čtecí akce bez změny souborů.",
            "read_file": "Xeno ověřil záměr: přečtení souboru je čtecí akce bez zápisu na disk.",
            "find_file_or_folder": "Xeno ověřil záměr: hledání v lokálních složkách je čtecí akce s omezeným rozsahem.",
            "open_url": "Xeno ověřil záměr: otevření odkazu je lokální akce v prohlížeči.",
            "search_web": "Xeno ověřil záměr: webové hledání je otevření vyhledávací URL, ne automatické procházení webu.",
            "run_project": "Xeno ověřil záměr: projekt se má spustit z aktivního workspace a má zůstat za potvrzením.",
            "create_calculator": "Xeno ověřil záměr: jde o tvorbu kódu na disku, takže Luna má připravit změnu a čekat na Accept.",
            "create_scripts": "Xeno ověřil záměr: jde o vytvoření projektových skriptů na disku, takže Luna má připravit změnu a čekat na Accept.",
            "create_web_page": "Xeno ověřil záměr: jde o vytvoření webových souborů v projektu a následné vysvětlení výsledku.",
            "draft_email": "Xeno ověřil záměr: u emailu smí Luna připravit pouze koncept, automatické odeslání zůstává zakázané.",
            "create_folders": "Xeno ověřil záměr: jde o bezpečnou přípravu struktury složek v projektu.",
            "edit_files": "Xeno ověřil záměr: bude se měnit soubor, proto je správné držet akci za potvrzením.",
            "open_workspace_in_vscode": "Xeno ověřil záměr: otevřít aktuální workspace ve VS Code je vratná lokální akce.",
            "open_app": "Xeno ověřil záměr: otevření aplikace je lokální akce a má jít přes potvrzení.",
            "open_path": "Xeno ověřil záměr: otevření cesty je lokální akce bez úprav souborů.",
            "mouse_click": "Xeno ověřil záměr: kliknutí na souřadnice je systémový vstup a musí zůstat za potvrzením.",
            "type_text": "Xeno ověřil záměr: psaní textu do aktivního okna je systémový vstup a musí zůstat za potvrzením.",
            "press_shortcut": "Xeno ověřil záměr: klávesová zkratka ovlivní aktivní okno, proto musí zůstat za potvrzením.",
            "system_input": "Xeno ověřil záměr: systémový vstup je povolený pouze jako přesný potvrzený krok.",
            "multi_step_action": "Xeno ověřil záměr: vícekrokovou akci držet jako jeden plán a provést až po potvrzení.",
        }
        reason = reason_map.get(intent, "Xeno ověřil záměr a nenašel blokující riziko.")
        if project_context:
            reason += " Projektový kontext je k dispozici."
        if desktop_context:
            reason += " Obrazovkový kontext je k dispozici."

        return {
            "status": "approved",
            "intent": intent,
            "risk": risk,
            "requiresConfirmation": requires_confirmation,
            "recommendedAction": title,
            "reason": reason,
            "category": category,
        }

    def build_model_support(
        self,
        user_input: str,
        model_generate: Callable[[list[dict[str, str]]], str] | None,
        intelligence_level: str = "4",
    ) -> str:
        if model_generate is None:
            return ""

        level = str(intelligence_level).strip()
        if level not in {"4", "5"}:
            return ""

        request_shape = self.classify_request(user_input)
        if not request_shape["consult"]:
            return ""

        project_summary = ""
        action_summary = ""
        if request_shape["project_request"]:
            result = self.project_builder.build_from_request(user_input, intelligence_level=level)
            handoff_summary = "No action-ready agent handoff yet."
            if result.agent_run is not None:
                handoff_summary = self.task_agent.create_handoff_summary(result.agent_run)
            project_summary = (
                f"Project: {result.blueprint.project_name}. "
                f"Type: {result.blueprint.project_type}. "
                f"Difficulty: {result.blueprint.difficulty}. "
                f"Milestones: {' | '.join(result.blueprint.milestones[:4])}. "
                f"Risks: {' | '.join(result.blueprint.risks[:4])}. "
                f"Agent handoff: {handoff_summary}"
            )
        if request_shape["action_request"]:
            action_summary = self.task_agent.create_action_support(user_input, intelligence_level=level)

        system_prompt = (
            "You are Xeno, Luna's hidden strategic system. "
            "Write only compact internal planning notes for Luna and the agents. "
            "Use project context, live vision context, memory, and action policy as one connected system when they are provided. "
            "Protect the boundary between read-only context, reversible actions, file changes, and risky system actions. "
            "Do not greet, do not roleplay, and do not mention the user directly. "
            "Return 3 short sections: Strategic read, Main risk, Best next move. "
            "Keep it concrete, system-aware, and execution-focused."
        )
        user_prompt = (
            f"Intelligence level: {level}\n"
            f"Automation mode: {request_shape['automation_mode']}\n"
            f"User request: {user_input}\n"
            f"Planning context: {project_summary or 'No project blueprint needed.'}\n"
            f"Action context: {action_summary or 'No action-specific support.'}"
        )
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
        try:
            result = self._clean_model_support(model_generate(messages))
        except Exception:
            return ""
        lowered = result.lower()
        if not result or lowered.startswith("luna: lm studio") or lowered.startswith("luna: unexpected"):
            return ""
        return result

    def build_hidden_support(self, user_input: str, intelligence_level: str = "4") -> str:
        parts: list[str] = []
        level = str(intelligence_level).strip()
        request_shape = self.classify_request(user_input)

        automation_summary = self.build_automation_summary(user_input)
        if automation_summary:
            parts.append("Hidden Xeno automation: " + automation_summary)

        if request_shape["project_request"]:
            result = self.project_builder.build_from_request(user_input, intelligence_level=level)
            step_titles = ", ".join(step.title for step in result.agent_run.steps[:4]) if result.agent_run else ""
            parts.append(
                "Hidden Xeno support: advanced planning requested. "
                f"Planning level: {level}. "
                f"Project focus: {result.blueprint.project_name}. "
                f"Type: {result.blueprint.project_type}. "
                f"Difficulty: {result.blueprint.difficulty}. "
                f"Milestones: {' | '.join(result.blueprint.milestones[:3])}. "
                f"Initial execution steps: {step_titles}."
            )
            if result.blueprint.risks:
                parts.append("Hidden Xeno risk notes: " + " | ".join(result.blueprint.risks[:3]))
            if result.agent_run is not None:
                parts.append("Hidden Xeno handoff: " + self.task_agent.create_handoff_summary(result.agent_run))

        if request_shape["action_request"]:
            parts.append(self.task_agent.create_action_support(user_input, intelligence_level=level))

        return "\n".join(part for part in parts if part)

    def can_handle(self, user_input: str) -> bool:
        return bool(self.classify_request(user_input)["project_request"])

    def handle(
        self,
        user_input: str,
        intelligence_level: str = "4",
        model_generate: Callable[[list[dict[str, str]]], str] | None = None,
    ) -> str:
        result = self.project_builder.build_from_request(user_input, intelligence_level=intelligence_level)
        blueprint_text = self.project_builder.format_blueprint(result.blueprint)
        agent_text = self.task_agent.format_run(result.agent_run) if result.agent_run else ""
        model_support = self.build_model_support(user_input, model_generate, intelligence_level=intelligence_level)
        parts = [result.summary, result.xeno_note]
        automation_summary = self.build_automation_summary(user_input)
        if automation_summary:
            parts.append("Xeno automation:\n" + automation_summary)
        if model_support:
            parts.append("Xeno model guidance:\n" + model_support)
        parts.append(blueprint_text)
        if agent_text:
            parts.append(agent_text)
        parts.append(f"Next step: {result.next_step}")
        return "\n\n".join(part for part in parts if part)
