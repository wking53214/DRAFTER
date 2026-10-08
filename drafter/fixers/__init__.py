"""One module per Ghost detector the Drafter knows how to answer."""

from .doc_test_count import fix_doc_test_count

#: Ghost detector name -> fixer.
FIXERS = {"doc_test_count_drift": fix_doc_test_count}

__all__ = ["FIXERS", "fix_doc_test_count"]
