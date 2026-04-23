from app.models.base_model import BaseModel


class SimpleModel(BaseModel):
    def generate(self, prompt: str | list[dict[str, str]]) -> str:
        if isinstance(prompt, list):
            last_user_messages = [msg["content"] for msg in prompt if msg["role"] == "user"]
            text = last_user_messages[-1].lower() if last_user_messages else ""
        else:
            text = prompt.lower()
            if "User:" in prompt:
                text = prompt.split("User:")[-1].strip().lower()

        if any(greeting in text for greeting in ["ahoj", "cau", "cao", "dobry den", "hello", "hi"]):
            return "Luna: Jsem tady 🙂 Co potrebujes?"

        if any(phrase in text for phrase in ["jak se mas", "jak se mas?", "how are you"]):
            return "Luna: Jsem připravená pokračovat 🙂 Co je teď potřeba?"

        if any(phrase in text for phrase in ["what can", "co umis", "co dokaz", "co dovede"]):
            return "Luna: Nejvic pomuzu s premyslenim nad projektem, dalsimi kroky a praktickym resenim problemu ✨"

        if "project" in text or "projekt" in text:
            return "Luna: Muzeme ho rozdelit na kroky, srovnat strukturu nebo vyresit dalsi tah 🚀"

        return "Luna: Rozumim. Pojdme to vzit po poradku. 🙂"
