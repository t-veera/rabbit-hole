#!/usr/bin/env python3
"""Builds the packaged backend (app/desktop_main.py + a bundled Postgres via
pgserver) into a standalone onedir bundle with PyInstaller, for the current
OS only — PyInstaller doesn't cross-compile, so this runs once per OS in CI
(see .github/workflows/release.yml), same as electron-builder does for the
Electron shell around it.

Run from anywhere; paths below are all relative to this file.

    python desktop/build_backend.py

Output: backend/dist/rabbit-hole-backend/ (a folder — the shell's
package.json copies this into its own resources, see package.json's "extraResources").
"""

import importlib.util
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BACKEND = ROOT / "backend"
FRONTEND = ROOT / "frontend"

# PyInstaller's --add-data separator is ';' on Windows, ':' everywhere else.
SEP = ";" if sys.platform.startswith("win") else ":"


def _add_data(src: Path, dest: str) -> str:
    return f"{src}{SEP}{dest}"


def main() -> None:
    print("==> Building frontend")
    subprocess.run(["npm", "install"], cwd=FRONTEND, check=True, shell=sys.platform.startswith("win"))
    subprocess.run(["npm", "run", "build"], cwd=FRONTEND, check=True, shell=sys.platform.startswith("win"))

    frontend_dist = FRONTEND / "dist"
    if not frontend_dist.is_dir():
        raise SystemExit("frontend/dist wasn't produced by npm run build")

    dist_dir = BACKEND / "dist"
    build_dir = BACKEND / "build"
    for stale in (dist_dir, build_dir):
        if stale.exists():
            shutil.rmtree(stale)

    # pgserver's pginstall/ directory is a real, self-contained Postgres
    # install (bin/lib/share/include) whose binaries locate their own
    # plugins (e.g. lib/postgresql/dict_snowball.so) via a path computed
    # relative to bin/initdb at Postgres's own compile time — not via the
    # ELF dynamic linker. PyInstaller's usual binary collection (what
    # --collect-all does) doesn't know that and flattens those .so files
    # into _internal/ alongside unrelated system libraries, which silently
    # breaks that relative lookup (confirmed: initdb fails on
    # dict_snowball.so). Adding the whole directory as one opaque data blob
    # instead — bypassing PyInstaller's binary analysis for it entirely —
    # keeps the exact layout Postgres expects.
    pgserver_spec = importlib.util.find_spec("pgserver")
    if not pgserver_spec or not pgserver_spec.submodule_search_locations:
        raise SystemExit("pgserver isn't importable in this Python environment")
    pgserver_dir = Path(pgserver_spec.submodule_search_locations[0])

    print("==> Running PyInstaller")
    subprocess.run(
        [
            sys.executable,
            "-m",
            "PyInstaller",
            "--name",
            "rabbit-hole-backend",
            "--onedir",
            "--noconfirm",
            "--console",
            "--collect-submodules",
            "pgserver",
            "--add-data",
            _add_data(pgserver_dir / "pginstall", "pgserver/pginstall"),
            "--add-data",
            _add_data(BACKEND / "alembic.ini", "."),
            "--add-data",
            _add_data(BACKEND / "alembic", "alembic"),
            "--add-data",
            _add_data(frontend_dist, "frontend_dist"),
            str(BACKEND / "app" / "desktop_main.py"),
        ],
        cwd=BACKEND,
        check=True,
    )

    output = dist_dir / "rabbit-hole-backend"
    print(f"==> Backend bundle ready at {output}")


if __name__ == "__main__":
    main()
