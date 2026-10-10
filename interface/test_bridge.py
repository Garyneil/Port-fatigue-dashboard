import importlib.util
from pathlib import Path
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('bridge', Path(__file__).with_name('eeg_bridge.py'))
bridge = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bridge)


class BridgeTests(unittest.TestCase):
    def test_no_device_means_no_data(self):
        self.assertFalse(bridge.LatestEEG(250).payload()['has_data'])

    def test_only_eeg_is_exposed_and_stale_data_expires(self):
        store = bridge.LatestEEG(250)
        with patch.object(bridge.time, 'time', return_value=100):
            store.update([0]+list(range(12)))
            payload = store.payload()
            self.assertEqual(payload['eeg'], list(range(8)))
            self.assertTrue(payload['has_data'])
            self.assertNotIn('fatigue_probability', payload)
        with patch.object(bridge.time, 'time', return_value=106):
            self.assertFalse(store.payload()['has_data'])
            self.assertNotIn('eeg', store.payload())

    def test_bad_sample_is_rejected(self):
        store = bridge.LatestEEG(250)
        store.update([0]+[float('nan')]*8)
        self.assertFalse(store.payload()['has_data'])


if __name__ == '__main__':
    unittest.main()
