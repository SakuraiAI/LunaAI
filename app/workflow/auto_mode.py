from app.workflow.models import WorkflowDecision


class AutoMode:
    def decide(self, message: str) -> str:
        normalized = message.lower()

        learning_keywords = [
            "learn",
            "explain",
            "teach",
            "understand",
            "how does",
            "what is",
            "why",
            "jak",
            "proc",
            "vysvetli",
            "nauc",
            "co je",
        ]
        collaboration_keywords = [
            "build",
            "create",
            "make",
            "write",
            "project",
            "plan",
            "design",
            "improve",
            "pomoz mi",
            "udelat",
            "navrhni",
            "vytvor",
            "projekt",
        ]

        if any(keyword in normalized for keyword in learning_keywords):
            return "learning"

        if any(keyword in normalized for keyword in collaboration_keywords):
            return "collaboration"

        return "auto"

    def choose_strategy(self, user_input: str) -> str:
        normalized = user_input.lower()
        explanation_signals = ["how", "why", "what", "explain", "understand", "jak", "proc", "co"]
        action_signals = [
            "build", "make", "create", "fix", "plan", "write", "udelat", "vytvor",
            "otevri", "open", "implement", "scaffold", "workflow", "agent"
        ]

        if any(signal in normalized for signal in explanation_signals):
            return "explain"

        if any(signal in normalized for signal in action_signals):
            return "act"

        return "balanced"

    def run(self, user_input: str) -> WorkflowDecision:
        strategy = self.choose_strategy(user_input)

        if strategy == "explain":
            instruction = (
                "Auto mode selected explanation-first. "
                "Answer like a capable human colleague: clear, calm, and specific. "
                "Give enough detail to be useful, but skip filler."
            )
            automation_mode = "learning"
            reasoning_box = "white_box"
        elif strategy == "act":
            instruction = (
                "Auto mode selected action-first. "
                "Focus on concrete steps, useful structure, and practical execution. "
                "Keep the tone composed and direct."
            )
            automation_mode = "execution"
            reasoning_box = "black_box"
        else:
            instruction = (
                "Auto mode selected a balanced response. "
                "Combine a clear explanation with practical next steps. "
                "Keep the answer natural and avoid generic assistant filler."
            )
            automation_mode = "balanced"
            reasoning_box = "black_box"

        return WorkflowDecision(
            mode="auto",
            selected_mode="auto",
            strategy=strategy,
            automation_mode=automation_mode,
            reasoning_box=reasoning_box,
            instruction=instruction,
            user_input=user_input,
        )
