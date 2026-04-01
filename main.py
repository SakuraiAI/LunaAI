import os
import sys

from app.core.engine import LunaEngine
from app.core.logger import get_logger
from app.ui.desktop_app import LunaDesktopApp
from app.ui.qml_app import LunaQmlApp


logger = get_logger(__name__)


def _ui_choice() -> str:
    if "--qml" in sys.argv:
        return "qml"
    if "--widgets" in sys.argv:
        return "widgets"
    return os.getenv("LUNA_UI", "widgets").strip().lower() or "widgets"


def main() -> None:
    engine = LunaEngine()
    choice = _ui_choice()
    try:
        if choice == "qml":
            app = LunaQmlApp(engine)
        else:
            app = LunaDesktopApp(engine)
        app.run()
    except Exception as error:
        logger.exception("Desktop UI failed, falling back to CLI: %s", error)
        engine.run()


if __name__ == "__main__":
    main()
