"""Unit test for session_scope's rollback behaviour, with no database."""

import pytest

from juicebox.persistence import database


class _StubSession:
    """A session double that records whether commit or rollback ran."""

    def __init__(self):
        self.committed = False
        self.rolled_back = False

    async def commit(self):
        self.committed = True

    async def rollback(self):
        self.rolled_back = True

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc_info):
        return False


async def test_session_scope_rolls_back_and_reraises_on_error(monkeypatch):
    stub_session = _StubSession()
    monkeypatch.setattr(database, "async_session_factory", lambda: stub_session)

    with pytest.raises(RuntimeError):
        async with database.session_scope() as session:
            assert session is stub_session
            raise RuntimeError("boom")

    assert stub_session.rolled_back is True
    assert stub_session.committed is False
