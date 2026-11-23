"""Restore only OpenStick's scoped AP NAT; never reload the system firewall.

NM's shared-mode DHCP/AP can remain active after its dynamic NAT table is lost.
The caller holds network/modem locks and supplies an already connected, consented
SIM interface. This module never activates a connection or runs from a GET.
"""
import json
import re
import subprocess

TABLE = 'openstick_ap_share'
OWNER = 'openstick-ap-share-v1'
SUBNET = '192.168.8.0/24'
ERROR = 'AP_SHARING_FAILED'


class ApSharing:
    def __init__(self, network):self.network = network

    @staticmethod
    def interface(value):
        return isinstance(value,str) and re.fullmatch(r'(?:wwan|rmnet)[A-Za-z0-9_.-]{0,26}',value) is not None

    def current(self):
        result=self.network.run(['nft','-j','list','tables'],capture_output=True,text=True,timeout=8)
        if result.returncode:raise ValueError()
        tables=json.loads(result.stdout)['nftables']
        if not any(item.get('table',{}).get('family')=='inet' and item['table'].get('name')==TABLE for item in tables):
            return None
        result=self.network.run(['nft','-j','list','table','inet',TABLE],capture_output=True,text=True,timeout=8)
        if result.returncode:raise ValueError()
        rows=json.loads(result.stdout)['nftables']
        definitions=[row['table'] for row in rows if 'table' in row]
        chains=[row['chain'] for row in rows if 'chain' in row]
        rules=[row['rule'] for row in rows if 'rule' in row]
        if (len(definitions)!=1 or definitions[0].get('comment')!=OWNER or len(chains)!=1 or len(rules)!=1
                or any(set(row)-{'metainfo','table','chain','rule'} for row in rows)):
            raise ValueError()
        chain=chains[0];rule=rules[0]
        if (any(value.get('family')!='inet' or value.get('table')!=TABLE for value in (chain,rule))
                or {k:chain.get(k) for k in ('name','type','hook','prio','policy')}
                    !={'name':'srcnat','type':'nat','hook':'postrouting','prio':99,'policy':'accept'}
                or rule.get('chain')!='srcnat'):
            raise ValueError()
        expr=rule['expr']
        interface=expr[1]['match']['right']
        if not self.interface(interface) or expr!=self.expressions(interface):raise ValueError()
        return interface

    @staticmethod
    def expressions(interface):
        return [
            {'match':{'op':'==','left':{'payload':{'protocol':'ip','field':'saddr'}},
                      'right':{'prefix':{'addr':'192.168.8.0','len':24}}}},
            {'match':{'op':'==','left':{'meta':{'key':'oifname'}},'right':interface}},
            {'masquerade':None},
        ]

    def reconcile(self, interface):
        try:
            if interface is not None and not self.interface(interface):raise ValueError()
            previous=self.current()
            if previous==interface:return False
            prefix='delete table inet '+TABLE+'\n' if previous is not None else ''
            if interface is None:rules=prefix
            else:
                rules=(prefix+'table inet '+TABLE+' {\n comment "'+OWNER+'"\n'
                    ' chain srcnat {\n type nat hook postrouting priority 99; policy accept;\n'
                    ' ip saddr '+SUBNET+' oifname "'+interface+'" masquerade\n }\n}\n')
            result=self.network.run(['nft','--check','-f','-'],input=rules,text=True,capture_output=True,timeout=8)
            if result.returncode:raise ValueError()
            result=self.network.run(['nft','-f','-'],input=rules,text=True,capture_output=True,timeout=8)
            if result.returncode or self.current()!=interface:raise ValueError()
            return True
        except (ValueError,KeyError,IndexError,TypeError,OSError,subprocess.SubprocessError):
            raise RuntimeError(ERROR) from None
