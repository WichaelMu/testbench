from contextlib import contextmanager

from prompt_toolkit.input.ansi_escape_sequences import ANSI_SEQUENCES
from prompt_toolkit.keys import Keys


@contextmanager
def ctrl_enter_sequences():
    sequences = ('\x1b[13;5u', '\x1b[27;5;13~')
    previous  = {sequence: ANSI_SEQUENCES.get(sequence) for sequence in sequences}
    ANSI_SEQUENCES.update (dict.fromkeys (sequences, Keys.ControlJ))

    try:
        yield

    finally:
        for sequence, key in previous.items ():
            if key is None:
                ANSI_SEQUENCES.pop (sequence, None)
            else:
                ANSI_SEQUENCES[sequence] = key
