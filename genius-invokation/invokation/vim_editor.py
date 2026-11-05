from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
from dataclasses import asdict
from pathlib import Path

from .history import History
from .model import Navigator, Payload, Target, payload_bytes, pretty_json


def editor_command ():
    for name in ('kvim', 'vim'):
        command = shutil.which (name)
        if command:
            return command

    raise ValueError ('The JSON editor needs kvim or vim installed on PATH.')


class Session:
    """The editor state shared by Vim and the history database."""

    def __init__ (self, history, target, initial = None, state = None):
        self.history, self.target = history, target
        text, cursor = history.draft (target.key)
        if initial is not None:
            text, cursor = initial, len (initial)

        self.navigator = Navigator (text, cursor)
        self.text, self.cursor = text, cursor
        self.action, self.error = '', ''

        if state is not None:
            self.navigator.draft = state['draft']
            self.navigator.draft_cursor = state['draft_cursor']
            self.navigator.current_id = state['current_id']
            self.navigator.global_scope = state['global_scope']
            self.text, self.cursor = state['text'], state['cursor']

        self.records = history.payloads (None if self.navigator.global_scope else target.key)

    def update (self, text, cursor):
        cursor = min (max (cursor, 0), len (text))
        if text != self.text:
            self.navigator.edited (text, cursor)
        elif self.navigator.current_id is None:
            self.navigator.draft_cursor = cursor

        self.text, self.cursor = text, cursor

    def select (self, payload):
        self.text, self.cursor = self.navigator.select (payload)

    def toggle (self):
        self.navigator.global_scope = not self.navigator.global_scope
        self.records = self.history.payloads (None if self.navigator.global_scope else self.target.key)
        if self.navigator.current_id and not any (item.id == self.navigator.current_id for item in self.records):
            self.select (Payload ('', self.navigator.draft))

    def request (self, action, count = 1):
        self.error, self.action = '', ''
        if action in ('older', 'newer'):
            step = max (1, min (count, 999999)) * (1 if action == 'older' else -1)
            self.text, self.cursor = self.navigator.move (self.records, step)
        elif action == 'scope':
            self.toggle ()
        elif action in ('format', 'invoke'):
            try:
                payload_bytes (self.text)
                self.text = pretty_json (self.text)
                self.cursor = len (self.text)
                self.navigator.edited (self.text, self.cursor)
                if action == 'invoke':
                    self.action = action
            except json.JSONDecodeError as exc:
                self.cursor = min (exc.pos, len (self.text))
                self.error = F'JSON error · line {exc.lineno}, column {exc.colno}: {exc.msg}'
        elif action in ('history', 'cancel'):
            self.action = action

        self.history.save_draft (self.target.key, self.navigator.draft, self.navigator.draft_cursor)

    def snapshot (self):
        return {
            'history_path': str (self.history.path.resolve ()),
            'target': asdict (self.target),
            'draft': self.navigator.draft,
            'draft_cursor': self.navigator.draft_cursor,
            'current_id': self.navigator.current_id,
            'global_scope': self.navigator.global_scope,
            'text': self.text,
            'cursor': self.cursor,
            'records': [asdict (item) for item in self.records],
            'action': self.action,
            'error': self.error,
        }


def write_state (path, state):
    temporary = path.with_suffix ('.new')
    temporary.write_text (json.dumps (state, ensure_ascii = True), encoding = 'utf-8')
    temporary.replace (path)


def bridge (state_path):
    """Handle one synchronous Vim request; return only after the draft is saved."""
    state_path = Path (state_path)
    state = json.loads (state_path.read_text (encoding = 'utf-8'))
    request = json.loads (state_path.with_name ('request.json').read_text (encoding = 'utf-8'))
    history = History (Path (state['history_path']))
    try:
        session = Session (history, Target (**state['target']), state = state)
        session.update (request['text'], request['cursor'])
        session.request (request['action'], request.get ('count', 1))
        write_state (state_path, session.snapshot ())
    finally:
        history.close ()


class Editor:
    def __init__ (self, history, target, initial = None):
        self.session = Session (history, target, initial)

    def pick_history (self):
        from .ui import Choice, Picker, safe_line

        def choices ():
            return [Choice (
                item.id,
                ('Draft' if not item.id else ', '.join (item.targets)) + ' · ' + safe_line (item.text).strip ()[:100],
                item.text, item
            ) for item in self.session.navigator.items (self.session.records)]

        def toggle ():
            self.session.toggle ()
            return choices ()

        picker = Picker (
            ' Payload history · Enter loads a payload · Esc returns to Vim', choices (),
            toggle = toggle,
            scope = lambda: 'GLOBAL history' if self.session.navigator.global_scope else 'LAMBDA history',
            selected = self.session.navigator.current_id or ''
        )
        selected = picker.run ()
        if selected is not None:
            self.session.select (selected.value)

    def run (self):
        command = editor_command ()
        with tempfile.TemporaryDirectory (prefix = 'genius-invokation-') as directory:
            root = Path (directory)
            state_path = root / 'state.json'
            payload_path = root / 'payload.json'
            launcher = root / 'editor.vim'
            helper = root / 'bridge.py'
            helper.write_text (
                'import sys\n'
                + F'sys.path.insert(0, {str (Path (__file__).resolve ().parent.parent)!r})\n'
                + 'from invokation.vim_editor import bridge\n'
                + 'bridge(sys.argv[1])\n', encoding = 'utf-8'
            )

            def quote (value):
                return "'" + str (value).replace ("'", "''") + "'"

            launcher.write_text (
                F'let g:invokation_state_path = {quote (state_path)}\n'
                + 'let g:invokation_bridge = [' + ', '.join (quote (part) for part in (sys.executable, helper, state_path)) + ']\n'
                + F'execute "source " . fnameescape({quote (Path (__file__).with_name ("editor.vim"))})\n',
                encoding = 'utf-8'
            )

            while True:
                self.session.request ('save')
                write_state (state_path, self.session.snapshot ())
                payload_path.write_text (self.session.text, encoding = 'utf-8')
                result = subprocess.run ([command, '-f', '-n', '-i', 'NONE', '-S', str (launcher), str (payload_path)])
                state = json.loads (state_path.read_text (encoding = 'utf-8'))
                self.session = Session (self.session.history, self.session.target, state = state)
                if result.returncode:
                    raise ValueError (F'{Path (command).name} exited with status {result.returncode}; the latest saved draft is in history.')
                if state['action'] == 'invoke':
                    payload_bytes (self.session.text)
                    return pretty_json (self.session.text)
                if state['action'] != 'history':
                    raise KeyboardInterrupt ()
                self.pick_history ()
