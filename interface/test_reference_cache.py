import tempfile
import unittest
from pathlib import Path
import numpy as np
from live_fatigue_inference50 import LiveFatigueInference


class ReferenceCacheTests(unittest.TestCase):
    def complete_reference(self, model):
        model.center = np.repeat(np.eye(2)[None], 3, axis=0)
        model.reference_scale = np.array([2., 3.])
        model.reference_epochs = [model.center.copy() for _ in range(12)]
        model.reference_amplitudes = [model.reference_scale.copy() for _ in range(12)]
        model.save_reference()

    def test_completed_reference_is_restored_without_restoring_old_scores(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parent) as folder:
            path = Path(folder) / 'reference.npz'
            model = LiveFatigueInference(reference_path=path)
            self.complete_reference(model)
            restored = LiveFatigueInference(reference_path=path)
            np.testing.assert_array_equal(restored.center, model.center)
            np.testing.assert_array_equal(restored.reference_scale, model.reference_scale)
            self.assertTrue(restored.snapshot()['reference_loaded'])
            self.assertEqual(restored.snapshot()['progress_percent'], 100)
            self.assertNotIn('drowsy_model_score', restored.snapshot())
            restored.push({'wear_code':0}, 1000)
            self.assertIsNotNone(restored.center)
            self.assertEqual(restored.snapshot()['status'], 'wear_failed')
            restored.push({'wear_code':1,'sequence':0,'eeg_filtered':[1.,2.]}, 1001)
            self.assertTrue(restored.snapshot()['reference_ready'])
            self.assertLessEqual(restored.snapshot()['remaining_seconds'], 14)
            restored.recalibrate()
            self.assertFalse(path.exists())
            self.assertEqual(restored.snapshot()['progress_percent'], 0)
            self.assertIsNone(restored.center)

    def test_corrupt_or_model_incompatible_cache_falls_back_to_collection(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parent) as folder:
            path = Path(folder) / 'reference.npz'
            path.write_bytes(b'not a saved reference')
            model = LiveFatigueInference(reference_path=path)
            self.assertIsNone(model.center)
            self.complete_reference(model)
            with np.load(path, allow_pickle=False) as saved:
                data = {key:saved[key] for key in saved.files}
            data['model_fingerprint'] = 'different-model'
            np.savez_compressed(path, **data)
            model = LiveFatigueInference(reference_path=path)
            self.assertIsNone(model.center)
            self.assertFalse(model.snapshot()['reference_loaded'])


if __name__ == '__main__':
    unittest.main()
