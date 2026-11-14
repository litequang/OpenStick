from contextlib import nullcontext
import uuid

import pytest

from uz801_manager.sms_archive import ArchivedModem, SmsArchive, message_fingerprint
from uz801_manager.modem_device import ModemManager, OperationJournal, RadioPreference, MESSAGING, ROOT, SMS
from test_modem_device import Bus


def incoming(**changes):
    return {'number': '+84900111222', 'text': '<script>private fixture</script>',
            'timestamp': '2026-11-14T10:00:00Z', 'state': 3, 'path': ROOT + '/SMS/4', **changes}


class Backend:
    def __init__(self, error=None):self.calls=[]; self.error=error
    def call(self, action, **values):
        self.calls.append((action, values))
        if self.error:raise RuntimeError(self.error)
        if action == 'messages':return {'messages': [incoming()], 'limited': False}
        return {'submitted': True, 'path': ROOT + '/SMS/9'}


def test_archive_persists_and_read_does_not_require_sim(tmp_path):
    backend=Backend(); modem=ArchivedModem(backend, SmsArchive(tmp_path))
    first=modem.call('messages')['messages']
    assert first[0]['direction']=='received' and first[0]['text']=='<script>private fixture</script>'
    assert len(modem.call('messages')['messages'])==1
    offline=Backend('SIM_REQUIRED')
    assert ArchivedModem(offline, SmsArchive(tmp_path)).call('archive')['messages']==first
    assert offline.calls==[]


def test_local_delete_wipes_body_and_tombstone_prevents_reimport(tmp_path):
    archive=SmsArchive(tmp_path); modem=ArchivedModem(Backend(),archive)
    row=modem.call('messages')['messages'][0]
    modem.call('archive_delete', id=row['id'], delete_modem=False, confirm=True)
    assert modem.call('messages')['messages']==[]
    with archive.database() as db:
        deleted=dict(db.execute('SELECT * FROM messages').fetchone())
    assert deleted['text']==deleted['number']==deleted['timestamp']==''


def test_interrupted_send_is_durable_and_never_replayed(tmp_path):
    backend=Backend('RESULT_UNKNOWN'); archive=SmsArchive(tmp_path)
    operation=str(uuid.uuid4())
    values=dict(operation=operation, number='+84900111222', text='synthetic', confirm=True)
    with pytest.raises(RuntimeError,match='RESULT_UNKNOWN'):ArchivedModem(backend,archive).call('send',**values)
    again=ArchivedModem(backend,SmsArchive(tmp_path))
    assert again.call('archive')['messages'][0]['outcome']=='unknown'
    with pytest.raises(RuntimeError,match='ALREADY_ATTEMPTED'):again.call('send',**values)
    assert len(backend.calls)==1


def test_sent_history_is_separate_from_delivery_confirmation(tmp_path):
    modem=ArchivedModem(Backend(),SmsArchive(tmp_path))
    modem.call('send',operation=str(uuid.uuid4()),number='+84900111222',text='fixture',confirm=True)
    row=modem.call('archive')['messages'][0]
    assert row['direction']=='sent' and row['outcome']=='submitted'


def test_incomplete_received_message_is_archived_only_when_complete(tmp_path):
    archive=SmsArchive(tmp_path)
    archive.import_messages([incoming(state=2)])
    assert archive.list()['messages']==[]
    archive.import_messages([incoming()]);archive.import_messages([incoming(path=ROOT+'/SMS/88')])
    assert len(archive.list()['messages'])==1


def test_delete_on_modem_rechecks_exact_content_before_typed_delete(tmp_path):
    class DeleteBus(Bus):
        def call_blocking(self,*args,**kwargs):
            if args[3]=='Delete':self.calls.append((args[1],args[2],args[3],args[4],args[5]));return
            return super().call_blocking(*args,**kwargs)
    bus=DeleteBus();journal=OperationJournal(tmp_path/'operations');radio=RadioPreference(tmp_path/'radio')
    modem=ModemManager(bus_factory=lambda:bus,journal=journal,radio=radio,lock_factory=nullcontext)
    row=modem.call('messages')['messages'][0]
    bus.props[SMS]['Text']='different private content'
    with pytest.raises(RuntimeError,match='MESSAGE_CHANGED'):
        modem.call('delete',path=row['path'],fingerprint=message_fingerprint(row),confirm=True)
    assert not any(c[2]=='Delete' for c in bus.calls)
    row['text']=bus.props[SMS]['Text']
    modem.call('delete',path=row['path'],fingerprint=message_fingerprint(row),confirm=True)
    delete=[c for c in bus.calls if c[2]=='Delete']
    assert delete==[(ROOT+'/Modem/0', MESSAGING,'Delete','o',(row['path'],))] or delete==[(ROOT+'/Modem/0', MESSAGING,'Delete','o',[row['path']])]


def test_failed_modem_delete_keeps_local_history(tmp_path):
    archive=SmsArchive(tmp_path);archive.import_messages([incoming()])
    row=archive.list()['messages'][0]
    modem=ArchivedModem(Backend('RESULT_UNKNOWN'),archive)
    with pytest.raises(RuntimeError):modem.call('archive_delete',id=row['id'],delete_modem=True,confirm=True)
    assert archive.list()['messages'][0]['id']==row['id']


def test_identical_text_without_timestamp_in_distinct_sms_objects_is_preserved(tmp_path):
    archive=SmsArchive(tmp_path)
    archive.import_messages([incoming(timestamp='',path=ROOT+'/SMS/1'),incoming(timestamp='',path=ROOT+'/SMS/2')])
    assert len(archive.list()['messages'])==2


def test_sent_and_received_identical_payload_are_not_conflated(tmp_path):
    archive=SmsArchive(tmp_path)
    archive.import_messages([incoming(),incoming(state=5)])
    assert {row['direction'] for row in archive.list()['messages']}=={'sent','received'}
