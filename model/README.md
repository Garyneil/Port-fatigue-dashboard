# SEED-VIG 黎曼疲劳模型

本目录把前端演示项目推进为“可加载模型参数 + 可复现训练 + 可校准推理”的研究原型。

## 模型方法

`17通道EEG → 收缩协方差矩阵 → 黎曼对齐（RA）→ 单位点切空间 → 标准化 → 逻辑回归`

- 输入：3秒、17通道、128 Hz，即 `(n, 17, 384)`。
- 输出：每个窗口的困倦概率。
- 新操作员接入：必须先用一批无标签基线窗口估计个人黎曼中心。
- 报警：模型只输出概率；连续平滑、迟滞阈值和持续时间应由决策层完成。

## 全量训练结果

- 12名受试者，4566段EEG，清醒/困倦各2283段。
- 留一受试者交叉验证平均平衡准确率：`0.891 ± 0.053`。
- 平均F1：`0.892 ± 0.054`。
- 平均ROC-AUC：`0.943 ± 0.044`。

这些指标使用目标受试者整批无标签窗口估计黎曼中心，属于离线传导式结果，不代表码头现场性能。

## 已提交文件

```text
model/
├── artifacts/
│   ├── seed_vig_ra_tangent_lr_v1.npz  # 数字权重与标准化参数
│   ├── metadata.json                    # 数据、方法、指标和适用边界
│   └── loso_metrics.csv                 # 逐受试者验证结果
├── riemann_core.py                      # 黎曼数学与EEG特征
├── train_seed_vig.py                    # 可复现训练脚本
├── infer.py                             # 校准与推理CLI
└── requirements.txt
```

原始数据不提交到Git仓库。

训练数据来源：[Extracted SEED-VIG, Figshare 26104987 v1](https://doi.org/10.6084/m9.figshare.26104987.v1)，许可为CC BY 4.0。

## 重新训练

```powershell
python -m pip install -r model/requirements.txt
python model/train_seed_vig.py --data path/to/SEED_VIG.mat
```

## 推理输入

准备一个NPZ：

```python
import numpy as np

np.savez(
    "operator_input.npz",
    baseline_epochs=baseline,  # (n_baseline, 17, 384)，无标签个人基线
    target_epochs=windows,     # (n_windows, 17, 384)，待检测窗口
)
```

执行：

```powershell
python model/infer.py --input operator_input.npz
```

## 重要边界

当前验证使用目标受试者整批无标签数据估计对齐中心，属于传导式离线估计。码头在线版本应只使用当时已经获得的短时基线或历史滚动窗口，并重新验证误报率、漏报率和报警延迟。本模型仅供研究验证，不可直接作为港口安全决策依据。
