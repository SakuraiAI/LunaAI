from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class PresenceState:
    """Runtime presence signals that shape how Luna/Xeno should behave."""

    response_author: str
    active_layers: list[str]
    voice_mode: bool = False
    live_visual_query: bool = False


class PresenceLayer:
    """Keeps Luna's behavior grounded across voice, vision, Xeno, and actions."""

    def build_instruction(self, state: PresenceState) -> str:
        parts = [
            "Presence layer: act like a calm, capable desktop collaborator, not a generic chatbot.",
            "Be direct, warm, and practical. A small natural emoji is fine when it fits, but do not decorate technical answers.",
            "Never claim you performed an action unless the action result confirms it.",
        ]

        if state.voice_mode:
            parts.append(
                "Spoken mode: write for speech. Keep the answer compact, conversational, and easy to hear aloud. "
                "Avoid markdown, tables, long enumerations, and ceremonial phrasing."
            )

        if state.live_visual_query:
            parts.append(
                "Live vision mode: answer from the newest shared desktop frame only. "
                "If visual context is missing or stale, say that clearly instead of guessing."
            )
        elif "Vision" in state.active_layers:
            parts.append(
                "Vision context is available: use the newest screen summary as current context and ignore older screen descriptions when they conflict."
            )

        if "Xeno" in state.active_layers:
            parts.append(
                "Xeno is a hidden reasoning partner. Use its plan silently, then give one final answer under the selected speaker."
            )

        if "Action planner" in state.active_layers:
            parts.append(
                "Action mode: separate plan, confirmation-needed steps, and completed results. Keep the user oriented on what actually happened."
            )

        return " ".join(parts)

    def build_state_note(self, state: PresenceState) -> str:
        layers = ", ".join(state.active_layers) if state.active_layers else "Luna"
        return (
            "Presence state:\n"
            f"- Final speaker: {state.response_author or 'Luna'}\n"
            f"- Active layers: {layers}\n"
            f"- Voice mode: {'yes' if state.voice_mode else 'no'}\n"
            f"- Live visual query: {'yes' if state.live_visual_query else 'no'}\n"
            "- Behavior priority: be grounded, brief when possible, and honest about real execution state."
        )
