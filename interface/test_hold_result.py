"""Validate hold-last-display behavior without accepting missing data as new inference."""
import unittest
from unittest.mock import patch
from live_fatigue_inference50 import LiveFatigueInference
from sichiray_bridge import Store


class HoldResultTests(unittest.TestCase):
    def seed_result(self, model, score=.37):
        model.set_result('fatigue_inference', '倾向清醒', drowsy_model_score=score,
            predicted_class='alert', fatigue_tendency='alert')

    def test_missing_data_holds_number_then_recovery_updates(self):
        model = LiveFatigueInference()
        self.seed_result(model)
        for status in ('data_gap', 'packet_loss', 'rate_out_of_range'):
            model.set_result(status, 'missing')
            result = model.snapshot()
            self.assertEqual(result['drowsy_model_score'], .37)
            self.assertTrue(result['display_stale'])
            self.assertFalse(result['ready'])
        model.reset(preserve_reference=True)
        self.assertEqual(model.snapshot()['drowsy_model_score'], .37)
        self.seed_result(model, .29)
        self.assertEqual(model.snapshot()['drowsy_model_score'], .29)
        self.assertFalse(model.snapshot().get('display_stale', False))
        model.reset()
        self.assertNotIn('drowsy_model_score', model.snapshot())

    def test_calibration_count_is_preserved_without_inventing_a_score(self):
        model = LiveFatigueInference()
        model.reference_epochs = [None] * 5
        model.set_result('data_gap', 'missing')
        self.assertEqual(model.snapshot()['reference_windows'], 5)
        self.assertEqual(model.snapshot()['progress_percent'], 42)
        self.assertNotIn('drowsy_model_score', model.snapshot())

    def test_stream_disconnect_holds_but_manual_close_does_not(self):
        store = Store()
        self.seed_result(store.inference)
        store.count = 100
        store.status = 'disconnected'
        with patch('sichiray_bridge.time.time', return_value=100):
            payload = store.payload()
        self.assertFalse(payload['has_data'])
        self.assertEqual(payload['candidate_inference']['status'], 'data_interrupted')
        self.assertTrue(payload['candidate_inference']['display_stale'])
        self.assertEqual(payload['candidate_inference']['drowsy_model_score'], .37)
        store.inference.reset()
        store.status = 'closed'
        self.assertNotIn('drowsy_model_score', store.payload()['candidate_inference'])


if __name__ == '__main__':
    unittest.main()
