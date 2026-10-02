from app.policies import get_policy


def test_ip_policy():
    policy = get_policy("ip")

    assert policy.name == "default:ip"
    assert policy.capacity == 10
    assert policy.refill_rate == 1


def test_user_policy():
    policy = get_policy("user_id")

    assert policy.name == "default:user_id"
    assert policy.capacity == 20
    assert policy.refill_rate == 2


def test_api_key_policy():
    policy = get_policy("api_key")

    assert policy.name == "default:api_key"
    assert policy.capacity == 50
    assert policy.refill_rate == 5


def test_unknown_identity_uses_ip_default_policy():
    policy = get_policy("unknown")

    assert policy.name == "default:ip"
    assert policy.capacity == 10
    assert policy.refill_rate == 1


def test_search_ip_policy():
    policy = get_policy(
        "ip",
        "/api/search",
    )

    assert policy.name == "search:ip"
    assert policy.capacity == 5
    assert policy.refill_rate == 1


def test_search_user_policy():
    policy = get_policy(
        "user_id",
        "/api/search",
    )

    assert policy.name == "search:user_id"
    assert policy.capacity == 10
    assert policy.refill_rate == 2


def test_search_api_key_policy():
    policy = get_policy(
        "api_key",
        "/api/search",
    )

    assert policy.name == "search:api_key"
    assert policy.capacity == 25
    assert policy.refill_rate == 5


def test_upload_ip_policy():
    policy = get_policy(
        "ip",
        "/api/upload",
    )

    assert policy.name == "upload:ip"
    assert policy.capacity == 2
    assert policy.refill_rate == 0.5


def test_unknown_endpoint_uses_default_policy():
    policy = get_policy(
        "api_key",
        "/api/demo",
    )

    assert policy.name == "default:api_key"
    assert policy.capacity == 50
    assert policy.refill_rate == 5