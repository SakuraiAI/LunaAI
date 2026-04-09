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
                "Use clear structure, simple language, and practical examples. "
                "When useful, break the answer into parts and go deeper than a short summary."
            ),
            user_input=user_input,
        )
