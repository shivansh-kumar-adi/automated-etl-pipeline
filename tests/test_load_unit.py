from contextlib import nullcontext
from unittest.mock import Mock

import pytest

from src.load import load_posts


class ScalarResult:
    def __init__(self, value): self.value = value
    def scalar_one(self): return self.value


def test_load_counts_insert_and_update():
    connection = Mock()
    connection.execute.side_effect = [ScalarResult(True), ScalarResult(False)]
    posts = [{"id": 1}, {"id": 2}]
    assert load_posts(connection, posts) == (1, 1)


def test_database_error_is_propagated_for_transaction_rollback():
    connection = Mock()
    connection.execute.side_effect = RuntimeError("database failed")
    with pytest.raises(RuntimeError, match="database failed"):
        load_posts(connection, [{"id": 1}])
