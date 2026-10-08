"""Proposer: the in-loop maker. It reads what Ghost Tools found and proposes one fix.

WHAT IT DOES
    Turns a Ghost Tools finding into a proposed change, as data.

WHAT IT NEVER DOES
    Write a file (Elegant applies). Detect or count anything (Ghost reports).
    Judge its own work (Elegant's suite gate and Ghost's re-inspection do).
    Beautify or write the final README (Streamline, once, after the loop).
    Import Streamline, Ghost Tools or SWIZZLE. It imports only Elegant's data shapes.
"""

from .seat import Proposer

__version__ = "0.1.0"
__all__ = ["Proposer", "__version__"]
