from app.xeno.models import ProjectBlueprint, ProjectRequirement, ProjectTask


class XenoPlanner:
    def is_project_builder_request(self, user_input: str) -> bool:
        normalized = user_input.strip().lower()
        signals = [
            "build project",
            "project builder",
            "create app",
            "create project",
            "make app",
            "make project",
            "navrhni projekt",
            "vytvor projekt",
            "udelat projekt",
            "udělat projekt",
            "postav projekt",
            "scaffold",
            "architecture for",
            "execution plan",
            "task agent",
            "xeno",
        ]
        return any(signal in normalized for signal in signals)

    def create_blueprint(
        self,
        project_name: str,
        goal: str,
        stack: list[str] | None = None,
    ) -> ProjectBlueprint:
        suggested_stack = stack or ["Python", "Desktop UI", "Local AI Model"]
        folders = [
            "config/",
            "app/core/",
            "app/memory/",
            "app/models/",
            "app/tools/",
            "app/workflow/",
            "app/ui/",
            "app/xeno/",
            "data/chats/",
        ]
        core_files = [
            "main.py",
            "config/settings.py",
            "app/core/engine.py",
            "app/ui/desktop_app.py",
            "app/xeno/project_builder.py",
            "app/xeno/task_agent.py",
        ]
        requirements = [
            ProjectRequirement(
                name="clear_goal",
                description="The project should have a clear primary goal and target outcome.",
                priority="high",
            ),
            ProjectRequirement(
                name="modular_architecture",
                description="Core logic should stay separated from UI, memory, and tools.",
                priority="high",
            ),
            ProjectRequirement(
                name="execution_path",
                description="The assistant should propose actionable next steps, not only ideas.",
                priority="high",
            ),
            ProjectRequirement(
                name="agent_ready_tasks",
                description="The plan should be decomposed into steps that a task agent can execute and track.",
                priority="high",
            ),
        ]
        tasks = [
            ProjectTask(
                title="Define scope",
                description="Clarify what the first shippable version of the project must do.",
            ),
            ProjectTask(
                title="Choose stack",
                description="Confirm runtime, UI layer, model backend, and data storage.",
            ),
            ProjectTask(
                title="Scaffold modules",
                description="Create folders, service boundaries, and core interfaces.",
            ),
            ProjectTask(
                title="Implement first workflow",
                description="Ship one end-to-end user flow before adding advanced features.",
            ),
            ProjectTask(
                title="Prepare agent execution path",
                description="Translate the project into milestones and steps that Xeno's task agent can drive.",
            ),
        ]

        return ProjectBlueprint(
            project_name=project_name,
            goal=goal,
            suggested_stack=suggested_stack,
            folders=folders,
            core_files=core_files,
            requirements=requirements,
            tasks=tasks,
        )
