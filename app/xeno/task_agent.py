from app.xeno.models import AgentRun, AgentStep, ProjectBlueprint


class TaskAgent:
    def create_run(self, blueprint: ProjectBlueprint) -> AgentRun:
        steps = [
            AgentStep(
                title="Align the scope",
                description="Confirm the first version, target user, and most important outcome.",
                status="completed",
                tool="reasoning",
                output="Initial project intent captured from the request.",
            ),
            AgentStep(
                title="Design the execution path",
                description="Turn the blueprint into a practical sequence of milestones and delivery steps.",
                status="in_progress",
                tool="planning",
                output="Execution path prepared and ready for refinement.",
            ),
            AgentStep(
                title="Prepare implementation structure",
                description="Map folders, core files, and responsibilities into a shippable starting structure.",
                tool="builder",
            ),
            AgentStep(
                title="Ship the first milestone",
                description="Choose the first small deliverable that proves the project works end to end.",
                tool="execution",
            ),
        ]

        return AgentRun(
            name=f"{blueprint.project_name} Agent",
            objective=blueprint.goal,
            current_phase="execution_design",
            steps=steps,
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
        ]
        return any(signal in normalized for signal in signals)

    def describe(self) -> str:
        return (
            "The task agent is Luna's hidden execution layer. "
            "It turns action-heavy requests into concrete steps and acts like Luna's hands."
        )

    def create_action_support(self, user_input: str) -> str:
        normalized = user_input.strip().lower()

        if any(signal in normalized for signal in ["chrome", "browser", "prohlizec"]):
            return (
                "Hidden task agent support: browser action requested. "
                "Interpret the request as an execution task. "
                "Break it into steps such as open browser, locate the requested page, verify relevance, and report the result clearly."
            )

        if any(signal in normalized for signal in ["find page", "find website", "najdi stranku", "vyhledej", "search for"]):
            return (
                "Hidden task agent support: page-finding task requested. "
                "Act as if an execution layer is preparing the search and navigation steps. "
                "Give a clear action-oriented answer with the next concrete move."
            )

        return (
            "Hidden task agent support: execution-oriented request detected. "
            "Use a step-based plan and prioritize concrete action over abstract explanation."
        )

    def format_run(self, run: AgentRun) -> str:
        lines = [
            f"Agent: {run.name}",
            f"Objective: {run.objective}",
            f"Current phase: {run.current_phase}",
            "Steps:",
        ]

        for index, step in enumerate(run.steps, start=1):
            status = step.status.replace("_", " ").title()
            lines.append(f"{index}. [{status}] {step.title}")
            lines.append(f"   {step.description}")
            if step.output:
                lines.append(f"   Output: {step.output}")

        return "\n".join(lines)
