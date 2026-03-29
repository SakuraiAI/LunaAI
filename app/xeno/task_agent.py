from app.xeno.models import AgentRun, AgentStep, ProjectBlueprint


class TaskAgent:
    def create_run(self, blueprint: ProjectBlueprint) -> AgentRun:
        steps = [
            AgentStep(
                title="Lock the first milestone",
                description="Confirm what the first useful version must really deliver and cut anything non-essential.",
                status="completed",
                tool="reasoning",
                output="Initial scope captured from the request.",
                risk="medium",
            ),
            AgentStep(
                title="Map the execution path",
                description="Turn the project into milestones, dependencies, and a realistic next action.",
                status="in_progress",
                tool="planning",
                output="Execution track prepared for the first working slice.",
                risk="low",
            ),
            AgentStep(
                title="Prepare local workspace",
                description="Create the folders, starter files, and environment structure needed for execution.",
                tool="builder",
                dependencies=["Lock the first milestone", "Map the execution path"],
            ),
            AgentStep(
                title="Build the first working slice",
                description="Create one end-to-end result that proves the system works in practice.",
                tool="execution",
                risk="medium",
                dependencies=["Prepare local workspace"],
            ),
            AgentStep(
                title="Review quality and next step",
                description="Summarize what was built, what still blocks progress, and what should happen next.",
                tool="review",
                dependencies=["Build the first working slice"],
            ),
        ]

        return AgentRun(
            name=f"{blueprint.project_name} Agent",
            objective=blueprint.goal,
            current_phase="execution_design",
            steps=steps,
            execution_mode="guided" if blueprint.difficulty == "high" else "accelerated",
            recommended_next_action="Prepare the workspace and ship the smallest working milestone.",
        )

    def can_handle(self, user_input: str) -> bool:
        normalized = user_input.strip().lower()
        signals = [
            "open chrome",
            "open browser",
            "find page",
            "find website",
            "search for",
            "go to website",
            "open site",
            "open web",
            "open page",
            "otevri chrome",
            "otevri prohlizec",
            "najdi stranku",
            "najdi web",
            "otevri web",
            "otevri stranku",
            "vyhledej",
            "vyhledat",
            "vytvor soubor",
            "vytvo? soubor",
            "vytvor slozku",
            "vytvo? slo?ku",
            "create file",
            "create folder",
            "python projekt",
            "web projekt",
            "pyside projekt",
            "rewrite file",
            "append to file",
            "open workspace",
            "otevri workspace",
            "otev?i workspace",
            "otevri vscode",
            "otev?i vscode",
            "project scaffold",
            "implement",
            "workflow",
            "automation",
        ]
        return any(signal in normalized for signal in signals)

    def describe(self) -> str:
        return (
            "The task agent is Luna's hidden execution layer. "
            "It turns action-heavy requests into concrete steps and acts like Luna's hands, eyes, and working layer."
        )

    def create_action_support(self, user_input: str) -> str:
        normalized = user_input.strip().lower()

        if any(signal in normalized for signal in ["chrome", "browser", "prohlizec"]):
            return (
                "Hidden task agent support: browser action requested. "
                "Prepare navigation steps, verify the target page, and report only real completed actions."
            )

        if any(signal in normalized for signal in ["find page", "find website", "najdi stranku", "vyhledej", "search for"]):
            return (
                "Hidden task agent support: research-navigation task requested. "
                "Break it into search, relevance check, and next concrete move."
            )

        if any(signal in normalized for signal in ["soubor", "file", "projekt", "project", "workspace", "vscode", "folder", "slozku", "slo?ku"]):
            return (
                "Hidden task agent support: local build or file-system action requested. "
                "Prefer verified execution, track the next step, and keep the response tied to what truly happened on disk."
            )

        if any(signal in normalized for signal in ["implement", "workflow", "automation", "agent"]):
            return (
                "Hidden task agent support: multi-step execution requested. "
                "Convert the goal into a short run, identify dependencies, and prefer one finished slice over many partial steps."
            )

        return (
            "Hidden task agent support: execution-oriented request detected. "
            "Use a step-based plan, protect local actions with permissions, and prioritize concrete progress over abstract explanation."
        )

    def format_run(self, run: AgentRun) -> str:
        lines = [
            f"Agent: {run.name}",
            f"Objective: {run.objective}",
            f"Current phase: {run.current_phase}",
            f"Execution mode: {run.execution_mode}",
            f"Recommended next action: {run.recommended_next_action}",
            "Steps:",
        ]

        for index, step in enumerate(run.steps, start=1):
            status = step.status.replace("_", " ").title()
            lines.append(f"{index}. [{status}] {step.title}")
            lines.append(f"   {step.description}")
            lines.append(f"   Tool: {step.tool} | Risk: {step.risk}")
            if step.dependencies:
                lines.append(f"   Depends on: {', '.join(step.dependencies)}")
            if step.output:
                lines.append(f"   Output: {step.output}")

        return "\n".join(lines)

