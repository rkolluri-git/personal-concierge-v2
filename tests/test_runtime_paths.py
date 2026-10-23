"""Fresh installations must be portable and independent of household config."""
from pathlib import Path
import os
import subprocess
import sys

from regional_settings import RegionalSettings
from runtime_paths import config_dir


def test_native_default_is_checkout_private_config():
    assert config_dir({}) == Path(__file__).resolve().parents[1] / 'config'


def test_explicit_config_takes_precedence_over_calendar_compatibility(tmp_path):
    assert config_dir({'FAMILY_CONFIG_DIR': str(tmp_path / 'new'),
                       'CALENDAR_CONFIG_DIR': str(tmp_path / 'legacy')}) == tmp_path / 'new'
    assert config_dir({'CALENDAR_CONFIG_DIR': str(tmp_path)}) == tmp_path


def test_new_install_does_not_assume_a_school_district():
    assert RegionalSettings.from_env({}).school_calendar == 'none'
    assert RegionalSettings.from_env({'FAMILY_SCHOOL_CALENDAR': 'cobb'}).school_calendar == 'cobb'


def test_adapters_share_config_without_creating_keys_on_import(tmp_path):
    env = dict(os.environ, FAMILY_CONFIG_DIR=str(tmp_path), PYTHONPATH='backend')
    for key in ('CALENDAR_CONFIG_DIR', 'FAMILY_ACCESS_KEY_PATH', 'FAMILY_SECRETS_KEY_PATH',
                'FAMILY_MESSAGING_CONFIG'):
        env.pop(key, None)
    code = '''
from runtime_paths import CONFIG_DIR
import access_control, sensitive_crypto, calendar_service, school_calendar_service, events_service
assert access_control.KEY_PATH.parent == CONFIG_DIR
assert sensitive_crypto.KEY_PATH.parent == CONFIG_DIR
assert calendar_service.CONFIG == CONFIG_DIR
assert school_calendar_service.CONFIG == CONFIG_DIR
assert events_service.STORE.parent == CONFIG_DIR
assert not list(CONFIG_DIR.iterdir())
'''
    subprocess.run([sys.executable, '-c', code], env=env, check=True)
