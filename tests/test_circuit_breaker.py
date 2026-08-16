from agent_engine.discussion.circuit_breaker import CircuitBreaker


def test_should_disable_after_three_failures():
    cb = CircuitBreaker(threshold=3)
    assert cb.disabled("jobs") is False
    cb.record_fail("jobs")
    cb.record_fail("jobs")
    assert cb.disabled("jobs") is False
    cb.record_fail("jobs")
    assert cb.disabled("jobs") is True
    cb.record_ok("jobs")
    assert cb.disabled("jobs") is False
