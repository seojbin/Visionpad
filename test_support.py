"""Engine-level layout and interaction checks. No physical hardware required."""
import copy, importlib.util, json, math, re, sys, types, unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parent
class Pad:
 def __init__(self,width,height):self.width=width;self.height=height;self.clear()
 def clear(self):self.dots=[[0]*self.width for _ in range(self.height)];self.outside=[]
 def to_list(self):return self.dots
 def set_dot(self,x,y,*args):
  x,y=round(x),round(y)
  if 0<=x<self.width and 0<=y<self.height:self.dots[y][x]=1
  else:self.outside.append((x,y))
 def draw_line(self,x1,y1,x2,y2):
  n=max(1,round(max(abs(x2-x1),abs(y2-y1))))
  for i in range(n+1):self.set_dot(x1+(x2-x1)*i/n,y1+(y2-y1)*i/n)
 def draw_box(self,x,y,w,h):
  x,y=round(x)-w//2,round(y)-h//2
  for a,b,c,d in [(x,y,x+w-1,y),(x,y+h-1,x+w-1,y+h-1),(x,y,x,y+h-1),(x+w-1,y,x+w-1,y+h-1)]:self.draw_line(a,b,c,d)
 def draw_arrow(self,x,y,direction,size=2):
  pts={'left':[(-size,0),(size,-size),(size,size)],'right':[(size,0),(-size,-size),(-size,size)],'up':[(0,-size),(-size,size),(size,size)],'down':[(0,size),(-size,-size),(size,-size)]}[direction]
  for a,b in zip(pts,pts[1:]+pts[:1]):self.draw_line(x+a[0],y+a[1],x+b[0],y+b[1])
 def __getattr__(self,name):return lambda *a,**kw:None
prior=sys.modules.get('dotpad');sys.modules['dotpad']=types.SimpleNamespace(DotPad=Pad)
spec=importlib.util.spec_from_file_location('display_engine',ROOT/'game_engine.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
if prior is None:del sys.modules['dotpad']
else:sys.modules['dotpad']=prior
