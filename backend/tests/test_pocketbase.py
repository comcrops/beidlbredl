import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest
from unittest.mock import patch, MagicMock
import pocketbase


@pytest.fixture(autouse=True)
def clear_token_cache():
    pocketbase._token_cache = None
    pocketbase._token_fetched_at = 0
    pocketbase._collection_ready = set()
    yield
    pocketbase._token_cache = None
    pocketbase._token_fetched_at = 0
    pocketbase._collection_ready = set()


def _ok_auth():
    m = MagicMock()
    m.ok = True
    m.json.return_value = {'token': 'tok123'}
    return m


def _fail_auth():
    m = MagicMock()
    m.ok = False
    m.status_code = 401
    return m


def test_admin_token_returns_token_on_success():
    with patch('pocketbase.requests.post', return_value=_ok_auth()):
        assert pocketbase.admin_token() == 'tok123'


def test_admin_token_caches_token():
    with patch('pocketbase.requests.post', return_value=_ok_auth()) as mock_post:
        pocketbase.admin_token()
        pocketbase.admin_token()
    assert mock_post.call_count == 1


def test_admin_token_returns_none_without_credentials(monkeypatch):
    monkeypatch.delenv('PB_ADMIN_EMAIL', raising=False)
    monkeypatch.delenv('PB_ADMIN_PASSWORD', raising=False)
    assert pocketbase.admin_token() is None


def test_admin_token_bootstraps_on_auth_failure():
    responses = [_fail_auth(), MagicMock(ok=True), _ok_auth()]
    with patch('pocketbase.requests.post', side_effect=responses):
        token = pocketbase.admin_token()
    assert token == 'tok123'
