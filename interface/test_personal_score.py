import hashlib
import json
from pathlib import Path
import tempfile
import unittest
import numpy as np
from live_fatigue_inference50 import LiveFatigueInference,MODEL
from personal_score import PersonalScoreProfile,reference_signature


class PersonalScoreTests(unittest.TestCase):
    def profile(self,path):
        center=np.repeat(np.eye(2)[None],3,axis=0)
        data=dict(schema=1,method='log_relative_band_v1',input_source='device_filtered',
            model_fingerprint=hashlib.sha256(MODEL.read_bytes()).hexdigest(),
            reference_signature=reference_signature(center,np.ones(2)),
            mean=[0,0],scale=[1,1],coef=[1,-1],intercept=0,max_standardized_feature=4)
        path.write_text(json.dumps(data),encoding='utf-8')
        return data,center

    def test_relative_score_is_invariant_to_common_energy_gain(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as folder:
            path=Path(folder)/'synthetic-profile.json'
            data,center=self.profile(path)
            profile=PersonalScoreProfile(path,data['model_fingerprint'])
            covariance=np.array([np.eye(2)*v for v in (10,4,2)])
            self.assertAlmostEqual(profile.predict(covariance),profile.predict(covariance*100),places=12)
            self.assertTrue(profile.compatible(center,np.ones(2)))
            self.assertFalse(profile.compatible(center*2,np.ones(2)))
            with self.assertRaises(ValueError):profile.predict(np.array([np.eye(2)*v for v in (1,1e-10,1e-10)]))
            with self.assertRaises(ValueError):PersonalScoreProfile(path,'different-public-model')

    def test_switch_clears_old_score_and_reference_change_disables_profile(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as folder:
            path=Path(folder)/'synthetic-profile.json'
            data,center=self.profile(path)
            model=LiveFatigueInference(personal_profile_path=path)
            model.center=center;model.reference_scale=np.ones(2)
            self.assertEqual(model.snapshot()['model_mode'],'generic')
            model.set_personal_mode(True)
            self.assertEqual(model.snapshot()['model_mode'],'personal_experimental')
            model.set_result('fatigue_inference','test',drowsy_model_score=.7,fatigue_tendency='drowsy',predicted_class='drowsy')
            model.set_personal_mode(False)
            self.assertIsNone(model.last_valid_result)
            self.assertNotIn('drowsy_model_score',model.snapshot())
            model.set_personal_mode(True)
            model.recalibrate()
            self.assertFalse(model.personal_mode)
            self.assertFalse(model.personal_profile_available)
            self.assertFalse(model.snapshot()['hardware_validated'])


if __name__=='__main__':unittest.main()
