import tempfile
import unittest
from unittest.mock import patch
from engine.config import load_config
from engine.core.engine import GameEngine

class ReleaseTests(unittest.TestCase):
    def test_all_animals_release_idle_repeat_and_daily_limit(self):
        for kind in ('cat','dog','chicken','sheep'):
            with self.subTest(kind=kind),tempfile.TemporaryDirectory() as tmp:
                e=GameEngine(load_config('game'),save_dir=tmp)
                pet=kind in ('cat','dog');f=e.registry.features['pets' if pet else 'pasture']
                if pet:
                    f.adopt(kind);a=f.selected();e.set_page('pet_detail');move=f.stroke;stat='affection'
                    f.rows=lambda a:tuple('1'*36 for _ in range(24));f.position=lambda a,detail=False:(29,25)
                else:
                    a=e.pasture_animals[kind];a['owned']=True;e.pasture_selected=kind;e.set_page('animal_detail');move=f.pet_motion;stat='friendship'
                with patch(('game.pets.feature.' if pet else 'game.pasture.feature.')+'time.monotonic') as clock:
                    def stroke(start,seconds):
                        for i in range(int(seconds*10)+1):
                            clock.return_value=start+i*.1;move(28+i%2,22)
                    stroke(100,1)
                    clock.return_value=101.1;move(0,0)
                    self.assertIsNone(f._pet_feedback);self.assertEqual(a[stat],0)
                    stroke(110,4)
                    self.assertIsNone(f._pet_feedback);self.assertEqual(a[stat],0)
                    clock.return_value=114.1;move(0,0)
                    first=f._pet_feedback['id'];self.assertEqual(a[stat],10)
                    self.assertEqual(f._pet_feedback['events'][0]['sound'],kind+'_main')
                    clock.return_value=114.2;move(0,0);self.assertEqual(f._pet_feedback['id'],first)
                    stroke(120,2.5)
                    self.assertEqual(f._pet_feedback['id'],first)
                    clock.return_value=123.1;e.get_state()
                    self.assertNotEqual(f._pet_feedback['id'],first);self.assertEqual(a[stat],10)
                    last=f._pet_feedback['id'];clock.return_value=123.3;e.get_state();self.assertEqual(f._pet_feedback['id'],last)
                    e.day+=1;stroke(130,2.5);clock.return_value=133.1;e.get_state();self.assertEqual(a[stat],20)
                    stroke(140,2.5);e.paused=True;clock.return_value=143.1;e.get_state();self.assertIsNone(f._pet_feedback)
