"""Transient movement session; completion happens on exit or idle, never mid-stroke."""
import itertools
import math
import time

class PettingSession:
    def __init__(self):
        self.clear()
    def clear(self):
        self.previous=None
        self.last_motion=None
        self.seconds=0.0
    def finish(self,threshold):
        ready=self.seconds>=threshold
        self.clear()
        return ready
    def poll(self,now,threshold,idle):
        if self.last_motion is not None and now-self.last_motion>=idle:
            return self.finish(threshold)
        return False
    def move(self,x,y,now,inside,threshold,idle,gap):
        if not inside:return self.finish(threshold)
        ready=self.poll(now,threshold,idle)
        if self.previous:
            t,px,py=self.previous
            if math.hypot(x-px,y-py)>=0.2:
                if 0<now-t<=gap:self.seconds+=now-t
                self.last_motion=now
        else:self.last_motion=now
        self.previous=(now,x,y)
        return ready


_feedback_counter = itertools.count(1)


def next_feedback_id():
    """Unique ID for one petting completion; the browser plays each ID's sound once.

    `time.monotonic_ns()` alone repeats on Windows (about 15 ms resolution), so two completions in
    one tick shared an ID and the second sound was dropped. The counter keeps every ID distinct.
    """
    return f"{time.monotonic_ns()}-{next(_feedback_counter)}"
