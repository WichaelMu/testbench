import os
import shutil
import subprocess


class FormatterError (RuntimeError):
    pass

def print_response (text, jq_filter = '.'):
    zsh = shutil.which ('zsh')

    if (not zsh):
        raise FormatterError ('mjsn requires zsh. The raw Lambda response is retained in history.')

    env = dict (os.environ, GENIUS_INVOKATION_JQ_FILTER=jq_filter)

    try:
        result = subprocess.run (
            [ zsh, '-i', '-c', 'whence mjsn >/dev/null 2>&1 || exit 127\n' 'setopt pipefail\nmjsn -C -- $GENIUS_INVOKATION_JQ_FILTER', 'genius-invokation-mjsn' ],
            input = text, text = True, capture_output = True, timeout = 30, env = env,
        )
    except (subprocess.TimeoutExpired, OSError) as exc:
        raise FormatterError (F'mjsn failed: {exc}. The raw Lambda response is retained in history.') from exc

    if (result.returncode):
        detail = result.stderr.strip () or F'mjsn exited with status {result.returncode}'
        raise FormatterError (F'mjsn failed: {detail}. The raw Lambda response is retained in history.')

    if (result.stdout):
        print (result.stdout, end='' if result.stdout.endswith ('\n') else '\n')
