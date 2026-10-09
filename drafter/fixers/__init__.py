"""One module per Ghost detector the Drafter knows how to answer."""

from .dead_code import fix_dead_code
from .doc_test_count import fix_doc_test_count

#: Ghost detector name -> fixer.
FIXERS = {"doc_test_count_drift": fix_doc_test_count, "dead_code": fix_dead_code}

__all__ = ["FIXERS", "fix_dead_code", "fix_doc_test_count"]
