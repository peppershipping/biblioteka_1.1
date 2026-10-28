from app.ratelimit_core import MemoryRateLimiter


class FakeClock:
    def __init__(self):
        self.now = 1000.0

    def __call__(self):
        return self.now


def test_requests_over_limit_are_rejected():
    limiter = MemoryRateLimiter(clock=FakeClock())
    results = [limiter.hit("ip:1", limit=3, window=60)[0] for _ in range(5)]
    assert results == [True, True, True, False, False]


def test_limits_are_per_key():
    limiter = MemoryRateLimiter(clock=FakeClock())
    for _ in range(3):
        limiter.hit("a", 3, 60)
    assert limiter.hit("a", 3, 60)[0] is False
    assert limiter.hit("b", 3, 60)[0] is True


def test_window_resets_after_expiry_and_reports_retry_after():
    clock = FakeClock()
    limiter = MemoryRateLimiter(clock=clock)
    for _ in range(3):
        limiter.hit("a", 3, 60)
    allowed, retry_after = limiter.hit("a", 3, 60)
    assert not allowed and 1 <= retry_after <= 60
    clock.now += 61
    assert limiter.hit("a", 3, 60)[0] is True
