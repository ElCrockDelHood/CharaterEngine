"""Create the project virtual environment and install all dependencies.

    python scripts/bootstrap.py            # .venv with backend + dev extras
    python scripts/bootstrap.py --minimal  # domain only (no backend deps)

Never commit the virtual environment (it is machine specific; see .gitignore).
"""

import argparse
import sys
import venv

from _common import ROOT, VENV_DIR, run, venv_python


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--minimal", action="store_true", help="Install only the pure domain package")
    parser.add_argument("--recreate", action="store_true", help="Delete and recreate the venv")
    args = parser.parse_args()

    if args.recreate and VENV_DIR.exists():
        import shutil
        shutil.rmtree(VENV_DIR)

    if not VENV_DIR.exists():
        print(f"Creating venv at {VENV_DIR} with {sys.executable}")
        venv.EnvBuilder(with_pip=True, upgrade_deps=True).create(VENV_DIR)

    py = venv_python()
    extras = "[dev]" if args.minimal else "[backend,dev,schema]"
    run([py, "-m", "pip", "install", "--upgrade", "pip"])
    run([py, "-m", "pip", "install", "-e", f"{ROOT}{extras}"])
    print("\nBootstrap complete. Activate with:")
    print(r"  .venv\Scripts\activate    (Windows)")
    print("  source .venv/bin/activate (Linux/macOS)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
