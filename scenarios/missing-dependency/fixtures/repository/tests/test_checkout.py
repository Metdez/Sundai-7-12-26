from unittest import mock

from src.payments import charge


def test_charge_posts_to_gateway():
    with mock.patch("src.payments.requests.post") as post:
        post.return_value.json.return_value = {"status": "ok"}
        assert charge("o-1", 999)["status"] == "ok"


def test_charge_raises_on_error():
    with mock.patch("src.payments.requests.post") as post:
        post.return_value.raise_for_status.side_effect = RuntimeError("declined")
        try:
            charge("o-2", 100)
            assert False, "expected error"
        except RuntimeError:
            pass
