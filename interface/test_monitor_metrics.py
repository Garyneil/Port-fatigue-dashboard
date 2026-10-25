import unittest
from unittest.mock import patch
from sichiray_bridge import Store, parse_line
from test_sichiray import LINE


class MonitorMetricTests(unittest.TestCase):
    def test_elapsed_monitoring_time_starts_on_first_packet_and_freezes_on_stop(self):
        store = Store()
        self.assertEqual(store.payload()['monitor_seconds'], 0)
        with patch('sichiray_bridge.time.time', return_value=100), patch('sichiray_bridge.time.monotonic', return_value=50):
            store.update(parse_line(LINE))
        with patch('sichiray_bridge.time.time', return_value=101), patch('sichiray_bridge.time.monotonic', return_value=55):
            self.assertEqual(store.payload()['monitor_seconds'], 5)
        store.status = 'closed'
        store.monitor_stopped = 56
        with patch('sichiray_bridge.time.monotonic', return_value=1000):
            self.assertEqual(store.payload()['monitor_seconds'], 6)

    def test_recent_sequence_loss_and_arrival_gaps_are_reported(self):
        store = Store()
        for stamp,sequence in ((100,254),(100.02,255),(100.04,0),(100.06,3),(101,4)):
            packet = parse_line(LINE)
            packet['sequence'] = sequence
            with patch('sichiray_bridge.time.time', return_value=stamp):
                store.update(packet)
        with patch('sichiray_bridge.time.time', return_value=101):
            health = store.payload()['stream_health']
        self.assertEqual(health['estimated_missing_frames'], 2)
        self.assertTrue(health['time_discontinuity'])
        self.assertFalse(health['sequence_discontinuity'])


if __name__ == '__main__':
    unittest.main()
