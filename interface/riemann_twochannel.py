"""Causal 250 Hz filter bank and initial-session calibrated Riemannian features."""
import numpy as np
from scipy.signal import butter,sosfilt,sosfilt_zi
FS=250
BANDS=((.5,4),(4,8),(8,13),(13,30))
WINDOW_SECONDS=4
CALIBRATION_SECONDS=60

def spectral(a,fn):
    v,u=np.linalg.eigh((a+a.swapaxes(-1,-2))/2)
    v=np.maximum(v,1e-8)
    return (u*fn(v)[...,None,:])@u.swapaxes(-1,-2)
def logm(a):return spectral(a,np.log)
def expm(a):
    v,u=np.linalg.eigh((a+a.swapaxes(-1,-2))/2)
    return (u*np.exp(v)[...,None,:])@u.swapaxes(-1,-2)
def invsqrt(a):return spectral(a,lambda x:1/np.sqrt(x))
def cov(epoch):
    x=epoch-epoch.mean(axis=-1,keepdims=True)
    c=x@x.T/max(1,x.shape[-1]-1)
    return .9*c+.1*np.trace(c)/2*np.eye(2)+np.eye(2)*1e-8

def filter_signals(x):
    out=[]
    for low,high in BANDS:
        sos=butter(4,[low,high],btype='bandpass',fs=FS,output='sos')
        zi=sosfilt_zi(sos)[:,None,:]*x[None,:,0,None]
        y,_=sosfilt(sos,x,axis=-1,zi=zi);out.append(y)
    # Broadband signal only for quality screening, not a model input.
    sos=butter(4,[.5,30],btype='bandpass',fs=FS,output='sos')
    q,_=sosfilt(sos,x,axis=-1,zi=sosfilt_zi(sos)[:,None,:]*x[None,:,0,None])
    return np.asarray(out),q

def quality(epoch):
    if epoch.shape!=(2,FS*WINDOW_SECONDS) or not np.isfinite(epoch).all():return 'invalid'
    std=epoch.std(axis=-1)
    if np.min(std)<.1:return 'flat'
    if np.max(np.ptp(epoch,axis=-1))>300 or np.max(std)>100:return 'artifact'
    return 'ok'

def epoch_covs(filtered,start,end):
    return np.array([cov(b[:,start:end]) for b in filtered])

def features(covariances,centers):
    t=invsqrt(centers)
    aligned=t@covariances@t
    logs=logm(aligned)
    return np.stack([logs[...,0,0],logs[...,0,1]*np.sqrt(2),logs[...,1,1]],axis=-1).reshape(len(covariances),-1)

def fit_calibration(filtered,q):
    epochs=[]
    for end in np.arange(14,CALIBRATION_SECONDS+1,WINDOW_SECONDS):
        b=int(end*FS);a=b-FS*WINDOW_SECONDS
        if quality(q[:,a:b])=='ok':epochs.append(epoch_covs(filtered,a,b))
    if len(epochs)<5:raise ValueError(f'Insufficient valid initial calibration windows: {len(epochs)}')
    return expm(logm(np.array(epochs)).mean(axis=0)),len(epochs)
