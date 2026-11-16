from pathlib import Path


def test_lan_firewall_allows_only_wifi_ipv4_admin_port():
    root = Path(__file__).resolve().parents[1]
    rule = (root / 'scripts/nftables/52_openstick_lan.nft').read_text()
    assert 'meta nfproto ipv4 iifname "wlan0" tcp dport 8765 accept' in rule
    assert 'flush' not in rule and 'forward {' not in rule
    assert 'wwan0' not in rule and 'dport 80 ' not in rule
    assert 'need networkmanager nftables' in (root / 'scripts/openrc/openstick-lan').read_text()


def test_mdns_accepts_multicast_queries_without_imposing_response_ttl_on_clients():
    root = Path(__file__).resolve().parents[1]
    rules = (root / 'scripts/nftables/53_openstick_mdns.nft').read_text().splitlines()
    accepts = [line.strip() for line in rules if ' accept ' in line and not line.lstrip().startswith('#')]
    multicast = [line for line in accepts if 'ip daddr 224.0.0.251' in line]
    assert len(multicast) == 1
    assert 'ip ttl' not in multicast[0]
    assert all('iifname "wlan0"' in line and 'udp dport 5353' in line for line in accepts)
    assert any('ip ttl 255' in line for line in accepts)  # Preserve stricter unicast ingress.
    assert 'flush ruleset' not in '\n'.join(rules) and 'chain forward' not in '\n'.join(rules)
