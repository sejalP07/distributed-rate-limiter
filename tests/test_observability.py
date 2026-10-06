import json
import logging

from app.observability import (
    log_rate_limit_rejection,
)


def test_rate_limit_rejection_log(
    caplog,
):
    with caplog.at_level(
        logging.WARNING,
        logger="rate_limiter",
    ):
        log_rate_limit_rejection(
            identity_type="api_key",
            identity="39",
            method="GET",
            endpoint="/api/search",
            policy_name="search:api_key",
            limit=25,
            remaining=0,
            retry_after_seconds=1,
        )

    assert len(caplog.records) == 1

    event = json.loads(
        caplog.records[0].message
    )

    assert event["event"] == "rate_limit_rejected"
    assert event["identity_type"] == "api_key"
    assert event["identity"] == "39"
    assert event["method"] == "GET"
    assert event["endpoint"] == "/api/search"
    assert event["policy"] == "search:api_key"
    assert event["limit"] == 25
    assert event["remaining"] == 0
    assert event["retry_after_seconds"] == 1


def test_rate_limit_log_does_not_contain_secret(
    caplog,
):
    secret = "rl_super_secret_value"

    with caplog.at_level(
        logging.WARNING,
        logger="rate_limiter",
    ):
        log_rate_limit_rejection(
            identity_type="api_key",
            identity="39",
            method="GET",
            endpoint="/api/demo",
            policy_name="default:api_key",
            limit=50,
            remaining=0,
            retry_after_seconds=1,
        )

    assert secret not in caplog.records[0].message