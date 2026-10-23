"""Unit tests use an in-memory database URL and never open the household database."""
import os

os.environ['DATABASE_URL'] = 'sqlite:///:memory:'
# Existing fixtures describe a US household. Regional tests explicitly override settings.
os.environ['FAMILY_LOCALE'] = 'en-US'
os.environ['FAMILY_COUNTRY'] = 'US'
os.environ['FAMILY_TIMEZONE'] = 'America/New_York'
os.environ['FAMILY_UNITS'] = 'imperial'
os.environ['FAMILY_SCHOOL_CALENDAR'] = 'cobb'
os.environ['FAMILY_MESSAGING_PROVIDER'] = 'imessage'

# Keep all test-generated keys/caches outside the checkout and deployment.
import tempfile
from pathlib import Path
_TEST_CONFIG = tempfile.TemporaryDirectory(prefix="concierge-tests-")
os.environ['FAMILY_CONFIG_DIR'] = _TEST_CONFIG.name
os.environ['CALENDAR_CONFIG_DIR'] = _TEST_CONFIG.name
os.environ['FAMILY_ACCESS_KEY_PATH'] = str(Path(_TEST_CONFIG.name) / 'access.key')
os.environ['FAMILY_SECRETS_KEY_PATH'] = str(Path(_TEST_CONFIG.name) / 'secrets.key')
