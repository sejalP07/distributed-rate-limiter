from app.api_key import (
    generate_api_key,
    hash_api_key,
    verify_api_key,
)


def test_generate_api_key_has_prefix():
    api_key = generate_api_key()

    assert api_key.startswith("rl_")
    assert len(api_key) > 40


def test_api_keys_are_random():
    first = generate_api_key()
    second = generate_api_key()

    assert first != second


def test_hash_api_key_is_deterministic():
    api_key = generate_api_key()

    first_hash = hash_api_key(api_key)
    second_hash = hash_api_key(api_key)

    assert first_hash == second_hash


def test_hash_is_not_plaintext():
    api_key = generate_api_key()

    api_key_hash = hash_api_key(api_key)

    assert api_key not in api_key_hash
    assert len(api_key_hash) == 64


def test_verify_api_key_success():
    api_key = generate_api_key()

    api_key_hash = hash_api_key(api_key)

    assert verify_api_key(
        api_key,
        api_key_hash,
    ) is True


def test_verify_api_key_failure():
    api_key = generate_api_key()
    another_key = generate_api_key()

    api_key_hash = hash_api_key(api_key)

    assert verify_api_key(
        another_key,
        api_key_hash,
    ) is False


def test_empty_api_key_is_rejected():
    try:
        hash_api_key("")
        assert False
    except ValueError:
        assert True