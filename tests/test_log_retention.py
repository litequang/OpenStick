import os
from pathlib import Path

import pytest

from uz801_manager.log_retention import LIMITS, LogRetention, rotate


def test_rotation_preserves_writer_inode_and_appending_and_caps_private_archives(tmp_path):
    path=tmp_path/'fixture.log'
    with path.open('ab',buffering=0) as writer:
        writer.write(b'a'*40)
        inode=path.stat().st_ino
        assert rotate(path,8)
        assert path.stat().st_ino==inode and path.read_bytes()==b''
        assert (tmp_path/'fixture.log.1').read_bytes()==b'a'*16
        writer.write(b'b'*30);assert rotate(path,8)
        writer.write(b'new')
        assert path.read_bytes()==b'new'
    assert (tmp_path/'fixture.log.1').read_bytes()==b'b'*16
    assert (tmp_path/'fixture.log.2').read_bytes()==b'a'*16
    assert not list(tmp_path.glob('.openstick-log-*'))
    if os.name!='nt':assert (tmp_path/'fixture.log.1').stat().st_mode&0o777==0o600


def test_only_fixed_logs_and_once_a_minute_are_considered(tmp_path,monkeypatch):
    calls=[];clock=[100]
    monkeypatch.setattr('uz801_manager.log_retention.rotate',lambda p,n:calls.append((p,n)))
    service=LogRetention(tmp_path,clock=lambda:clock[0]);service.tick();service.tick()
    assert len(calls)==len(LIMITS) and all(p.is_relative_to(tmp_path) for p,n in calls)
    clock[0]=159;service.tick();assert len(calls)==len(LIMITS)
    clock[0]=160;service.tick();assert len(calls)==2*len(LIMITS)


def test_small_and_missing_logs_are_untouched_and_failed_archive_does_not_truncate(tmp_path,monkeypatch):
    path=tmp_path/'fixture.log';assert not rotate(path,8)
    path.write_bytes(b'small');assert not rotate(path,8)
    path.write_bytes(b'long'*20)
    monkeypatch.setattr('uz801_manager.log_retention.os.replace',lambda *a:(_ for _ in ()).throw(OSError('fixture')))
    with pytest.raises(OSError):rotate(path,8)
    assert path.read_bytes()==b'long'*20
    assert not list(tmp_path.glob('.openstick-log-*'))


@pytest.mark.skipif(os.name=='nt',reason='Linux symlink/hardlink protections')
def test_symlink_hardlink_and_archive_links_refuse_without_touching_target(tmp_path):
    target=tmp_path/'owner';target.write_bytes(b'private'*20)
    log=tmp_path/'fixture.log';log.symlink_to(target)
    assert not rotate(log,8);log.unlink();os.link(target,log)
    assert not rotate(log,8);log.unlink();log.write_bytes(b'x'*30)
    (tmp_path/'fixture.log.1').symlink_to(target)
    assert not rotate(log,8) and log.read_bytes()==b'x'*30
    assert target.read_bytes()==b'private'*20
