"""Private GSM keyfile settings; no activation, radio changes or secret export."""
import configparser
import re

FIELDS = {'name', 'apn', 'username', 'password', 'password_action', 'auth', 'ip_family', 'roaming'}
AUTH = ('auto', 'none', 'pap', 'chap', 'pap_chap')
AUTH_KEYS = ('noauth', 'refuse-pap', 'refuse-chap', 'refuse-mschap', 'refuse-mschapv2', 'refuse-eap')


def validate_cellular(value):
    for key, limit in [('name', 80), ('username', 128), ('password', 128)]:
        text = value[key]
        if (not isinstance(text, str) or len(text) > limit
                or any(ord(c) < 32 or ord(c) == 127 for c in text)):
            raise ValueError('INPUT_INVALID')
    if (not isinstance(value['apn'], str) or len(value['apn']) > 100
            or value['apn'] and not re.fullmatch('[a-z0-9][a-z0-9.-]*', value['apn'])
            or value['auth'] not in AUTH or value['ip_family'] not in ('auto', 'ipv4', 'ipv6', 'ipv4v6')
            or value['password_action'] not in ('keep', 'replace', 'clear')
            or type(value['roaming']) is not bool):raise ValueError('INPUT_INVALID')
    if value['password_action'] != 'replace' and value['password']:raise ValueError('INPUT_INVALID')
    if value['password_action'] == 'replace' and not value['password']:raise ValueError('INPUT_INVALID')
    if not value['apn'] and (value['username'] or value['password'] or value['auth'] != 'auto'):
        raise ValueError('INPUT_INVALID')


def key_string(value):
    # GLib keyfile scalar strings, including passwords with literal backslashes
    # or edge spaces. Newlines/control characters were rejected before writing.
    return value.replace('\\', '\\\\').replace(' ', '\\s')


def from_key_string(value):
    return re.sub(r'\\([\\s])', lambda m: ' ' if m[1] == 's' else '\\', value)


def parse_profile(text):
    # GLib preserves trailing scalar spaces, whereas ConfigParser strips them.
    # NM normalizes its output to literal trailing spaces. Protect those before
    # parsing so a subsequent "keep password" cannot truncate an existing key.
    section = None
    lines = []
    for line in text.splitlines():
        if line.startswith('[') and line.endswith(']'):section = line[1:-1]
        match = re.fullmatch(r'(username|password)=(.*)', line) if section == 'gsm' else None
        if match:line = match[1]+'='+match[2].replace(' ', '\\s')
        lines.append(line)
    profile = configparser.ConfigParser(interpolation=None)
    profile.read_string('\n'.join(lines))
    return profile


def summary(profile, name=''):
    auth = 'auto'
    if profile.has_section('ppp') and any(profile.has_option('ppp', k) for k in AUTH_KEYS):
        allowed = [k for k in ('pap', 'chap') if not profile.getboolean('ppp', 'refuse-'+k, fallback=False)]
        auth = 'pap_chap' if len(allowed) == 2 else allowed[0] if allowed else 'none'
    v4 = profile.get('ipv4', 'method', fallback='auto') != 'disabled'
    v6 = profile.get('ipv6', 'method', fallback='auto') not in ('disabled', 'ignore')
    family = 'ipv4v6' if (not profile.getboolean('ipv4', 'may-fail', fallback=True)
                          and not profile.getboolean('ipv6', 'may-fail', fallback=True)) else 'auto'
    if not v6:family = 'ipv4'
    elif not v4:family = 'ipv6'
    return {'name': name, 'apn': profile.get('gsm', 'apn', fallback=''),
            'username': from_key_string(profile.get('gsm', 'username', fallback='')),
            'password_saved': bool(profile.get('gsm', 'password', fallback='')),
            'auth': auth, 'ip_family': family,
            'roaming': not profile.getboolean('gsm', 'home-only', fallback=True)}


def apply(profile, value):
    apn = value['apn']
    profile.set('gsm', 'auto-config', 'false' if apn else 'true')
    for key in ('apn', 'username'):
        if value[key]:profile.set('gsm', key, key_string(value[key]))
        else:profile.remove_option('gsm', key)
    if not apn or value['password_action'] == 'clear':profile.remove_option('gsm', 'password')
    elif value['password_action'] == 'replace':profile.set('gsm', 'password', key_string(value['password']))
    profile.set('gsm', 'password-flags', '0')
    profile.set('gsm', 'home-only', 'false' if value['roaming'] else 'true')
    if not profile.has_section('ppp'):profile.add_section('ppp')
    for key in AUTH_KEYS:profile.remove_option('ppp', key)
    if value['auth'] != 'auto':
        profile.set('ppp', 'noauth', 'true' if value['auth'] == 'none' else 'false')
        for method in ('pap', 'chap', 'mschap', 'mschapv2', 'eap'):
            allowed = value['auth'] == method or value['auth'] == 'pap_chap' and method in ('pap', 'chap')
            profile.set('ppp', 'refuse-'+method, 'false' if allowed else 'true')
    for family in ('ipv4', 'ipv6'):
        if not profile.has_section(family):profile.add_section(family)
        enabled = value['ip_family'] in ('auto', 'ipv4v6', family)
        profile.set(family, 'method', 'auto' if enabled else 'disabled')
        profile.set(family, 'may-fail', 'true' if value['ip_family'] == 'auto' else 'false')
