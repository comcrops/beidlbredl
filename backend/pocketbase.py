import os
import time
import logging
import requests

log = logging.getLogger(__name__)

PB_URL = os.environ.get('POCKETBASE_URL', 'http://pocketbase:8090')

_token_cache: str | None = None
_token_fetched_at: float = 0
_TOKEN_TTL = 3600

_collection_ready: set[str] = set()


def admin_token() -> str | None:
    global _token_cache, _token_fetched_at
    if _token_cache and time.time() - _token_fetched_at < _TOKEN_TTL:
        return _token_cache

    email = os.environ.get('PB_ADMIN_EMAIL', '')
    password = os.environ.get('PB_ADMIN_PASSWORD', '')
    if not email or not password:
        return None

    resp = requests.post(
        f'{PB_URL}/api/collections/_superusers/auth-with-password',
        json={'identity': email, 'password': password},
        timeout=5,
    )
    if resp.ok:
        _token_cache = resp.json().get('token')
        _token_fetched_at = time.time()
        log.warning('PocketBase superuser auth OK')
        return _token_cache

    log.warning('PocketBase superuser auth failed (%s), trying bootstrap', resp.status_code)
    requests.post(
        f'{PB_URL}/api/collections/_superusers/records',
        json={'email': email, 'password': password, 'passwordConfirm': password},
        timeout=5,
    )
    resp = requests.post(
        f'{PB_URL}/api/collections/_superusers/auth-with-password',
        json={'identity': email, 'password': password},
        timeout=5,
    )
    if resp.ok:
        _token_cache = resp.json().get('token')
        _token_fetched_at = time.time()
        log.warning('PocketBase bootstrap + auth OK')
        return _token_cache

    log.error('PocketBase auth failed after bootstrap: %s %s', resp.status_code, resp.text)
    return None


def ensure_collection(
    name: str,
    fields: list[dict],
    rules: dict | None = None,
) -> None:
    if name in _collection_ready:
        return

    default_rules = {
        'listRule': '',
        'viewRule': '',
        'createRule': '',
        'updateRule': None,
        'deleteRule': None,
    }

    for attempt in range(6):
        try:
            token = admin_token()
            if not token:
                log.error('No PocketBase admin token for collection %s', name)
                _collection_ready.add(name)
                return
            headers = {'Authorization': f'Bearer {token}'}
            check = requests.get(
                f'{PB_URL}/api/collections/{name}', headers=headers, timeout=5
            )
            if check.status_code == 404:
                log.warning('Collection %s not found, creating...', name)
                r = requests.post(
                    f'{PB_URL}/api/collections',
                    headers=headers,
                    timeout=5,
                    json={
                        'name': name,
                        'type': 'base',
                        'fields': fields,
                        **(rules or default_rules),
                    },
                )
                log.warning('Collection %s create: %s %s', name, r.status_code, r.text)
            else:
                log.warning('Collection %s check: %s', name, check.status_code)
            _collection_ready.add(name)
            return
        except Exception as e:
            log.warning('ensure_collection %s attempt %d: %s', name, attempt, e)
            if attempt < 5:
                time.sleep(3)

    log.error('ensure_collection %s gave up after 6 attempts', name)
    _collection_ready.add(name)
