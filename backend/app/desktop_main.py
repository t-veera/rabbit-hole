"""Entry point for the packaged desktop build (see desktop/), not the normal
dev flow (README's two-terminal `uvicorn --reload` + `npm run dev`).

Starts a local, bundled Postgres via pgserver — real binaries, no Docker, no
system install, no root — instead of the docker-compose Postgres the dev
flow uses, runs migrations against it, then serves the exact same app
(including the built frontend, via app.main's static-file mount) on one
port. This is the process the Electron shell (desktop/main.js) spawns and
waits on; pgserver's own process-exit hook stops Postgres cleanly when this
process exits, so the shell doesn't need to manage that separately.
"""

import os
import signal
import sys
from pathlib import Path


def _resource_path(relative: str) -> Path:
    """Resolves a bundled resource both when frozen by PyInstaller
    (extracted under sys._MEIPASS) and when run straight from source
    (this file lives at backend/app/desktop_main.py, so its grandparent
    is backend/, where alembic.ini actually lives)."""
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[1]))
    return base / relative


def _app_data_dir() -> Path:
    import platformdirs

    return Path(platformdirs.user_data_dir("RabbitHole", "RabbitHole"))


def _restore_system_library_path() -> None:
    """PyInstaller points LD_LIBRARY_PATH at its bundled libs, and child
    processes inherit it. pgserver's initdb shells out via /bin/sh, so the
    system shell ends up loading our older bundled libreadline and dies
    (`undefined symbol: rl_print_keybinding` on Arch), which initdb reports
    as "postgres not found". Our own libs are already loaded by now, and the
    Postgres binaries don't need the override, so hand children the
    original value back."""
    if not getattr(sys, "frozen", False):
        return
    original = os.environ.pop("LD_LIBRARY_PATH_ORIG", None)
    if original is not None:
        os.environ["LD_LIBRARY_PATH"] = original
    else:
        os.environ.pop("LD_LIBRARY_PATH", None)


def _prune_dead_pgserver_handles(pg_data_dir: Path) -> None:
    """pgserver only stops Postgres when the last process in its
    .handle_pids.json exits. A run that died without cleaning up (crash,
    SIGKILL, power loss) leaves its PID in there for good, so every later
    run thinks another handle is still open and leaves Postgres running on
    quit. Drop PIDs that no longer exist before taking our own handle."""
    import json

    import psutil

    handles = pg_data_dir / ".handle_pids.json"
    try:
        pids = json.loads(handles.read_text())
    except (OSError, ValueError):
        return
    live = [pid for pid in pids if psutil.pid_exists(pid)]
    if live != pids:
        handles.write_text(json.dumps(live))


def main() -> None:
    _restore_system_library_path()

    import pgserver

    data_dir = _app_data_dir()
    pg_data_dir = data_dir / "pgdata"
    pg_data_dir.mkdir(parents=True, exist_ok=True)
    _prune_dead_pgserver_handles(pg_data_dir)

    print(f"[rabbit-hole] starting local Postgres in {pg_data_dir}", flush=True)
    db = pgserver.get_server(str(pg_data_dir))
    os.environ["DATABASE_URL"] = db.get_uri().replace("postgresql://", "postgresql+psycopg://", 1)

    # No .env file in a packaged install — every setting either has a safe
    # default already (app/config.py) or the user adds it later from the
    # Settings page (services/settings_store.py), which needs no restart.

    frontend_dist = _resource_path("frontend_dist")
    if frontend_dist.is_dir():
        os.environ["FRONTEND_DIST_DIR"] = str(frontend_dist)

    print("[rabbit-hole] running database migrations", flush=True)
    from alembic import command
    from alembic.config import Config

    alembic_cfg = Config(str(_resource_path("alembic.ini")))
    alembic_cfg.set_main_option("script_location", str(_resource_path("alembic")))
    command.upgrade(alembic_cfg, "head")

    print("[rabbit-hole] starting server on http://127.0.0.1:8420", flush=True)
    import uvicorn

    from app.main import app  # imported after DATABASE_URL is set — app.db reads it at import time

    # The shell quits us with SIGTERM. Uvicorn shuts down gracefully, then
    # re-raises that signal once it restores the previous handler, and with
    # the default handler that kills the process before the finally below
    # (or pgserver's atexit hook) runs, leaving Postgres orphaned. Exiting
    # normally on SIGTERM instead lets cleanup happen.
    signal.signal(signal.SIGTERM, lambda *_: sys.exit(0))

    try:
        uvicorn.run(app, host="127.0.0.1", port=8420, log_level="info")
    finally:
        db.cleanup()


if __name__ == "__main__":
    main()
