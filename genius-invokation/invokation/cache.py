from __future__ import annotations

import configparser
import hashlib
import json
import os
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from .history import History
from .model import Target, split_function


MAX_AGE = timedelta (days=7)


def utc_now ():
    return datetime.now (timezone.utc)

def relative_age (elapsed):
    units        = ( ('day', 86400000), ('hour', 3600000), ('minute', 60000), ('second', 1000), ('millisecond', 1) )
    milliseconds = max (0, (elapsed.days * 86400 + elapsed.seconds) * 1000 + elapsed.microseconds // 1000)
    highest      = next ((i for i, (_, size) in enumerate (units) if milliseconds >= size), 4)
    pieces = []

    for name, size in units[highest:highest + 2]:
        value, milliseconds = divmod (milliseconds, size)
        if (value or not pieces):
            pieces.append (f'{value} {name}{'' if value == 1 else 's'}')

    return ', '.join (pieces) + ' ago'

def describe_refresh (timestamp, at = None):
    if (timestamp is None):
        return 'never'

    local  = timestamp.astimezone (ZoneInfo ('Australia/Sydney'))
    offset = local.strftime ('%z')
    offset = offset[:3] + ':' + offset[3:]
    age    = relative_age ((at or utc_now ()).astimezone (timezone.utc) - timestamp.astimezone (timezone.utc))

    return F'{local:%Y-%m-%d %H:%M:%S %Z} (UTC{offset}) · {age}'

def effective_profile (profile = None):
    return profile or os.environ.get ('AWS_DEFAULT_PROFILE') or os.environ.get ('AWS_PROFILE') or 'default'

def _configuration (path):
    parser = configparser.RawConfigParser ()
    try:
        with path.open (encoding='utf-8-sig') as stream:
            parser.read_file (stream)

    except FileNotFoundError:
        pass

    except configparser.Error as exc:
        raise ValueError (f'Could not read AWS configuration {path}: {exc}') from exc

    return parser

@dataclass (frozen = True)
class CacheContext:
    profile: str
    region: str | None
    key: str

    @classmethod
    def local (cls, profile = None, region = None):
        selected         = effective_profile (profile)
        config_path      = Path (os.environ.get ('AWS_CONFIG_FILE', '~/.aws/config')).expanduser ()
        credentials_path = Path (os.environ.get ('AWS_SHARED_CREDENTIALS_FILE', '~/.aws/credentials')).expanduser ()

        config      = _configuration (config_path)
        credentials = _configuration (credentials_path)

        current = selected

        sections = {}
        settings = {}
        visited  = set ()

        while current and current not in visited:
            visited.add (current)

            section = 'default' if current == 'default' else f'profile {current}'
            values  = dict (config[section]) if config.has_section (section) else {}

            credential_values = dict (credentials[current]) if credentials.has_section (current) else {}
            sections[section] = {'configuration': values, 'credentials': credential_values}

            if (current == selected):
                settings = {**values, **credential_values}

            for prefix, setting in ( ('sso-session', 'sso_session'), ('services', 'services') ):
                extra = f'{prefix} {values.get (setting, '')}'
                if (config.has_section (extra)):
                    sections[extra] = dict (config[extra])

            current = values.get ('source_profile')

        resolved_region = (region or os.environ.get ('AWS_REGION') or os.environ.get ('AWS_DEFAULT_REGION') or settings.get ('region'))

        material = {
            'version': 1, 'profile': selected, 'region': resolved_region,
            'config_path': str (config_path.resolve ()),
            'credentials_path': str (credentials_path.resolve ()),
            'sections': sections,
            'environment': {key: value for key, value in os.environ.items () if key.startswith ('AWS_') and key not in ( 'AWS_PAGER', 'AWS_CLI_AUTO_PROMPT', 'AWS_MAX_ATTEMPTS', 'AWS_RETRY_MODE') }
        }
        key = hashlib.sha256 (json.dumps (material, sort_keys = True).encode ()).hexdigest ()
        return cls (selected, resolved_region, key)

@dataclass
class Snapshot:
    functions: list[Target]
    refreshed_at: datetime

    def fresh (self, at = None):
        age = (at or utc_now ()).astimezone (timezone.utc) - self.refreshed_at.astimezone (timezone.utc)
        return timedelta (0) <= age <= MAX_AGE

class LambdaCache:
    def __init__(self, history, namespace):
        self.db = history.db
        self.namespace = namespace
        with self.db:
            self.db.execute ('''CREATE TABLE IF NOT EXISTS lambda_cache (namespace TEXT PRIMARY KEY, refreshed_at TEXT NOT NULL, functions TEXT NOT NULL)''')

    def load (self):
        row = self.db.execute ('SELECT refreshed_at,functions FROM lambda_cache WHERE namespace=?', (self.namespace,)).fetchone ()
        if (row is None):
            return None

        try:
            refreshed_at = datetime.fromisoformat (row['refreshed_at'])
            if (refreshed_at.tzinfo is None):
                return None

            data = json.loads (row['functions'])
            if (not isinstance (data, list)):
                return None

            functions = []
            for item in data:
                if (not isinstance (item, dict) or set (item) != {'name', 'arn'} or not isinstance (item['name'], str) or not isinstance (item['arn'], str) or len (item['arn'].split (':')) != 7 or ':function:' not in item['arn']):
                    return None

                functions.append (Target (item['name'], item['arn']))
            return Snapshot (functions, refreshed_at)

        except (ValueError, TypeError):
            return None

    def save (self, functions, at = None):
        snapshot = Snapshot (functions, (at or utc_now ()).astimezone (timezone.utc))
        data = json.dumps ([{'name': target.name, 'arn': target.arn} for target in functions])
        with self.db:
            self.db.execute (
                '''INSERT INTO lambda_cache VALUES (?,?,?) ON CONFLICT (namespace) DO UPDATE SET refreshed_at=excluded.refreshed_at, functions=excluded.functions''',
                (self.namespace, snapshot.refreshed_at.isoformat (), data)
            )

        return snapshot

def find_cached (value, functions, qualifier = None):
    if (not value):
        return None

    base, embedded = split_function (value)
    if (embedded and qualifier and embedded != qualifier):
        raise ValueError ('The function\'s alias/version conflicts with --qualifier.')

    qualifier = qualifier or embedded
    for target in functions:
        if (base in (target.name, target.arn, ':'.join (target.arn.split (':')[4:]))):
            return Target (target.name, target.arn, qualifier)

    if (base.startswith ('arn:') and ':function:' in base and len (base.split (':')) == 7):
        return Target (base.split (':function:', 1)[1], base, qualifier)

    return None
