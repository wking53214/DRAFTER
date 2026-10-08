"""Drafter: the in-loop maker. It reads what Ghost Tools found and proposes one fix.

WHAT IT DOES
    Turns a Ghost Tools finding into a proposed change, as data.

WHAT IT NEVER DOES
    Write a file (Warden applies). Detect or count anything (Ghost reports).
    Judge its own work (Warden's suite gate and Ghost's re-inspection do).
    Beautify or write the final README (Burnish, once, after the loop).
    Import Burnish, Ghost Tools or SWIZZLE. It imports only Warden's data shapes.
"""

from .seat import Drafter

__version__ = "0.1.0"
__all__ = ["Drafter", "__version__"]
