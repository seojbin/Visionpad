"""Old speech folders move into .audio/ once, without losing or overwriting anything."""
from pathlib import Path
import tempfile
import unittest

from engine.services.audio_files import migrate_legacy_audio


def write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


class AudioMigrationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="visionpad audio move ")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.notes = []

    def migrate(self):
        return migrate_legacy_audio(self.root, log=self.notes.append)

    def test_old_voice_cache_and_reports_move_and_the_old_folders_disappear(self):
        write(self.root / "models/piper/voice.onnx", "model")
        write(self.root / "models/piper/voice.onnx.json", "{}")
        write(self.root / ".cache/speech/abc.wav", "wav")
        write(self.root / "output/audio/demo-ready.json", "{}")
        moved = self.migrate()
        self.assertEqual(len(moved), 3)
        self.assertEqual((self.root / ".audio/voices/voice.onnx").read_text(encoding="utf-8"), "model")
        self.assertTrue((self.root / ".audio/voices/voice.onnx.json").is_file())
        self.assertTrue((self.root / ".audio/cache/abc.wav").is_file())
        self.assertTrue((self.root / ".audio/reports/demo-ready.json").is_file())
        for old in ("models", ".cache", "output"):
            self.assertFalse((self.root / old).exists(), old)
        self.assertIn("Moved speech files to .audio/", self.notes[0])

    def test_existing_new_files_win_and_other_content_is_left_in_place(self):
        write(self.root / "models/piper/voice.onnx", "old")
        write(self.root / ".audio/voices/voice.onnx", "new")
        write(self.root / ".cache/speech/abc.wav", "wav")
        write(self.root / ".cache/huggingface/x.bin", "other")
        self.migrate()
        self.assertEqual((self.root / ".audio/voices/voice.onnx").read_text(encoding="utf-8"), "new")
        self.assertEqual((self.root / "models/piper/voice.onnx").read_text(encoding="utf-8"), "old")
        self.assertTrue((self.root / ".cache/huggingface/x.bin").is_file())
        self.assertFalse((self.root / ".cache/speech").exists())
        self.assertTrue(any("already exist" in note for note in self.notes))
        self.assertTrue(any("Left in place" in note and ".cache/huggingface" in note for note in self.notes))

    def test_nothing_to_move_is_silent_and_a_second_run_changes_nothing(self):
        self.assertEqual(self.migrate(), [])
        write(self.root / "output/audio/samples.json", "[]")
        self.migrate()
        self.notes.clear()
        self.assertEqual(self.migrate(), [])
        self.assertEqual(self.notes, [])
