"""Settings interactions never silently discard drafts or duplicate writes."""
import shutil
import subprocess

import pytest


@pytest.mark.skipif(shutil.which('node') is None, reason='Node unavailable')
def test_settings_consent_drafts_and_duplicate_requests():
    subprocess.run(['node', 'tests/settings_actions_fixture.cjs'], check=True, timeout=15)
