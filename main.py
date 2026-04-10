from app.core.engine import LunaEngine
from app.core.logger import get_logger


logger = get_logger(__name__)


def main() -> None:
    engine = LunaEngine()
    try:
        engine.run()
    except Exception as error:
        logger.exception("Backend CLI failed: %s", error)
        raise


if __name__ == "__main__":
    main()
