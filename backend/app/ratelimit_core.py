"""
Ограничение частоты запросов: счётчик «фиксированное окно» в памяти процесса.
Чистый модуль без зависимостей от FastAPI (ТЗ 15.3). Для нескольких экземпляров
backend используется Redis — см. ratelimit.py.
"""

import threading
import time


class MemoryRateLimiter:
    def __init__(self, clock=time.monotonic):
        self._clock = clock
        self._lock = threading.Lock()
        self._windows: dict[str, tuple[float, int]] = {}
        self._last_cleanup = clock()

    def hit(self, key: str, limit: int, window: int) -> tuple[bool, int]:
        """
        Регистрирует запрос. Возвращает (разрешён, секунд_до_сброса).
        Запросы сверх limit за window секунд отклоняются.
        """
        now = self._clock()
        with self._lock:
            self._cleanup(now, window)
            start, count = self._windows.get(key, (now, 0))
            if now - start >= window:
                start, count = now, 0
            count += 1
            self._windows[key] = (start, count)
            retry_after = max(1, int(window - (now - start)))
            return count <= limit, retry_after

    def reset(self) -> None:
        with self._lock:
            self._windows.clear()

    def _cleanup(self, now: float, window: int) -> None:
        # раз в минуту удаляем устаревшие окна, чтобы словарь не рос бесконечно
        if now - self._last_cleanup < 60:
            return
        self._last_cleanup = now
        stale = [k for k, (start, _) in self._windows.items() if now - start >= window * 2]
        for k in stale:
            del self._windows[k]
