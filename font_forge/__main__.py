"""
CLI entry point.

    python -m font_forge                    build the default config
    python -m font_forge my_config.json     build a specific config
    python -m font_forge studio             open the drag-and-drop studio
"""
import argparse
import sys
from pathlib import Path

from font_forge.config import load_config
from font_forge.core import SheetToFontBuilder

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CONFIG = ROOT / "configs" / "ethernium.json"


def run_build(config_path: Path) -> int:
    if not config_path.is_file():
        print(f"Config not found: {config_path}")
        return 1

    config = load_config(config_path)
    # A studio config sits next to its own sheet; the bundled configs live in
    # configs/ and refer to sheets at the project root.
    root = config_path.parent
    if not (root / config["sheet"]).is_file():
        root = ROOT
    SheetToFontBuilder(config, root).build()
    print("\nDone.")
    return 0


def run_studio(args: argparse.Namespace) -> int:
    from font_forge.studio import serve

    serve(
        workspace=Path(args.workspace).resolve(),
        port=args.port,
        open_browser=not args.no_browser,
    )
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(prog="font_forge", description=__doc__)
    sub = parser.add_subparsers(dest="command")

    studio = sub.add_parser("studio", help="drag an alphabet image, get a font")
    studio.add_argument("--workspace", default=str(ROOT / "studio_out"),
                        help="where sheets, configs and fonts are written")
    studio.add_argument("--port", type=int, default=8730)
    studio.add_argument("--no-browser", action="store_true")

    build = sub.add_parser("build", help="build a font from a config")
    build.add_argument("config", nargs="?", default=str(DEFAULT_CONFIG))

    # Bare `python -m font_forge [config.json]` still builds, as before.
    argv = sys.argv[1:]
    if argv and argv[0] not in {"studio", "build", "-h", "--help"}:
        argv = ["build", *argv]
    args = parser.parse_args(argv)

    if args.command == "studio":
        return run_studio(args)
    return run_build(Path(getattr(args, "config", DEFAULT_CONFIG)))


if __name__ == "__main__":
    raise SystemExit(main())
