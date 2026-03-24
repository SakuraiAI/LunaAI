def build_chat_prompt(
    system_prompt: str,
    user_input: str,
    history_text: str = "",
    mode: str = "collaboration",
) -> str:
    return f"""
{system_prompt}

Mode: {mode}

History:
{history_text}

User: {user_input}
""".strip()
