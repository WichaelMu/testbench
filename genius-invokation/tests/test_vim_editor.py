import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from invokation.history import History
from invokation.model import Target, pretty_json
from invokation.vim_editor import Editor, Session, editor_command


class SessionTests (unittest.TestCase):
    def setUp (self):
        self.directory = tempfile.TemporaryDirectory ()
        self.addCleanup (self.directory.cleanup)
        self.history = History (Path (self.directory.name) / 'history.sqlite3')
        self.addCleanup (self.history.close)
        self.target = Target ('test', 'arn:aws:lambda:ap-southeast-2:123456789012:function:test')
        self.other = Target ('other', 'arn:aws:lambda:ap-southeast-2:123456789012:function:other')
        self.history.begin (self.target, '{"entry": 1}')
        self.history.begin (self.target, '{"entry": 2}')
        self.history.begin (self.other, '{"other": true}')

    def test_kvim_preferred_with_vim_fallback (self):
        for available, expected in [({'kvim', 'vim'}, 'kvim'), ({'vim'}, 'vim')]:
            with self.subTest (available = available), patch (
                'invokation.vim_editor.shutil.which', side_effect = lambda name: '/bin/' + name if name in available else None
            ):
                self.assertEqual (editor_command (), '/bin/' + expected)
        with patch ('invokation.vim_editor.shutil.which', return_value = None):
            with self.assertRaisesRegex (ValueError, 'kvim or vim'):
                editor_command ()

    def test_history_wraps_without_losing_draft_or_cursor (self):
        session = Session (self.history, self.target, 'draft')
        session.update ('draft', 2)
        session.request ('older')
        self.assertEqual (json.loads (session.text), {'entry': 2})
        session.request ('older')
        self.assertEqual (json.loads (session.text), {'entry': 1})
        session.request ('older')
        self.assertEqual ((session.text, session.cursor), ('draft', 2))
        session.request ('newer')
        self.assertEqual (json.loads (session.text), {'entry': 1})
        self.assertEqual (self.history.draft (self.target.key), ('draft', 2))

    def test_editing_history_becomes_draft_and_scope_falls_back_to_it (self):
        session = Session (self.history, self.target, '{}')
        session.request ('older')
        session.update ('{"edited": true}', 4)
        session.request ('save')
        self.assertIsNone (session.navigator.current_id)
        self.assertEqual (self.history.draft (self.target.key), ('{"edited": true}', 4))
        session.request ('scope')
        session.request ('older')
        self.assertEqual (json.loads (session.text), {'other': True})
        session.request ('scope')
        self.assertIsNone (session.navigator.current_id)
        self.assertEqual ((session.text, session.cursor), ('{"edited": true}', 4))

    def test_invalid_payload_cannot_invoke (self):
        session = Session (self.history, self.target, '{"oops":}')
        session.request ('invoke')
        self.assertEqual (session.action, '')
        self.assertIn ('JSON error', session.error)
        self.assertEqual (session.cursor, 8)
        self.assertEqual (self.history.draft (self.target.key)[0], '{"oops":}')

    def run_vim (self, script, initial = None, *, result = None, cancelled = False, executable = None, exit_command = None):
        executable = executable or shutil.which ('kvim') or shutil.which ('vim')
        if executable is None:
            self.skipTest ('Vim is not installed')
        root = Path (self.directory.name)
        driver = root / 'test.vim'
        log = root / 'vim.log'
        assertions = root / 'assertions.json'
        exit_command = exit_command or ('call InvokationRequest("cancel")' if cancelled else 'call InvokationRequest("invoke")')
        driver.write_text (
            script + '\ncall writefile([json_encode(v:errors)], ' + repr (str (assertions)) + ')\n'
            + exit_command + '\n',
            encoding = 'utf-8'
        )
        real_run = subprocess.run

        def launch (args):
            process = real_run (
                [executable, '-Nu', 'NONE', '-es', '-V1' + str (log), *args[1:], '-S', str (driver)],
                capture_output = True, text = True, timeout = 20
            )
            self.assertEqual (process.returncode, 0, process.stderr + '\n' + log.read_text ())
            self.assertEqual (json.loads (assertions.read_text ()), [])
            return process

        with patch ('invokation.vim_editor.subprocess.run', side_effect = launch):
            editor = Editor (self.history, self.target, initial)
            if cancelled:
                with self.assertRaises (KeyboardInterrupt):
                    editor.run ()
            else:
                self.assertEqual (editor.run (), pretty_json (result or initial))

    def test_real_vim_motions_history_sidebar_and_draft (self):
        draft = '{\n  "draft": true\n}'
        self.run_vim (r'''
let main = bufnr('%')
let sidebar = winbufnr(2)
call assert_equal(['› Draft', '  History 1', '  History 2'], getbufline(sidebar, 1, '$'))
normal! gg0
call feedkeys('j', 'xt')
call assert_equal(2, line('.'))
call feedkeys('llh', 'xt')
call assert_equal(2, col('.'))
call feedkeys('k', 'xt')
call assert_equal(1, line('.'))
call assert_equal(main, bufnr('%'))
call feedkeys("\<Up>", 'xt')
call assert_match('"entry": 2', join(getline(1, '$'), "\n"))
call assert_equal(['  Draft', '› History 1', '  History 2'], getbufline(sidebar, 1, '$'))
call feedkeys("\<Left>\<Right>", 'xt')
call assert_equal(['  Draft', '› History 1', '  History 2'], getbufline(sidebar, 1, '$'))
call feedkeys("\<Down>", 'xt')
call assert_match('"draft": true', join(getline(1, '$'), "\n"))
call feedkeys("2\<Up>", 'xt')
call assert_match('"entry": 1', join(getline(1, '$'), "\n"))
call feedkeys("i\<Up>\<Esc>", 'xt')
call assert_match('"draft": true', join(getline(1, '$'), "\n"))
normal! gg0
call feedkeys('/draft' . "\<CR>", 'xt')
call assert_equal(2, line('.'))
call assert_equal(main, bufnr('%'))
''', draft)

    def test_real_vim_edits_undo_unicode_cursor_and_save (self):
        self.run_vim (r'''
normal! gg0
call feedkeys('A ' . "\<Esc>", 'xt')
call InvokationRequest('save')
call feedkeys('u', 'xt')
call assert_equal('{', getline(1))
call cursor(2, byteidx(getline(2), 6) + 1)
call InvokationRequest('save')
let state = json_decode(join(readfile(g:invokation_state_path), "\n"))
call assert_equal(8, state.cursor)
call assert_equal(v:null, state.current_id)
call feedkeys('A' . "\<CR>\<Esc>", 'xt')
call InvokationRequest('save')
let state = json_decode(join(readfile(g:invokation_state_path), "\n"))
call assert_equal('', state.action)
call assert_match("\n", state.draft)
''', '{\n  "é雪": 1\n}', cancelled = True)
        self.assertIn ('é雪', self.history.draft (self.target.key)[0])

    def test_standard_vim_fallback_runs_same_editor (self):
        self.run_vim ('call assert_equal("json", &filetype)', '{}', executable = shutil.which ('vim'))

    def test_real_vim_quit_saves_without_invoking (self):
        self.run_vim ('''
call feedkeys('A ' . "\\<Esc>", 'xt')
''', '{}', cancelled = True, exit_command = 'quit')
        self.assertEqual (self.history.draft (self.target.key)[0], '{} ')

    def test_only_ctrl_j_has_an_invoke_key_binding (self):
        self.run_vim (r'''
for key in ['<C-CR>', '<C-kEnter>', '<F5>']
    for mode in ['n', 'i', 'x']
        call assert_equal('', maparg(key, mode))
    endfor
endfor
''', '{}', exit_command = r'call feedkeys("\<C-J>", "xt")')

    def test_typed_write_quit_invokes (self):
        for command in ('wq', 'wq!'):
            with self.subTest (command = command):
                self.run_vim ('', '{"invoke": true}', exit_command = F'call feedkeys(":{command}\\<CR>", "xt")')

    def test_typed_force_quit_exits_without_invoking (self):
        self.run_vim ('', '{"incomplete":', cancelled = True, exit_command = r'call feedkeys(":q!\<CR>", "xt")')
        self.assertEqual (self.history.draft (self.target.key)[0], '{"incomplete":')

    def test_write_only_saves_to_sqlite (self):
        self.run_vim (r'''
call feedkeys('A ' . "\<Esc>", 'xt')
call feedkeys(":w!\<CR>", 'xt')
let state = json_decode(join(readfile(g:invokation_state_path), "\n"))
call assert_equal('{} ', state.draft)
call assert_equal('', state.action)
call assert_equal(['{}'], readfile(expand('%:p')))
''', '{}', cancelled = True)
        self.assertEqual (self.history.draft (self.target.key)[0], '{} ')

    def test_write_quit_rejects_invalid_json_and_stays_in_editor (self):
        self.run_vim (r'''
call feedkeys(":wq!\<CR>", 'xt')
let state = json_decode(join(readfile(g:invokation_state_path), "\n"))
call assert_equal('', state.action)
call assert_match('JSON error', state.error)
call assert_equal('json', &filetype)
''', '{"incomplete":', cancelled = True)

    def test_real_vim_preserves_trailing_newline_and_combining_cursor (self):
        draft = '{"e\u0301": 1}\n'
        self.history.save_draft (self.target.key, draft, 4)
        self.run_vim (r'''
call InvokationRequest('save')
let state = json_decode(join(readfile(g:invokation_state_path), "\n"))
call assert_equal(4, state.cursor)
call assert_equal('', getline('$'))
''', cancelled = True)
        self.assertEqual (self.history.draft (self.target.key), (draft, 4))

    @unittest.skipUnless (os.name == 'posix', 'Requires a Unix terminal')
    def test_real_vim_saves_without_enabling_terminal_echo (self):
        import fcntl
        import pty
        import struct
        import termios

        if not (shutil.which ('kvim') or shutil.which ('vim')):
            self.skipTest ('Vim is not installed')
        root = Path (self.directory.name)
        flags_path = root / 'terminal-flags.json'
        driver = root / 'terminal-test.vim'
        driver.write_text ('call InvokationRequest("cancel")\n')
        master, slave = pty.openpty ()
        self.addCleanup (os.close, master)
        self.addCleanup (os.close, slave)
        fcntl.ioctl (slave, termios.TIOCSWINSZ, struct.pack ('HHHH', 30, 140, 0, 0))
        real_run = subprocess.run

        def launch (args):
            helper = Path (args[args.index ('-S') + 1]).with_name ('bridge.py')
            helper.write_text (
                'import json, os, termios\nfrom pathlib import Path\n'
                + F'fd = os.open({os.ttyname (slave)!r}, os.O_RDONLY | os.O_NOCTTY)\n'
                + F'Path({str (flags_path)!r}).write_text(json.dumps(termios.tcgetattr(fd)[3]))\n'
                + 'os.close(fd)\n' + helper.read_text ()
            )
            process = real_run (
                [args[0], '-Nu', 'NONE', *args[1:], '-S', str (driver)],
                stdin = slave, stdout = slave, stderr = slave,
                env = {**os.environ, 'TERM': 'xterm-256color'}, timeout = 10
            )
            self.assertEqual (process.returncode, 0)
            flags = json.loads (flags_path.read_text ())
            self.assertFalse (flags & termios.ECHO, 'Draft save must not echo arrow key escape sequences')
            self.assertFalse (flags & termios.ICANON, 'Draft save must keep raw terminal input')
            return process

        with patch ('invokation.vim_editor.subprocess.run', side_effect = launch):
            with self.assertRaises (KeyboardInterrupt):
                Editor (self.history, self.target, '{}').run ()


if __name__ == '__main__':
    unittest.main ()
