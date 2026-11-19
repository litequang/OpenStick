"""Owned cellular profile policy. Call mutations under network then modem lock."""
import io
import re


def profile_state(owner):
    from .hotspot import CELL_UUID
    from .cellular_profile import parse_profile
    path = owner.profiles / 'openstick-cellular.nmconnection'
    if path.is_symlink():raise RuntimeError('HOTSPOT_NOT_CONFIGURED')
    original = path.read_text()
    profile = parse_profile(original)
    if (profile.get('connection', 'uuid', fallback='') != CELL_UUID
            or profile.get('connection', 'type', fallback='') != 'gsm'
            or not profile.has_section('gsm')):
        raise RuntimeError('HOTSPOT_NOT_CONFIGURED')
    return path, original, profile


def roaming_status(owner):
    try:
        _, _, profile = profile_state(owner)
        return {'available': True,
                'allowed': not profile.getboolean('gsm', 'home-only', fallback=False),
                'home_locked': bool(profile.get('gsm', 'network-id', fallback=''))}
    except Exception:
        return {'available': False, 'allowed': None, 'home_locked': False}


def set_roaming(owner, allowed, home, register):
    # Never tear down or reconnect a live data session as a side effect.
    if (owner.read('setup-pending.json') or owner.read('hotspot-pending.json')
            or owner.read('network-policy.json').get('enabled')):
        raise RuntimeError('NETWORK_BUSY')
    devices = owner.network.devices()
    if len(devices) != 1:raise RuntimeError('MODEM_UNAVAILABLE')
    if owner.network.active(devices[0]):raise RuntimeError('CELLULAR_ALREADY_ACTIVE')
    if not allowed and not re.fullmatch(r'[0-9]{5,6}', home):
        raise RuntimeError('HOME_NETWORK_UNAVAILABLE')
    path, original, profile = profile_state(owner)
    profile.set('gsm', 'home-only', 'false' if allowed else 'true')
    if allowed:profile.remove_option('gsm', 'network-id')
    else:profile.set('gsm', 'network-id', home)
    output = io.StringIO();profile.write(output, space_around_delimiters=False)
    try:
        owner.atomic(path, output.getvalue());owner.network.load(path)
        register('' if allowed else home)
    except Exception:
        # Restore file settings but never retry an uncertain registration command.
        try:owner.atomic(path, original);owner.network.load(path)
        except Exception:raise RuntimeError('ROLLBACK_FAILED') from None
        raise RuntimeError('RESULT_UNKNOWN') from None
    return {'saved': True, 'roaming': roaming_status(owner)}


# MM LTE enum values are 30 + E-UTRA band number (B1..B44).
# These are frequency filters, not an ordering or a promise of local coverage.
LTE_LABELS = {31:'B1 · 2100 MHz', 33:'B3 · 1800 MHz', 37:'B7 · 2600 MHz',
              38:'B8 · 900 MHz', 58:'B28 · 700 MHz', 71:'B41 · 2500 MHz'}


def band_choices(supported):
    supported = sorted(set(int(n) for n in (supported or []) if int(n) not in (0, 256)))
    if not any(31 <= n <= 74 for n in supported):return []
    choices = [{'id':'auto', 'label':'Tự động · tất cả băng modem hỗ trợ (khuyên dùng)', 'bands':[256]}]
    # Retain every non-LTE band so existing 3G/2G fallback is not silently removed.
    fallback = [n for n in supported if not 31 <= n <= 74]
    vietnam = [n for n in supported if n in LTE_LABELS]
    if vietnam:
        choices.append({'id':'vietnam', 'label':'Việt Nam · nhóm B1/B3/B7/B8/B28/B41 được hỗ trợ',
                        'bands':sorted(fallback+vietnam)})
    for band in supported:
        if 31 <= band <= 74:
            label = LTE_LABELS.get(band, f'B{band-30}')
            choices.append({'id':f'b{band-30}', 'label':label+' · thử riêng',
                            'bands':sorted(fallback+[band])})
    return choices
