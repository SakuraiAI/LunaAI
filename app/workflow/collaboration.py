from app.workflow.models import WorkflowDecision


class CollaborationWorkflow:
    def run(self, user_input: str) -> WorkflowDecision:
        return WorkflowDecision(
            mode="collaboration",
            selected_mode="collaboration",
            automation_mode="execution",
            strategy="act",
            instruction=(
                "Help the user build, plan, or improve something concrete. "
                "Be practical, organized, and action-oriented. "
                "Suggest steps, structure, and useful options instead of only giving theory."
            ),
            user_input=user_input,
        )
