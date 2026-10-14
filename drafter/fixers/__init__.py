"""One module per Ghost detector the Drafter knows how to answer."""

from .dead_code import fix_dead_code
from .doc_test_count import fix_doc_test_count
from .list_membership import fix_list_membership

#: Ghost detector name -> fixer.
FIXERS = {"doc_test_count_drift": fix_doc_test_count, "dead_code": fix_dead_code,
          "list_membership_in_loop": fix_list_membership}

__all__ = ["FIXERS", "fix_dead_code", "fix_doc_test_count", "fix_list_membership"]
