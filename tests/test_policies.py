from app.policies import get_policy


def test_ip_policy():
    policy = get_policy("ip")

    assert policy.name == "ip"
    assert policy.capacity == 10
    assert policy.refill_rate == 1


def test_user_policy():
    policy = get_policy("user_id")

    assert policy.name == "user_id"
    assert policy.capacity == 20
    assert policy.refill_rate == 2


def test_api_key_policy():
    policy = get_policy("api_key")

    assert policy.name == "api_key"
    assert policy.capacity == 50
    assert policy.refill_rate == 5


def test_unknown_identity_uses_default_policy():
    policy = get_policy("unknown")

    assert policy.capacity == 10
    assert policy.refill_rate == 1