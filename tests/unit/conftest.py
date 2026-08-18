"""Isolation for unit tests."""

import os

import pytest


@pytest.fixture(autouse=True)
def isolated_environment(monkeypatch, tmp_path):
    """Run each unit test with no JUICEBOX_ variables and no .env file.

    Settings reads both, so without this a developer's own environment
    decides whether the tests asserting defaults pass.
    """
    for key in list(os.environ):
        if key.startswith("JUICEBOX_"):
            monkeypatch.delenv(key)
    monkeypatch.chdir(tmp_path)
