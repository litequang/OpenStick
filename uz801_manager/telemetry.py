"""Bounded, single-flight display snapshots; never used for action preflight."""
from copy import deepcopy
import threading
import time


class SnapshotPending(Exception):
    pass


def invalidate_display(app, action):
    if action not in ('status', 'overview', 'profiles', 'messages', 'archive'):
        for snapshot in app.extensions.get('telemetry', {}).values():snapshot.invalidate()
        backend = app.extensions.get('hosting', {}).get('backend')
        invalidate = getattr(backend, 'invalidate_status', None)
        if callable(invalidate):invalidate()


def snapshot_response(snapshot):
    from flask import jsonify
    try:return jsonify(snapshot.get())
    except SnapshotPending:
        response = jsonify(error='STATUS_PENDING')
        response.status_code = 503
        response.headers['Retry-After'] = '1'
        return response


class ReadOnlySnapshot:
    def __init__(self, producer, *, ttl=5, max_age=30, clock=time.monotonic):
        self.producer, self.ttl, self.max_age, self.clock = producer, ttl, max_age, clock
        self.lock = threading.Lock()
        self.value = None
        self.at = 0
        self.retry_at = 0
        self.running = False
        self.generation = 0

    def invalidate(self):
        with self.lock:
            self.generation += 1
            self.value = None
            self.retry_at = 0

    def _collect(self, generation):
        try:
            value = self.producer()
            if not isinstance(value, dict):raise ValueError()
            value = deepcopy(value)
            with self.lock:
                if generation == self.generation:
                    self.value, self.at = value, self.clock()
        except Exception:
            # Preserve the old sample's age, never raw subprocess/DBus errors.
            with self.lock:self.retry_at = self.clock() + 2
        finally:
            with self.lock:self.running = False

    def get(self):
        with self.lock:
            age = max(0, self.clock() - self.at)
            if (self.value is None or age >= self.ttl) and not self.running and self.clock() >= self.retry_at:
                self.running = True
                thread = threading.Thread(target=self._collect, args=(self.generation,),
                                          name='header-telemetry', daemon=True)
                try:thread.start()
                except Exception:
                    self.running = False
                    self.retry_at = self.clock() + 2
            if self.value is None or age > self.max_age:raise SnapshotPending()
            value = deepcopy(self.value)
            value['_telemetry'] = {'age_seconds': round(age, 2), 'stale': age >= self.ttl,
                                   'refreshing': self.running}
            return value
