"""Drafter: the in-loop maker. It reads what Ghost Tools found and proposes one fix.

WHAT IT DOES
    Turns a Ghost Tools finding into a proposed change, as data.

WHAT IT NEVER DOES
    Write a file (Warden applies). Detect or count anything (Ghost reports).
    Judge its own work (Warden's suite gate and Ghost's re-inspection do).
    Beautify or write the final README (Burnish, once, after the loop).
    Import Burnish, Ghost Tools or SWIZZLE. The seat imports only the shared
    data shapes (Warden's models, CNS's rows); the `drafter` command line also
    reads Ghost's JSON through Warden's own reader.

LOGGING
    The library writes to the `drafter` logger (stdlib `logging`) and never
    configures it. Ordinary refusals are DEBUG. A surprise (an exception that is
    not a deliberate refusal) is WARNING, with its traceback at DEBUG, and its
    reason also reaches Warden's `drafter_skipped`.
"""

import logging

from .seat import Drafter

__version__ = "0.2.17"
__all__ = ["Drafter", "__version__"]

logging.getLogger(__name__).addHandler(logging.NullHandler())
