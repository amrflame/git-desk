# Git Desk — Ubuntu / Linux x86_64

`GitDesk` is a standalone desktop executable. Python, Tkinter and their runtime
are included. Git must already be installed (`git --version`).

Built and tested on Zorin OS 18 / Ubuntu 24.04 (64-bit x86_64).
Older Ubuntu releases and ARM devices have not been validated.

## Run

Extract the archive, then double-click `GitDesk` in the file manager.
If Ubuntu asks for execution permission, use Properties → Permissions →
Allow executing file as program, or run:

```bash
chmod +x GitDesk
./GitDesk
```

You can also open a repository directly:

```bash
./GitDesk "/path/to/your/repository"
```

No Python installation is needed on the target computer. Git authentication uses
existing credential helpers / SSH agents, with a GUI credentials fallback for HTTPS.
Do not put tokens into repository URLs. Browse uses Zenity or KDialog when available,
with the bundled Tk folder dialog as a fallback.

The one-file executable unpacks its runtime into a temporary directory at startup.
This needs a writable temporary directory that permits executing files.

## Rebuild

From the project root, run `./build_linux.sh` on Linux x86_64 with Python 3.10+
and Tkinter installed. The build uses an isolated virtual environment and pins
PyInstaller 6.22.3. Artifacts are written to `dist/linux-x86_64/`.

PyInstaller's Linux compatibility depends on the build system; building on an older
Ubuntu baseline is necessary before claiming support for older releases:
https://pyinstaller.org/en/stable/usage.html#making-gnu-linux-apps-forward-compatible
