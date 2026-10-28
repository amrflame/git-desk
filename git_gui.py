#!/usr/bin/env python3
"""Git Desk — a single-file Git GUI.

Run: python3 git_gui.py [repository]
Requires Python 3.10+, Tkinter, and Git in PATH. No pip dependencies.
Keyboard: Ctrl+O opens a repository; F5 refreshes; Ctrl+Enter commits.
Remote operations use existing Git credential helpers / SSH agents.
HTTPS credentials can also be entered in a masked Git authentication dialog.
Pull uses --ff-only. Conflicts and authentication errors appear in Activity.
"""
from __future__ import annotations

import os
import queue
import shlex
import shutil
import subprocess
import sys
import tempfile
import threading
import tkinter as tk
from dataclasses import dataclass
from contextlib import contextmanager
from pathlib import Path
from tkinter import filedialog, messagebox, simpledialog, ttk

BG = '#10141e'
PANEL = '#181e2b'
FIELD = '#202839'
TEXT = '#e7edf7'
MUTED = '#91a0b8'
ACCENT = '#75a7ff'
GREEN = '#66d9ac'
RED = '#ff8794'


class GitError(Exception):
    pass


def system_environment():
    """Let system Git / desktop tools use system libraries in a frozen build."""
    env = os.environ.copy()
    if getattr(sys, 'frozen', False) and sys.platform.startswith('linux'):
        original = env.get('LD_LIBRARY_PATH_ORIG')
        if original is None:
            env.pop('LD_LIBRARY_PATH', None)
        else:
            env['LD_LIBRARY_PATH'] = original
    return env


@contextmanager
def authentication_environment():
    """Give Git an askpass launcher; credentials never enter this file or argv."""
    with tempfile.TemporaryDirectory(prefix='git-desk-askpass-') as directory:
        windows = os.name == 'nt'
        launcher = Path(directory) / ('askpass.cmd' if windows else 'askpass.sh')
        command = ([sys.executable, '--askpass'] if getattr(sys, 'frozen', False) else
                   [sys.executable, str(Path(__file__).resolve()), '--askpass'])
        if windows:
            launcher.write_text('@echo off\n' + subprocess.list2cmdline(command) + ' %*\n', encoding='utf-8')
        else:
            launcher.write_text('#!/bin/sh\nexec ' + shlex.join(command) + ' "$@"\n', encoding='utf-8')
            launcher.chmod(0o700)
        yield {'GIT_ASKPASS': str(launcher)}


def askpass(prompt):
    """Invoked by Git as a child process, with its stdout piped back to Git."""
    root = tk.Tk()
    root.withdraw()
    root.attributes('-topmost', True)
    secret = 'username' not in prompt.lower()
    hint = ('Enter your username.' if not secret else
            'Enter your password or access token.\n'
            'For Azure DevOps, use a Personal Access Token (PAT).\n'
            'Git Desk does not save this value; your configured Git credential helper may save it.')
    # Close an abandoned prompt before the parent Git command times out.
    root.after(110000, root.destroy)
    try:
        value = simpledialog.askstring('Git authentication', prompt + '\n\n' + hint,
                                       show='*' if secret else '', parent=root)
        if value is None:
            return 1
        sys.stdout.write(value + '\n')
        sys.stdout.flush()
        return 0
    except tk.TclError:
        return 1
    finally:
        try:
            root.destroy()
        except tk.TclError:
            pass


@dataclass
class Change:
    index: str
    worktree: str
    path: str
    original: str = ''

    @property
    def untracked(self):
        return self.index == '?' and self.worktree == '?'

    @property
    def staged(self):
        return self.index not in (' ', '?', '!')

    @property
    def unstaged(self):
        return self.worktree != ' ' or self.untracked

    @property
    def paths(self):
        return [self.path, self.original] if self.original else [self.path]


def parse_status(output):
    """Parse porcelain v1 NUL records, including rename source paths."""
    records = iter(output.split('\0'))
    changes = []
    for record in records:
        if not record:
            continue
        xy, path = record[:2], record[3:]
        original = next(records, '') if 'R' in xy or 'C' in xy else ''
        changes.append(Change(xy[0], xy[1], path, original))
    return changes


class Repository:
    def __init__(self, directory):
        self.path = str(Path(directory).resolve())
        self.path = self.run('rev-parse', '--show-toplevel').strip()

    def run(self, *args, timeout=120):
        env = system_environment()
        # Credential helpers take priority; askpass supplies a GUI fallback for HTTPS.
        env.update(GIT_TERMINAL_PROMPT='0', GIT_PAGER='cat', GIT_LITERAL_PATHSPECS='1')
        env['GIT_SSH_COMMAND'] = env.get('GIT_SSH_COMMAND', 'ssh') + ' -oBatchMode=yes'
        try:
            with authentication_environment() as authentication:
                env.update(authentication)
                result = subprocess.run(
                    ['git', '-c', 'color.ui=false', '-c', 'core.quotepath=false', *args],
                    cwd=self.path, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                    timeout=timeout,
                    creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0,
                )
        except subprocess.TimeoutExpired as exc:
            raise GitError('Git timed out. Check your network / credentials, then refresh the repository.') from exc
        except OSError as exc:
            raise GitError(str(exc)) from exc
        output = result.stdout.decode('utf-8', errors='replace')
        error = result.stderr.decode('utf-8', errors='replace')
        if result.returncode:
            raise GitError((error or output or f'Git exited with code {result.returncode}').strip())
        return output + (error if args and args[0] not in ('status', 'diff') else '')

    def snapshot(self):
        changes = parse_status(self.run('status', '--porcelain=v1', '-z', '--untracked-files=all'))
        branch = self.run('branch', '--show-current').strip()
        if not branch:
            branch = 'Detached HEAD · ' + self.run('rev-parse', '--short', 'HEAD').strip()
        refs = self.run('for-each-ref', '--format=%(refname)\t%(refname:short)\t%(symref)', 'refs/heads', 'refs/remotes')
        local, remote = [], []
        for line in refs.splitlines():
            ref, name, symbolic = line.split('\t', 2)
            if not symbolic:
                (remote if ref.startswith('refs/remotes/') else local).append(name)
        upstream, ahead, behind = '', 0, 0
        try:
            upstream = self.run('rev-parse', '--abbrev-ref', '@{upstream}').strip()
            ahead, behind = map(int, self.run('rev-list', '--left-right', '--count', 'HEAD...@{upstream}').split())
        except GitError:
            pass
        try:
            history = self.run('log', '-25', '--format=%h  %s%n    %an · %ar')
        except GitError:
            history = 'No commits yet. Stage files and create your first commit.'
        return dict(changes=changes, branch=branch, local=local, remote=remote,
                    upstream=upstream, ahead=ahead, behind=behind, history=history)

    def unstage(self, paths=None):
        try:
            self.run('rev-parse', '--verify', 'HEAD')
        except GitError:
            return self.run('rm', '--cached', '-r', '--', *(paths or ['.']))
        return self.run('restore', '--staged', '--', *(paths or ['.']))


class GitDesk(tk.Tk):
    def __init__(self, initial=None):
        super().__init__()
        self.title('Git Desk — Git Controller')
        self.geometry('1240x820')
        self.minsize(1000, 700)
        self.configure(bg=BG)
        self.repo = None
        self.repository_dialog = None
        self.snapshot_data = None
        self.busy = False
        self.events = queue.Queue()
        self.actions = []
        self.diff_generation = 0
        self.path_var = tk.StringVar(value='Choose a local Git repository to get started')
        self.status_var = tk.StringVar(value='Ready')
        self.branch_var = tk.StringVar(value='No repository selected')
        self.sync_var = tk.StringVar(value='')
        self.filter_var = tk.StringVar(value='All changes')
        self._style()
        self._build()
        self.after(80, self._poll)
        if initial:
            self.after(150, lambda: self.open_repository(initial))

    def _style(self):
        style = ttk.Style(self)
        style.theme_use('clam')
        style.configure('.', background=BG, foreground=TEXT, font=('DejaVu Sans', 10))
        style.configure('TFrame', background=BG)
        style.configure('Card.TFrame', background=PANEL)
        style.configure('TLabel', background=BG, foreground=TEXT)
        style.configure('Muted.TLabel', foreground=MUTED)
        style.configure('Heading.TLabel', font=('DejaVu Sans', 18, 'bold'))
        style.configure('TButton', background=FIELD, foreground=TEXT, borderwidth=0, padding=(13, 9))
        style.map('TButton', background=[('active', '#33425e'), ('disabled', '#19202d')],
                  foreground=[('disabled', '#57647b')])
        style.configure('Accent.TButton', background='#336cce', foreground='white')
        style.map('Accent.TButton', background=[('active', '#4281ec'), ('disabled', '#23334b')])
        style.configure('Treeview', background=PANEL, fieldbackground=PANEL, foreground=TEXT,
                        borderwidth=0, rowheight=32)
        style.configure('Treeview.Heading', background=FIELD, foreground=MUTED, padding=8)
        style.map('Treeview', background=[('selected', '#2a466e')], foreground=[('selected', 'white')])
        style.configure('TNotebook', background=BG, borderwidth=0)
        style.configure('TNotebook.Tab', padding=(15, 9), background=FIELD)
        style.map('TNotebook.Tab', background=[('selected', PANEL)], foreground=[('selected', ACCENT)])
        style.configure('TCombobox', fieldbackground=FIELD, background=FIELD, foreground=TEXT,
                        arrowcolor=TEXT, padding=5)
        style.configure('TEntry', fieldbackground=FIELD, foreground=TEXT, insertcolor=TEXT, padding=9)
        style.map('TCombobox', fieldbackground=[('readonly', FIELD)], foreground=[('readonly', TEXT)])
        style.configure('Horizontal.TProgressbar', background=ACCENT, troughcolor=BG, borderwidth=0)
        style.configure('TPanedwindow', background=BG)

    def button(self, parent, label, command, accent=False, always=False):
        b = ttk.Button(parent, text=label, command=command, style='Accent.TButton' if accent else 'TButton')
        if not always:
            self.actions.append(b)
            b.state(['disabled'])
        return b

    def text_box(self, parent, **kwargs):
        box = tk.Text(parent, bg=PANEL, fg=TEXT, insertbackground=TEXT, relief='flat',
                      font=('DejaVu Sans Mono', 10), padx=14, pady=12,
                      selectbackground='#2a466e', wrap='word', **kwargs)
        return box

    def _build(self):
        header = ttk.Frame(self, padding=(22, 18, 22, 12))
        header.pack(fill='x')
        ttk.Label(header, text='Git Desk', style='Heading.TLabel').pack(side='left')
        ttk.Label(header, text='  /  YOUR REPOSITORY, IN CONTROL', style='Muted.TLabel').pack(side='left', padx=12)
        self.open_btn = self.button(header, 'Open repository…', self.choose_repository, accent=True, always=True)
        self.open_btn.pack(side='right')
        repo_bar = ttk.Frame(self, padding=(22, 4, 22, 12))
        repo_bar.pack(fill='x')
        ttk.Label(repo_bar, textvariable=self.path_var, style='Muted.TLabel').pack(anchor='w')
        bar = ttk.Frame(self, padding=(22, 0, 22, 15))
        bar.pack(fill='x')
        ttk.Label(bar, textvariable=self.branch_var, font=('DejaVu Sans', 12, 'bold'), foreground=GREEN).pack(side='left')
        ttk.Label(bar, textvariable=self.sync_var, style='Muted.TLabel').pack(side='left', padx=14)
        for label, callback in [('Refresh', self.refresh), ('Fetch', self.fetch), ('Pull', self.pull), ('Push', self.push)]:
            self.button(bar, label, callback).pack(side='right', padx=(6, 0))
        body = ttk.Panedwindow(self, orient='horizontal')
        body.pack(fill='both', expand=True, padx=22)
        left = ttk.Frame(body)
        center = ttk.Frame(body)
        body.add(left, weight=1)
        body.add(center, weight=4)
        ttk.Label(left, text='BRANCHES', style='Muted.TLabel').pack(anchor='w', pady=(4, 12))
        self.branches = ttk.Treeview(left, show='tree', selectmode='browse', height=12)
        self.branches.pack(fill='both', expand=True, padx=(0, 12))
        self.branches.bind('<Double-1>', lambda _e: self.switch_branch())
        branch_buttons = ttk.Frame(left)
        branch_buttons.pack(fill='x', pady=10, padx=(0, 12))
        self.button(branch_buttons, 'Switch', self.switch_branch).pack(side='left', fill='x', expand=True)
        self.button(branch_buttons, '+ New', self.new_branch).pack(side='left', fill='x', expand=True, padx=(6, 0))
        ttk.Label(left, text='Double-click a branch to switch.\nRemote branches create local tracking branches.',
                  style='Muted.TLabel', wraplength=225).pack(anchor='w', pady=(0, 12))
        ttk.Label(left, text='FILE STATUS\nM  Modified    A  Added\nD  Deleted      R  Renamed\n?  Untracked   U  Conflict', style='Muted.TLabel', justify='left').pack(anchor='w', pady=(0, 8))
        vertical = ttk.Panedwindow(center, orient='vertical')
        vertical.pack(fill='both', expand=True)
        files_panel = ttk.Frame(vertical)
        lower = ttk.Frame(vertical)
        vertical.add(files_panel, weight=3)
        vertical.add(lower, weight=3)
        file_header = ttk.Frame(files_panel)
        file_header.pack(fill='x', pady=(0, 8))
        self.count_label = ttk.Label(file_header, text='CHANGES  ·  0 files', style='Muted.TLabel')
        self.count_label.pack(side='left')
        self.filter_box = ttk.Combobox(file_header, textvariable=self.filter_var, state='readonly', width=17,
                                      values=['All changes', 'Unstaged', 'Staged'])
        self.filter_box.pack(side='right')
        self.filter_box.bind('<<ComboboxSelected>>', lambda _e: self.render_files())
        table = ttk.Frame(files_panel)
        table.pack(fill='both', expand=True)
        self.files = ttk.Treeview(table, columns=('index', 'work', 'path'), show='headings', selectmode='extended', height=7)
        for name, title, width in [('index', 'Staged', 65), ('work', 'Working', 75), ('path', 'File path', 480)]:
            self.files.heading(name, text=title)
            self.files.column(name, width=width, minwidth=55, stretch=name == 'path')
        scroll = ttk.Scrollbar(table, orient='vertical', command=self.files.yview)
        self.files.configure(yscrollcommand=scroll.set)
        self.files.pack(side='left', fill='both', expand=True)
        scroll.pack(side='right', fill='y')
        self.files.bind('<<TreeviewSelect>>', self.preview)
        file_actions = ttk.Frame(files_panel)
        file_actions.pack(fill='x', pady=8)
        for label, command in [('Stage selected', self.stage_selected), ('Stage all', self.stage_all),
                               ('Unstage selected', self.unstage_selected), ('Unstage all', self.unstage_all)]:
            self.button(file_actions, label, command).pack(side='left', padx=(0, 6))
        notebook = ttk.Notebook(lower)
        notebook.pack(fill='both', expand=True)
        self.diff = self.text_box(notebook, state='disabled')
        self.history = self.text_box(notebook, state='disabled')
        self.output = self.text_box(notebook, state='disabled')
        for widget, title in [(self.diff, 'Changes preview'), (self.history, 'Recent commits'), (self.output, 'Activity')]:
            notebook.add(widget, text=title)
            widget.bind('<Control-a>', lambda e: (e.widget.tag_add('sel', '1.0', 'end'), 'break')[-1])
        self.diff.tag_configure('add', foreground=GREEN)
        self.diff.tag_configure('remove', foreground=RED)
        self.diff.tag_configure('hunk', foreground=ACCENT)
        commit_panel = ttk.Frame(self, padding=(22, 12, 22, 10))
        commit_panel.pack(fill='x')
        ttk.Label(commit_panel, text='COMMIT MESSAGE', style='Muted.TLabel').pack(anchor='w', pady=(0, 6))
        row = ttk.Frame(commit_panel)
        row.pack(fill='x')
        self.message = self.text_box(row, height=2)
        self.message.pack(side='left', fill='x', expand=True)
        self.button(row, 'Commit staged', self.commit, accent=True).pack(side='left', padx=(10, 0))
        self.message.bind('<Control-Return>', lambda _e: self.commit())
        footer = ttk.Frame(self, padding=(22, 0, 22, 10))
        footer.pack(fill='x')
        ttk.Label(footer, textvariable=self.status_var, style='Muted.TLabel').pack(side='left')
        self.progress = ttk.Progressbar(footer, mode='indeterminate', length=130)
        self.progress.pack(side='right')
        self.bind('<F5>', lambda _e: self.refresh())
        self.bind('<Control-o>', lambda _e: self.choose_repository())
        self.set_text(self.diff, 'Open a repository to view its changes.\n\nSelect files to preview. Use Ctrl / Shift to select multiple files.\n\nStage → write a message → commit → push.')

    @staticmethod
    def set_text(widget, value):
        widget.configure(state='normal')
        widget.delete('1.0', 'end')
        widget.insert('1.0', value)
        widget.configure(state='disabled')

    def log(self, value):
        self.output.configure(state='normal')
        self.output.insert('end', value.rstrip() + '\n\n')
        self.output.see('end')
        self.output.configure(state='disabled')

    def _set_busy(self, busy, label='Ready'):
        self.busy = busy
        self.status_var.set(label)
        for button in self.actions:
            button.state(['disabled'] if busy or not self.repo else ['!disabled'])
        self.open_btn.state(['disabled'] if busy else ['!disabled'])
        self.progress.start(12) if busy else self.progress.stop()

    def job(self, label, work, done=None):
        if self.busy:
            return
        self.diff_generation += 1
        self._set_busy(True, label + '…')
        def worker():
            try:
                self.events.put(('done', done, work(), label))
            except Exception as exc:
                self.events.put(('error', str(exc), label))
        threading.Thread(target=worker, daemon=True).start()

    def _poll(self):
        try:
            while True:
                event = self.events.get_nowait()
                if event[0] == 'done':
                    _, done, result, label = event
                    self._set_busy(False)
                    if done:
                        done(result)
                    self.status_var.set(label + ' · done')
                elif event[0] == 'error':
                    _, error, label = event
                    self._set_busy(False, label + ' · failed')
                    self.log(label + '\n' + error)
                    messagebox.showerror(label, error, parent=self)
                    if self.repo and label != 'Refresh':
                        self.refresh()
                elif event[0] == 'preview':
                    _, generation, value = event
                    if generation == self.diff_generation:
                        self.set_text(self.diff, value)
                        for i, line in enumerate(value.splitlines(), 1):
                            tag = 'add' if line.startswith('+') else 'remove' if line.startswith('-') else 'hunk' if line.startswith('@@') else None
                            if tag:
                                self.diff.tag_add(tag, f'{i}.0', f'{i}.end')
        except queue.Empty:
            pass
        self.after(80, self._poll)

    def choose_repository(self):
        if self.busy:
            return
        if self.repository_dialog and self.repository_dialog.winfo_exists():
            self.repository_dialog.lift()
            return
        dialog = self.repository_dialog = tk.Toplevel(self)
        dialog.title('Open repository')
        dialog.configure(bg=BG)
        dialog.transient(self)
        dialog.resizable(True, False)
        dialog.geometry('700x215')
        dialog.minsize(520, 215)
        content = ttk.Frame(dialog, padding=22)
        content.pack(fill='both', expand=True)
        ttk.Label(content, text='Open a local Git repository', font=('DejaVu Sans', 13, 'bold')).pack(anchor='w')
        ttk.Label(content, text='Type or paste a folder path, or browse your computer.',
                  style='Muted.TLabel').pack(anchor='w', pady=(6, 12))
        row = ttk.Frame(content)
        row.pack(fill='x')
        path = tk.StringVar(value=self.repo.path if self.repo else '')
        entry = ttk.Entry(row, textvariable=path, name='repository_path')
        entry.pack(side='left', fill='x', expand=True)
        process = None

        def close():
            if process is not None and process.poll() is None:
                process.terminate()
                # Reap the native picker without holding up the Tk event loop.
                threading.Thread(target=process.communicate, daemon=True).start()
            dialog.destroy()
            self.repository_dialog = None

        def open_path(_event=None):
            if process is not None and process.poll() is None:
                return
            value = path.get().strip()
            if len(value) >= 2 and value[0] == value[-1] and value[0] in ('"', "'"):
                value = value[1:-1]
            value = os.path.expandvars(os.path.expanduser(value))
            if not value or not Path(value).is_dir():
                messagebox.showerror('Invalid folder', 'Enter an existing folder path.', parent=dialog)
                entry.focus_set()
                return
            close()
            self.open_repository(value)

        def fallback(initial):
            selected = filedialog.askdirectory(title='Choose a Git repository', initialdir=initial, parent=dialog)
            if selected:
                path.set(selected)
            entry.focus_set()

        def browse():
            nonlocal process
            initial = Path(os.path.expandvars(os.path.expanduser(path.get().strip())))
            if not initial.is_dir():
                initial = Path(self.repo.path) if self.repo else Path.home()
            # Tk's Linux picker lacks the desktop Places / mounted volumes sidebar.
            # Use the installed desktop picker, keeping Tk as a portable fallback.
            tools = ['kdialog', 'zenity'] if 'KDE' in os.environ.get('XDG_CURRENT_DESKTOP', '').upper() else ['zenity', 'kdialog']
            picker = next((shutil.which(tool) for tool in tools if shutil.which(tool)), None) if sys.platform.startswith('linux') else None
            if not picker:
                fallback(str(initial))
                return
            args = ([picker, '--file-selection', '--directory', '--title=Choose a Git repository',
                     '--filename=' + str(initial) + os.sep] if Path(picker).name == 'zenity' else
                    [picker, '--getexistingdirectory', str(initial), '--title', 'Choose a Git repository'])
            try:
                process = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                                           env=system_environment())
            except OSError:
                fallback(str(initial))
                return
            browse_button.state(['disabled'])
            open_button.state(['disabled'])

            def collect():
                if not dialog.winfo_exists():
                    return
                if process.poll() is None:
                    dialog.after(80, collect)
                    return
                output, _ = process.communicate()
                browse_button.state(['!disabled'])
                open_button.state(['!disabled'])
                if process.returncode == 0:
                    selected = os.fsdecode(output).rstrip('\r\n')
                    if selected:
                        path.set(selected)
                elif process.returncode != 1:  # 1 means the user cancelled.
                    fallback(str(initial))
                dialog.lift()
                entry.focus_set()
            dialog.after(80, collect)

        browse_button = ttk.Button(row, text='Browse…', command=browse)
        browse_button.pack(side='left', padx=(8, 0))
        actions = ttk.Frame(content)
        actions.pack(fill='x', pady=(18, 0))
        open_button = ttk.Button(actions, text='Open repository', style='Accent.TButton', command=open_path)
        open_button.pack(side='right')
        ttk.Button(actions, text='Cancel', command=close).pack(side='right', padx=8)
        dialog.protocol('WM_DELETE_WINDOW', close)
        dialog.bind('<Escape>', lambda _e: close())
        entry.bind('<Return>', open_path)
        dialog.grab_set()
        entry.focus_set()
        entry.select_range(0, 'end')

    def open_repository(self, directory):
        def work():
            repo = Repository(directory)
            return repo, repo.snapshot()
        def done(result):
            self.repo, data = result
            self.path_var.set(self.repo.path)
            self.title(f'Git Desk — {Path(self.repo.path).name}')
            self.message.delete('1.0', 'end')
            self.apply_snapshot(data)
            self._set_busy(False)
            self.log('Opened ' + self.repo.path)
        self.job('Open repository', work, done)

    def refresh(self):
        if self.repo and not self.busy:
            self.job('Refresh', self.repo.snapshot, self.apply_snapshot)

    def apply_snapshot(self, data):
        self.snapshot_data = data
        self.branch_var.set('●  ' + data['branch'])
        self.sync_var.set(f"↑ {data['ahead']}   ↓ {data['behind']}  ·  {data['upstream']}" if data['upstream'] else 'No upstream configured')
        self.branches.delete(*self.branches.get_children())
        for key, label in [('local', 'LOCAL'), ('remote', 'REMOTE')]:
            self.branches.insert('', 'end', iid=key, text=label, open=True)
            for i, name in enumerate(data[key]):
                self.branches.insert(key, 'end', iid=f'{key}:{i}', text=('●  ' if name == data['branch'] else '    ') + name, values=(name,))
        self.set_text(self.history, data['history'])
        self.render_files()
        self.set_text(self.diff, 'Select a file to preview its changes.' if data['changes'] else 'Working tree clean. All changes are committed.')

    def render_files(self):
        self.diff_generation += 1
        self.files.delete(*self.files.get_children())
        if not self.snapshot_data:
            return
        changes = self.snapshot_data['changes']
        for i, change in enumerate(changes):
            if self.filter_var.get() == 'Staged' and not change.staged:
                continue
            if self.filter_var.get() == 'Unstaged' and not change.unstaged:
                continue
            path = f'{change.original} → {change.path}' if change.original else change.path
            self.files.insert('', 'end', iid=str(i), values=(change.index.strip() or '—', change.worktree.strip() or '—', path))
        staged = sum(c.staged for c in changes)
        self.count_label.configure(text=f'CHANGES  ·  {len(changes)} files  ·  {staged} staged')

    def selected_changes(self):
        if not self.repo or self.busy:
            return []
        selected = [self.snapshot_data['changes'][int(i)] for i in self.files.selection()]
        if not selected:
            messagebox.showinfo('Select files', 'Select one or more files first.', parent=self)
        return selected

    def mutate(self, label, action, after=None):
        if not self.repo or self.busy:
            return
        repo = self.repo
        def work():
            output = action(repo)
            return output, repo.snapshot()
        def done(result):
            output, data = result
            self.log(label + '\n' + (output or 'Completed successfully.'))
            self.apply_snapshot(data)
            if after:
                after()
        self.job(label, work, done)

    def stage_selected(self):
        changes = self.selected_changes()
        if changes:
            paths = list(dict.fromkeys(p for c in changes for p in c.paths))
            self.mutate('Stage selected files', lambda r: r.run('add', '-A', '--', *paths))

    def stage_all(self):
        self.mutate('Stage all changes', lambda r: r.run('add', '-A', '--', '.'))

    def unstage_selected(self):
        changes = self.selected_changes()
        if changes:
            paths = list(dict.fromkeys(p for c in changes if c.staged for p in c.paths))
            if paths:
                self.mutate('Unstage selected files', lambda r: r.unstage(paths))

    def unstage_all(self):
        self.mutate('Unstage all changes', lambda r: r.unstage())

    def commit(self):
        if not self.repo or self.busy:
            return
        message = self.message.get('1.0', 'end').strip()
        if not message:
            messagebox.showinfo('Commit message', 'Write a commit message first.', parent=self)
            return
        if not any(c.staged for c in self.snapshot_data['changes']):
            messagebox.showinfo('No staged changes', 'Stage files before creating a commit.', parent=self)
            return
        self.mutate('Commit', lambda r: r.run('commit', '-m', message), lambda: self.message.delete('1.0', 'end'))

    def fetch(self):
        self.mutate('Fetch all remotes', lambda r: r.run('fetch', '--all', '--prune'))

    def pull(self):
        self.mutate('Pull · fast-forward only', lambda r: r.run('pull', '--ff-only'))

    def push(self):
        if not self.repo or self.busy:
            return
        if self.snapshot_data['upstream']:
            self.mutate('Push', lambda r: r.run('push'))
        else:
            # Resolve remotes in the worker, including credential-free local repos.
            def action(repo):
                branch = repo.run('branch', '--show-current').strip()
                if not branch:
                    raise GitError('Switch to a local branch before pushing.')
                remotes = repo.run('remote').splitlines()
                if not remotes:
                    raise GitError('No remote configured. Add a remote with: git remote add origin <URL>')
                remote = 'origin' if 'origin' in remotes else remotes[0] if len(remotes) == 1 else None
                if not remote:
                    raise GitError('Multiple remotes found without origin. Configure an upstream for this branch first.')
                return repo.run('push', '--set-upstream', remote, branch)
            self.mutate('Push & set upstream', action)

    def switch_branch(self):
        if not self.repo or self.busy:
            return
        selection = self.branches.selection()
        if not selection or ':' not in selection[0]:
            return
        branch = self.branches.item(selection[0], 'values')[0]
        if selection[0].startswith('remote:'):
            local_name = branch.split('/', 1)[1]
            if local_name in self.snapshot_data['local']:
                self.mutate('Switch to ' + local_name, lambda r: r.run('switch', local_name))
            else:
                self.mutate('Track ' + branch, lambda r: r.run('switch', '--track', '-c', local_name, branch))
        else:
            self.mutate('Switch to ' + branch, lambda r: r.run('switch', branch))

    def new_branch(self):
        if not self.repo or self.busy:
            return
        name = simpledialog.askstring('Create branch', 'New branch name (created from current HEAD):', parent=self)
        if name and name.strip():
            name = name.strip()
            def action(repo):
                if name.startswith('-'):
                    raise GitError('Branch names cannot start with a dash.')
                repo.run('check-ref-format', '--branch', name)
                return repo.run('switch', '-c', name)
            self.mutate('Create branch ' + name, action)

    def preview(self, _event=None):
        self.diff_generation += 1
        generation = self.diff_generation
        selection = self.files.selection()
        if not selection or not self.repo or self.busy:
            return
        change = self.snapshot_data['changes'][int(selection[0])]
        repo = self.repo
        staged_only = self.filter_var.get() == 'Staged'
        self.set_text(self.diff, 'Loading preview…')
        def work():
            try:
                if change.untracked:
                    path = Path(repo.path) / change.path
                    if path.is_symlink():
                        value = 'Symbolic link → ' + os.readlink(path)
                    else:
                        with path.open('rb') as stream:
                            raw = stream.read(100001)
                        value = 'Binary file · preview unavailable' if b'\0' in raw else raw[:100000].decode('utf-8', errors='replace')
                        if len(raw) > 100000:
                            value += '\n\n[Preview limited to 100 KB]'
                    value = 'UNTRACKED · ' + change.path + '\n\n' + value
                else:
                    sections = []
                    if change.staged:
                        sections.append('STAGED\n' + repo.run('diff', '--cached', '--no-ext-diff', '--no-textconv', '--', *change.paths))
                    if change.unstaged and not staged_only:
                        sections.append('WORKING TREE\n' + repo.run('diff', '--no-ext-diff', '--no-textconv', '--', *change.paths))
                    value = '\n\n'.join(sections) or 'No textual diff available.'
                    if len(value) > 200000:
                        value = value[:200000] + '\n[Preview truncated]'
            except Exception as exc:
                value = str(exc)
            self.events.put(('preview', generation, value))
        threading.Thread(target=work, daemon=True).start()


def main():
    if not shutil.which('git'):
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror('Git required', 'Install Git and make sure it is available in PATH.')
        root.destroy()
        return 1
    app = GitDesk(sys.argv[1] if len(sys.argv) > 1 else None)
    app.mainloop()
    return 0


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == '--askpass':
        raise SystemExit(askpass(sys.argv[2] if len(sys.argv) > 2 else 'Git credentials:'))
    raise SystemExit(main())
