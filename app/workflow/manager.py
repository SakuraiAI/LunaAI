from app.workflow.auto_mode import AutoMode
from app.workflow.collaboration import CollaborationWorkflow
from app.workflow.learning import LearningWorkflow


class WorkflowManager:
    def __init__(self) -> None:
        self.mode = "auto"
        self.manual_override = False
        self.learning = LearningWorkflow()
        self.collaboration = CollaborationWorkflow()
        self.auto_mode = AutoMode()

    def set_mode(self, mode: str, manual_override: bool = True) -> None:
        self.mode = mode
        self.manual_override = manual_override

    def process(
        self,
        user_input: str,
        history: list[dict[str, str]] | None = None,
    ) -> dict[str, str]:
        history = history or []
        text = user_input.strip().lower()

        if text == "/learning":
            self.set_mode("learning", manual_override=True)
            return {
                "mode": self.mode,
                "selected_mode": self.mode,
                "reasoning_box": "white_box",
                "user_input": user_input,
                "system_message": "Mode changed to learning.",
                "instruction": (
                    "Explain in detail, step by step, with examples and clear structure."
                ),
                "context": self.build_context(history),
            }

        if text == "/collaboration":
            self.set_mode("collaboration", manual_override=True)
            return {
                "mode": self.mode,
                "selected_mode": self.mode,
                "reasoning_box": self.select_reasoning_box(user_input, "collaboration"),
                "user_input": user_input,
                "system_message": "Mode changed to collaboration.",
                "instruction": (
                    "Help create, structure, and improve ideas with practical next steps."
                ),
                "context": self.build_context(history),
            }

        if text == "/auto":
            self.set_mode("auto", manual_override=False)
            workflow_data = self.auto_mode.run(user_input)
            workflow_data["mode"] = "auto"
            workflow_data["reasoning_box"] = "black_box"
            workflow_data["system_message"] = "Mode changed to auto. Luna will now choose the style automatically."
            workflow_data["context"] = self.build_context(history)
            return workflow_data

        if self.manual_override:
            if self.mode == "learning":
                workflow_data = self.learning.run(user_input)
            elif self.mode == "collaboration":
                workflow_data = self.collaboration.run(user_input)
            else:
                workflow_data = self.auto_mode.run(user_input)
                workflow_data["mode"] = "auto"
        else:
            selected_mode = self.auto_mode.decide(user_input)
            if selected_mode == "learning":
                workflow_data = self.learning.run(user_input)
            elif selected_mode == "collaboration":
                workflow_data = self.collaboration.run(user_input)
            else:
                workflow_data = self.auto_mode.run(user_input)
            workflow_data["mode"] = "auto"
            workflow_data["selected_mode"] = selected_mode

        workflow_data.setdefault("selected_mode", workflow_data.get("mode", "auto"))
        workflow_data["reasoning_box"] = self.select_reasoning_box(
            user_input,
            workflow_data.get("selected_mode", "auto"),
        )
        workflow_data["system_message"] = None
        workflow_data["context"] = self.build_context(history)
        return workflow_data

    def select_reasoning_box(self, user_input: str, selected_mode: str) -> str:
        normalized = user_input.strip().lower()
        white_box_signals = [
            "explain",
            "detail",
            "detailed",
            "step by step",
            "show me how",
            "teach",
            "why",
            "how",
            "understand",
            "example",
            "examples",
            "jak",
            "proc",
            "vysvetli",
            "podrobne",
            "detailne",
            "ukaz postup",
            "priklad",
            "priklady",
        ]

        if selected_mode == "learning":
            return "white_box"

        if any(signal in normalized for signal in white_box_signals):
            return "white_box"

        return "black_box"

    def build_context(self, history: list[dict[str, str]]) -> str:
        if not history:
            return ""
        last_messages = history[-3:]
        return " | ".join(item["content"] for item in last_messages)
