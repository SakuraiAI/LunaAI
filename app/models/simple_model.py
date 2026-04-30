from app.models.base_model import BaseModel


class SimpleModel(BaseModel):
    def generate(self, prompt: str | list[dict[str, str]]) -> str:
        if isinstance(prompt, list):
            last_user_messages = [item.get("content", "") for item in prompt if item.get("role") == "user"]
            last_input = (last_user_messages[-1] if last_user_messages else "").strip().lower()
        elif "User:" in prompt:
            last_input = prompt.split("User:")[-1].strip().lower()
        elif " User:" in prompt:
            last_input = prompt.split(" User:")[-1].strip().lower()
        else:
            last_input = prompt.strip().lower()

        if "hello" in last_input or "hi" in last_input:
            return "Luna: Hello, I am Luna. I am ready to help you with projects and ideas."

        if "what can you do" in last_input or "what do you do" in last_input:
            return "Luna: Right now I can handle simple chat, keep basic conversation context, and serve as a starting point for your local AI platform."

        if "project" in last_input:
            return "Luna: I can help you with project planning, structure, architecture, and further development."

        if "stop" in last_input:
            return "Luna: Understood. I will try to respond more precisely to your last message."

        if "end" in last_input or "quit" in last_input:
            return "Luna: Understood."

        return "Luna: I understand. I am still in an early version, but we can already communicate together."
