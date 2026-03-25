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
            "She focuses on planning, project building, architecture, and turning ideas into structured execution steps through a task agent."
        )

    def should_consult(self, user_input: str) -> bool:
        normalized = user_input.strip()
        if not normalized:
            return False
        return self.planner.is_project_builder_request(normalized) or self.task_agent.can_handle(normalized)

    def build_hidden_support(self, user_input: str) -> str:
        parts: list[str] = []

        if self.planner.is_project_builder_request(user_input):
            result = self.project_builder.build_from_request(user_input)
            step_titles = ", ".join(step.title for step in result.agent_run.steps[:3]) if result.agent_run else ""
            parts.append(
                "Hidden Xeno support: advanced planning requested. "
                f"Project focus: {result.blueprint.project_name}. "
                f"Goal: {result.blueprint.goal}. "
                f"Initial execution steps: {step_titles}."
            )

        if self.task_agent.can_handle(user_input):
            parts.append(self.task_agent.create_action_support(user_input))

        return "\n".join(parts)

    def can_handle(self, user_input: str) -> bool:
        return self.planner.is_project_builder_request(user_input)

    def handle(self, user_input: str) -> str:
        result = self.project_builder.build_from_request(user_input)
        blueprint_text = self.project_builder.format_blueprint(result.blueprint)
        agent_text = self.task_agent.format_run(result.agent_run) if result.agent_run else ""
        parts = [result.summary, blueprint_text]
        if agent_text:
            parts.append(agent_text)
        parts.append(f"Next step: {result.next_step}")
        return "\n\n".join(parts)
