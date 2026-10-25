"""Online SADT RT-defined alert/drowsy tendency, Fp1/Fp2 tangent-space model."""
from collections import deque
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import logging
import os
from zipfile import BadZipFile
import numpy as np
from scipy.special import expit
from signal_processing50 import filter_bank as _filter
from riemann_twochannel import cov,features,expm,logm
MODEL=Path(__file__).resolve().parent / 'models' / 'sadt-fatigue-v1' / 'model.npz'

class LiveFatigueInference:
 def __init__(self,model_path=MODEL,reference_path=None):
  self.model=np.load(model_path,allow_pickle=False) if Path(model_path).exists() else None
  self.model_fingerprint=hashlib.sha256(Path(model_path).read_bytes()).hexdigest() if self.model is not None else ''
  self.reference_path=Path(reference_path) if reference_path else None
  self.reference_cache_error=None
  self.reset()
  self.load_reference()

 def load_reference(self):
  if not self.reference_path or not self.reference_path.exists():return False
  try:
   with np.load(self.reference_path,allow_pickle=False) as data:
    if data['schema'].item()!=1 or data['model_fingerprint'].item()!=self.model_fingerprint:
     raise ValueError('Reference model/version mismatch')
    center=np.array(data['center']);scale=np.array(data['reference_scale'])
    epochs=np.array(data['reference_epochs']);amplitudes=np.array(data['reference_amplitudes'])
    if center.shape!=(3,2,2) or scale.shape!=(2,) or epochs.shape!=(12,3,2,2) or amplitudes.shape!=(12,2):
     raise ValueError('Invalid reference shapes')
    if not all(np.isfinite(a).all() for a in (center,scale,epochs,amplitudes)) or np.any(scale<=0) or np.any(amplitudes<=0):
     raise ValueError('Invalid reference values')
    if not np.allclose(center,center.swapaxes(-1,-2)) or np.min(np.linalg.eigvalsh(center))<=0:
     raise ValueError('Invalid reference covariance')
    saved_at=str(data['saved_at'].item())
   self.center=center;self.reference_scale=scale
   self.reference_epochs=list(epochs);self.reference_amplitudes=list(amplitudes)
   self.reference_loaded=True;self.reference_saved_at=saved_at
   self.set_result('waiting_for_data','已加载上次参考，等待头环数据')
   return True
  except (OSError,ValueError,KeyError,EOFError,TypeError,BadZipFile) as error:
   self.reference_cache_error=str(error)
   logging.warning('Reference cache not loaded: %s',error)
   return False

 def save_reference(self):
  if self.center is None or not self.reference_path:return
  try:
   self.reference_path.parent.mkdir(parents=True,exist_ok=True)
   saved_at=datetime.now(timezone.utc).isoformat()
   temporary=self.reference_path.with_suffix('.tmp')
   with temporary.open('wb') as stream:
    np.savez_compressed(stream,schema=1,model_fingerprint=self.model_fingerprint,
      center=self.center,reference_scale=self.reference_scale,
      reference_epochs=np.asarray(self.reference_epochs),
      reference_amplitudes=np.asarray(self.reference_amplitudes),saved_at=saved_at)
   os.replace(temporary,self.reference_path)
   self.reference_saved_at=saved_at;self.reference_cache_error=None
  except OSError as error:
   self.reference_cache_error=str(error)
   logging.warning('Reference cache not saved: %s',error)

 def recalibrate(self):
  self.reset()
  if self.reference_path:
   try:self.reference_path.unlink(missing_ok=True);self.reference_cache_error=None
   except OSError as error:
    self.reference_cache_error=str(error)
    logging.warning('Old reference cache not cleared: %s',error)
  self.set_result('waiting_for_data','重新校准已开始，等待采集有效参考片段 0/12')
  return self.snapshot()

 def reset(self,preserve_reference=False):
  if not preserve_reference:self.reference_loaded=False;self.reference_saved_at=None
  refs=getattr(self,"reference_epochs",[]) if preserve_reference else []
  amplitudes=getattr(self,"reference_amplitudes",[]) if preserve_reference else []
  center=getattr(self,"center",None) if preserve_reference else None
  scale=getattr(self,"reference_scale",None) if preserve_reference else None
  self.last_valid_result=getattr(self,'last_valid_result',None) if preserve_reference else None
  self.first_time=None;self.last_time=None;self.last_seq=None;self.index=0;self.missing=0;self.last_prediction_index=-1
  self.rows=deque(maxlen=2000);self.center=center;self.reference_scale=scale
  self.reference_epochs=refs;self.reference_amplitudes=amplitudes;self.last_reference_index=-100000
  self.set_result('waiting_for_data','等待头环数据')

 def set_result(self,status,message,**extra):
  self.result=dict(status=status,ready=status=='fatigue_inference',message=message,
    model='SADT Fp1/Fp2 黎曼疲劳分类 v1',output_meaning='SADT反应行为标签训练的疲劳倾向分类',
    hardware_validated=False,probability_calibrated=False,progress_percent=0,**extra)
  if status=='fatigue_inference':
   self.result['prediction_timestamp']=self.last_time
   self.last_valid_result=dict(self.result,prediction_timestamp=self.last_time)

 def push(self,packet,received_at):
  if self.model is None:self.set_result('model_missing','未找到疲劳分类模型');return
  if packet.get('wear_code')==0:
   self.reset(preserve_reference=True);self.last_valid_result=None
   self.set_result('wear_failed','设备报告佩戴失败，请调整电极和耳夹');return
  values=np.asarray(packet['eeg_filtered'],dtype=float)
  if values.shape!=(2,) or not np.isfinite(values).all():self.set_result('invalid_signal','脑电数值无效');return
  if self.last_time is not None and received_at-self.last_time>2:self.reset(preserve_reference=True)
  seq=int(packet['sequence'])
  if self.last_seq is None:self.first_time=received_at
  else:
   step=(seq-self.last_seq)%256
   if step==0:return
   if step>128:self.reset(preserve_reference=True);return self.push(packet,received_at)
   self.index+=step;self.missing+=max(0,step-1)
  self.last_seq=seq;self.last_time=received_at
  self.rows.append((self.index,received_at,*values))
  elapsed=received_at-self.first_time
  if elapsed<14:
   remaining=max(0,14-elapsed)+4*max(0,11-len(self.reference_epochs)) if self.center is None else max(0,14-elapsed)
   message=(f'已加载上次参考；信号预热，剩余 {max(0,14-elapsed):.0f} 秒' if self.reference_loaded
     else f'参考已就绪；信号预热，剩余 {max(0,14-elapsed):.0f} 秒') if self.center is not None else f'收集有效参考片段 {len(self.reference_epochs)}/12；信号预热'
   self.set_result('calibrating',message,reference_windows=len(self.reference_epochs),remaining_seconds=round(remaining,1),elapsed_seconds=round(elapsed,1))
   self.result['progress_percent']=int(len(self.reference_epochs)/12*100);return
  check_rate=min(60,max(35,self.index/max(elapsed,.001)))
  if self.index-self.last_prediction_index<check_rate:return
  self.last_prediction_index=self.index
  recent=np.asarray(self.rows)
  recent=recent[recent[:,1]>=received_at-14]
  span=recent[-1,1]-recent[0,1]
  steps=recent[-1,0]-recent[0,0]
  rate=steps/max(span,.001)
  current_rows=recent[recent[:,0]>=recent[-1,0]-rate*4]
  current_steps=current_rows[-1,0]-current_rows[0,0]
  window_missing=max(0,int(current_steps)-(len(current_rows)-1))
  loss=window_missing/max(1,current_steps)
  if len(current_rows)<2 or np.max(np.diff(current_rows[:,1]))>.5:
   self.set_result("data_gap","当前窗口接收时间不连续，等待数据恢复");return
  if not 35<=rate<=60:self.set_result('rate_out_of_range','实际帧率超出35至60包/秒适配范围',estimated_stream_rate_hz=round(rate,2));return
  if loss>.02:self.set_result('packet_loss','当前窗口存在缺帧，等待数据恢复',missing_sequence_frames=window_missing);return
  a=np.asarray(self.rows);idx=a[:,0];grid=np.linspace(idx[-1]-rate*13.98,idx[-1],700)
  if grid[0]<idx[0] or np.count_nonzero(idx>=grid[0])<rate*14*.9:return
  sig=np.vstack([np.interp(grid,idx,a[:,c]) for c in (2,3)])
  f=_filter(sig)
  current=np.std(sig[:,-200:],axis=1)
  if np.min(current)<1e-8:
   self.set_result('poor_signal','当前波形平直，暂停判定');return
  if self.center is None:
   if self.index-self.last_reference_index>=rate*4:
    self.reference_epochs.append(np.array([cov(ch[:,-200:]) for ch in f]))
    self.reference_amplitudes.append(current)
    self.last_reference_index=self.index
   count=len(self.reference_epochs)
   if count<12:
    self.set_result('calibrating',f'收集有效参考片段 {count}/12',reference_windows=count,remaining_seconds=4*(12-count),elapsed_seconds=round(elapsed,1))
    self.result['progress_percent']=int(count/12*100);return
   self.center=expm(logm(np.array(self.reference_epochs)).mean(axis=0))
   self.reference_scale=np.maximum(np.median(self.reference_amplitudes,axis=0),1e-8)
   self.save_reference()
  if np.min(current)<1e-8 or np.max(current/self.reference_scale)>10:
   self.set_result('poor_signal','波形平直或相对初始参考突变，暂停判定');return
  C=np.array([cov(ch[:,-200:]) for ch in f]);feat=features(C[None],self.center)[0]
  z=(feat-self.model['mean'])/self.model['scale']
  if not np.isfinite(z).all() or np.max(np.abs(z))>8:
   self.set_result('out_of_distribution','脑电特征超出训练参考范围，暂不判定');return
  score=float(expit(z@self.model['coef']+self.model['intercept']))
  tendency='drowsy' if score>=.6 else 'alert' if score<=.4 else 'uncertain'
  label={'drowsy':'倾向疲劳','alert':'倾向清醒','uncertain':'暂不确定'}[tendency]
  self.set_result('fatigue_inference',label,drowsy_model_score=score,predicted_class='drowsy' if score>=.5 else 'alert',
   fatigue_tendency=tendency,elapsed_seconds=round(elapsed,1),estimated_stream_rate_hz=round(rate,2),missing_sequence_frames=window_missing,lifetime_missing_sequence_frames=self.missing,
   wear_code=packet.get('wear_code'),reference='12 non-overlapping quality-approved 4s epochs; persisted personal reference; manually replaceable; not verified alert',sequence_modulus_assumption=256)
  self.result['progress_percent']=100

 def snapshot(self,status=None,message=None):
  result=dict(self.result)
  if status is not None:result.update(status=status,ready=False,message=message)
  count=len(self.reference_epochs)
  result.update(reference_windows=count,reference_ready=self.center is not None,
    reference_loaded=self.reference_loaded,reference_saved_at=self.reference_saved_at,
    reference_cache_error=self.reference_cache_error,
    last_prediction_timestamp=(self.last_valid_result.get('prediction_timestamp') if self.last_valid_result else None),
    progress_percent=100 if self.center is not None else round(count/12*100))
  transient=result['status'] in ('data_gap','packet_loss','rate_out_of_range','data_interrupted','calibrating','waiting_for_data')
  if transient and self.last_valid_result:
   for key in ('drowsy_model_score','predicted_class','fatigue_tendency','prediction_timestamp'):
    result[key]=self.last_valid_result[key]
   result.update(display_stale=True,message='数据缺失，显示上次有效结果；恢复后自动更新')
  elif transient and result['status'] in ('data_gap','packet_loss','rate_out_of_range','data_interrupted'):
   result['message']=f'数据缺失，已收集有效参考片段 {count}/12；恢复后继续'
  return result
