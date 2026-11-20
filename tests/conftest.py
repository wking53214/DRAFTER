import pytest


@pytest.fixture(autouse=True)
def _allow_public_removal_by_default(monkeypatch, request):
    """The fixer tests exercise the removal mechanics on ordinary public names.

    The default (public names refused) is covered by tests/test_public_removal_opt_in.py,
    which marks itself `keeps_default` so this fixture leaves the environment alone.
    """
    if request.node.get_closest_marker("keeps_default") is None:
        monkeypatch.setenv("DRAFTER_ALLOW_PUBLIC_REMOVAL", "1")
