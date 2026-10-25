"""Online SADT RT-defined alert/drowsy tendency, Fp1/Fp2 tangent-space model."""
from collections import deque
from pathlib import Path
import numpy as np
from scipy.special import expit
from signal_processing50 import filter_bank as _filter
from riemann_twochannel import cov,features,expm,logm
MODEL=Path(__file__).resolve().parent / 'models' / 'sadt-fatigue-v1' / 'model.npz'

class LiveFatigueInference:
 def __init__(self,model_path=MODEL):
  self.model=np.load(model_path,allow_pickle=False) if Path(model_path).exists() else None
  self.reset()

 def reset(self,preserve_reference=False):
  refs=getattr(self,"reference_epochs",[]) if preserve_reference else []
  amplitudes=getattr(self,"reference_amplitudes",[]) if preserve_reference else []
  center=getattr(self,"center",None) if preserve_reference else None
  scale=getattr(self,"reference_scale",None) if preserve_reference else None
  self.first_time=None;self.last_time=None;self.last_seq=None;self.index=0;self.missing=0;self.last_prediction_index=-1
  self.rows=deque(maxlen=2000);self.center=center;self.reference_scale=scale
  self.reference_epochs=refs;self.reference_amplitudes=amplitudes;self.last_reference_index=-100000
  self.set_result('waiting_for_data','等待头环数据')

 def set_result(self,status,message,**extra):
  self.result=dict(status=status,ready=status=='fatigue_inference',message=message,
    model='SADT Fp1/Fp2 黎曼疲劳分类 v1',output_meaning='SADT反应行为标签训练的疲劳倾向分类',
    hardware_validated=False,probability_calibrated=False,progress_percent=0,**extra)

 def push(self,packet,received_at):
  if self.model is None:self.set_result('model_missing','未找到疲劳分类模型');return
  if packet.get('wear_code')==0:
   self.reset();self.set_result('wear_failed','设备报告佩戴失败，请调整电极和耳夹');return
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
   self.set_result('calibrating',f'收集有效参考片段 {len(self.reference_epochs)}/12；断流后滤波预热',reference_windows=len(self.reference_epochs),remaining_seconds=round(remaining,1),elapsed_seconds=round(elapsed,1))
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
   self.set_result("poor_signal","当前窗口接收时间不连续，暂停判定");return
  if not 35<=rate<=60:self.set_result('rate_out_of_range','实际帧率超出35至60包/秒适配范围',estimated_stream_rate_hz=round(rate,2));return
  if loss>.02:self.set_result('packet_loss','序号估计缺帧超过2%，暂停判定',missing_sequence_frames=window_missing);return
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
   wear_code=packet.get('wear_code'),reference='12 non-overlapping quality-approved 4s epochs; fixed within wear session; not verified alert',sequence_modulus_assumption=256)
  self.result['progress_percent']=100

 def snapshot(self):return dict(self.result)
