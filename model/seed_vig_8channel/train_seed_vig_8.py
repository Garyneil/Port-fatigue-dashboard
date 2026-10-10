from pathlib import Path
import sys, json, csv, hashlib, shutil, time, argparse
import numpy as np
import scipy, sklearn, mne
from scipy.io import loadmat
from scipy.optimize import linear_sum_assignment
from sklearn.metrics import accuracy_score, balanced_accuracy_score, f1_score, roc_auc_score

parser = argparse.ArgumentParser(description='Train independent eight-channel SEED-VIG model')
parser.add_argument('--data', type=Path, required=True)
parser.add_argument('--output', type=Path, required=True, help='New output directory')
args = parser.parse_args()
SRC = Path(__file__).resolve().parent
OUT = args.output.resolve()
DATA = args.data.resolve()
sys.path.insert(0, str(SRC))
from riemann_core import epochs_to_covariances, log_euclidean_mean, align_covariances, tangent_features_at_identity
from train_seed_vig import train_classifier
from infer import FatigueModel

def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()
def writecsv(name, rows):
    with (OUT/name).open('w', newline='', encoding='utf-8-sig') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
def score(y,p):
    return dict(accuracy=float(accuracy_score(y,p>=.5)), balanced_accuracy=float(balanced_accuracy_score(y,p>=.5)), f1=float(f1_score(y,p>=.5,zero_division=0)), roc_auc=float(roc_auc_score(y,p)))
def save_model(path, scaler, clf, indices):
    np.savez_compressed(path,scaler_mean=scaler.mean_,scaler_scale=scaler.scale_,classifier_coef=clf.coef_[0],classifier_intercept=clf.intercept_,classes=clf.classes_,n_channels=[8],window_samples=[384],sample_rate_hz=[128],shrinkage=[.1],decision_threshold=[.5],channel_indices=indices,channel_names=np.array(selected))

if __name__ == '__main__':
    OUT.mkdir(parents=True,exist_ok=False)
    shutil.copy2(__file__, OUT/'train_seed_vig_8.py')
    for name in ['riemann_core.py','infer.py','train_seed_vig.py']:
        shutil.copy2(SRC/name, OUT/name)
    targets=['F3','Fz','F4','C3','Cz','C4','P3','P4']
    available=['FT7','FT8','T7','T8','TP7','TP8','CP1','CP2','P1','Pz','P2','PO3','POz','PO4','O1','Oz','O2']
    montage=mne.channels.make_standard_montage('standard_1005')
    pos=montage.get_positions()['ch_pos']
    unit=lambda names: np.array([pos[n]/np.linalg.norm(pos[n]) for n in names])
    dist=np.arccos(np.clip(unit(targets)@unit(available).T,-1,1))
    rr,indices=linear_sum_assignment(dist)
    assert np.array_equal(rr,np.arange(8)) and len(set(indices))==8
    selected=[available[i] for i in indices]
    mapping=[dict(target=t,actual=selected[k],zero_based_index=int(indices[k]),one_based_index=int(indices[k]+1),angular_distance_degrees=float(np.degrees(dist[k,indices[k]])),independent_nearest=available[dist[k].argmin()],equivalent=False) for k,t in enumerate(targets)]
    writecsv('channel_mapping.csv',mapping)
    np.savez_compressed(OUT/'montage_distances.npz',targets=targets,available=available,distance_radians=dist,target_xyz=np.array([pos[n] for n in targets]),available_xyz=np.array([pos[n] for n in available]))
    digest=sha(DATA)
    assert digest=='e74ab8452f174b4081eebbb395e556767aac04790121933c5de123e444bc5ab7'
    raw=loadmat(DATA,variable_names=['EEGsample','substate','subindex'])
    assert raw['EEGsample'].shape==(4566,17,384)
    X=np.asarray(raw['EEGsample'][:,indices,:],dtype=float)
    y=raw['substate'].ravel().astype(int); subjects=raw['subindex'].ravel().astype(int)
    assert np.isfinite(X).all() and set(y)=={0,1}
    cov=epochs_to_covariances(X,.1)
    features=np.empty((len(y),36)); baseline={}; evaluation={}; centers={}; splits=[]
    # Selection uses only subject ID and seed, never labels or EEG values.
    for s in np.unique(subjects):
        ids=np.flatnonzero(subjects==s)
        b=np.sort(np.random.default_rng(20261010+int(s)).choice(ids,20,replace=False))
        e=np.setdiff1d(ids,b)
        baseline[int(s)]=b; evaluation[int(s)]=e
        centers[int(s)]=log_euclidean_mean(cov[b])
        features[e]=tangent_features_at_identity(align_covariances(cov[e],centers[int(s)]))
        splits.extend(dict(subject=int(s),epoch_index=int(i),role='calibration' if i in b else 'evaluation') for i in ids)
    writecsv('split_manifest.csv',splits)
    folds=[]; predictions=[]; checks=[]
    for s in np.unique(subjects):
        s=int(s); test=evaluation[s]
        train=np.concatenate([evaluation[t] for t in evaluation if t!=s])
        assert not np.any(subjects[train]==s)
        scaler,clf=train_classifier(features[train],y[train])
        path=OUT/f'loso_subject_{s:02d}.npz'
        save_model(path,scaler,clf,indices)
        expected=clf.predict_proba(scaler.transform(features[test]))[:,1]
        model=FatigueModel(path)
        start=time.perf_counter()
        actual=np.array(model.predict(X[baseline[s]],X[test])['fatigue_probability'])
        elapsed=time.perf_counter()-start
        assert np.allclose(actual,expected,rtol=1e-10,atol=1e-10)
        # Target batch composition must not change a prediction.
        single=float(model.predict(X[baseline[s]],X[test[:1]])['fatigue_probability'][0])
        mutated=X[test[:4]].copy(); mutated[1:]*=100
        same=float(model.predict(X[baseline[s]],mutated)['fatigue_probability'][0])
        assert abs(single-actual[0])<1e-10 and abs(single-same)<1e-10
        folds.append(dict(subject=s,n_calibration=20,n_train=len(train),n_test=len(test),**score(y[test],actual)))
        checks.append(dict(subject=s,reload_max_abs_error=float(np.max(abs(actual-expected))),target_batch_invariant=True,other_target_mutation_invariant=True,inference_seconds=elapsed,ms_per_window=elapsed*1000/len(test)))
        predictions.extend(dict(subject=s,epoch_index=int(i),true_label=int(y[i]),fatigue_probability=float(p),predicted_label=int(p>=.5),model_file=path.name) for i,p in zip(test,actual))
        print(json.dumps(folds[-1]),flush=True)
    writecsv('loso_metrics.csv',folds); writecsv('loso_predictions.csv',predictions)
    train=np.concatenate(list(evaluation.values()))
    scaler,clf=train_classifier(features[train],y[train])
    final=OUT/'seed_vig_8ch_ra_tangent_lr_v1.npz'; save_model(final,scaler,clf,indices)
    # Standalone CLI example uses a held-out fold, not the final all-subject model.
    s=1; ids=evaluation[s][:5]
    np.savez_compressed(OUT/'inference_input_subject01.npz',baseline_epochs=X[baseline[s]],target_epochs=X[ids])
    result=FatigueModel(OUT/'loso_subject_01.npz').predict(X[baseline[s]],X[ids])
    result.update(subject=1,target_epoch_indices=ids.tolist(),true_labels=y[ids].tolist(),model='loso_subject_01.npz')
    (OUT/'inference_output_subject01.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    summary=dict(dataset_path=str(DATA),dataset_sha256=digest,shape=list(raw['EEGsample'].shape),selected_channels=selected,zero_based_indices=indices.tolist(),n_features=36,n_subjects=len(evaluation),n_calibration=240,n_evaluation=len(predictions),mapping_method='Minimum total spherical angular distance, one-to-one Hungarian assignment, MNE standard_1005 template; normalized xyz around template origin; no measured lab coordinates',source_commit='10ce354dd12aaea36ccb36640c8a68d3b805a7db',source_hashes={n:sha(SRC/n) for n in ['riemann_core.py','train_seed_vig.py','infer.py']},versions=dict(numpy=np.__version__,scipy=scipy.__version__,sklearn=sklearn.__version__,mne=mne.__version__),protocol='LOSO; 20 randomly selected unlabeled calibration epochs per subject offered before inference; excluded from classifier fitting and scoring; frozen center; scaler/LR trained on other subjects only; fixed seed, C=1, balanced classes, threshold=.5',temporal_limitation='No timestamps/original chronological order or independent personal baseline exist. This is a disjoint calibration-before-query replay, not proven chronological prospective validation. Class-balanced extreme-state extracted dataset cannot establish live performance.',mean={k:float(np.mean([r[k] for r in folds])) for k in score(y[train],np.full(len(train),.5))},std={k:float(np.std([r[k] for r in folds],ddof=1)) for k in ['accuracy','balanced_accuracy','f1','roc_auc']},pooled=score(np.array([r['true_label'] for r in predictions]),np.array([r['fatigue_probability'] for r in predictions])),inference_checks=checks,final_model_sha256=sha(final),final_model_note='Deployment candidate trained on all subjects; no independent validation claimed for final-model example',labels='0 alert, 1 drowsy; source-defined labels',input_contract='Actual selected electrodes in exact saved order, 128 Hz, (n,8,384), finite values, same units/reference/preprocessing as training; requires 20 unlabeled calibration epochs; laboratory F3/Fz/F4/C3/Cz/C4/P3/P4 cannot be relabeled as these electrodes')
    (OUT/'metadata.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
    text='# SEED-VIG 8通道训练与实测推理\n\n'
    text+='数据 SHA256 已重新验证；4566×17×384，12名被试。复用原仓库协方差、对齐、切空间、分类器训练和 NPZ 推理代码。\n\n'
    text+='## 电极映射\n\n全局一对一最小球面角距离，避免同一实际通道重复充当多个输入。不是每个电极单独的最近邻，也不是物理等价替换。头模不是实验室帽子的实测坐标。\n\n|目标|实际|零起始索引|角距离|\n|---|---|---|---|\n'
    for r in mapping: text+=f"|{r['target']}|{r['actual']}|{r['zero_based_index']}|{r['angular_distance_degrees']:.2f}°|\n"
    text+='\n## 验证\n\n每人20个无标签窗口作为预先提供的校准集合，其余4326窗口参与LOSO评价。校准窗口不参与分类器训练或评分；所有测试窗口不参与中心、标准化或分类器拟合。训练被试也采用相同校准流程。\n\n'
    text+=f"被试宏平均 ± 样本标准差：{summary['mean']} ± {summary['std']}\n\n合并指标：{summary['pooled']}\n\n"
    text+='12个LOSO模型均重新加载并完成真实EEG推理，概率与sklearn一致（误差记录在metadata）；单窗口与批量推理一致，改变其他预测窗口不影响当前预测。全部实测概率见loso_predictions.csv。\n\n'
    text+='## 时间信息缺失\n\nMAT没有时间戳、原始顺序或独立基线，因此仅证明无预测数据泄漏的校准后查询流程，无法完成真实时间上的“无未来信息”验证。随机校准集合不应解释为实验最初60秒；筛选后的3秒窗口可能不连续。\n\n'
    text+='## 使用\n\n最终模型：seed_vig_8ch_ra_tangent_lr_v1.npz。严格输入顺序：'+', '.join(selected)+'. 每个窗口8×384，128Hz。36维切空间。实验室原8电极不能直接输入该模型并认为等价。单位、参考和完整预处理未知，实验室泛化性能尚未核实。\n\n'
    text+='独立重载推理示例（留出被试1模型）：\n\n```powershell\npython infer.py --model loso_subject_01.npz --input inference_input_subject01.npz\n```\n\n输出见inference_output_subject01.json；该示例属于LOSO留出数据，不用全量模型的训练内输出冒充外部验证。无ICA、伪迹处理或仪表盘修改。\n'
    (OUT/'summary.md').write_text(text,encoding='utf-8')
    print(json.dumps(dict(output=str(OUT),mean=summary['mean'],std=summary['std'],example=result),ensure_ascii=False),flush=True)
