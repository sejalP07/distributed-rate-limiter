from app.token_bucket import TokenBucket


bucket = TokenBucket(
    capacity=5,
    refill_rate=1,
)

for request_number in range(1, 8):
    allowed = bucket.try_consume()

    print(
        f"Request {request_number}: "
        f"{'ALLOWED' if allowed else 'REJECTED'}, "
        f"tokens={bucket.available_tokens():.2f}"
    )