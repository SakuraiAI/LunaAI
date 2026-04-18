from app.workflow.models import WorkflowDecision


class LearningWorkflow:
    def run(self, user_input: str) -> WorkflowDecision:
        return WorkflowDecision(
            mode="learning",
            selected_mode="learning",
            automation_mode="learning",
            strategy="explain",
            reasoning_box="white_box",
            instruction=(
                "Explain in detail and teach step by step. "
                "Use clear structure, adult language, and practical examples. "
                "Be patient and precise, but do not sound patronizing or generic."
            ),
            user_input=user_input,
        )
