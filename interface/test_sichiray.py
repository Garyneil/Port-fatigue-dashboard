import unittest
from unittest.mock import patch
from sichiray_bridge import parse_line, Store
LINE=b'132,3.73,0,6.27,65535,32768,0,0,-.06,.07,.02,-2.41,.97,9.59,0,0,0,0,0,50,50\n'
class Tests(unittest.TestCase):
    def test_signed_and_mapping(self):
        p=parse_line(LINE)
        self.assertEqual(p['eeg'],[-1,-32768])
        self.assertEqual(p['acceleration'],[-2.41,.97,9.59])
    def test_history_cursor_and_bounded_buffer(self):
        from collections import deque
        s=Store(); s.history=deque(maxlen=2)
        for _ in range(3): s.update(parse_line(LINE))
        batch=s.samples(0)
        self.assertEqual([r['id'] for r in batch['samples']],[2,3])
        self.assertEqual(batch['samples'][0]['eeg_filtered'],[0,0])
        self.assertEqual([r['id'] for r in s.samples(2)['samples']],[3])
        self.assertEqual(s.samples(3)['samples'],[])
        self.assertEqual(s.samples(0)['session'],batch['session'])

    def test_invalid(self):
        for line in [b'1,2', LINE.replace(b'3.73',b'nan'), LINE.replace(b'65535',b'65536')]:
            with self.assertRaises(ValueError): parse_line(line)
    def test_wear_stale_and_no_model(self):
        s=Store()
        with patch('sichiray_bridge.time.time',return_value=100):
            s.update(parse_line(LINE)); p=s.payload()
            self.assertTrue(p['has_data']); self.assertEqual(p['wear_status'],'failed')
            self.assertNotIn('attention',p); self.assertNotIn('fatigue_probability',p)
        with patch('sichiray_bridge.time.time',return_value=103):
            self.assertFalse(s.payload()['has_data']); self.assertNotIn('eeg',s.payload())
if __name__=='__main__': unittest.main()
