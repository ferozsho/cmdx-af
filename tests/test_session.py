import pytest
from session import Session

def test_session_context_tracking():
    """Test that session context is correctly tracked and persists."""
    session = Session()
    session.set_context('user_id', 123)
    assert session.get_context('user_id') == 123
    session.set_context('role', 'admin')
    assert session.get_context('role') == 'admin'
    assert session.get_context('user_id') == 123

def test_session_context_isolation():
    """Test that session state is isolated between instances."""
    session1 = Session()
    session2 = Session()
    session1.set_context('key', 'value1')
    assert session2.get_context('key') is None

def test_session_context_persistence_across_calls():
    """Test that context persists across multiple calls within the same session."""
    session = Session()
    session.set_context('counter', 0)
    for _ in range(5):
        session.set_context('counter', session.get_context('counter') + 1)
    assert session.get_context('counter') == 5
