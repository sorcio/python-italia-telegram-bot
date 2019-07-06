from datetime import datetime, timedelta
from math import exp


class ActivityMonitor:
    def __init__(self, base_level=0, last_timestamp=None, period=600.0):
        self.activity_level = base_level
        self.last_timestamp = last_timestamp or datetime.utcnow()
        self.period = period

    def on_message(self, timestamp=None):
        if not timestamp:
            timestamp = datetime.utcnow()
        activity_level = self.get_activity_level(timestamp)
        activity_level += 1
        self.activity_level = activity_level
        self.last_timestamp = timestamp

    def get_activity_level(self, timestamp=None):
        if not timestamp:
            timestamp = datetime.utcnow()
        assert timestamp >= self.last_timestamp
        elapsed_time = (timestamp - self.last_timestamp).total_seconds()
        level = self.activity_level
        decay = exp(-elapsed_time / self.period)
        level *= decay
        return level

    def get_frequency(self, timestamp=None):
        if not timestamp:
            timestamp = datetime.utcnow()
        return self.get_activity_level(timestamp) / self.period
