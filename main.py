from app.core.engine import LunaEngine
from app.core.logger import get_logger
from app.ui.desktop_app import LunaDesktopApp


logger = get_logger(__name__)


def main() -> None:
    try:
        app = LunaDesktopApp(LunaEngine())
        app.run()
    except Exception as error:
        logger.exception("Desktop UI failed, falling back to CLI: %s", error)
        engine = LunaEngine()
        engine.run()


if __name__ == "__main__":
    main()
