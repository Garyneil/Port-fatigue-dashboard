# Port Fatigue Dashboard

双通道额区脑电与黎曼流形疲劳倾向识别研究原型

A research prototype for fatigue-tendency recognition using dual-channel frontal EEG and Riemannian geometry.

[在线前端 / Dashboard](https://garyneil.github.io/Port-fatigue-dashboard/) · [头环接口 / Headset interface](interface/SICHIRAY_README.md) · [历史方案 / Legacy documentation](README.legacy.md)

> GitHub Pages 提供静态前端。真实头环采集与模型推理使用下方 Windows 演示包；模型及推理代码已包含在仓库中，完整训练数据另行管理。

> GitHub Pages hosts the static frontend. The Windows demo bundles live acquisition, inference and the numeric model. Full training data are managed separately.

## Windows 一键演示包

[下载最新 Windows 演示包](https://github.com/Garyneil/Port-fatigue-dashboard/releases/latest) · [三步使用说明](DEMO_GUIDE.md)

连接同款 Sichiray 双子座头环，完整解压下载包，双击 `PortFatigueDemo.exe`，选择串口并点击“启动演示”。应用自带 Python 运行环境、界面、采集程序和 SADT 双通道推理模型；可离线运行，无需安装开发环境。启动窗口提供停止采集、日志与下载更新入口。

模型与运行代码现已收录在 `interface/`，不再依赖开发电脑的固定盘符。训练数据与完整训练复现环境不包含在演示包内。在线页面可用于界面与仿真展示；真实头环演示使用本地包。GitHub Actions 会构建、自检并将可下载 ZIP 发布到 Releases。

## 中文说明

### 系统概述

本系统面向码头远程操控作业中的持续注意负荷与疲劳风险监测需求，构建了一套融合**双通道额区脑电采集、分频带协方差表征、黎曼流形对齐与切空间分类**的实时分析方法。系统以左额 Fp1、右额 Fp2 两路脑电为输入，将公开驾驶疲劳数据上的模型训练与便携式头环的在线采集相结合，形成从生理信号获取、信号质量控制、特征提取到疲劳倾向判别和前端可视化的完整处理链路。

### 数据与标签构建

在数据与标签构建方面，采用 SADT 驾驶数据中的 Fp1/Fp2 原始脑电，以驾驶反应时相对于个体基线的变化建立清醒与困倦两端状态标签。该策略以可观测的行为表现作为监督依据，使模型学习脑电活动与警觉性下降之间的统计关联。训练与评估共覆盖 **20 名被试、6,939 个脑电窗口**，并采用按被试独立的交叉验证，避免同一被试的数据同时进入训练集与测试集，使评估结果更能反映模型面对新个体时的泛化能力。

### 信号处理

在信号处理方面，离线训练与在线推理采用统一的预处理流程，将数据重采样至模型使用的 **50 Hz**，并分别提取 δ、θ、α 频段信号。这里的 50 Hz 是模型处理频率；头环标称硬件采样率为 **250 Hz**，在线数据是否连续、串口是否存在缺帧仍需单独检查。系统针对各频段构建双通道收缩协方差矩阵，联合描述左右额区脑电的能量变化与通道间协同关系。收缩估计用于改善短时间窗内协方差计算的数值稳定性，为后续流形分析提供正定矩阵输入。

### 黎曼特征与分类

在特征建模方面，系统将协方差矩阵视为对称正定矩阵流形上的数据点，利用黎曼几何处理其非欧氏结构。通过个体初始参考进行黎曼对齐，减轻不同个体基础脑电水平及采集条件差异造成的分布偏移；随后将对齐后的矩阵映射至切空间，形成可供分类器使用的向量特征。最终利用逻辑回归建立清醒与困倦之间的判别边界，实现从多频段脑电空间结构到疲劳倾向分数的映射。**这一方法的核心，是将双通道脑电的频段能量与空间关联纳入统一表征，并结合个体参考进行适配。**

### 在线部署与可视化

在在线部署方面，系统通过串口持续接收 Sichiray 双子座头环数据，在滑动时间窗内完成质量检查、特征计算与分类更新。质量控制综合考虑佩戴状态、数据连续性、缺帧情况、信号平直及异常幅值等因素；当输入不满足推理条件时，暂停更新判定，并在前端显示相应状态。前端同步呈现双通道滤波 EEG 波形、设备注意力与放松度曲线，以及模型疲劳倾向分数，为现场观察和后续实验复核提供直观依据。其中，注意力和放松度保留为设备输出指标，与模型的疲劳判别结果分别展示。

### 验证结果与适用边界

目前，模型在按被试独立验证中取得 **73.8% 的平均平衡准确率和 0.817 的平均 AUC**，并已通过未参与训练被试的原始脑电回放及头环实时数据推理链路验证。这些结果说明，双通道额区脑电结合黎曼几何特征具有一定的清醒与困倦区分能力，也为低通道、便携式疲劳监测提供了可实施的技术基础。当前前端显示的 0—100 分为分类模型输出的缩放分数，尚未经概率校准；公开驾驶数据上的离线表现也不能直接等同于码头作业中的识别准确率。后续将通过头环脑电与同步行为表现、主观疲劳标签的配对采集，进一步验证跨设备、跨场景适用性，并据此完善个体校准与判定阈值。

## English

### System Overview

This system addresses sustained attentional demands and fatigue-risk monitoring in remotely operated port tasks. It implements a real-time analysis pipeline combining **dual-channel frontal EEG acquisition, frequency-band covariance representation, Riemannian alignment, and tangent-space classification**. Using left-frontal Fp1 and right-frontal Fp2 signals, the system connects model training on a public driving-fatigue dataset with online acquisition from a portable EEG headset. The workflow covers physiological signal acquisition, signal-quality control, feature extraction, fatigue-tendency classification, and frontend visualization.

### Data and Label Construction

The model uses raw Fp1/Fp2 EEG from the SADT driving dataset. Alert and drowsy labels represent two endpoint states defined by changes in driving reaction time relative to an individual baseline. This behavioral supervision enables the model to learn statistical associations between EEG activity and reduced vigilance. Training and evaluation cover **20 participants and 6,939 EEG windows**. Subject-independent cross-validation keeps each participant out of the training set when evaluating that participant, providing an assessment of generalization to unseen individuals.

### Signal Processing

Offline training and online inference follow a consistent preprocessing pipeline. Data are resampled to the model processing rate of **50 Hz**, and signals are extracted separately in the δ, θ, and α bands. The 50 Hz rate refers to model processing; the headset has a nominal hardware sampling rate of **250 Hz**, while online stream continuity and missing serial frames require separate checks. For each band, a two-channel shrinkage covariance matrix jointly represents frontal EEG energy changes and interchannel relationships. Shrinkage estimation improves numerical stability for short-window covariance estimates and supplies positive-definite inputs for manifold analysis.

### Riemannian Features and Classification

Covariance matrices are treated as points on the manifold of symmetric positive-definite matrices, allowing Riemannian geometry to account for their non-Euclidean structure. Riemannian alignment based on an individual's initial reference reduces distribution shifts associated with baseline EEG differences and acquisition conditions. The aligned matrices are then mapped into a tangent space to obtain vector features for classification. Logistic regression learns a decision boundary between alert and drowsy states and maps multiband EEG spatial structure to a fatigue-tendency score. **The central idea is to represent band-specific energy and interchannel relationships within a common framework, with adaptation based on an individual reference.**

### Online Deployment and Visualization

The online system continuously receives data from the Sichiray Gemini dual-channel headset over a serial connection. Quality checks, feature computation, and classification updates operate on sliding windows. Quality control considers headset contact status, stream continuity, missing frames, flat signals, and abnormal amplitudes. When input conditions are unsuitable for inference, prediction updates are suspended and the frontend displays the relevant status. The dashboard presents filtered dual-channel EEG waveforms, device-provided attention and relaxation curves, and the model's fatigue-tendency score. Attention and relaxation remain separate device outputs and are displayed independently of the fatigue classifier.

### Validation Results and Scope

Subject-independent evaluation achieved a **mean balanced accuracy of 73.8% and a mean AUC of 0.817**. The inference pipeline has also been exercised using raw EEG replay from a participant excluded from training and live headset data. These results support the feasibility of distinguishing alert and drowsy states using dual-channel frontal EEG with Riemannian features, providing a practical basis for portable, low-channel-count fatigue monitoring. The displayed 0–100 value is a scaled classifier output and has not been probability-calibrated. Offline performance on public driving data must not be interpreted as recognition accuracy in port operations. Further paired recordings of headset EEG, concurrent behavioral performance, and subjective fatigue labels are needed to assess cross-device and cross-scenario applicability and refine individual calibration and decision thresholds.

## 历史文档 / Legacy Documentation

旧版 SEED-VIG、八通道模型与 Jetson 方案保留于 [README.legacy.md](README.legacy.md)，不代表当前双通道 SADT 模型的输入要求或性能。

Earlier SEED-VIG, eight-channel, and Jetson workflows remain in [README.legacy.md](README.legacy.md) and do not describe the input requirements or performance of the current dual-channel SADT model.
