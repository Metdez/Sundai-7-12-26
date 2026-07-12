import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.pagination import paginate

TASKS = [f"task-{i}" for i in range(25)]


def test_first_item():
    assert paginate(TASKS, page=1, page_size=5)[0] == "task-0"


def test_second_page_start():
    assert paginate(TASKS, page=2, page_size=5)[0] == "task-5"


def test_full_page_size():
    page = paginate(TASKS, page=1, page_size=10)
    assert len(page) == 10
