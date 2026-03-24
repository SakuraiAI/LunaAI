from app.models.base_model import BaseModel


class SimpleModel(BaseModel):
    def generate(self, prompt: str | list[dict[str, str]]) -> str:
        print("DEBUG MODEL USED")

        if isinstance(prompt, list):
            last_user_messages = [msg["content"] for msg in prompt if msg["role"] == "user"]
            text = last_user_messages[-1].lower() if last_user_messages else ""
        else:
            text = prompt.lower()
            if "User:" in prompt:
                text = prompt.split("User:")[-1].strip().lower()

        print("DEBUG last_input:", text)

        if "hello" in text or "hi" in text:
            return "Luna: Hello, I am Luna. I am happy to help you with projects and ideas."

        if "what can" in text:
            return "Luna: Right now I can handle basic chat, keep conversation memory, and continue growing over time."

        if "project" in text:
            return "Luna: I can help you with project design, structure, and development."

        return "Luna: I understand. I am still in an early version, but we can already communicate together."
