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
        if not normalized:
            return {
                "consult": False,
                "project_request": False,
                "action_request": False,
                "automation_mode": "none",
            }

        project_request = self.planner.is_project_builder_request(normalized)
        action_request = self.task_agent.can_handle(normalized)
        consult = project_request or action_request
        automation_mode = "balanced"
        if project_request and action_request:
            automation_mode = "hybrid"
        elif project_request:
            automation_mode = "planning"
        elif action_request:
            automation_mode = "execution"

        return {
            "consult": consult,
            "project_request": project_request,
            "action_request": action_request,
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
        return " | ".join(parts)

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
