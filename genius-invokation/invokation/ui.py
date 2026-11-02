from __future__ import annotations

import asyncio
import json
import re
import sqlite3
from dataclasses import dataclass
from typing import Any, Callable

from prompt_toolkit.application import Application
from prompt_toolkit.data_structures import Point
from prompt_toolkit.document import Document
from prompt_toolkit.filters import Condition
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.keys import Keys
from prompt_toolkit.layout import ConditionalContainer, HSplit, Layout, Window
from prompt_toolkit.layout.controls import FormattedTextControl
from prompt_toolkit.layout.dimension import Dimension
from prompt_toolkit.lexers import PygmentsLexer
from prompt_toolkit.styles import Style
from prompt_toolkit.widgets import Frame, TextArea
from pygments.lexers.data import JsonLexer

from .history import History
from .model import Navigator, Payload, Target, payload_bytes, pretty_json
from .terminal import ctrl_enter_sequences


STYLE = Style.from_dict ({
    'title'                    : 'bold #83d6d0',
    'hint'                     : '#a5aab8',
    'error'                    : 'bold #ff6b7a',
    'selected'                 : 'bg:#294959 #fffffF',
    'match'                    : '#eecb7b',
    'status'                   : 'bg:#243242 #fffffF',
    'frame.border'             : '#628887',
    'line-number'              : '#697586',
    'line-number.current'      : '#83d6d0',
    'pygments.literal.string'  : '#a5d6a7',
    'pygments.literal.number'  : '#eecb7b',
    'pygments.keyword.constant': '#b6a0ed',
})


def safe_line (text):
    return re.sub (R'[\x00-\x1f\x7f-\x9f]', ' ', text)

@dataclass
class Choice:
    key: str
    label: str
    text: str
    value: Any = None

class Picker:
    def __init__ (self, title, choices, *, toggle = None, scope = None, on_select = None, on_cancel = None, selected = None):
        self.title, self.choices       = title, choices
        self.toggle, self.scope        = toggle, scope or (lambda: "")
        self.on_select, self.on_cancel = on_select, on_cancel

        self.index           = next ((i for i, item in enumerate (choices) if item.key == selected), 0)
        self.count           = ''
        self.query           = ''
        self.searching       = False
        self.notice          = ''
        self.search_snapshot = ('', self.index)
        self.preview         = TextArea (read_only = True, lexer = PygmentsLexer (JsonLexer), scrollbar = True, wrap_lines = True)
        self.search          = TextArea (height = 1, prompt = '/', multiline = False)

        self.search.buffer.on_text_changed += self.search_changed

        self.control     = FormattedTextControl (self.rows, focusable = True, get_cursor_position = lambda: Point (0, self.index))
        self.list_window = Window (self.control, wrap_lines = False, height = Dimension (min = 3, weight = 2), scroll_offsets = None)

        self.root = HSplit ([
            Window (FormattedTextControl (lambda: [ ('class:title', self.title) ]), height = 1),
            Window (FormattedTextControl (lambda: [ ('class:hint', self.help ()) ]), height = 2),

            Frame (self.list_window, title = 'Select'),
            Frame (self.preview, title='Preview', height=Dimension (min=4, preferred=10, max=12)),

            ConditionalContainer (self.search, Condition (lambda: self.searching)),
            Window (FormattedTextControl (self.status), height = 1),
        ])

        self.layout   = Layout (self.root, focused_element = self.control)
        self.bindings = self.bindings ()

        self.refresh ()

    def help (self):
        extra = '  Ctrl+A scope' if self.toggle else ''
        return ('↑/↓ j/k move  3k/3↑ count  Ctrl+E/Y scroll  / search  n/N matches\nEnter select  Esc back' + extra)

    def rows (self):
        if (not self.choices):
            return [ ("class:hint", "No saved payloads; your draft is still available.") ]

        result = []
        width = max (3, len (str (len (self.choices))))

        for i, item in enumerate (self.choices):
            style  = "class:selected" if i == self.index else ("class:match" if self.matches (item) and self.query else "")
            number = i + 1 if i == self.index else abs (i - self.index)

            result.append ((style, F'{'›' if i == self.index else ' '} {number:>{width}}  {safe_line (item.label)}'))
            if (i + 1 < len (self.choices)):
                result.append (('', '\n'))
        return result

    def status (self):
        search = F' /{self.query}' if self.query else ''
        position = F'{self.index + 1}/{len (self.choices)}' if self.choices else '0/0'
        return [ ('class:status', F' {self.scope ()}  {position}{search}  {self.count} {self.notice}') ]

    def matches (self, item):
        return self.query.casefold () in (item.label + '\n' + item.text).casefold ()

    def refresh (self, choices = None):
        if (choices is not None):
            key          = self.choices[self.index].key if self.choices else ''
            self.choices = choices
            self.index   = next ((i for i, item in enumerate (choices) if item.key == key), 0)

        self.index = min (max (self.index, 0), max (0, len (self.choices) - 1))
        text       = self.choices[self.index].text if self.choices else ''

        self.preview.buffer.set_document (Document (text, 0), bypass_readonly = True)

    def move (self, direction):
        step       = int (self.count or '1')
        self.count = ''

        if (self.choices):
            self.index = min (max (self.index + step * direction, 0), len (self.choices) - 1)

        self.notice = ''
        self.refresh ()

    def find (self, direction, include_current = False):
        if (not self.query or not self.choices):
            return

        repetitions = int (self.count or '1')
        self.count  = ''
        matches = [ i for i, item in enumerate (self.choices) if self.matches (item) ]
        if (not matches):
            self.notice = 'No matches'
            return

        if (include_current and self.index in matches):
            self.notice = ''
            return

        ordered = matches if direction > 0 else list (reversed (matches))
        ahead   = [i for i in ordered if (i - self.index) * direction > 0]
        first   = ahead[0] if ahead else ordered[0]

        self.index = ordered[(ordered.index (first) + repetitions - 1) % len (ordered)]
        self.notice = ''
        self.refresh ()

    def scroll (self, direction: int):
        step       = int (self.count or '1')
        self.count = ''
        info       = self.list_window.render_info

        if (not info or not self.choices):
            return

        height = info.window_height
        top    = min (max (self.list_window.vertical_scroll + direction * step, 0), max (0, len (self.choices) - height))

        self.list_window.vertical_scroll = top
        selected = min (max (self.index, top), top + height - 1)

        if (selected != self.index):
            self.index = selected
            self.refresh ()

        self.notice = ''

    def search_changed (self, buffer):
        if (self.searching):
            self.query = buffer.text
            self.find (1, include_current = True)

    def bindings (self):
        keys = KeyBindings ()
        normal = Condition (lambda: not self.searching)
        searching = ~normal

        @keys.add ('up', filter = normal)
        @keys.add ('k', filter = normal)
        def up (event):
            self.move (-1)

        @keys.add ('down', filter = normal)
        @keys.add ('j', filter = normal)
        def down (event):
            self.move (1)

        @keys.add (Keys.Any, filter = normal)
        def count (event):
            if (event.data in '0123456789' and len (event.data) == 1):
                self.count = (self.count + event.data)[-6:]

            else:
                self.count = ''

        @keys.add ('/', filter=normal)
        def search (event):
            self.search_snapshot = (self.query, self.index)
            self.searching       = True
            self.count           = ''
            self.search.text     = ''

            event.app.layout.focus (self.search)

        @keys.add ('n', filter = normal)
        def next_match (event):
            self.find (1)

        @keys.add ('N', filter = normal)
        def previous_match (event):
            self.find (-1)

        @keys.add ('enter', filter = searching)
        def finish_search (event):
            self.searching = False
            event.app.layout.focus (self.control)

        @keys.add ('enter', filter = normal)
        def accept (event):
            if (self.choices):
                item = self.choices[self.index]

                if (self.on_select):
                    self.on_select (event.app, item)

                else:
                    event.app.exit (result = item)

        @keys.add ('escape', filter = searching, eager = True)
        def cancel_search (event):
            self.query, self.index = self.search_snapshot
            self.searching         = False
            self.notice            = ''

            self.refresh ()
            event.app.layout.focus (self.control)

        @keys.add ('escape', filter = normal, eager = True)
        def cancel (event):
            if (self.on_cancel):
                self.on_cancel (event.app)

            else:
                event.app.exit (result = None)

        @keys.add ('c-c')
        @keys.add ('c-d')
        def abort (event):
            event.app.exit (exception = KeyboardInterrupt ())

        @keys.add ('c-a')
        def toggle (event):
            if (self.toggle):
                self.refresh (self.toggle ())
                self.find (1, include_current = True)

        @keys.add ('pageup', filter = normal)
        def page_up (event):
            self.count = '10'
            self.move (-1)

        @keys.add ('pagedown', filter = normal)
        def page_down (event):
            self.count = '10'
            self.move (1)

        @keys.add ('c-e', filter = normal)
        def scroll_down (event):
            self.scroll (1)

        @keys.add ('c-y', filter = normal)
        def scroll_up (event):
            self.scroll (-1)

        @keys.add ('c-up', filter = normal)
        def preview_up (event):
            self.preview.buffer.cursor_up (count = 3)

        @keys.add ('c-down', filter = normal)
        def preview_down (event):
            self.preview.buffer.cursor_down (count = 3)

        return keys

    def run (self, **kwargs):
        return Application (layout = self.layout, key_bindings = self.bindings, full_screen = True, style = STYLE, **kwargs).run ()


class Editor:
    def __init__ (self, history, target, initial = None, **application_kwargs):
        self.history, self.target = history, target
        text, cursor              = history.draft (target.key)

        if (initial is not None):
            text, cursor = initial, len (initial)

        self.navigator      = Navigator (text, cursor)
        self.records        = history.payloads (target.key)
        self.error          = ''
        self.notice         = ''
        self.browsing       = False
        self.count          = ''
        self.changing       = False
        self.save_handle    = None
        self.picker         = None
        self.area           = TextArea (
            text         = text,
            lexer        = PygmentsLexer (JsonLexer),
            line_numbers = True,
            scrollbar    = True,
            wrap_lines   = True,
            multiline    = True
        )

        self.area.buffer.cursor_position             = cursor
        self.area.buffer.on_text_changed            += self.changed
        self.area.buffer.on_cursor_position_changed += self.cursor_changed

        self.root = HSplit ([
            Window (FormattedTextControl (lambda: [ ('class:title', ' Genius Invokation · ' + target.label) ]), height = 1),
            Window (FormattedTextControl ([ ('class:hint', ' Enter newline · Ctrl+Enter/F5 invoke · F4 format · ↑/↓ payload history\n Ctrl+A scope · Ctrl+R history/search · Esc browse (j/k, /, n/N) · Ctrl+C save & quit') ]), height = 2),
            Frame (self.area, title = 'JSON payload'),
            Window (FormattedTextControl (self.status), height = 1),
            Window (FormattedTextControl (lambda: [ ('class:error', self.error) ]), height = 2),
        ])

        self.layout   = Layout (self.root, focused_element=self.area)
        self.bindings = self.bindings ()
        self.app      = Application (layout = self.layout, key_bindings = self.bindings, full_screen = True, style = STYLE, **application_kwargs)

    def scope (self):
        return 'GLOBAL history' if self.navigator.global_scope else 'LAMBDA history'

    def status (self):
        mode   = 'BROWSE · i/Enter to edit' if self.browsing else 'EDIT'
        source = 'draft' if self.navigator.current_id is None else 'saved payload'
        return [ ('class:status', F' {mode} · {self.scope ()} · {source} · {len (self.records)} saved · {self.count} {self.notice}') ]

    def save (self, strict = False):
        self.save_handle = None
        cursor           = self.area.buffer.cursor_position
        in_whitespace    = cursor > 0 and self.area.text[cursor - 1].isspace ()

        if (not strict and not in_whitespace and self.app.layout is self.layout and self.navigator.current_id is None and len (self.area.text) <= 65536):
            original = self.area.text

            try:
                formatted = pretty_json (original)

            except json.JSONDecodeError:
                formatted = original

            if (formatted != original):
                cursor = self.area.buffer.cursor_position
                tokens = R'"(?:\\.|[^"\\])*"|[^\s{}\[\],:]+|[{}\[\],:]'
                before = list (re.finditer (tokens, original))
                after  = list (re.finditer (tokens, formatted))
                mapped = len (formatted)

                for left, right in zip (before, after):
                    if (cursor <= left.end ()):
                        mapped = right.start () + min (max (cursor - left.start (), 0), len (right.group ()))
                        break

                self.display (formatted, mapped)
                self.navigator.edited (formatted, mapped)
                self.notice = 'JSON valid · formatted'
        try:
            self.history.save_draft (self.target.key, self.navigator.draft, self.navigator.draft_cursor)

        except (OSError, ValueError, sqlite3.Error) as exc:
            self.error = F'Could not save draft: {exc}'
            if (strict):
                raise

        self.app.invalidate ()

    def schedule_save (self):
        if (self.save_handle):
            self.save_handle.cancel ()

        try:
            self.save_handle = asyncio.get_running_loop ().call_later (0.25, self.save)

        except RuntimeError:
            pass

    def changed (self, buffer):
        if (self.changing):
            return

        self.error  = ''
        self.notice = ''
        self.navigator.edited (buffer.text, buffer.cursor_position)
        self.schedule_save ()

    def cursor_changed (self, buffer):
        if (not self.changing and self.navigator.current_id is None):
            self.navigator.draft_cursor = buffer.cursor_position
            self.schedule_save ()

    def display (self, text, cursor):
        self.changing = True

        try:
            self.area.buffer.set_document (Document (text, cursor))

        finally:
            self.changing = False

        self.error = ''

    def move (self, step):
        count      = int (self.count or '1')
        self.count = ''
        self.display (*self.navigator.move (self.records, step * count))

    def toggle (self):
        self.navigator.global_scope = not self.navigator.global_scope
        self.records                = self.history.payloads (None if self.navigator.global_scope else self.target.key)

        if self.navigator.current_id and not any (item.id == self.navigator.current_id for item in self.records):
            self.display (*self.navigator.select (Payload ("", self.navigator.draft)))

        return self.history_choices ()

    def history_choices (self):
        choices = []
        for item in self.navigator.items (self.records):
            if (item.id):
                preview = safe_line (item.text).strip ()[:100]
                label = ', '.join (item.targets) + '  ·  ' + preview

            else:
                label = '[Current draft]  ' + safe_line (item.text).strip ()[:100]
            choices.append (Choice (item.id, label, item.text, item))

        return choices

    def open_history (self, app, search = False, direction = None):
        previous_query = self.picker.query if self.picker else ''

        def restore (current_app):
            current_app.layout       = self.layout
            current_app.key_bindings = self.bindings

            current_app.layout.focus (self.area)
            current_app.invalidate ()

        def select (current_app, item):
            self.display (*self.navigator.select (item.value))
            self.browsing = False
            restore (current_app)

        self.picker = Picker (' Payload history · Enter loads a payload for editing',
                             self.history_choices (), toggle = self.toggle, scope = self.scope,
                             on_select = select, on_cancel = restore,
                             selected = self.navigator.current_id or ''
        )

        self.picker.query = previous_query
        app.layout        = self.picker.layout
        app.key_bindings  = self.picker.bindings

        if (direction):
            self.picker.find (direction)

        if (search):
            self.picker.search_snapshot = (previous_query, self.picker.index)
            self.picker.searching       = True
            self.picker.search.text     = ''
            app.layout.focus (self.picker.search)

        app.invalidate ()

    def validate (self):
        text = self.area.text

        try:
            payload_bytes (text)
            return pretty_json (text)

        except json.JSONDecodeError as exc:
            self.area.buffer.cursor_position = min (exc.pos, len (text))
            self.error = F'JSON error · line {exc.lineno}, column {exc.colno}: {exc.msg}'
            self.browsing = False

            return None

    def bindings (self):
        keys   = KeyBindings ()
        browse = Condition (lambda: self.browsing)

        @keys.add ('enter')
        def enter (event):
            if (self.browsing):
                self.browsing = False
                self.count    = ''
                return

            self.insert_newline ()

        @keys.add ('c-j')
        @keys.add ('f5')
        def accept (event):
            text = self.validate ()

            if (text is not None):
                self.navigator.edited (text, len (text))
                event.app.exit (result = text)

        @keys.add ('up')
        @keys.add ('k', filter = browse)
        def older (event):
            self.move (1)

        @keys.add ('down')
        @keys.add ('j', filter = browse)
        def newer (event):
            self.move (-1)

        @keys.add ('c-p')
        def line_up (event):
            self.area.buffer.cursor_up ()

        @keys.add ('c-n')
        def line_down (event):
            self.area.buffer.cursor_down ()

        @keys.add ('escape')
        def browse_mode (event):
            self.browsing = True
            self.count    = ''

        @keys.add ('i', filter = browse)
        def edit_mode (event):
            self.browsing = False
            self.count    = ''

        @keys.add (Keys.Any, filter = browse)
        def count (event):
            if (event.data in '0123456789' and len (event.data) ==  1):
                self.count = (self.count + event.data)[-6:]

            else:
                self.count = ''

        @keys.add ('c-a')
        def toggle_scope (event):
            self.toggle ()

        @keys.add ('c-r')
        def history (event):
            self.open_history (event.app)

        @keys.add ('/', filter = browse | Condition (lambda: not self.area.text.strip ()))
        def search (event):
            self.open_history (event.app, search = True)

        @keys.add ('n', filter = browse)
        def next_match (event):
            self.open_history (event.app, direction = 1)

        @keys.add ('N', filter = browse)
        def previous_match (event):
            self.open_history (event.app, direction = -1)

        @keys.add ('escape', 'enter')
        def newline (event):
            self.browsing = False
            self.insert_newline ()

        @keys.add ('tab')
        def indent (event):
            self.area.buffer.insert_text ('  ')

        @keys.add ('f4')
        def format_payload (event):
            text = self.validate ()

            if (text is not None):
                self.area.buffer.set_document (Document (text, len (text)))
                self.notice = 'Formatted JSON'

        @keys.add (Keys.BracketedPaste)
        def paste (event):
            self.browsing = False
            data = event.data.replace ('\r\n', '\n').replace ('\r', '\n')
            self.area.buffer.insert_text (data)

            try:
                text = pretty_json (self.area.text)

            except json.JSONDecodeError:
                return

            self.area.buffer.set_document (Document (text, len (text)))

        @keys.add ('c-c')
        @keys.add ('c-d')
        def abort (event):
            event.app.exit (exception = KeyboardInterrupt ())

        return keys

    def insert_newline (self):
        before = self.area.buffer.document.current_line_before_cursor
        indent = re.match (R' *', before).group (0)

        if (before.rstrip ().endswith (('{', '['))):
            indent += '  '

        self.area.buffer.insert_text ('\n' + indent)

    async def run_async (self):
        try:
            with ctrl_enter_sequences ():
                return await self.app.run_async ()

        finally:
            if (self.save_handle):
                self.save_handle.cancel ()

            self.save (strict = True)

    def run (self):
        return asyncio.run (self.run_async ())

def choose_function (functions, query = '', **kwargs):
    choices = [ Choice (item.key, item.label, json.dumps ({'FunctionName': item.name, 'FunctionArn': item.key}, indent=2), item) for item in functions ]
    title   = F' No exact Lambda match for {query!r} · closest names first' if query else ' Select a Lambda'
    choice  = Picker (title, choices).run (**kwargs)

    return choice.value if choice else None
