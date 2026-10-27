"""
cache.py — a tiny in-memory cache whose entries expire after a while.

Why: SerpApi's free plan has 250 searches a month and Gemini's free tier has
a daily limit. If two people check the same company on the same day, the
second check re-uses the first answer instead of spending the quota again.

It lives in memory, so it is emptied whenever the server restarts — simple,
and good enough for a student project.
"""

import threading
import time


class TimedCache:
    def __init__(self, max_age_seconds: float, max_entries: int = 500):
        self.max_age_seconds = max_age_seconds
        self.max_entries = max_entries
        self._items: dict = {}  # key -> (time saved, value)
        self._lock = threading.Lock()  # the checks run in parallel threads

    def get(self, key):
        """Return the saved value, or None if there is none or it is too old."""
        with self._lock:
            item = self._items.get(key)
            if item is None:
                return None
            saved_at, value = item
            if time.monotonic() - saved_at > self.max_age_seconds:
                del self._items[key]  # expired
                return None
            return value

    def set(self, key, value) -> None:
        with self._lock:
            if len(self._items) >= self.max_entries:
                # Full: forget the oldest entry (dicts remember insertion order).
                self._items.pop(next(iter(self._items)))
            self._items[key] = (time.monotonic(), value)

    def clear(self) -> None:
        with self._lock:
            self._items.clear()
