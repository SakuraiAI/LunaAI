from app.workflow.auto_mode import AutoMode
from app.workflow.collaboration import CollaborationWorkflow
from app.workflow.learning import LearningWorkflow
from app.workflow.models import WorkflowDecision


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

    def _build_context(self, history: list[dict[str, str]]) -> str:
        if not history:
            return ""
        last_messages = history[-3:]
        return " | ".join(item.get("content", "") for item in last_messages if item.get("content"))

    def _command_decision(self, user_input: str, history: list[dict[str, str]]) -> WorkflowDecision | None:
        text = user_input.strip().lower()
        context = self._build_context(history)

        if text == "/learning":
            self.set_mode("learning", manual_override=True)
            return WorkflowDecision(
                mode="learning",
                selected_mode="learning",
                automation_mode="learning",
                reasoning_box="white_box",
                user_input=user_input,
                system_message="Mode changed to learning.",
                instruction="Explain in detail, step by step, with examples and clear structure.",
                context=context,
                strategy="explain",
            )

        if text == "/collaboration":
            self.set_mode("collaboration", manual_override=True)
            return WorkflowDecision(
                mode="collaboration",
                selected_mode="collaboration",
                automation_mode="execution",
                reasoning_box=self.select_reasoning_box(user_input, "collaboration"),
                user_input=user_input,
                system_message="Mode changed to collaboration.",
                instruction="Help create, structure, and improve ideas with practical next steps.",
                context=context,
                strategy="act",
            )

        if text == "/auto":
            self.set_mode("auto", manual_override=False)
            decision = self.auto_mode.run(user_input)
            decision.system_message = "Mode changed to auto. Luna will now choose the style automatically."
            decision.context = context
            return decision

        return None

    def process(
        self,
        user_input: str,
        history: list[dict[str, str]] | None = None,
    ) -> dict[str, str | None]:
        history = history or []
        command_decision = self._command_decision(user_input, history)
        if command_decision is not None:
            return command_decision.to_dict()

        if self.manual_override:
            if self.mode == "learning":
                decision = self.learning.run(user_input)
            elif self.mode == "collaboration":
                decision = self.collaboration.run(user_input)
            else:
                decision = self.auto_mode.run(user_input)
        else:
            selected_mode = self.auto_mode.decide(user_input)
            if selected_mode == "learning":
                decision = self.learning.run(user_input)
            elif selected_mode == "collaboration":
                decision = self.collaboration.run(user_input)
            else:
                decision = self.auto_mode.run(user_input)
            decision.selected_mode = selected_mode

        decision.mode = "auto" if not self.manual_override else self.mode
        if decision.selected_mode == "auto":
            decision.selected_mode = decision.mode
        decision.reasoning_box = self.select_reasoning_box(user_input, decision.selected_mode)
        decision.system_message = None
        decision.context = self._build_context(history)
        return decision.to_dict()

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
