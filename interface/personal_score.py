"""Local, explicitly experimental relative-band personal score profile."""
import hashlib
import json
from pathlib import Path
import numpy as np
from scipy.special import expit


def reference_signature(center, scale):
    return hashlib.sha256(np.ascontiguousarray(center,dtype=np.float64).tobytes()
        + np.ascontiguousarray(scale,dtype=np.float64).tobytes()).hexdigest()


class PersonalScoreProfile:
    def __init__(self, path, model_fingerprint):
        raw=Path(path).read_bytes()
        data=json.loads(raw)
        if (data.get('schema')!=1 or data.get('method')!='log_relative_band_v1'
            or data.get('model_fingerprint')!=model_fingerprint
            or data.get('input_source')!='device_filtered'):
            raise ValueError('Personal profile model or method mismatch')
        self.mean=np.asarray(data['mean'],dtype=float)
        self.scale=np.asarray(data['scale'],dtype=float)
        self.coef=np.asarray(data['coef'],dtype=float)
        self.intercept=float(data['intercept'])
        self.limit=float(data.get('max_standardized_feature',4))
        self.reference=data['reference_signature']
        if any(a.shape!=(2,) or not np.isfinite(a).all() for a in (self.mean,self.scale,self.coef)):
            raise ValueError('Invalid personal model arrays')
        if np.any(self.scale<=0) or not np.isfinite(self.intercept) or not 0<self.limit<=8:
            raise ValueError('Invalid personal model parameters')
        self.fingerprint=hashlib.sha256(raw).hexdigest()

    def compatible(self,center,scale):
        return center is not None and scale is not None and reference_signature(center,scale)==self.reference

    def predict(self,covariances):
        energy=np.trace(covariances,axis1=-2,axis2=-1)
        if energy.shape!=(3,) or not np.isfinite(energy).all() or np.any(energy<=0):
            raise ValueError('Invalid band covariance energy')
        vector=np.log(energy[1:]/energy[0])
        z=(vector-self.mean)/self.scale
        if not np.isfinite(z).all() or np.max(np.abs(z))>self.limit:
            raise ValueError('Personal feature outside development range')
        return float(expit(z@self.coef+self.intercept))
