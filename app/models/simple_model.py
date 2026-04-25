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

        if any(
            phrase in text
            for phrase in [
                "sdílení obrazovky",
                "sdileni obrazovky",
                "sdílet obrazovku",
                "sdilet obrazovku",
                "share screen",
                "desktop share",
                "shere desktop",
                "share deskop",
                "shere deskop",
                "deskop share",
            ]
        ):
            return (
                "Luna: V LunaAI nepoužívej Zoom ani OBS. Otevři v aplikaci tlačítko +, zvol Desktop share, "
                "vyber obrazovku nebo okno a nech běžet živý náhled. Luna a Xeno pak čtou průběžně obnovované framy jako vizuální kontext. 👀"
            )

        if any(greeting in text for greeting in ["ahoj", "cau", "cao", "dobry den", "hello", "hi"]):
            return "Luna: Jsem tady 🙂 Co potřebuješ?"

        if any(phrase in text for phrase in ["jak se mas", "jak se máš", "how are you"]):
            return "Luna: Jsem připravená pokračovat 🙂 Co je teď potřeba?"

        if any(phrase in text for phrase in ["what can", "co umis", "co umíš", "co dokaz", "co dokáž"]):
            return "Luna: Nejvíc pomůžu s projektem, dalšími kroky, kódem, akcemi v PC a čtením obrazovky přes Desktop share ✨"

        if "project" in text or "projekt" in text:
            return "Luna: Můžeme ho rozdělit na kroky, srovnat strukturu nebo rovnou udělat další praktický tah 🚀"

        return "Luna: Rozumím. Pojďme to vzít prakticky a po pořádku 🙂"
