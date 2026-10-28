# Git Desk — Windows x64

Double-click `GitDesk.exe` to run. There is no installer and no Python setup is
needed on the target computer. Git for Windows must be installed and available
in PATH (verify with `git --version`). Restart Git Desk after installing Git.

Target: Windows 10 / 11, 64-bit x86_64. ARM64 and 32-bit builds are not included.
Built with Windows CPython 3.12.10 and PyInstaller 6.22.3. Smoke-tested under
Wine 10 using real Windows Git, including startup, repository operations, and
the compiled authentication helper. Native Windows testing is still pending.

Open a repository with **Open repository**. You can paste a folder path or use
**Browse** to open the normal Windows folder picker. Stage / Add the files,
write a message, click **Commit staged**, and then **Push**.

Authentication uses Git credential helpers or SSH agents that are already
configured. HTTPS can also display a username / password / token dialog.
The executable keeps piped stdout available for Git's authentication helper,
while hiding its own console when opened from Explorer. Do not rebuild it
with --windowed / --noconsole without also replacing the stdout-based helper.

You can run the program with a repository path:

```bat
GitDesk.exe "C:\Projects\My repository"
```

This local build is unsigned. It is a portable executable, not a Windows installer.
SHA256SUMS contains the hash of GitDesk.exe.

## Rebuild on Windows

Install 64-bit Python 3.12 with Tcl/Tk and the `py` launcher. Run `build_windows.cmd`
from the source project. It installs the build tool into an isolated virtual
environment, generates `dist\windows-x86_64\GitDesk.exe`, and writes
`dist\GitDesk-Windows-x86_64.zip`.
