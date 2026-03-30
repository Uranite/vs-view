import argparse
import os
import sys
from logging import INFO, getLogger
from pathlib import Path

from vsview.logging import setup_logging

setup_logging(int(os.getenv("PYI_LOG_LEVEL", INFO)))

ROOT_DIR = Path.cwd()
SPEC_PATH = (Path(__file__).parent / "vsview.spec").resolve()

logger = getLogger(__name__)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build the vsview executable with PyInstaller.")
    parser.add_argument(
        "--onefile",
        action="store_true",
        help="Bundle the application into a single executable instead of an onedir build.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    logger.info("Executing PyInstaller...")
    try:
        import PyInstaller.__main__

        if args.onefile:
            os.environ["VSVIEW_PYI_ONEFILE"] = "1"
            logger.info("----------- Build mode: onefile -----------")
        else:
            os.environ.pop("VSVIEW_PYI_ONEFILE", None)
            logger.info("----------- Build mode: onedir -----------")

        PyInstaller.__main__.run(["--noconfirm", "--clean", str(SPEC_PATH)])
    except Exception:
        logger.exception("PyInstaller failed")
        sys.exit(1)

    logger.info("----------- Build completed successfully! -----------")
    dist_dir = ROOT_DIR / "dist"
    logger.info("----------- Output folder located in: %s -----------", dist_dir)


if __name__ == "__main__":
    main()
