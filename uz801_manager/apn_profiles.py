"""Named private APN presets. Saving a preset never applies it to a modem."""
import configparser
import json
import uuid

from .cellular_profile import FIELDS, from_key_string, parse_profile, summary, validate_cellular

ERRORS = {'APN_PROFILES_UNAVAILABLE', 'APN_PROFILE_NOT_FOUND', 'APN_PROFILE_ACTIVE',
          'APN_PROFILE_NAME_EXISTS', 'APN_PROFILE_LIMIT'}
ACTIONS = ('apn_save', 'apn_apply', 'apn_delete')


def valid_id(value, *, draft=False):
    if draft and value in ('', 'current'):return True
    try:return isinstance(value, str) and str(uuid.UUID(value)) == value
    except (ValueError, TypeError, AttributeError):return False


class ApnProfiles:
    def __init__(self, owner):
        self.owner = owner
        self.path = owner.directory / 'apn-profiles.json'

    def current(self):
        path = self.owner.profiles / 'openstick-cellular.nmconnection'
        try:
            if path.is_symlink():raise ValueError()
            profile = parse_profile(path.read_text())
            from .hotspot import CELL_UUID
            if (profile.get('connection', 'uuid', fallback='') != CELL_UUID
                    or profile.get('connection', 'type', fallback='') != 'gsm'):raise ValueError()
            value = summary(profile, self.owner.read('hotspot.json').get('apn_name', ''))
            value.pop('password_saved')
            value['password'] = from_key_string(profile.get('gsm', 'password', fallback=''))
            return value
        except (OSError, ValueError, configparser.Error):return None

    def read(self):
        try:
            if self.path.is_symlink() or self.path.stat().st_size > 131072:raise ValueError()
            value = json.loads(self.path.read_text())
            if not isinstance(value, dict) or set(value) != {'version', 'profiles'} or type(value['version']) is not int or value['version'] != 1:raise ValueError()
            rows = value['profiles']
            if not isinstance(rows, list) or len(rows) > 20:raise ValueError()
            ids, names = set(), set()
            for row in rows:
                if not isinstance(row, dict) or set(row) != (FIELDS - {'password_action'}) | {'id'}:raise ValueError()
                if not valid_id(row['id']) or row['id'] in ids or not row['name'].strip() or row['name'].casefold() in names:raise ValueError()
                validate_cellular({**row, 'password_action':'replace' if row['password'] else 'clear'})
                ids.add(row['id']);names.add(row['name'].casefold())
            return rows
        except FileNotFoundError:return []
        except (OSError, ValueError, TypeError, KeyError, AttributeError):
            raise RuntimeError('APN_PROFILES_UNAVAILABLE') from None

    def write(self, rows):
        if self.path.is_symlink():raise RuntimeError('APN_PROFILES_UNAVAILABLE')
        self.owner.directory.mkdir(mode=0o700, parents=True, exist_ok=True)
        try:self.owner.atomic(self.path, json.dumps({'version':1, 'profiles':rows}, ensure_ascii=False))
        except Exception:raise RuntimeError('APN_PROFILES_UNAVAILABLE') from None

    @staticmethod
    def public(row):
        return {**{k:v for k,v in row.items() if k != 'password'}, 'password_saved':bool(row['password'])}

    def state(self):
        current = self.current()
        return {'profiles':[{**self.public(row), 'active':{k:v for k,v in row.items() if k != 'id'} == current}
                            for row in self.read()]}

    def find(self, identity):
        value = next((row for row in self.read() if row['id'] == identity), None)
        if value is None:raise RuntimeError('APN_PROFILE_NOT_FOUND')
        return value

    def save(self, values):
        rows = self.read();identity = values['profile_id']
        source = self.current() if identity == 'current' else self.find(identity) if identity else None
        if identity == 'current' and source is None:raise RuntimeError('APN_PROFILE_NOT_FOUND')
        name = values['name'].strip()
        if any(row['name'].casefold() == name.casefold() and row['id'] != identity for row in rows):
            raise RuntimeError('APN_PROFILE_NAME_EXISTS')
        if identity in ('', 'current'):
            if len(rows) >= 20:raise RuntimeError('APN_PROFILE_LIMIT')
            identity = str(uuid.uuid4())
        password = values['password'] if values['password_action'] == 'replace' else (source or {}).get('password', '') if values['password_action'] == 'keep' else ''
        row = {k:values[k] for k in FIELDS - {'password_action', 'password'}}
        row.update(id=identity, name=name, password=password if values['apn'] else '')
        validate_cellular({**row, 'password_action':'replace' if row['password'] else 'clear'})
        self.write([r for r in rows if r['id'] != identity] + [row])
        return {**self.state(), 'saved_profile_id':identity}

    def delete(self, identity):
        row = self.find(identity)
        if {k:v for k,v in row.items() if k != 'id'} == self.current():raise RuntimeError('APN_PROFILE_ACTIVE')
        self.write([r for r in self.read() if r['id'] != identity])
        return self.state()

    def apply(self, identity):
        row = self.find(identity)
        values = {k:v for k,v in row.items() if k != 'id'}
        values['password_action'] = 'replace' if row['password'] else 'clear'
        self.owner.configure_apn(row['apn'], details=values)
        return self.state()
