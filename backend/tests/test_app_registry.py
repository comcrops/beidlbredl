from apps import APP_REGISTRY


def test_registry_is_list():
    assert isinstance(APP_REGISTRY, list)


def test_hello_world_in_registry():
    ids = [app['id'] for app in APP_REGISTRY]
    assert 'hello-world' in ids


def test_hello_world_has_required_fields():
    app = next(a for a in APP_REGISTRY if a['id'] == 'hello-world')
    assert 'name' in app
    assert 'icon' in app
    assert 'has_mobile_controls' in app
    assert app['has_mobile_controls'] is True
