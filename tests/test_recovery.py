"""Recovery planning and archive safety: never duplicate finished source frames."""
import io
from pathlib import Path
import tempfile
import unittest
import zipfile
from tools.recover_alpine import make_tasks, latest, extract_named

MISSING = [61, 65, 68, 77, 79, 85, 88, 91, 94, 95, 98, 99]


class RecoverySafetyTest(unittest.TestCase):
    def test_exactly_144_missing_frames_no_duplicates_or_finished_frames(self):
        tasks = make_tasks(MISSING)
        frames = [f for task in tasks for f in range(task['start'], task['end'] + 1)]
        expected = [f for chunk in MISSING for f in range(chunk * 12 + 1, chunk * 12 + 13)]
        self.assertEqual(len(tasks), 144)
        self.assertEqual(frames, expected)
        self.assertEqual(len(set(frames)), 144)
        self.assertEqual(len({task['shard'] for task in tasks}), 144)
        self.assertTrue(all(task['start'] == task['end'] for task in tasks))
        self.assertEqual(frames[-1], 1200)
        self.assertEqual(len(set(range(1, 1201)) - set(frames)), 1056)

    def test_three_frame_shards_are_also_bounded(self):
        tasks = make_tasks(MISSING, 3)
        self.assertEqual(len(tasks), 48)
        self.assertTrue(all(task['end'] - task['start'] + 1 == 3 for task in tasks))

    def test_reject_duplicate_out_of_range_and_unsafe_tasks(self):
        for chunks, size in [([61, 61], 1), ([100], 1), ([-1], 1), ([61], 12), ([61], 0)]:
            with self.assertRaises(ValueError):
                make_tasks(chunks, size)
        with self.assertRaises(RuntimeError):
            make_tasks([])
        with self.assertRaises(RuntimeError):
            make_tasks(list(range(100)))

    def test_newest_nonexpired_artifact_selected(self):
        items = [{'id': 1, 'name': 'clip'}, {'id': 3, 'name': 'clip', 'expired': True},
                 {'id': 2, 'name': 'clip'}, {'id': 4, 'name': 'other'}]
        self.assertEqual(latest(items, 'clip')['id'], 2)
        self.assertIsNone(latest(items, 'missing'))

    def test_only_expected_files_are_written(self):
        stream = io.BytesIO()
        with zipfile.ZipFile(stream, 'w') as archive:
            archive.writestr('nested/frame.png', b'expected')
            archive.writestr('../../outside.txt', b'untrusted')
        with tempfile.TemporaryDirectory() as directory:
            destination = Path(directory) / 'safe'
            extract_named(stream.getvalue(), destination, ['frame.png'])
            self.assertEqual((destination / 'frame.png').read_bytes(), b'expected')
            self.assertEqual(list(destination.iterdir()), [destination / 'frame.png'])
            self.assertFalse((Path(directory) / 'outside.txt').exists())
            with self.assertRaises(RuntimeError):
                extract_named(stream.getvalue(), destination, ['../outside.txt'])

    def test_missing_or_ambiguous_zip_members_rejected(self):
        stream = io.BytesIO()
        with zipfile.ZipFile(stream, 'w') as archive:
            archive.writestr('a/frame.png', b'one')
            archive.writestr('b/frame.png', b'two')
        with tempfile.TemporaryDirectory() as directory:
            for name in ['frame.png', 'missing.png']:
                with self.assertRaises(RuntimeError):
                    extract_named(stream.getvalue(), Path(directory), [name])
