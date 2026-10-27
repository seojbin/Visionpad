"""Emergency seeds must not consume tutorial progress or repeat while owned."""
import copy
import tempfile
import unittest

from engine.config import load_config
from engine.core.engine import GameEngine


class SeedHelpTests(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.engine = GameEngine(load_config('game'), save_dir=folder.name)
        self.engine.travel_to('town')

    def empty_seeds(self):
        self.engine.resources['seeds'] = {seed: 0 for seed in self.engine.config['seeds']}

    def test_help_precedes_every_quest_stage_and_preserves_progress(self):
        e = self.engine
        for stage in ('new', 'soup_given', 'seeds_given', 'vegetable_requested', 'done'):
            with self.subTest(stage=stage):
                self.empty_seeds()
                e.resources['coin'] = 0
                e.rowan_stage = stage
                before = copy.deepcopy(e.resources)
                used = e.time_used_cells
                result = e.perform_action('talk_rowan', {})
                before['seeds']['carrot'] = 1
                self.assertEqual(e.resources, before)
                self.assertEqual(e.rowan_stage, stage)
                self.assertEqual(e.time_used_cells, used)
                self.assertEqual(e.current_page, 'town')
                self.assertFalse(e.rowan_submit_open)
                self.assertIn('I found a carrot seed on the path.', result['tts'])
                self.assertEqual(result['speech_channel'], 'quest')
                self.assertEqual(result['speech_profile'], 'shopkeeper')
                self.assertEqual(result['priority'], 'dialogue')
                self.assertEqual(result['state']['dialogue']['text'], e.rowan_dialogue)

    def test_next_talk_resumes_quest_and_replay_does_not_grant(self):
        e = self.engine
        self.empty_seeds()
        e.talk_rowan()
        before = copy.deepcopy(e.resources)
        e.perform_action('repeat_rowan', {})
        self.assertEqual(e.resources, before)
        e.talk_rowan()
        self.assertEqual(e.rowan_stage, 'soup_given')
        self.assertEqual(e.resources['seeds']['carrot'], 1)
        self.assertEqual(e.resources['foods']['rowan_soup'], 1)

    def test_any_crop_seed_blocks_help_even_with_zero_gold(self):
        e = self.engine
        for seed in e.config['seeds']:
            with self.subTest(seed=seed):
                self.empty_seeds()
                e.resources['seeds'][seed] = 1
                e.resources['coin'] = 0
                e.rowan_stage = 'done'
                before = dict(e.resources['seeds'])
                result = e.talk_rowan()
                self.assertEqual(e.resources['seeds'], before)
                self.assertNotIn('I found a', result['tts'])

    def test_gold_and_flower_seeds_do_not_block_crop_seed_help(self):
        e = self.engine
        self.empty_seeds()
        e.resources['coin'] = 1000
        e.flower_seeds = 5
        e.talk_rowan()
        self.assertEqual(e.resources['coin'], 1000)
        self.assertEqual(e.flower_seeds, 5)
        self.assertEqual(e.resources['seeds']['carrot'], 1)

    def test_help_returns_when_seeds_run_out_again(self):
        e = self.engine
        self.empty_seeds()
        e.rowan_stage = 'done'
        e.talk_rowan()
        e.resources['seeds']['carrot'] = 0
        e.talk_rowan()
        self.assertEqual(e.resources['seeds']['carrot'], 1)
        self.assertEqual(e.rowan_stage, 'done')

    def test_both_rowan_targets_offer_help_but_hover_does_not_grant(self):
        e = self.engine
        self.empty_seeds()
        e.rowan_stage = 'done'
        targets = [obj for obj in e.get_objects() if obj.get('action') == 'talk_rowan']
        self.assertTrue(targets)
        for obj in targets:
            self.assertIn('Seeds available', obj['tts'])
            e.pointer_move(obj['x'], obj['y'])
        self.assertFalse(any(e.resources['seeds'].values()))
        icon = next(obj for obj in targets if obj['type'] == 'rowan')
        self.assertTrue(icon['quest_available'])
        e.talk_rowan()
        targets = [obj for obj in e.get_objects() if obj.get('action') == 'talk_rowan']
        self.assertTrue(all('Seeds available' not in obj['tts'] for obj in targets))

    def test_help_does_not_consume_pending_activity_reaction(self):
        e = self.engine
        self.empty_seeds()
        e.record_activity('harvest', 'Tomato')
        before = copy.deepcopy(e.npc_reactions)
        e.talk_rowan()
        self.assertEqual(e.npc_reactions, before)
        self.assertTrue(e.recent_reaction('shopkeeper'))

    def test_saved_gift_blocks_duplicate_after_restore(self):
        e = self.engine
        self.empty_seeds()
        e.talk_rowan()
        state = e.snapshot()
        self.empty_seeds()
        e.restore_snapshot(state)
        e.talk_rowan()
        self.assertEqual(e.resources['seeds']['carrot'], 1)
        self.assertEqual(e.rowan_stage, 'soup_given')

    def test_missing_bag_entries_and_absent_carrot_use_configured_seed(self):
        e = self.engine
        e.resources['seeds'] = {}
        del e.config['seeds']['carrot']
        result = e.talk_rowan()
        self.assertEqual(sum(e.resources['seeds'].values()), 1)
        self.assertTrue(set(e.resources['seeds']) <= set(e.config['seeds']))
        self.assertIn('seed on the path', result['tts'])

    def test_outside_village_does_not_grant(self):
        e = self.engine
        self.empty_seeds()
        e.travel_to('home')
        e.talk_rowan()
        self.assertFalse(any(e.resources['seeds'].values()))
