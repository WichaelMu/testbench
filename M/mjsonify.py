import os
import sys
import json
import ast
import datetime as _dt

def tzlocal ():
    # stdlib-only local tzinfo
    return _dt.datetime.now ().astimezone ().tzinfo

def tzutc ():
    return _dt.timezone.utc

def tzoffset (name, offset_seconds):
    delta = _dt.timedelta (seconds = int (offset_seconds))
    if isinstance (name, str):
        return _dt.timezone (delta, name)
    return _dt.timezone (delta)

def safe_eval_boto3_repr (text):
    safe_globals = {
        '__builtins__': {},
        'datetime': _dt,
        'tzlocal': tzlocal,
        'tzutc': tzutc,
        'tzoffset': tzoffset,
    }
    return eval (text, safe_globals, {})

def main ():
    inbound = sys.stdin.read ().strip ()
    if (len (inbound) == 0):
        return json.dumps ({'MJSN': 'Nothing was received as input.'})

    try:
        try:
            dict_form = json.loads (inbound)

        except Exception:
            try:
                dict_form = ast.literal_eval (inbound)

            except Exception:
                dict_form = safe_eval_boto3_repr (inbound)

        return json.dumps (dict_form, default = str, indent = 4)

    except Exception as e:
        return json.dumps (
            {
                'MJSN': 'Failed to parse input',
                'error': str (e),
                'head': inbound[:300],
            },
            indent=4,
        )

if (__name__ == '__main__'):
    print (main ())
