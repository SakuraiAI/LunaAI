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
            "postav projekt",
            "scaffold",
            "architecture for",
            "execution plan",
            "task agent",
            "xeno",
            "roadmap",
            "workflow",
            "research plan",
            "agent plan",
        ]
        return any(signal in normalized for signal in signals)

    def classify_request(self, user_input: str) -> dict[str, str]:
        normalized = user_input.strip().lower()

        project_type = "general"
        if any(token in normalized for token in ["game", "unreal", "unity", "blender"]):
            project_type = "creative_tech"
        elif any(token in normalized for token in ["website", "web app", "landing", "frontend", "backend", "api"]):
            project_type = "web"
        elif any(token in normalized for token in ["desktop", "pyside", "qt", "windows app"]):
            project_type = "desktop"
        elif any(token in normalized for token in ["research", "analyze", "vyzkum", "analyza", "research plan"]):
            project_type = "research"
        elif any(token in normalized for token in ["automation", "agent", "workflow", "tooling"]):
            project_type = "automation"

        difficulty = "medium"
        if any(token in normalized for token in ["enterprise", "complex", "large", "agent", "multi", "system", "platform"]):
            difficulty = "high"
        elif any(token in normalized for token in ["simple", "small", "mini", "basic"]):
            difficulty = "low"

        return {
            "project_type": project_type,
            "difficulty": difficulty,
        }

    def suggest_stack(self, user_input: str, project_type: str) -> list[str]:
        normalized = user_input.strip().lower()

        if project_type == "desktop":
            return ["Python", "PySide6", "Local AI Model", "JSON Storage"]
        if project_type == "web":
            stack = ["HTML/CSS/JS", "Python Backend", "Local AI Model"]
            if "react" in normalized:
                stack.insert(0, "React")
            return stack
        if project_type == "creative_tech":
            stack = ["Python", "Workspace Automation", "Project Memory"]
            if "unreal" in normalized:
                stack.insert(0, "Unreal Engine 5")
            if "blender" in normalized:
                stack.insert(0, "Blender")
            return stack
        if project_type == "research":
            return ["Research Workflow", "Project Memory", "Internet Tooling", "Execution Notes"]
        if project_type == "automation":
            return ["Python", "Task Agents", "Desktop Actions", "Execution Log"]
        return ["Python", "Desktop UI", "Local AI Model"]

    def create_blueprint(
        self,
        project_name: str,
        goal: str,
        stack: list[str] | None = None,
    ) -> ProjectBlueprint:
        classification = self.classify_request(goal)
        project_type = classification["project_type"]
        difficulty = classification["difficulty"]
        suggested_stack = stack or self.suggest_stack(goal, project_type)

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
            "data/projects/",
        ]
        if project_type in {"web", "creative_tech"}:
            folders.extend(["assets/", "docs/"])

        core_files = [
            "main.py",
            "config/settings.py",
            "app/core/engine.py",
            "app/ui/desktop_app.py",
            "app/xeno/project_builder.py",
            "app/xeno/task_agent.py",
        ]
        if project_type == "web":
            core_files.extend(["app.py", "README.md"])
        elif project_type == "desktop":
            core_files.extend(["app/ui/desktop_app.py", "requirements.txt"])
        elif project_type == "research":
            core_files.extend(["docs/research_notes.md", "docs/findings.md"])

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
        if difficulty == "high":
            requirements.append(
                ProjectRequirement(
                    name="safety_and_review",
                    description="High-impact actions should be permission-aware and reviewed through logs.",
                    priority="high",
                )
            )

        tasks = [
            ProjectTask(
                title="Clarify the real target",
                description="Lock the first version, target user, and concrete outcome.",
                tool="reasoning",
                priority="high",
            ),
            ProjectTask(
                title="Choose the implementation stack",
                description="Confirm runtime, tools, data storage, and delivery constraints.",
                tool="planning",
                priority="high",
            ),
            ProjectTask(
                title="Create the workspace structure",
                description="Scaffold folders and starter files for the first milestone.",
                tool="builder",
                priority="high",
            ),
            ProjectTask(
                title="Build the first working slice",
                description="Deliver one end-to-end flow that proves the project works.",
                tool="execution",
                priority="high",
            ),
            ProjectTask(
                title="Review and harden the system",
                description="Capture risks, missing pieces, and the next improvement cycle.",
                tool="review",
                priority="medium",
            ),
        ]

        milestones = [
            "Define the smallest useful version.",
            "Prepare a stable workspace and starter files.",
            "Ship one usable end-to-end milestone.",
            "Tighten quality, automation, and memory.",
        ]

        risks = [
            "Project scope may grow faster than the first version can support.",
            "Execution needs to stay aligned with local tools, permissions, and reliability.",
        ]
        if project_type == "research":
            risks.append("Research-heavy work can drift unless each finding is tied to a next step.")
        if project_type == "creative_tech":
            risks.append("Creative pipelines often break if file conventions and workspace structure are not fixed early.")

        execution_notes = [
            "Prefer a shippable first milestone over a broad feature list.",
            "Let Luna talk to the user while Xeno keeps the plan structured underneath.",
            "Use agents for concrete execution, not for vague explanation.",
        ]

        return ProjectBlueprint(
            project_name=project_name,
            goal=goal,
            project_type=project_type,
            difficulty=difficulty,
            target_outcome=goal,
            suggested_stack=suggested_stack,
            folders=folders,
            core_files=core_files,
            requirements=requirements,
            tasks=tasks,
            milestones=milestones,
            risks=risks,
            execution_notes=execution_notes,
        )

