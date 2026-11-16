"""Shared radio/data vetoes. Missing intent preserves pre-Quick-Settings behavior."""
import json
import os
from pathlib import Path
import tempfile

NAME = 'quick-settings.json'


def load_intent(directory='/var/lib/openstick'):
    path = Path(directory) / NAME
    try:
        value = json.loads(path.read_text(encoding='utf-8'))
        if (not isinstance(value, dict) or set(value) != {'version', 'airplane', 'data_allowed'}
                or value['version'] != 1 or type(value['airplane']) is not bool
                or type(value['data_allowed']) is not bool
                or value['airplane'] and value['data_allowed']):
            raise ValueError('INVALID_INTENT')
        return value
    except FileNotFoundError:
        return None
    except (OSError, ValueError, TypeError):
        # Corrupt persisted consent never grants radio/data permission.
        return {'version': 1, 'airplane': True, 'data_allowed': False}


def radio_allowed(directory='/var/lib/openstick'):
    value = load_intent(directory)
    return value is None or not value['airplane']


def data_allowed(directory='/var/lib/openstick'):
    value = load_intent(directory)
    return value is None or not value['airplane'] and value['data_allowed']


def save_intent(directory, *, airplane, data_allowed):
    if type(airplane) is not bool or type(data_allowed) is not bool or airplane and data_allowed:
        raise ValueError('INPUT_INVALID')
    root = Path(directory)
    root.mkdir(mode=0o700, parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix='.quick-', dir=root)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as output:
            json.dump({'version': 1, 'airplane': airplane, 'data_allowed': data_allowed}, output)
            output.flush()
            os.fsync(output.fileno())
        os.replace(temporary, root / NAME)
        if os.name != 'nt':
            fd = os.open(root, os.O_RDONLY)
            try:
                os.fsync(fd)
            finally:
                os.close(fd)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
