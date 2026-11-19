import shutil
import subprocess

import pytest


@pytest.mark.skipif(shutil.which('node') is None, reason='Node unavailable')
def test_settings_projection_cache_never_persists_secrets():
    subprocess.run(['node', 'tests/settings_cache_fixture.cjs'], check=True, timeout=10)


@pytest.mark.skipif(shutil.which('node') is None, reason='Node unavailable')
def test_usage_cache_does_not_wait_for_a_fresh_sample_to_render():
    subprocess.run(['node', 'tests/sim_usage_cache_fixture.cjs'], check=True, timeout=10)
