from datetime import datetime, timedelta
from math import exp
from typing import Optional


class ActivityMonitor:
    def __init__(self, period: float = 600.0, threshold: float = 0.5):
        self.period = period
        self.threshold = threshold
        self._activity_level = 0.0
        self._alerting = False
        self._frequency = 0.0
        self._last_timestamp: Optional[datetime] = None

    def update_activity(self, timestamp: datetime = None, level: float = 1.0):
        if not timestamp:
            timestamp = datetime.utcnow()
        if self._last_timestamp is not None:
            self._compute_activity_level(timestamp)
        self._activity_level += level
        self._frequency = self._activity_level / self.period
        self._last_timestamp = timestamp
        if self._frequency > self.threshold:
            if self._alerting:
                return False
            self._alerting = True
            return True
        else:
            self._alerting = False
            return False

    def _compute_activity_level(self, timestamp: datetime = None):
        if not timestamp:
            timestamp = datetime.utcnow()
        assert self._last_timestamp is not None
        assert timestamp >= self._last_timestamp
        elapsed_time = (timestamp - self._last_timestamp).total_seconds()
        level = self._activity_level
        decay = exp(-elapsed_time / self.period)
        level *= decay
        self._activity_level = level

    def get_frequency(self, timestamp: datetime = None):
        if not timestamp:
            timestamp = datetime.utcnow()
        if self._last_timestamp is not None:
            self._compute_activity_level(timestamp)
        return self._frequency

    @property
    def last_frequency(self):
        return self._frequency
