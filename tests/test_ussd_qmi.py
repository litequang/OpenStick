import json
import subprocess
import uuid

import pytest

from uz801_manager.ussd_qmi import QmiUssd, read_session


def values():return {'code':'*101#','operation':str(uuid.uuid4()),'confirm':True}


def test_typed_qmi_payload_is_stdin_only_and_current_reply_is_returned():
    payload=values()
    def run(args,**kwargs):
        assert payload['code'] not in ' '.join(args)
        assert json.loads(kwargs['input'])=={'action':'ussd_start',**payload}
        assert kwargs['shell'] is False
        return subprocess.CompletedProcess(args,0,json.dumps({'reply':'same balance','ussd_state':1,
            'response_source':'QMI_METHOD_RESPONSE','modem_acknowledged':True}).encode(),b'')
    assert QmiUssd(run=run).call('ussd_start',**payload)['reply']=='same balance'


@pytest.mark.parametrize('output',[b'private raw +84900111222',b'[]',b'{"error":"private balance"}',b'{"reply":""}'])
def test_invalid_qmi_helper_output_is_filtered(output):
    def run(args,**kwargs):return subprocess.CompletedProcess(args,0,output,b'private error')
    with pytest.raises(RuntimeError,match='^USSD_FAILED$'):QmiUssd(run=run).call('ussd_start',**values())


def test_qmi_helper_timeout_does_not_repeat_transmission():
    calls=[]
    def run(args,**kwargs):calls.append(args);raise subprocess.TimeoutExpired(args,145)
    with pytest.raises(RuntimeError,match='^USSD_TIMEOUT$'):QmiUssd(run=run).call('ussd_start',**values())
    assert len(calls)==1


def test_invalid_cached_session_is_not_used(tmp_path):
    path=tmp_path/'session.json'
    for value in [{'state':True,'cid':2},{'state':3,'cid':999},{'state':3,'cid':'2'},[]]:
        path.write_text(json.dumps(value))
        assert read_session(path)=={}
