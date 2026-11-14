"""Private, persistent SMS history. Transmission is never replayed by this store."""
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import time
import uuid

from .modem import validate_action


def message_fingerprint(message):
    # State is deliberately excluded: receiving -> received is the same SMS.
    parts = [message[k] for k in ('number', 'text', 'timestamp')]
    parts.append('received' if message.get('state') == 3 else 'sent')
    if not message['timestamp']:parts.append(message.get('path'))
    return hashlib.sha256(json.dumps(parts,
                                     ensure_ascii=True).encode()).hexdigest()


class SmsArchive:
    def __init__(self, directory='/var/lib/openstick/sms'):
        self.directory = Path(directory)

    @contextmanager
    def database(self):
        self.directory.mkdir(parents=True, exist_ok=True, mode=0o700)
        if os.name != 'nt':os.chmod(self.directory, 0o700)
        target = self.directory / 'messages.db'
        fd = os.open(target, os.O_WRONLY | os.O_CREAT | getattr(os, 'O_NOFOLLOW', 0), 0o600)
        os.close(fd)
        if os.name != 'nt':os.chmod(target, 0o600)
        db = sqlite3.connect(target, timeout=10)
        db.row_factory = sqlite3.Row
        try:
            db.execute('PRAGMA secure_delete=ON')
            db.execute('''CREATE TABLE IF NOT EXISTS messages (
                id TEXT PRIMARY KEY, fingerprint TEXT UNIQUE, operation TEXT UNIQUE,
                number TEXT NOT NULL, text TEXT NOT NULL, timestamp TEXT NOT NULL,
                direction TEXT NOT NULL, outcome TEXT NOT NULL, source TEXT,
                seen REAL NOT NULL, deleted INTEGER NOT NULL DEFAULT 0)''')
            with db:yield db
        finally:db.close()

    def import_messages(self, messages):
        with self.database() as db:
            for m in messages:
                # Incomplete multipart SMS is not an archive-ready message.
                if m.get('state') not in (3, 4, 5):continue
                direction = 'received' if m['state'] == 3 else 'sent'
                fingerprint = message_fingerprint(m)
                existing = db.execute('SELECT id FROM messages WHERE fingerprint=?', (fingerprint,)).fetchone()
                if existing:
                    db.execute('UPDATE messages SET source=? WHERE id=?', (m.get('path'), existing['id']))
                    continue
                # A successful local send already has an archive record. Match
                # only an exact, current DBus path plus content, never a number alone.
                sent = db.execute('''SELECT id FROM messages WHERE source=? AND number=? AND text=?
                    AND direction='sent' AND fingerprint IS NULL AND seen>?''',
                    (m.get('path'), m['number'], m['text'], time.time() - 300)).fetchone() if direction == 'sent' else None
                if sent:
                    db.execute('UPDATE messages SET fingerprint=?, timestamp=? WHERE id=?',
                               (fingerprint, m['timestamp'], sent['id']))
                    continue
                db.execute('''INSERT INTO messages VALUES (?, ?, NULL, ?, ?, ?, ?, ?, ?, ?, 0)''',
                           (str(uuid.uuid4()), fingerprint, m['number'], m['text'], m['timestamp'],
                            direction, 'received' if direction == 'received' else 'submitted',
                            m.get('path'), time.time()))

    def begin_send(self, operation, number, text):
        with self.database() as db:
            try:
                db.execute('''INSERT INTO messages VALUES (?, NULL, ?, ?, ?, ?, 'sent',
                              'unknown', NULL, ?, 0)''',
                           (str(uuid.uuid4()), operation, number, text,
                            time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()), time.time()))
            except sqlite3.IntegrityError:raise RuntimeError('ALREADY_ATTEMPTED') from None

    def finish_send(self, operation, outcome, source=None):
        with self.database() as db:
            db.execute('UPDATE messages SET outcome=?, source=? WHERE operation=?', (outcome, source, operation))

    def get(self, identity):
        with self.database() as db:
            row = db.execute('SELECT * FROM messages WHERE id=? AND deleted=0', (identity,)).fetchone()
            if not row:raise RuntimeError('MESSAGE_NOT_FOUND')
            return dict(row)

    def delete(self, identity):
        with self.database() as db:
            # Keep only a tombstone so the next refresh cannot resurrect an SMS.
            db.execute("UPDATE messages SET deleted=1, number='', text='', timestamp='', source=NULL WHERE id=?",
                       (identity,))

    def list(self):
        with self.database() as db:
            rows = db.execute('''SELECT id, number, text, timestamp, direction, outcome FROM messages
                                 WHERE deleted=0 ORDER BY seen DESC, id DESC LIMIT 1001''').fetchall()
            return {'messages': [dict(r) for r in rows[:1000]], 'limited': len(rows) > 1000, 'archived': True}


class ArchivedModem:
    def __init__(self, backend, archive=None):
        self.backend, self.archive = backend, archive or SmsArchive()

    def call(self, action, **values):
        validate_action({'action': action, **values})
        if action == 'archive':return self.archive.list()
        if action == 'messages':
            result = self.backend.call(action, **values)
            self.archive.import_messages(result['messages'])
            return {**self.archive.list(), 'modem_limited': result.get('limited', False)}
        if action == 'archive_delete':
            row = self.archive.get(values['id'])
            if values['delete_modem']:
                if not row['source'] or not row['fingerprint']:raise RuntimeError('MESSAGE_NOT_ON_MODEM')
                self.backend.call('delete', path=row['source'], fingerprint=row['fingerprint'], confirm=True)
            self.archive.delete(values['id'])
            return {'deleted': True}
        if action != 'send':return self.backend.call(action, **values)
        self.archive.begin_send(values['operation'], values['number'], values['text'])
        try:
            result = self.backend.call(action, **values)
        except Exception as exc:
            # An interrupted send remains unknown across process/device restarts.
            if str(exc) in {'SIM_REQUIRED', 'SIM_LOCKED', 'NOT_REGISTERED', 'UNSUPPORTED',
                            'MODEM_BUSY', 'MODEM_UNAVAILABLE', 'MODEM_AMBIGUOUS'}:
                self.archive.finish_send(values['operation'], 'not_submitted')
            raise
        self.archive.finish_send(values['operation'], 'submitted', result.get('path'))
        return result
