# Desktop packaging

Wraps the backend + a locally bundled Postgres (via [pgserver](https://github.com/orm011/pgserver),
real Postgres binaries with no Docker/system install/root needed) and the
built frontend into one double-clickable app per OS, using the same
Electron + electron-builder approach as [Folio](https://github.com/t-veera/folio).

Unlike Folio, there's a real backend + database here, not just a renderer —
so the packaging has an extra step: PyInstaller bundles `backend/app/desktop_main.py`
(which starts pgserver, runs migrations, then serves the app — see that
file's docstring) into a standalone executable, which the Electron shell
(`main.js`) spawns as a child process and waits on before opening a window.

## Building locally

Needs Python 3.9-3.12 specifically (pgserver's published wheel range —
newer Python versions aren't covered yet) and Node 20+.

```bash
pip install -r ../backend/requirements-desktop.txt
python build_backend.py          # -> ../backend/dist/rabbit-hole-backend/
npm install
npm run dist-linux                # or dist-win / dist-mac / dist-all
```

Output lands in `desktop/release/`.

PyInstaller doesn't cross-compile — building a real Windows/macOS artifact
means running this on that OS. `.github/workflows/release.yml` does exactly
that: a 3-OS matrix (windows-latest/ubuntu-latest/macos-latest), each
running the same two commands above natively, triggered by pushing a `v*`
tag. That's also the actual verification path for Windows/macOS — GitHub's
runners are real Windows/macOS machines, so a green build there means the
installer was genuinely produced on that OS, not just written by hand and
hoped to work.

## The one non-obvious gotcha

pgserver's `pginstall/` directory is a real Postgres install (bin/lib/share),
and its binaries locate their own plugins (e.g. `lib/postgresql/dict_snowball.so`)
via a path computed relative to `bin/initdb` at Postgres's own compile time —
not via the normal dynamic linker. PyInstaller's usual `--collect-all` flattens
`.so`/`.dll` files it finds into `_internal/` for its own dependency
analysis, which silently breaks that relative lookup (confirmed:
`initdb` fails with `could not access file "$libdir/dict_snowball"`).
`build_backend.py` bundles all of `pginstall/` as one opaque data blob
instead, bypassing PyInstaller's binary analysis for it entirely — keep
that if you ever touch the PyInstaller invocation.

## Data location

The bundled Postgres's data directory lives in the OS's normal per-user app
data folder (`platformdirs.user_data_dir("RabbitHole", "RabbitHole")`) —
e.g. `~/.local/share/RabbitHole/pgdata` on Linux, `~/Library/Application
Support/RabbitHole/pgdata` on macOS, `%LOCALAPPDATA%\RabbitHole\pgdata` on
Windows. Deleting that folder resets the app to a fresh database.
