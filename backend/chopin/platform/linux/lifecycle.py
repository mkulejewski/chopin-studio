"""Track frontend presence separately from launcher and API health checks."""
import time

IDLE_TIMEOUT = 5 * 60
POLL_INTERVAL = 1


class IdleShutdown:
    def __init__(self, clock=time.monotonic):
        self.clock = clock
        self.last_frontend = clock()
        self.disconnected_since = self.last_frontend

    def frontend_open(self):
        self.last_frontend = self.clock()

    def expired(self, connected):
        now = self.clock()
        if connected:
            self.disconnected_since = None
            return False
        if self.disconnected_since is None:
            self.disconnected_since = now
        return now - max(self.last_frontend, self.disconnected_since) >= IDLE_TIMEOUT
