"""Transient movement session; completion happens on exit or idle, never mid-stroke."""
import math

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
