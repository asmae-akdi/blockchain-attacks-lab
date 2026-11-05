"""Moteur a evenements discrets : une file de priorite triee par temps."""
import heapq
import itertools


class Simulator:
    def __init__(self):
        self.now = 0.0
        self._queue = []
        self._counter = itertools.count()   # departage les evenements simultanes
        self._stopped = False

    def schedule(self, delay: float, fn, *args) -> None:
        """Planifie fn(*args) dans `delay` secondes (temps simule)."""
        heapq.heappush(self._queue, (self.now + delay, next(self._counter), fn, args))

    def stop(self) -> None:
        self._stopped = True

    def run(self, until: float) -> None:
        while self._queue and not self._stopped and self._queue[0][0] <= until:
            t, _, fn, args = heapq.heappop(self._queue)
            self.now = t
            fn(*args)
        if not self._stopped:
            self.now = until
