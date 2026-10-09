"""The Drafter declares which version of Warden's shapes it was written for."""

import warden
from warden.cli import _load_seat

from drafter.seat import Drafter


def test_the_drafter_declares_contract_1():
    assert Drafter.requires_contract == "1"
    assert Drafter().requires_contract == "1"


def test_the_declaration_matches_the_warden_it_runs_with():
    assert Drafter.requires_contract == warden.CONTRACT


def test_warden_loads_the_drafter_with_no_contract_warning():
    warnings: list[str] = []
    seat = _load_seat("drafter.seat:Drafter", warnings)
    assert isinstance(seat, Drafter)
    assert warnings == []
