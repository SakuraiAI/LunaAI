from app.xeno.models import BuilderResult, ProjectBlueprint
from app.xeno.planner import XenoPlanner
from app.xeno.task_agent import TaskAgent


class ProjectBuilder:
    def __init__(
        self,
        planner: XenoPlanner | None = None,
        task_agent: TaskAgent | None = None,
    ) -> None:
        self.planner = planner or XenoPlanner()
        self.task_agent = task_agent or TaskAgent()

    def build_from_request(self, user_input: str) -> BuilderResult:
        project_name = self._guess_project_name(user_input)
        goal = self._guess_goal(user_input)
        blueprint = self.planner.create_blueprint(project_name=project_name, goal=goal)
        agent_run = self.task_agent.create_run(blueprint)
        summary = (
            f"Xeno prepared a starter blueprint for '{blueprint.project_name}' "
            f"with {len(blueprint.tasks)} initial tasks, {len(blueprint.folders)} folders, "
            f"and an execution agent ready to drive the next steps."
        )
        next_step = (
            "Confirm the project goal, preferred stack, and first shippable feature, "
            "then Xeno can turn the agent plan into a sharper execution track."
        )
        return BuilderResult(summary=summary, blueprint=blueprint, next_step=next_step, agent_run=agent_run)

    def format_blueprint(self, blueprint: ProjectBlueprint) -> str:
        requirements = ", ".join(item.name for item in blueprint.requirements)
        tasks = " | ".join(task.title for task in blueprint.tasks)
        stack = ", ".join(blueprint.suggested_stack)
        return (
            f"Project: {blueprint.project_name}\n"
            f"Goal: {blueprint.goal}\n"
            f"Stack: {stack}\n"
            f"Folders: {', '.join(blueprint.folders)}\n"
            f"Requirements: {requirements}\n"
            f"Tasks: {tasks}"
        )

    def _guess_project_name(self, user_input: str) -> str:
        words = [word.strip(".,!? ") for word in user_input.split() if word.strip(".,!? ")]
        if not words:
            return "New Project"
        return " ".join(words[:3]).title()

    def _guess_goal(self, user_input: str) -> str:
        cleaned = user_input.strip()
        if cleaned:
            return cleaned
        return "Build a new project with a clear first version and execution plan."
