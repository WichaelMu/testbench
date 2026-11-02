from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from decimal import Decimal
from difflib import SequenceMatcher


MAX_PAYLOAD_BYTES = 6 * 1024 * 1024


def parse_json (text: str):
    def reject_constant (value):
        pattern = R'"(?:\\.|[^"\\])*"|(?P<const>-Infinity|Infinity|NaN)'
        position = next ( (m.start () for m in re.finditer (pattern, text) if m.group ('const') == value), 0 )
        raise json.JSONDecodeError (F'{value} is not valid JSON', text, position)

    try:
        return json.loads (text, parse_constant=reject_constant, parse_float=Decimal)

    except (ValueError, RecursionError) as exc:
        if (isinstance (exc, json.JSONDecodeError)):
            raise

        raise json.JSONDecodeError (str (exc), text, 0) from exc

def dump (value, *, pretty = False, sort_keys = False, level = 0):
    if (isinstance (value, Decimal)):
        return str (value)

    if (isinstance (value, (dict, list))):
        mapping = isinstance (value, dict)
        opening, closing = ('{', '}') if mapping else ('[', ']')

        if (not value):
            return opening + closing

        keys = sorted (value) if mapping and sort_keys else value
        pieces = []

        for key in keys:
            item = value[key] if mapping else key
            rendered = dump (item, pretty=pretty, sort_keys=sort_keys, level=level + 1)

            if (mapping):
                rendered = json.dumps (key, ensure_ascii=True) + (': ' if pretty else ':') + rendered

            pieces.append (rendered)

        if (pretty):
            margin = '  ' * (level + 1)
            return opening + '\n' + margin + (',\n' + margin).join (pieces) + '\n' + '  ' * level + closing

        return opening + ','.join (pieces) + closing

    return json.dumps (value, ensure_ascii=True, allow_nan=False)

def render_json (text, **kwargs):
    try:
        return dump (parse_json (text), **kwargs)

    except RecursionError as exc:
        raise json.JSONDecodeError ('JSON is nested too deeply', text, 0) from exc

def pretty_json (text):
    return render_json (text, pretty = True)

def payload_bytes (text):
    data = render_json (text).encode ('utf-8')

    if (len (data) > MAX_PAYLOAD_BYTES):
        raise json.JSONDecodeError ('Payload exceeds Lambda\'s 6 MiB synchronous limit', text, 0)

    return data

def payload_id (text):
    canonical = render_json (text, sort_keys = True)
    return hashlib.sha256(canonical.encode ('utf-8')).hexdigest ()

@dataclass (frozen = True)
class Target:
    name: str
    arn: str
    qualifier: str | None = None

    @property
    def key (self):
        return self.arn + (F':{self.qualifier}' if self.qualifier else '')

    @property
    def region (self):
        return self.arn.split (':')[3]

    @property
    def account (self):
        return self.arn.split (':')[4]

    @property
    def label (self):
        name = self.name + (F':{self.qualifier}' if self.qualifier else '')
        return F'{name} (…{self.account[-4:]}, {self.region})'

def split_function (value):
    if (':function:' in value):
        prefix, name = value.split (':function:', 1)
        parts        = name.split (':', 1)

        return prefix + ':function:' + parts[0], parts[1] if len (parts) > 1 else None

    if (':' in value and not value.startswith ('arn:')):
        if (':function:' not in value and value.count (':') == 1):
            return tuple (value.split (':', 1))

    return value, None

def rank_functions (query, functions):
    query = query.casefold ()
    tokens = set (filter (None, re.split (r'[-_.\s]+', query)))

    def score (target):
        name       = target.name.casefold ()
        overlap    = len (tokens & set (re.split (r'[-_.\s]+', name))) / max (len (tokens), 1)
        similarity = SequenceMatcher (None, query, name).ratio ()

        return (query == name, bool (query) and query in name, overlap, similarity)

    return sorted (sorted (functions, key=lambda t: t.name), key=score, reverse=True)

@dataclass
class Payload:
    id: str
    text: str
    targets: list[str] = field (default_factory = list)

class Navigator:
    def __init__(self, text = '', cursor = None):
        self.draft        = text
        self.draft_cursor = len (text) if cursor is None else min (cursor, len (text))
        self.current_id   = None
        self.global_scope = False

    def edited (self, text, cursor):
        self.draft        = text
        self.draft_cursor = cursor
        self.current_id   = None

    def select (self, item):
        self.current_id = item.id or None

        if (not item.id):
            return self.draft, self.draft_cursor

        return item.text, len (item.text)

    def items (self, history):
        return [ Payload ('', self.draft, [ 'Current draft' ]), *history ]

    def move (self, history, step):
        items = self.items (history)
        index = next ((i for i, item in enumerate (items) if item.id == (self.current_id or '')), 0)

        return self.select (items[(index + step) % len (items)])
