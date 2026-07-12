import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from test_pagination import test_first_item, test_full_page_size, test_second_page_start

failures = 0
for test in (test_first_item, test_second_page_start, test_full_page_size):
    try:
        test()
    except AssertionError as exc:
        print(f"FAILED {test.__name__}: {exc}")
        failures += 1
print(f"{3 - failures} passed, {failures} failed")
sys.exit(1 if failures else 0)
