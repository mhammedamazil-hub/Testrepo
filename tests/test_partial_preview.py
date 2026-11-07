"""Preview safety tests; fake files stay in temporary test directories only."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from tools.assemble_partial_preview import contiguous_prefix, validate_segment


class PartialPreviewSafetyTest(unittest.TestCase):
    def test_stops_at_first_gap(self):
        selected, omitted = contiguous_prefix([
            {'name': 'alpine-segment-2', 'id': 3},
            {'name': 'alpine-segment-0', 'id': 1},
            {'name': 'alpine-segment-4', 'id': 5},
            {'name': 'alpine-segment-1', 'id': 2}])
        self.assertEqual([item['id'] for item in selected], [1, 2, 3])
        self.assertEqual(omitted, [4])

    def test_ignores_expired_and_unrelated_artifacts(self):
        selected, omitted = contiguous_prefix([
            {'name': 'alpine-segment-0', 'id': 1},
            {'name': 'alpine-segment-1', 'id': 2, 'expired': True},
            {'name': 'alpine-still', 'id': 3}])
        self.assertEqual(len(selected), 1)
        self.assertEqual(omitted, [])

    def test_no_opening_rejected(self):
        with self.assertRaises(RuntimeError):
            contiguous_prefix([{'name': 'alpine-segment-1', 'id': 2}])

    def test_complete_prefix_has_no_gaps(self):
        selected, omitted = contiguous_prefix([
            {'name': f'alpine-segment-{i}', 'id': i + 1} for i in range(100)])
        self.assertEqual(len(selected), 100)
        self.assertEqual(omitted, [])

    def test_segment_checksums_and_native_settings(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'segment_000.mp4'
            path.write_bytes(b'not-delivery-test-fixture')
            info = {'chunk': 0, 'start': 1, 'end': 12,
                    'source_frames_verified': 12, 'decoded_frames': 12,
                    'size': [1920, 1080], 'fps': 60, 'samples_max': 128,
                    'scene_sha256': 'a' * 64,
                    'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}
            path.with_suffix('.json').write_text(json.dumps(info))
            self.assertEqual(validate_segment(path, 0), info)
            path.write_bytes(b'tampered')
            with self.assertRaises(RuntimeError):
                validate_segment(path, 0)
            path.write_bytes(b'not-delivery-test-fixture')
            info['fps'] = 24
            path.with_suffix('.json').write_text(json.dumps(info))
            with self.assertRaises(RuntimeError):
                validate_segment(path, 0)
