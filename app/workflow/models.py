from dataclasses import asdict, dataclass


@dataclass(slots=True)
class WorkflowDecision:
    mode: str
    user_input: str
    instruction: str = ""
    selected_mode: str = "auto"
    reasoning_box: str = "black_box"
    system_message: str | None = None
    context: str = ""
    strategy: str = "balanced"
    automation_mode: str = "balanced"

    def to_dict(self) -> dict[str, str | None]:
        return asdict(self)
