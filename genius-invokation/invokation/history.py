from __future__ import annotations

import json
import os
import sqlite3
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path

from .model import Payload, Target, payload_id, pretty_json


def now ():
    return datetime.now (timezone.utc).isoformat (timespec = 'microseconds')

def default_path ():
    root = Path (os.environ.get ('XDG_DATA_HOME', str (Path.home () / '.local' / 'share')))
    return root / 'genius-invokation' / 'history.sqlite3'

TABLES = {
    'payloads': ('id', 'text', 'last_used'),
    'uses': ('payload_id', 'target', 'label', 'last_used'),
    'drafts': ('target', 'text', 'cursor', 'updated_at'),
    'invocations': ( 'id', 'payload_id', 'target', 'started_at', 'finished_at', 'status_code', 'executed_version', 'function_error', 'response', 'error' )
}

class History:
    def __init__ (self, path):
        self.path = path.expanduser ()
        self.path.parent.mkdir (mode = 0o700, parents = True, exist_ok = True)

        fd = os.open (self.path, os.O_CREAT | os.O_RDWR, 0o600)
        os.close (fd)

        self.db = sqlite3.connect (self.path, timeout=5)
        self.db.row_factory = sqlite3.Row
        self.db.execute ('PRAGMA foreign_keys=ON')

        version = self.db.execute ('PRAGMA user_version').fetchone ()[0]
        if (version not in (0, 1)):
            self.db.close ()
            raise ValueError (F'Unsupported history version {version}; no data was changed.')

        self.db.executescript ('''
            CREATE TABLE IF NOT EXISTS payloads (
                id TEXT PRIMARY KEY, text TEXT NOT NULL, last_used TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS uses (
                payload_id TEXT NOT NULL REFERENCES payloads (id), target TEXT NOT NULL,
                label TEXT NOT NULL, last_used TEXT NOT NULL,
                PRIMARY KEY (payload_id, target));
            CREATE TABLE IF NOT EXISTS drafts (
                target TEXT PRIMARY KEY, text TEXT NOT NULL,
                cursor INTEGER NOT NULL, updated_at TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS invocations (
                id TEXT PRIMARY KEY, payload_id TEXT NOT NULL REFERENCES payloads (id),
                target TEXT NOT NULL, started_at TEXT NOT NULL, finished_at TEXT,
                status_code INTEGER, executed_version TEXT, function_error TEXT,
                response TEXT, error TEXT);
            CREATE INDEX IF NOT EXISTS uses_target ON uses (target, last_used);
            PRAGMA user_version=1;
        ''')

    def close (self):
        self.db.close ()

    def draft (self, target):
        row = self.db.execute ('SELECT text,cursor FROM drafts WHERE target=?', (target,)).fetchone ()
        return (row['text'], row['cursor']) if row else ('', 0)

    def save_draft (self, target, text, cursor):
        with self.db:
            self.db.execute (
            '''
            INSERT INTO drafts VALUES (?,?,?,?)
            ON CONFLICT (target) DO UPDATE SET text=excluded.text,
            cursor=excluded.cursor, updated_at=excluded.updated_at
            ''', (target, text, min (max (cursor, 0), len (text)), now ()))

    def clear_draft (self, target):
        with self.db:
            self.db.execute ('DELETE FROM drafts WHERE target=?', (target,))

    def payloads (self, target = None):
        rows = self.db.execute (
        '''
            SELECT p.id,p.text,MAX (u.last_used) AS recent FROM payloads p
            JOIN uses u ON p.id=u.payload_id
            WHERE (? IS NULL OR u.target=?) GROUP BY p.id
            ORDER BY recent DESC,p.id
        ''', (target, target)).fetchall ()
        labels = {}

        for row in self.db.execute ('SELECT payload_id,label FROM uses ORDER BY label'):
            labels.setdefault (row['payload_id'], []).append (row['label'])

        return [Payload (row['id'], row['text'], labels.get (row['id'], [])) for row in rows]

    def begin (self, target, text):
        identifier, timestamp = payload_id (text), now ()
        invocation = str (uuid.uuid4())

        with self.db:
            self.db.execute ('''INSERT INTO payloads VALUES (?,?,?)
                ON CONFLICT (id) DO UPDATE SET last_used=excluded.last_used''',
                (identifier, pretty_json (text), timestamp)
            )

            self.db.execute ('''INSERT INTO uses VALUES (?,?,?,?)
                ON CONFLICT (payload_id,target) DO UPDATE SET
                label=excluded.label,last_used=excluded.last_used''',
                (identifier, target.key, target.label, timestamp)
            )

            self.db.execute ('''INSERT INTO invocations
                (id,payload_id,target,started_at) VALUES (?,?,?,?)''',
                (invocation, identifier, target.key, timestamp)
            )

        return invocation

    def finish (self, invocation, metadata = None, response = None, error = None):
        metadata = metadata or {}
        with self.db:
            self.db.execute ('''
                UPDATE invocations SET finished_at=?,status_code=?,
                executed_version=?,function_error=?,response=?,error=? WHERE id=?
            ''', (now (), metadata.get ('StatusCode'), metadata.get ('ExecutedVersion'),
                  metadata.get ('FunctionError'), response, error, invocation)
            )

    def export (self, destination):
        data = { 'format': 'genius-invokation', 'version': 1 }
        with self.db:
            self.db.execute ('BEGIN')

            for table in TABLES:
                data[table] = [ dict (row) for row in self.db.execute (F'SELECT * FROM {table}') ]

        destination = destination.expanduser ()
        if (destination.resolve () == self.path.resolve ()):
            raise ValueError ('The export destination must differ from the history database.')

        destination.parent.mkdir (mode = 0o700, parents = True, exist_ok = True)
        fd, temporary = tempfile.mkstemp (prefix = '.invokation-export-', dir = destination.parent)

        try:
            with os.fdopen (fd, 'w', encoding = 'utf-8') as stream:
                json.dump (data, stream, ensure_ascii = True, indent = 2)
                stream.write ('\n')
                stream.flush ()
                os.fsync (stream.fileno ())

            os.replace (temporary, destination)

        finally:
            if (os.path.exists (temporary)):
                os.unlink (temporary)

    def import_file (self, source):
        data = json.loads (source.expanduser ().read_text (encoding = 'utf-8'))

        if (not isinstance (data, dict) or data.get ('format') != 'genius-invokation' or type (data.get ('version')) is not int or data['version'] != 1):
            raise ValueError ('Not a supported Genius Invokation history export.')

        for table, columns in TABLES.items ():
            if (not isinstance (data.get (table), list)):
                raise ValueError (F'History export is missing {table}.')

            for row in data[table]:
                if (not isinstance (row, dict) or set (row) != set (columns)):
                    raise ValueError (F'Invalid {table} record.')

                for column, value in row.items ():
                    if (column in ('cursor', 'status_code')):
                        if (type (value) is not int and not (column == 'status_code' and value is None)):
                            raise ValueError (F'Invalid {table}.{column}.')

                    elif value is None and table == 'invocations' and column in (
                            'finished_at', 'executed_version', 'function_error', 'response', 'error'):

                        continue

                    elif (not isinstance (value, str)):
                        raise ValueError (F'Invalid {table}.{column}.')

                if (table == 'payloads' and payload_id (row['text']) != row['id']):

                    raise ValueError ('Payload checksum mismatch in export.')
                if (table == 'drafts' and not 0 <= row['cursor'] <= len (row['text'])):
                    raise ValueError ('Invalid draft cursor in export.')

        with self.db:
            for row in data['payloads']:
                self.db.execute ('''
                    INSERT INTO payloads VALUES (?,?,?) ON CONFLICT (id)
                    DO UPDATE SET last_used=MAX (last_used,excluded.last_used)
                ''', tuple (row[c] for c in TABLES['payloads'])
                )

            for row in data['uses']:
                self.db.execute ('''
                    INSERT INTO uses VALUES (?,?,?,?)
                    ON CONFLICT (payload_id,target) DO UPDATE SET label=excluded.label,
                    last_used=MAX (last_used,excluded.last_used)
                ''', tuple (row[c] for c in TABLES['uses']))
            for row in data['drafts']:
                self.db.execute ('''
                    INSERT INTO drafts VALUES (?,?,?,?) ON CONFLICT (target)
                    DO UPDATE SET text=excluded.text,cursor=excluded.cursor,
                    updated_at=excluded.updated_at WHERE excluded.updated_at > updated_at
                ''', tuple (row[c] for c in TABLES['drafts'])
                )

            for row in data['invocations']:
                self.db.execute ('''
                    INSERT INTO invocations VALUES (?,?,?,?,?,?,?,?,?,?)
                    ON CONFLICT (id) DO UPDATE SET finished_at=excluded.finished_at,
                    status_code=excluded.status_code,executed_version=excluded.executed_version,
                    function_error=excluded.function_error,response=excluded.response,error=excluded.error
                    WHERE excluded.finished_at IS NOT NULL AND
                    (invocations.finished_at IS NULL OR excluded.finished_at > invocations.finished_at)
                ''', tuple (row[c] for c in TABLES['invocations'])
                )
