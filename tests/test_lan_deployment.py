from pathlib import Path


def test_lan_firewall_allows_only_wifi_ipv4_admin_port():
    root = Path(__file__).resolve().parents[1]
    rule = (root / 'scripts/nftables/52_openstick_lan.nft').read_text()
    assert 'meta nfproto ipv4 iifname "wlan0" tcp dport 8765 accept' in rule
    assert 'flush' not in rule and 'forward {' not in rule
    assert 'wwan0' not in rule and 'dport 80 ' not in rule
    assert 'need networkmanager nftables' in (root / 'scripts/openrc/openstick-lan').read_text()
