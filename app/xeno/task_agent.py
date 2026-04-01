from typing import Callable

from app.xeno.models import AgentRun, AgentStep, ProjectBlueprint


class TaskAgent:
    def create_run(self, blueprint: ProjectBlueprint, intelligence_level: str = "4") -> AgentRun:
        level = str(intelligence_level).strip()
        steps = [
            AgentStep(
                title="Lock the first milestone",
                description="Confirm what the first useful version must really deliver and cut anything non-essential.",
                status="completed",
                tool="reasoning",
                output="Initial scope captured from the request.",
                risk="medium",
                action_ready=True,
                action_hint="create_scope_file",
                handoff_note="Agent can immediately prepare a clean scope document for review.",
            ),
            AgentStep(
                title="Map the execution path",
                description="Turn the project into milestones, dependencies, and a realistic next action.",
                status="in_progress",
                tool="planning",
                output="Execution track prepared for the first working slice.",
                risk="low",
                action_ready=True,
                action_hint="create_execution_plan",
                handoff_note="Agent can generate a next-step file and lock the practical run order.",
            ),
            AgentStep(
                title="Prepare local workspace",
                description="Create the folders, starter files, and environment structure needed for execution.",
                tool="builder",
                dependencies=["Lock the first milestone", "Map the execution path"],
                action_ready=True,
                action_hint="create_project_scaffold",
                handoff_note="Agent can scaffold the local workspace right now.",
            ),
            AgentStep(
                title="Build the first working slice",
                description="Create one end-to-end result that proves the system works in practice.",
                tool="execution",
                risk="medium",
                dependencies=["Prepare local workspace"],
                action_ready=True,
                action_hint="open_workspace_in_tool",
                handoff_note="Agent can open the right workspace and hand the next implementation move to Luna.",
            ),
            AgentStep(
                title="Observe the active workspace state",
                description="Capture what is currently open on the desktop so Luna and Xeno can align the next move with the real screen context.",
                tool="observation",
                risk="low",
                dependencies=["Build the first working slice"],
                action_ready=True,
                action_hint="observe_desktop_state",
                handoff_note="Agent can observe the active desktop state and capture the current app context.",
            ),
            AgentStep(
                title="Review quality and next step",
                description="Summarize what was built, what still blocks progress, and what should happen next.",
                tool="review",
                dependencies=["Build the first working slice", "Observe the active workspace state"],
                action_ready=True,
                action_hint="refresh_review_notes",
                handoff_note="Agent can refresh the review notes and prepare the next pass.",
            ),
        ]

        if level == "5":
            steps.insert(
                2,
                AgentStep(
                    title="Lock trust and safety boundaries",
                    description="Verify which actions should be confirmed, logged, or delayed before deeper execution.",
                    tool="safety",
                    risk="medium",
                    dependencies=["Lock the first milestone"],
                    action_ready=True,
                    action_hint="create_execution_plan",
                    handoff_note="Agent can lock the trust layer into the execution notes before continuing.",
                ),
            )
            steps.insert(
                3,
                AgentStep(
                    title="Shape the architecture handoff",
                    description="Make the system layers and agent boundaries explicit before the first big execution pass.",
                    tool="architecture",
                    risk="medium",
                    dependencies=["Lock the first milestone", "Map the execution path"],
                    action_ready=True,
                    action_hint="create_execution_plan",
                    handoff_note="Agent can capture the architecture handoff so Luna, Xeno, memory, and agents stay aligned.",
                )
            )
            steps.append(
                AgentStep(
                    title="Capture project memory and handoff state",
                    description="Store the critical decisions, risks, and next operational handoff for Luna and future runs.",
                    tool="memory",
                    risk="low",
                    dependencies=["Review quality and next step"],
                    action_ready=True,
                    action_hint="refresh_review_notes",
                    handoff_note="Agent can refresh memory-facing notes and preserve the latest handoff summary.",
                )
            )
        elif level == "3":
            steps = steps[:4]

        handoff_summary = self.create_handoff_summary_from_steps(steps)
        execution_mode = "guided"
        if blueprint.difficulty == "high" or level == "5":
            execution_mode = "strategic"
        elif blueprint.difficulty != "high":
            execution_mode = "accelerated"

        recommended_next_action = "Prepare the workspace and ship the smallest working milestone."
        if level == "5":
            recommended_next_action = "Lock the trust layer, prepare the workspace, and ship the smallest working milestone with clean handoff notes."
        elif level == "3":
            recommended_next_action = "Prepare the workspace and move quickly to the first usable result."

        return AgentRun(
            name=f"{blueprint.project_name} Agent",
            objective=blueprint.goal,
            current_phase="execution_design",
            steps=steps,
            execution_mode=execution_mode,
            recommended_next_action=recommended_next_action,
            handoff_summary=handoff_summary,
        )

    def create_handoff_summary_from_steps(self, steps: list[AgentStep]) -> str:
        ready_steps = [step for step in steps if step.action_ready]
        if not ready_steps:
            return "Xeno has no action-ready handoff for the agent yet."
        lead = ready_steps[0]
        lines = [
            f"Agent handoff ready: {lead.title}.",
            f"Immediate action: {lead.handoff_note or lead.description}",
        ]
        if len(ready_steps) > 1:
            lines.append("Queued after that: " + " | ".join(step.title for step in ready_steps[1:4]))
        return " ".join(lines)

    def create_handoff_summary(self, run: AgentRun) -> str:
        if run.handoff_summary:
            return run.handoff_summary
        return self.create_handoff_summary_from_steps(run.steps)

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

    def create_action_support(self, user_input: str, intelligence_level: str = "4") -> str:
        normalized = user_input.strip().lower()
        level = str(intelligence_level).strip()

        if any(signal in normalized for signal in ["chrome", "browser", "prohlizec"]):
            base = (
                "Hidden task agent support: browser action requested. "
                "Prepare navigation steps, verify the target page, and report only real completed actions."
            )
            if level == "5":
                base += " Preserve the concrete destination and avoid vague browsing."
            return base

        if any(signal in normalized for signal in ["find page", "find website", "najdi stranku", "vyhledej", "search for"]):
            base = (
                "Hidden task agent support: research-navigation task requested. "
                "Break it into search, relevance check, and next concrete move."
            )
            if level == "5":
                base += " Keep the chain short and evidence-aware."
            return base

        if any(signal in normalized for signal in ["soubor", "file", "projekt", "project", "workspace", "vscode", "folder", "slozku", "slo?ku"]):
            base = (
                "Hidden task agent support: local build or file-system action requested. "
                "Prefer verified execution, track the next step, and keep the response tied to what truly happened on disk."
            )
            if level == "5":
                base += " Preserve exact handoff notes for the next action."
            return base

        if any(signal in normalized for signal in ["implement", "workflow", "automation", "agent"]):
            base = (
                "Hidden task agent support: multi-step execution requested. "
                "Convert the goal into a short run, identify dependencies, and prefer one finished slice over many partial steps."
            )
            if level == "5":
                base += " Keep trust, permissions, and reversibility visible in the plan."
            return base

        return (
            "Hidden task agent support: execution-oriented request detected. "
            "Use a step-based plan, protect local actions with permissions, and prioritize concrete progress over abstract explanation."
        )

    def build_model_execution_support(
        self,
        objective: str,
        tasks: list[dict[str, object]],
        model_generate: Callable[[list[dict[str, str]]], str] | None,
        intelligence_level: str = "4",
    ) -> str:
        if model_generate is None:
            return ""
        level = str(intelligence_level).strip()
        if level not in {"4", "5"}:
            return ""
        if not tasks:
            return ""

        task_lines: list[str] = []
        for task in tasks[:4]:
            title = str(task.get("title", "Task")).strip()
            status = str(task.get("status", "pending")).strip()
            tool = str(task.get("tool", "")).strip()
            hint = str(task.get("action_hint", "")).strip()
            task_lines.append(f"- {title} [{status}] tool={tool or 'n/a'} hint={hint or 'n/a'}")

        messages = [
            {
                "role": "system",
                "content": (
                    "You are the task agent's hidden execution strategist. "
                    "Return only short internal notes with 3 lines: Chain read, Best safe step, Stop condition. "
                    "Do not greet. Do not roleplay. Keep it tightly operational and permission-aware."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Intelligence level: {level}\n"
                    f"Objective: {objective}\n"
                    "Upcoming tasks:\n" + "\n".join(task_lines)
                ),
            },
        ]
        try:
            result = str(model_generate(messages) or "").strip()
        except Exception:
            return ""
        if result.startswith("Luna:"):
            result = result.removeprefix("Luna:").strip()
        if result.startswith("Task agent:"):
            result = result.removeprefix("Task agent:").strip()
        lowered = result.lower()
        if not result or lowered.startswith("lm studio") or lowered.startswith("unexpected"):
            return ""
        return result

    def format_run(self, run: AgentRun) -> str:
        lines = [
            f"Agent: {run.name}",
            f"Objective: {run.objective}",
            f"Current phase: {run.current_phase}",
            f"Execution mode: {run.execution_mode}",
            f"Recommended next action: {run.recommended_next_action}",
            f"Handoff: {self.create_handoff_summary(run)}",
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
            if step.action_ready:
                lines.append(f"   Agent handoff: {step.handoff_note or step.action_hint}")

        return "\n".join(lines)
