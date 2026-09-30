from app.config import _get_float


def test_get_float_default():
    assert _get_float(
        "TEST_RATE_LIMIT_VALUE_NOT_SET",
        5,
    ) == 5


def test_get_float_environment(monkeypatch):
    monkeypatch.setenv(
        "TEST_RATE_LIMIT_VALUE",
        "10",
    )

    assert _get_float(
        "TEST_RATE_LIMIT_VALUE",
        5,
    ) == 10


def test_get_float_invalid(monkeypatch):
    monkeypatch.setenv(
        "TEST_RATE_LIMIT_INVALID",
        "abc",
    )

    try:
        _get_float(
            "TEST_RATE_LIMIT_INVALID",
            5,
        )
        assert False
    except ValueError:
        assert True
        