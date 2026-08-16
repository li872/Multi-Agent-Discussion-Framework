# 简单熔断：同一角色连续失败达到阈值后，本场讨论不再调用它
from collections import defaultdict


class CircuitBreaker:
    def __init__(self, threshold: int = 3):
        self.threshold = threshold
        self._fails: dict[str, int] = defaultdict(int)

    def disabled(self, key: str) -> bool:
        return self._fails[key] >= self.threshold

    def record_ok(self, key: str) -> None:
        self._fails[key] = 0

    def record_fail(self, key: str) -> None:
        self._fails[key] += 1
