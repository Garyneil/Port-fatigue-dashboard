# 独立8通道 RA + tangent-space logistic regression

本目录保存2026-10-10实测训练结果，复用主模型核心代码。最终模型与12折LOSO模型均已重新加载并通过推理一致性验证。

## 实際电极与索引

输入顺序为 FT7、CP1、FT8、P1、Pz、CP2、PO3、P2；原17通道零起始索引为 `[0,6,1,8,9,7,11,10]`。选取方法是标准头模球面角距离的全局一对一最小总距离。具体角度及独立最近邻见 `channel_mapping.csv`。

这些位置与实验室 F3、Fz、F4、C3、Cz、C4、P3、P4 不相同，不能直接重命名输入。额区没有邻近的可靠等价电极；本映射不是实测帽子坐标。

## 实测验证

数据4566×17×384，12名被试，SHA256已核实。每人固定随机种子选择20个无标签校准窗口，冻结个人对齐中心。240个校准窗口不参与分类器拟合或评分，其余4326个窗口做LOSO。标准化和逻辑回归仅在训练被试拟合。

|指标|被试宏平均 ± 样本标准差|
|---|---|
|平衡准确率|0.85181 ± 0.08272|
|F1|0.85405 ± 0.07609|
|ROC-AUC|0.91385 ± 0.06039|

MAT缺少时间戳、原始顺序和独立基线。因此这是校准集合先提供、查询集合随后推理的无预测数据泄漏验证，不能声称真实时间顺序下的前瞻验证。校准窗口并非连续最初60秒。各折结果见 `loso_metrics.csv`，全部实测输出见 `loso_predictions.csv`。

## 重现训练

从仓库根目录运行，输出目录必须尚不存在：

```powershell
python -m pip install -r model/seed_vig_8channel/requirements.txt
python model/seed_vig_8channel/train_seed_vig_8.py --data "E:/CODEX Projects/Methodology/data/external/SEED-VIG/SEED_VIG.mat" --output "outputs/seed_vig_8channel_reproduction"
```

重现训练会在本地生成推理输入和输出；原始EEG及含EEG的示例输入不上传仓库。完成后可运行：

```powershell
python outputs/seed_vig_8channel_reproduction/infer.py --model outputs/seed_vig_8channel_reproduction/loso_subject_01.npz --input outputs/seed_vig_8channel_reproduction/inference_input_subject01.npz
```

最终模型为 `seed_vig_8ch_ra_tangent_lr_v1.npz`，输入 `(n,8,384)`，128Hz，先提供20个无标签校准窗口，阈值0.5。单位、参考和完整预处理信息缺失，尚无实验室帽子泛化验证。

`inference_output_subject01.json` 来自留出被试模型；全量模型不能用训练内示例来声称独立准确率。`train_seed_vig_8.py` 已将原本本地绝对路径改为命令行参数，训练计算保持一致。

来源：Garyneil/Port-fatigue-dashboard commit `10ce354dd12aaea36ccb36640c8a68d3b805a7db`；[数据记录（CC BY 4.0）](https://doi.org/10.6084/m9.figshare.26104987.v1)。
