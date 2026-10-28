# Git Desk for VS Code

A compact native sidebar for Git repositories, branches, staging, commits, and sync.
No Python or npm dependencies are required to use the extension. Git must be installed,
and VS Code's built-in **Git** extension must be enabled.

## Install

1. In VS Code, open Extensions (`Ctrl+Shift+X`).
2. Open the `…` menu and choose **Install from VSIX…**.
3. Select `git-desk-controller-0.1.0.vsix`.
4. Click the **Git Desk** branch icon in the Activity Bar.

Alternatively: `code --install-extension /absolute/path/to/git-desk-controller-0.1.0.vsix`

## Use

- **Repository → Open Repository**: enter/paste a path or browse with VS Code's picker.
- **Select Repository** switches between repositories already detected by VS Code.
- **Branches** shows local and remote branches. The current branch has a checkmark.
  Use the branch's inline switch button or the toolbar's Switch Branch button.
  The `+` button creates and switches to a new branch.
- **Changes** groups staged and unstaged files. Click a file for the editor diff.
  Ctrl/Shift-select files and use the inline `+` / `−`, context menu, or `…` menu
  for **Stage Selected (Add)** / **Unstage Selected**.
- The Changes header has **Stage All** (`+`) and **Commit Staged** (`✓`).
  Commit asks for a message and includes staged files only.
- **Repository** includes visible **Fetch**, **Pull**, **Push**, and **Commit staged** actions.
- Every action is also available in the Command Palette (`Ctrl+Shift+P`) under **Git Desk**.

Fetch/Pull/Push use VS Code's built-in Git API and its existing authentication helpers.
If your provider needs a PAT or SSH setup, configure it as you would for regular VS Code Git.
This extension does not store passwords or tokens.
Pull fetches the upstream remote and only allows fast-forward updates. If branches diverge,
resolve that in VS Code's regular Git tools before pulling again. Push publishes a new
branch and sets its upstream when none exists. Force push is not included.

Operations act on the repository selected in **Git Desk**, including when several repositories
are open. The selection is remembered for the workspace. Untrusted workspaces are unsupported;
trust your workspace before using Git Desk. Git errors offer the built-in **Git Output** log.

## Development

Open this folder in VS Code and press `F5` to start the Extension Development Host.
The runtime source is `extension.js`; contributions and menus are in `package.json`.
Run `node --check extension.js` to validate JavaScript syntax.

To rebuild the installable package with Python 3: `python3 build_vsix.py`.
The desktop Python application remains available separately in the parent folder.
