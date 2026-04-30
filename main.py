from __future__ import annotations

import argparse

from app.core.engine import LunaEngine
from app.core.server import LunaServer
from app.ui.desktop_app import LunaDesktopApp


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="LunaAI launcher")
    parser.add_argument(
        "mode",
        nargs="?",
        choices=("cli", "desktop", "status", "server"),
        default="cli",
        help="Which LunaAI mode to run.",
    )
    return parser


def main() -> None:
    args = _build_parser().parse_args()

    if args.mode == "status":
        print(LunaServer().status_text())
        return

    if args.mode == "server":
        LunaServer().run()
        return

    engine = LunaEngine()

    if args.mode == "desktop":
        LunaDesktopApp(engine).run()
        return

    engine.run()


if __name__ == "__main__":
    main()
