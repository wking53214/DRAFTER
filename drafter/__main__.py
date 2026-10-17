"""`python -m drafter` is the same as the `drafter` command."""

import sys

from .cli import main

sys.exit(main())
