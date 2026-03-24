class LearningWorkflow:
    def run(self, user_input: str) -> dict[str, str]:
        return {
            "mode": "learning",
            "instruction": (
                "Explain in detail and teach step by step. "
                "Use clear structure, simple language, and practical examples. "
                "When useful, break the answer into parts and go deeper than a short summary."
            ),
            "user_input": user_input,
        }
