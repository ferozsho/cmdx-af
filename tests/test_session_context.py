import pytest
from src.session.context import SessionContext


def test_session_context_initialization():
    context = SessionContext()
    assert context.data == {}
    assert context.tracking_enabled is True


def test_session_context_set_and_get():
    context = SessionContext()
    context.set('user_id', 123)
    assert context.get('user_id') == 123


def test_session_context_get_missing_key():
    context = SessionContext()
    assert context.get('nonexistent') is None


def test_session_context_update():
    context = SessionContext()
    context.set('a', 1)
    context.update({'b': 2, 'c': 3})
    assert context.data == {'a': 1, 'b': 2, 'c': 3}


def test_session_context_clear():
    context = SessionContext()
    context.set('a', 1)
    context.clear()
    assert context.data == {}


def test_session_context_tracking_disabled():
    context = SessionContext(tracking_enabled=False)
    context.set('a', 1)
    assert context.data == {}


def test_session_context_tracking_enabled_after_disable():
    context = SessionContext()
    context.set_tracking(False)
    context.set('a', 1)
    assert context.data == {}
    context.set_tracking(True)
    context.set('b', 2)
    assert context.data == {'b': 2}


def test_session_context_get_returns_dict():
    context = SessionContext()
    context.set('user', {'name': 'Alice'})
    result = context.get('user')
    assert isinstance(result, dict)
    assert result['name'] == 'Alice'


def test_session_context_serialization():
    context = SessionContext()
    context.set('a', 1)
    serialized = context.to_json()
    assert serialized == '{"a": 1}'


def test_session_context_deserialization():
    context = SessionContext()
    context.from_json('{"a": 1}')
    assert context.data == {'a': 1}
