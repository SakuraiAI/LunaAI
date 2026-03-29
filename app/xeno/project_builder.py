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
            f"Xeno prepared a {blueprint.difficulty} difficulty blueprint for '{blueprint.project_name}' "
            f"as a {blueprint.project_type} project, with {len(blueprint.tasks)} structured tasks, "
            f"{len(blueprint.milestones)} milestones, and a stronger execution track for the agent layer."
        )
        next_step = agent_run.recommended_next_action or (
            "Confirm the first milestone and let the task agent prepare the local workspace."
        )
        xeno_note = (
            f"Xeno classified this as a {blueprint.project_type} request and tightened the plan around a {blueprint.difficulty} difficulty execution path."
        )
        return BuilderResult(
            summary=summary,
            blueprint=blueprint,
            next_step=next_step,
            agent_run=agent_run,
            xeno_note=xeno_note,
        )

    def format_blueprint(self, blueprint: ProjectBlueprint) -> str:
        requirements = ", ".join(f"{item.name} ({item.priority})" for item in blueprint.requirements)
        tasks = " | ".join(f"{task.title} [{task.tool}]" for task in blueprint.tasks)
        stack = ", ".join(blueprint.suggested_stack)
        milestones = " | ".join(blueprint.milestones)
        risks = " | ".join(blueprint.risks)
        notes = " | ".join(blueprint.execution_notes)
        return (
            f"Project: {blueprint.project_name}\n"
            f"Goal: {blueprint.goal}\n"
            f"Type: {blueprint.project_type}\n"
            f"Difficulty: {blueprint.difficulty}\n"
            f"Stack: {stack}\n"
            f"Folders: {', '.join(blueprint.folders)}\n"
            f"Core files: {', '.join(blueprint.core_files)}\n"
            f"Requirements: {requirements}\n"
            f"Tasks: {tasks}\n"
            f"Milestones: {milestones}\n"
            f"Risks: {risks}\n"
            f"Execution notes: {notes}"
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
