'use strict';

const vscode = require('vscode');
const path = require('path');
const os = require('os');
const { execFile } = require('child_process');
const { promisify } = require('util');
const execute = promisify(execFile);
const NONE = vscode.TreeItemCollapsibleState.None;
const EXPANDED = vscode.TreeItemCollapsibleState.Expanded;
const STATUS = ['M', 'A', 'D', 'R', 'C', 'M', 'D', '?', '!', 'A', 'R', 'T', 'U', 'U', 'U', 'U', 'U', 'U', 'U'];

function item(label, icon, description, command) {
  const node = new vscode.TreeItem(label, NONE);
  if (icon) node.iconPath = new vscode.ThemeIcon(icon);
  node.description = description;
  node.command = command;
  return node;
}
function command(id, ...args) {
  return { command: `gitDesk.${id}`, title: id, arguments: args };
}

class Provider {
  constructor(children) {
    this.children = children;
    this.emitter = new vscode.EventEmitter();
    this.onDidChangeTreeData = this.emitter.event;
  }
  getTreeItem(node) { return node; }
  getChildren(node) { return node ? (node.children || []) : this.children(); }
  refresh() { this.emitter.fire(); }
  dispose() { this.emitter.dispose(); }
}

class GitDesk {
  constructor(api, context) {
    this.api = api;
    this.context = context;
    this.repo = undefined;
    this.busy = false;
    this.prompt = options => vscode.window.showInputBox(options);
    this.output = vscode.window.createOutputChannel('Git Desk');
    this.repository = new Provider(() => this.repositoryItems());
    this.branches = new Provider(() => this.branchItems());
    this.changes = new Provider(() => this.changeItems());
    this.views = [
      vscode.window.createTreeView('gitDesk.repository', { treeDataProvider: this.repository }),
      vscode.window.createTreeView('gitDesk.branches', { treeDataProvider: this.branches }),
      vscode.window.createTreeView('gitDesk.changes', { treeDataProvider: this.changes, canSelectMany: true })
    ];
    context.subscriptions.push(this, this.output, this.repository, this.branches, this.changes, ...this.views);
    this.register('openRepository', () => this.open());
    this.register('selectRepository', () => this.select());
    this.register('showOutput', () => this.output.show());
    this.register('refresh', () => this.run('Refresh', r => r.status()));
    this.register('fetch', () => this.run('Fetch', r => r.fetch({ all: true, prune: true })));
    this.register('pull', () => this.run('Pull', r => this.pull(r)));
    this.register('push', () => this.run('Push', r => this.push(r)));
    this.register('stage', (node, selection) => this.stage(false, node, selection));
    this.register('stageAll', () => this.stage(true));
    this.register('unstage', (node, selection) => this.unstage(false, node, selection));
    this.register('unstageAll', () => this.unstage(true));
    this.register('commit', () => this.run('Commit', r => this.commit(r)));
    this.register('newBranch', () => this.run('Create branch', r => this.newBranch(r)));
    this.register('switchBranch', node => this.run('Switch branch', r => this.switchBranch(r, node)));
    this.register('preview', node => this.preview(node));
    context.subscriptions.push(api.onDidOpenRepository(repo => {
      if (!this.repo) this.use(repo);
    }), api.onDidCloseRepository(repo => {
      if (this.repo === repo) this.use(api.repositories.find(r => r !== repo));
    }));
    const saved = context.workspaceState.get('gitDesk.repository');
    this.use(api.repositories.find(r => r.rootUri.toString() === saved) || api.repositories[0]);
  }
  register(name, handler) {
    this.context.subscriptions.push(vscode.commands.registerCommand(`gitDesk.${name}`, async (...args) => {
      try { return await handler(...args); }
      catch (error) { this.error(name, error); }
    }));
  }
  error(label, error) {
    // Keep command output / URLs / credentials out of this extension's log.
    const detail = error.gitErrorCode || (error.code === 'ENOENT' ? 'Git executable not found' : 'Operation failed');
    this.output.appendLine(`${new Date().toLocaleTimeString()}  ${label}: ${detail}`);
    vscode.window.showErrorMessage(`Git Desk — ${label}: ${detail}. Open Git output for details.`, 'Git Output').then(choice => {
      if (choice) vscode.commands.executeCommand('git.showOutput');
    });
  }
  dispose() { this.stateSubscription?.dispose(); }
  use(repo) {
    this.stateSubscription?.dispose();
    this.repo = repo;
    if (repo) {
      this.stateSubscription = repo.state.onDidChange(() => this.refresh());
      this.context.workspaceState.update('gitDesk.repository', repo.rootUri.toString());
    }
    this.refresh();
  }
  refresh() {
    const name = this.repo ? path.basename(this.repo.rootUri.fsPath) : 'No repository';
    const head = this.repo?.state.HEAD;
    this.views[0].description = name;
    this.views[1].description = head?.name || (head?.commit ? head.commit.slice(0, 8) : '');
    this.views[2].description = this.repo ? `${this.repo.state.indexChanges.length} staged` : '';
    for (const provider of [this.repository, this.branches, this.changes]) provider.refresh();
  }
  async run(label, action) {
    if (this.busy) return vscode.window.showInformationMessage('Git Desk is finishing another operation.');
    if (!this.repo) return this.open();
    const repo = this.repo;
    this.busy = true;
    try {
      return await vscode.window.withProgress({ location: vscode.ProgressLocation.Notification, title: `Git Desk: ${label}` }, async () => {
        const result = await action(repo);
        await repo.status();
        this.output.appendLine(`${new Date().toLocaleTimeString()}  ${label} completed`);
        return result;
      });
    } catch (error) {
      this.error(label, error);
      try { await repo.status(); } catch { /* Original error already reported. */ }
    } finally {
      this.busy = false;
      this.refresh();
    }
  }
  async open() {
    if (this.busy) return;
    const choice = await vscode.window.showQuickPick([
      { label: '$(edit) Enter repository path', value: 'path' },
      { label: '$(folder-opened) Browse folders…', value: 'browse' }
    ], { title: 'Git Desk — Open Repository' });
    if (!choice) return;
    let uri;
    if (choice.value === 'browse') {
      [uri] = await vscode.window.showOpenDialog({ canSelectFiles: false, canSelectFolders: true, canSelectMany: false, openLabel: 'Open Repository' }) || [];
    } else {
      let input = await this.prompt({ title: 'Repository folder path', value: this.repo?.rootUri.fsPath || '', placeHolder: '/path/to/repository', ignoreFocusOut: true });
      if (!input?.trim()) return;
      input = input.trim().replace(/^(["'])(.*)\1$/, '$2');
      if (input === '~' || input.startsWith('~/') || input.startsWith('~\\')) input = path.join(os.homedir(), input.slice(2));
      uri = vscode.Uri.file(path.resolve(input));
    }
    if (!uri) return;
    const repo = await this.api.openRepository(uri);
    if (!repo) return vscode.window.showErrorMessage('That folder is not an available Git repository.');
    this.use(repo);
    await repo.status();
  }
  async select() {
    if (this.busy) return;
    if (!this.api.repositories.length) return this.open();
    const choice = await vscode.window.showQuickPick(this.api.repositories.map(repo => ({
      label: path.basename(repo.rootUri.fsPath), description: repo.rootUri.fsPath, repo
    })), { title: 'Select Git repository' });
    if (choice) this.use(choice.repo);
  }
  repositoryItems() {
    if (!this.repo) return [];
    const head = this.repo.state.HEAD;
    const branch = head?.name || (head?.commit ? `Detached HEAD · ${head.commit.slice(0, 8)}` : 'No commits yet');
    const root = item(path.basename(this.repo.rootUri.fsPath), 'repo', 'Change repository', command('selectRepository'));
    root.tooltip = this.repo.rootUri.fsPath;
    return [root,
      item(branch, 'git-branch', 'Current branch', command('switchBranch')),
      item(head?.upstream ? `${head.upstream.remote}/${head.upstream.name}` : 'No upstream', 'cloud', `↑ ${head?.ahead || 0}  ↓ ${head?.behind || 0}`),
      item('Fetch', 'cloud-download', 'Update remote branches', command('fetch')),
      item('Pull', 'arrow-down', 'Fast-forward only', command('pull')),
      item('Push', 'arrow-up', 'Publish local commits', command('push')),
      item('Commit staged…', 'check', `${this.repo.state.indexChanges.length} staged files`, command('commit'))
    ];
  }
  async branchItems() {
    const repo = this.repo;
    if (!repo) return [];
    const refs = await repo.getBranches({ remote: true });
    if (repo !== this.repo) return [];
    return [0, 1].map(type => {
      const group = new vscode.TreeItem(type === 0 ? 'Local branches' : 'Remote branches', EXPANDED);
      group.children = refs.filter(ref => ref.type === type && ref.name && !ref.name.endsWith('/HEAD')).map(ref => {
        const node = item(ref.name, ref.name === repo.state.HEAD?.name ? 'check' : 'git-branch', ref.name === repo.state.HEAD?.name ? 'active' : undefined);
        node.branch = ref;
        node.repo = repo;
        node.contextValue = 'branch';
        // Switching requires the inline button / context menu, avoiding accidental checkouts.
        return node;
      });
      return group;
    });
  }
  changeItems() {
    const repo = this.repo;
    if (!repo) return [];
    const state = repo.state;
    const unstaged = [...state.mergeChanges, ...state.workingTreeChanges, ...state.untrackedChanges];
    const groups = [['Staged', state.indexChanges, true], ['Changes', unstaged, false]];
    return groups.map(([label, changes, staged]) => {
      const group = new vscode.TreeItem(`${label} (${changes.length})`, EXPANDED);
      group.children = changes.map(change => {
        const relative = path.relative(repo.rootUri.fsPath, change.uri.fsPath);
        const node = item(relative, 'file', STATUS[change.status] || '?');
        node.resourceUri = change.uri;
        node.tooltip = change.uri.fsPath;
        node.change = change;
        node.repo = repo;
        node.staged = staged;
        node.contextValue = staged ? 'staged' : 'unstaged';
        node.command = command('preview', node);
        return node;
      });
      return group;
    });
  }
  selected(node, selection, staged) {
    let nodes = Array.isArray(selection) && selection.length ? selection : node?.change ? [node] : this.views[2].selection;
    return nodes.filter(n => n.change && n.repo === this.repo && n.staged === staged);
  }
  async stage(all, node, selection) {
    return this.run('Stage', async repo => {
      if (all) return repo.add([]); // An empty path list is the Git API's "add all".
      const paths = this.selected(node, selection, false).map(n => n.change.uri.fsPath);
      if (!paths.length) return vscode.window.showInformationMessage('Select files in Changes first.');
      await repo.add(paths);
    });
  }
  async unstage(all, node, selection) {
    return this.run('Unstage', async repo => {
      const paths = all ? repo.state.indexChanges.map(c => c.uri.fsPath) : this.selected(node, selection, true).map(n => n.change.uri.fsPath);
      if (!paths.length) return vscode.window.showInformationMessage('Select staged files first.');
      // Git's API revert() removes paths from the index; it preserves working files.
      await repo.revert(paths);
    });
  }
  async commit(repo) {
    await repo.status();
    if (!repo.state.indexChanges.length) return vscode.window.showInformationMessage('Stage files before committing.');
    const message = await this.prompt({ title: 'Commit staged files', prompt: 'Commit message',
      value: repo.inputBox.value, ignoreFocusOut: true, validateInput: v => v.trim() ? undefined : 'Enter a commit message.' });
    if (!message?.trim()) return;
    await repo.commit(message.trim(), { all: false, postCommitCommand: null });
    repo.inputBox.value = '';
    vscode.window.showInformationMessage('Git Desk: staged changes committed.');
  }
  async newBranch(repo) {
    const name = await this.prompt({ title: 'Create and switch to branch', prompt: 'New branch name', ignoreFocusOut: true });
    if (!name?.trim()) return;
    await this.local(repo, ['check-ref-format', '--branch', name.trim()]);
    await repo.createBranch(name.trim(), true);
  }
  async switchBranch(repo, node) {
    let branch = node?.repo === repo ? node.branch : undefined;
    if (!branch) {
      const refs = await repo.getBranches({ remote: true });
      const picked = await vscode.window.showQuickPick(refs.filter(r => r.name && !r.name.endsWith('/HEAD')).map(ref => ({
        label: ref.name, description: ref.type === 0 ? 'Local' : 'Remote', ref
      })), { title: 'Switch branch' });
      if (!picked) return;
      branch = picked.ref;
    }
    if (branch.type === 1) {
      const remote = branch.remote || repo.state.remotes.find(r => branch.name.startsWith(r.name + '/'))?.name;
      if (!remote) throw new Error('Remote not found');
      const localName = branch.name.slice(remote.length + 1);
      const locals = await repo.getBranches({ remote: false });
      if (locals.some(r => r.name === localName)) await repo.checkout(localName);
      else {
        await repo.createBranch(localName, true, branch.name);
        await repo.setBranchUpstream(localName, branch.name);
      }
    } else await repo.checkout(branch.name);
  }
  async push(repo) {
    const head = repo.state.HEAD;
    if (!head?.name) return vscode.window.showWarningMessage('Switch to a local branch before pushing.');
    if (head.upstream) return repo.push();
    const remotes = repo.state.remotes;
    if (!remotes.length) return vscode.window.showWarningMessage('No Git remote configured for this repository.');
    const choice = remotes.length === 1 ? { label: remotes[0].name } : await vscode.window.showQuickPick(remotes.map(r => ({ label: r.name })), { title: 'Publish branch to remote' });
    if (choice) await repo.push(choice.label, head.name, true);
  }
  async pull(repo) {
    const upstream = repo.state.HEAD?.upstream;
    if (!upstream) return vscode.window.showWarningMessage('Set an upstream for this branch first (Push can publish it).');
    await repo.fetch({ remote: upstream.remote });
    await this.local(repo, ['merge', '--ff-only', '--', `${upstream.remote}/${upstream.name}`]);
  }
  async local(repo, args) {
    // Only local Git operations use execFile; authenticated operations go through VS Code.
    try {
      const { stdout } = await execute(this.api.git.path, args, {
        cwd: repo.rootUri.fsPath, timeout: 120000, maxBuffer: 4 * 1024 * 1024,
        env: { ...process.env, GIT_TERMINAL_PROMPT: '0', GIT_LITERAL_PATHSPECS: '1' }, windowsHide: true
      });
      return stdout;
    } catch (error) {
      if (args[0] === 'check-ref-format') error.gitErrorCode = 'InvalidBranchName';
      else if (args[0] === 'merge') error.gitErrorCode = 'Fast-forward pull failed; check local changes and branch divergence';
      throw error;
    }
  }
  async preview(node) {
    if (!node?.change || node.repo !== this.repo) return;
    const { uri, originalUri, status } = node.change;
    if (!node.staged && (status === 7 || status === 9)) return vscode.commands.executeCommand('vscode.open', uri);
    const left = this.api.toGitUri(originalUri, node.staged ? 'HEAD' : '');
    const right = node.staged ? this.api.toGitUri(uri, '') : uri;
    return vscode.commands.executeCommand('vscode.diff', left, right, `${path.basename(uri.fsPath)} (${node.staged ? 'Staged' : 'Working tree'})`);
  }
}

async function activate(context) {
  const git = vscode.extensions.getExtension('vscode.git');
  if (!git) throw new Error('The built-in Git extension is required.');
  const exports = await git.activate();
  if (!exports.enabled) throw new Error('Enable Git in VS Code settings first.');
  const desk = new GitDesk(exports.getAPI(1), context);
  return { controller: desk };
}
module.exports = { activate };
