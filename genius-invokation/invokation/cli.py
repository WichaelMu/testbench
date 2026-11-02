from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path

from . import __version__
from .aws import AWS, AwsError
from .cache import CacheContext, LambdaCache, describe_refresh, find_cached
from .formatter import FormatterError, print_response
from .history import History, default_path
from .model import Target, payload_bytes, pretty_json, rank_functions, split_function


def parser ():
    result = argparse.ArgumentParser (
        prog='genius-invokation',
        description='Genshin-inspired interactive AWS Lambda invoker with portable JSON history.'
    )

    result.add_argument ('function', nargs = '?', help = 'Lambda name, ARN, or name:alias; typos open a ranked picker')
    result.add_argument ('--profile', help = 'AWS SSO/profile name (otherwise use AWS CLI defaults)')
    result.add_argument ('--region', help = 'AWS region (otherwise use ARN region or AWS CLI defaults)')
    result.add_argument ('--qualifier', help = 'Lambda alias or published version')
    result.add_argument ('--jq', '--jsonpath', dest = 'jq_filter', default = '.', metavar = 'FILTER', help = 'jq filter passed to mjsn for the response (default: whole result)')
    result.add_argument ('--refresh', action = 'store_true', help = 'Force a refresh of the cached Lambda list')

    payload = result.add_mutually_exclusive_group ()
    payload.add_argument ('--payload', help = 'Start the editor with this JSON text')
    payload.add_argument ('--payload-file', type = Path, help = 'Start the editor with a JSON file')

    result.add_argument ('--history-file', type = Path, default = default_path (), metavar = 'PATH', help = 'History database (default: %(default)s)')
    action = result.add_mutually_exclusive_group ()
    action.add_argument ('--check-login', action = 'store_true', help = 'Check AWS credentials and exit')
    action.add_argument ('--export-history', type = Path, metavar = 'FILE', help = 'Export all history/drafts/results as portable JSON')
    action.add_argument ('--import-history', type = Path, metavar = 'FILE', help = 'Merge an exported history; no AWS access required')
    result.add_argument ('--version', action = 'version', version = __version__)

    return result

def diagnose_login (aws: AWS, failure):
    print ('AWS request failed; checking login…', file=sys.stderr, flush = True)

    try:
        identity = aws.identity ()

    except AwsError as diagnostic:
        return AwsError (F'{failure}\n{diagnostic}')

    account = identity['Account']
    return AwsError (F'{failure}\nAWS credentials are valid for account …{account[-4:]}.')

def load_functions (aws, cache, force = False):
    snapshot = cache.load ()

    print ('Lambda cache last refresh: ' + describe_refresh (snapshot.refreshed_at if snapshot else None), flush = True)
    if (force or snapshot is None or not snapshot.fresh ()):
        print ('Refreshing Lambda list…', flush = True)
        try:
            functions = aws.functions ()

        except AwsError as exc:
            raise diagnose_login (aws, exc) from exc

        snapshot = cache.save (functions)
        print ('Lambda cache refreshed: ' + describe_refresh (snapshot.refreshed_at), flush = True)

    return snapshot.functions

def run (args):
    if (args.export_history or args.import_history):
        history = History (args.history_file)

        try:
            if (args.import_history):
                history.import_file (args.import_history)
                print (F'History merged into {history.path}')

            else:
                history.export (args.export_history)
                print (F'History exported to {args.export_history}')

        finally:
            history.close ()

        return 0

    region = args.region
    if (not region and args.function and args.function.startswith ('arn:')):
        if (len (args.function.split (':')) < 7 or ':function:' not in args.function):
            raise ValueError ('Expected a Lambda ARN such as arn:aws:lambda:REGION:ACCOUNT:function:NAME.')

        region = args.function.split (':')[3]

    context = CacheContext.local (args.profile, region)
    aws     = AWS (args.profile, context.region)

    if (args.check_login):
        print ('Checking AWS login…', flush = True)

        identity = aws.identity ()
        alias    = aws.account_alias ()

        print (F'AWS credentials valid · account …{identity['Account'][-4:]}' + (F' · account alias {alias}' if alias else '') + F' · profile {context.profile}')

        return 0

    if (not sys.stdin.isatty () or not sys.stdout.isatty ()):
        raise ValueError ('The editor needs an interactive terminal. Run it directly from zsh.')

    try:
        from .ui import Editor, choose_function

    except ImportError as exc:
        raise ValueError ('Missing editor dependencies. Run: python3 -m pip install -r ' + str (Path (__file__).resolve ().parent.parent / 'requirements.txt')) from exc

    history = History (args.history_file)

    try:
        print (F'Profile: {context.profile} · region: {context.region or 'AWS default'}', flush = True)

        functions = load_functions (aws, LambdaCache (history, context.key), args.refresh)
        target    = find_cached (args.function, functions, args.qualifier)

        if (target is None):
            if (not functions):
                raise ValueError ('No Lambda functions were found in the selected account and region. Use --refresh to discover newly added functions.')

            query, embedded_qualifier = split_function (args.function or '')
            if (':function:' in query):
                query = query.split (':function:', 1)[1]

            selected = choose_function (rank_functions (query, functions), args.function or '')
            if (selected is None):
                print ('Cancelled.')
                return 130

            target = Target (selected.name, selected.arn, args.qualifier or embedded_qualifier)

        print (F'Lambda: {target.label}', flush = True)

        initial = args.payload
        if (args.payload_file):
            initial = args.payload_file.expanduser ().read_text (encoding = 'utf-8-sig')

        if (initial is not None):
            try:
                initial = pretty_json (initial)

            except json.JSONDecodeError:
                pass

        editor = Editor (history, target, initial)
        text   = editor.run ()

        payload_bytes (text)
        invocation = history.begin (target, text)
        print (F'Invoking {target.label}…', flush = True)

        try:
            metadata, response = aws.invoke (target, text)

        except (AwsError, KeyboardInterrupt, OSError) as exc:
            history.finish (invocation, error = F'Invocation outcome not confirmed: {exc}')
            print ('The invocation outcome was not confirmed. The payload and attempt were saved; no automatic retry was made.', file = sys.stderr)

            if (isinstance (exc, AwsError)):
                raise diagnose_login (aws, exc) from exc

            raise

        history.finish (invocation, metadata, response)
        history.clear_draft (target.key)

        if (metadata.get ('FunctionError')):
            print (F'FunctionError: {metadata['FunctionError']}', file=sys.stderr, flush = True)

        print (F'StatusCode: {metadata.get ('StatusCode', 'unknown')}')
        print (F'ExecutedVersion: {metadata.get ('ExecutedVersion', 'unknown')}')
        print (flush = True)

        print_response (response, args.jq_filter)
        return 1 if metadata.get ('FunctionError') else 0

    finally:
        history.close ()


def main (argv = None):
    args = parser ().parse_args (argv)
    try:
        return run (args)

    except (KeyboardInterrupt, EOFError):
        print ('\nCancelled. Any active JSON draft was saved.', file = sys.stderr)
        return 130

    except (AwsError, FormatterError, OSError, ValueError, sqlite3.Error) as exc:
        print (F'genius-invokation: {exc}', file = sys.stderr)
        return 1
