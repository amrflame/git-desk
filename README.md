<div align="center">

<img src="vscode-extension/media/git-desk.svg" width="72" height="72" alt="Git Desk logo">

# Git Desk

**A simple, organized interface for everyday Git work.**

Manage repositories, branches, changes, and commits from a standalone desktop app or a native VS Code sidebar.

[Download](#download) · [Quick start](#quick-start) · [VS Code extension](#vs-code-extension) · [Run from source](#run-from-source) · [Build](#build-from-source)

</div>

---

## Overview

Git Desk brings the essential Git workflow into one place: open a repository, inspect changes, stage files, write a commit, and push. The desktop application is implemented in a **single Python file** using Tkinter, with no third-party runtime Python packages.

The VS Code extension provides the same core workflow through native sidebar views, file diffs, and command-palette actions. It runs directly in VS Code and does not require Python or the desktop app.

| Edition | Best for | Requirements |
| --- | --- | --- |
| Linux desktop | A portable Git GUI on Ubuntu / Zorin OS | Git installed; x86_64 Linux desktop |
| Windows desktop | A portable Git GUI on Windows | Git for Windows installed; x64 Windows |
| VS Code extension | Working with Git inside your editor | VS Code 1.96.0 or newer; Git; built-in Git extension enabled |
| Python source | Running or customizing the desktop application | Python 3.10 or newer; Tkinter; Git |

## Features

- **Open repositories your way:** type or paste a path, or browse folders.
- **See your branches:** local branches, remote branches, and the active branch.
- **Switch or create branches:** work with local branches or track a remote branch.
- **Inspect changes:** see file status and preview edits before committing.
- **Stage selected files or everything:** choose exactly what enters the next commit.
- **Unstage without losing edits:** remove files from the index while preserving their working copies.
- **Commit staged changes:** add a message and create a local commit.
- **Fetch, pull, and push:** update remote references, pull fast-forward updates, and publish commits.
- **Follow repository activity:** view operation results and the latest known upstream status.

The desktop app also includes recent commit history and keeps Git operations in background threads so the interface stays responsive.

## Download

Prebuilt packages are included in this repository:

| Package | Download | Launch |
| --- | --- | --- |
| Linux x86_64 | [GitDesk-Ubuntu-x86_64.tar.gz](dist/GitDesk-Ubuntu-x86_64.tar.gz?raw=true) | Extract, then run `GitDesk` |
| Windows x64 | [GitDesk-Windows-x86_64.zip](dist/GitDesk-Windows-x86_64.zip?raw=true) | Extract, then run `GitDesk.exe` |
| VS Code extension | [git-desk-controller-0.1.0.vsix](git-desk-controller-0.1.0.vsix?raw=true) | Install through VS Code |

Prefer the executable on its own? Download [GitDesk for Linux](dist/linux-x86_64/GitDesk?raw=true) or [GitDesk.exe for Windows](dist/windows-x86_64/GitDesk.exe?raw=true).

**Desktop executables include Python and Tkinter. You only need Git installed; you do not need to install Python to use them.**

### Platform and validation status

| Target | Validation |
| --- | --- |
| Linux x86_64 | Built and smoke-tested on Zorin OS 18 / Ubuntu 24.04 |
| Windows x64 | Built with Windows Python; tested under Wine 10 with real Windows Git. Native Windows testing is pending. |
| VS Code | Tested in an Extension Development Host with temporary repositories and a local Git remote |

Older Ubuntu releases, ARM64, and 32-bit desktop builds have not been validated. The Windows executable is unsigned. This project currently ships portable executables rather than system installers.

## Quick start

### Linux

Extract the Linux archive and open a terminal in the extracted folder:

```bash
chmod +x GitDesk
./GitDesk
```

To open a repository immediately:

```bash
./GitDesk "/path/to/your/repository"
```

You can also open the executable from your file manager after allowing it to run as a program.

### Windows

1. Install Git for Windows if it is not already available.
2. Extract `GitDesk-Windows-x86_64.zip`.
3. Double-click `GitDesk.exe`.
4. Select **Open repository…**, then enter a folder path or choose **Browse…**.

To open a repository from Command Prompt:

```bat
GitDesk.exe "C:\Projects\My repository"
```

### Your first commit

1. Open an existing Git repository.
2. Select a changed file to inspect its preview.
3. Select the files you want to include and click **Stage selected**, or use **Stage all**.
4. Enter a message in **COMMIT MESSAGE**.
5. Click **Commit staged** to create the local commit.
6. Click **Push** when you are ready to send your commits to the remote.

**Stage is Git Add.** Staging prepares changes for a commit; it does not commit or upload them. **Unstage** removes changes from the staging area without discarding your edits.

### Desktop keyboard shortcuts

| Shortcut | Action |
| --- | --- |
| `Ctrl+O` | Open a repository |
| `F5` | Refresh repository state |
| `Ctrl+Enter` | Commit staged changes using the entered message |
| `Ctrl` / `Shift` + click | Select multiple files |

## VS Code extension

The extension adds a **Git Desk** icon to VS Code's Activity Bar, with three views:

| View | What you can do |
| --- | --- |
| **Repository** | Choose a repository, see the current branch and upstream, fetch, pull, push, and commit |
| **Branches** | Browse local and remote branches, create a branch, and switch branches |
| **Changes** | Inspect diffs, select files, stage or unstage changes, and commit staged files |

### Install from VSIX

1. Download the `.vsix` package above.
2. Open VS Code's Extensions view with `Ctrl+Shift+X`.
3. Open the **…** menu and select **Install from VSIX…**.
4. Choose the downloaded file, then open **Git Desk** from the Activity Bar.

Alternatively, from the repository root:

```bash
code --install-extension git-desk-controller-0.1.0.vsix
```

The Changes header includes **Stage All** (`+`) and **Commit Staged** (`✓`). Select multiple files with Ctrl/Shift and use the inline buttons, context menu, or view menu for selected-file operations. All extension commands are also available through `Ctrl+Shift+P` under **Git Desk**.

The publisher is `amr-metwally`; the extension identifier is `amr-metwally.git-desk-controller`. The extension uses VS Code's Git authentication and remembers the selected repository for the workspace. The selected workspace must be trusted before the extension can run.

See the [extension guide](vscode-extension/README.md) for more details.

## Run from source

The desktop application's runtime source is [git_gui.py](git_gui.py). It uses the Python standard library and Tkinter; no `pip install` is required to run it.

On Ubuntu, install the runtime prerequisites if needed:

```bash
sudo apt install git python3 python3-tk
```

From the repository root:

```bash
python3 git_gui.py
```

Or pass a repository path:

```bash
python3 git_gui.py "/path/to/repository"
```

On Windows, install Python with Tcl/Tk support and Git for Windows, then run:

```bat
py -3 git_gui.py
```

## Build from source

### Linux executable

Build on Linux x86_64 using Python with Tkinter and `venv` support. On Ubuntu, `python3-venv` may also be needed for building.

```bash
chmod +x build_linux.sh
./build_linux.sh
```

The script creates an isolated build environment, installs PyInstaller 6.22.3, and produces:

```text
dist/linux-x86_64/GitDesk
dist/GitDesk-Ubuntu-x86_64.tar.gz
```

See [Linux packaging notes](packaging/linux/README.md) for runtime and compatibility details.

### Windows executable

On Windows, install 64-bit Python with Tcl/Tk and the `py` launcher. Python 3.12 was used for the existing build. From Command Prompt at the repository root:

```bat
build_windows.cmd
```

The script uses an isolated build environment and produces:

```text
dist\windows-x86_64\GitDesk.exe
dist\GitDesk-Windows-x86_64.zip
```

The Windows build hides its console when launched from Explorer while preserving piped output for Git's authentication helper. See [Windows packaging notes](packaging/windows/README.md) before changing these build options.

### VS Code package

Build the local VSIX package from the repository root using Python 3:

```bash
python3 vscode-extension/build_vsix.py
```

On Windows, the equivalent command is:

```bat
py -3 vscode-extension\build_vsix.py
```

To work on the extension, open the [vscode-extension](vscode-extension) folder in VS Code and press `F5` to launch the Extension Development Host. No npm runtime dependencies are required.

## Authentication and Git behavior

The desktop application uses existing Git credential helpers and SSH agents. For HTTPS, it can display a masked password or access-token prompt when credentials are needed. Git Desk does not persist credentials itself; configured Git helpers may store them according to their settings. The VS Code edition delegates authenticated operations to VS Code's built-in Git extension.

A few workflow details:

- **Pull is fast-forward only.** If branches have diverged, resolve the merge or rebase through your usual Git tools before pulling again.
- **Commit includes staged files only.** Unstaged changes stay in the working tree.
- **Push can set an upstream** when publishing a local branch for the first time.
- **Ahead/behind counts reflect the latest fetched state.** Fetch again to update your view of the remote.
- **Force push, destructive reset, and discard controls are not included.**

## Troubleshooting

| Issue | What to check |
| --- | --- |
| Git is not found | Verify `git --version` works in a terminal, then restart the application. |
| A folder cannot be opened | Select an existing Git repository or a folder inside one. |
| HTTPS authentication fails | Check your credential helper and your server's required sign-in or token permissions. |
| SSH authentication fails | Ensure your SSH key is configured and available through your SSH agent. |
| There is nothing to commit | Stage files first and enter a commit message. |
| Pull cannot fast-forward | Resolve branch divergence with your regular Git tools. |
| Linux reports permission denied | Allow executing the file, or run `chmod +x GitDesk`. |
| Source launch reports missing `tkinter` | Install Tkinter for the Python interpreter you are using. |
| VS Code commands are unavailable | Enable the built-in Git extension and trust the workspace. |

Desktop errors are recorded in **Activity**. Extension errors can open VS Code's **Git Output** panel.

## Repository layout

```text
.
├── README.md
├── git_gui.py                         # Single-file desktop application
├── build_linux.sh                     # Linux build script
├── build_windows.cmd                  # Windows build script
├── git-desk-controller-0.1.0.vsix       # Installable VS Code extension
├── vscode-extension/                  # Native VS Code extension source
│   ├── extension.js
│   ├── package.json
│   ├── build_vsix.py
│   ├── README.md
│   ├── LICENSE
│   └── media/
├── packaging/
│   ├── linux/                         # Linux packaging guide
│   └── windows/                       # Windows packaging guide and ZIP builder
└── dist/
    ├── GitDesk-Ubuntu-x86_64.tar.gz
    ├── GitDesk-Windows-x86_64.zip
    ├── linux-x86_64/                  # Executable, guide, SHA256SUMS
    └── windows-x86_64/                # Executable, guide, SHA256SUMS
```

Each desktop output folder includes `SHA256SUMS` for checking the executable against the packaged checksum. Local build environments and caches live under `.build/` and are not needed to run the application or distribute the packages.

## Contributing

Bug reports and improvements are welcome. When reporting a problem, include the edition you used, your OS version, the operation that failed, and the relevant error message. Test changes against a temporary Git repository before using them with your working projects.

The VS Code extension includes an [MIT license](vscode-extension/LICENSE).
