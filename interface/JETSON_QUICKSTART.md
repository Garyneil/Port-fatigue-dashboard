# Jetson Nano 脑电帽启动步骤（可直接复制）

实验室已确认：脑电帽接线完成，Jetson 的 `/dev/ttyTHS0` 串口此前测试能够接收数据。这个确认来自使用者的设备测试；本次没有远程连接 Jetson 进行实机复测。不需要重新接线，也不需要改成 Windows 的 COM 端口。

通电后还需要启动桥接程序。下面的步骤没有设置开机自启。

## 1. 首次准备

在 Jetson 终端复制执行。代码放到 `~/eeg-fatigue`，已存在的仓库不重复克隆：

```bash
mkdir -p "$HOME/eeg-fatigue"
cd "$HOME/eeg-fatigue"

if [ ! -d Port-fatigue-dashboard/.git ]; then
  git clone https://github.com/Garyneil/Port-fatigue-dashboard.git
fi
if [ ! -d eeg-ecg-action-dataset-collector/.git ]; then
  git clone https://github.com/Garyneil/eeg-ecg-action-dataset-collector.git
fi

cd Port-fatigue-dashboard
python3 -m venv .venv
.venv/bin/python -m pip install -r interface/requirements.txt
```

需要 Jetson 能联网下载仓库和依赖。如果提示找不到 Git、pip 或 venv，先安装缺少的工具，再重试：

```bash
sudo apt-get update
sudo apt-get install -y git python3-pip python3-venv
```

若已有这两个项目，可以复用原目录；启动命令里的 `--collector` 应指向含有 `config.yaml` 和 `serial_reader.py` 的采集项目根目录。

## 2. 核对采集配置

采集项目的 `config.yaml` 应保持已经测试可用的配置：

```yaml
runtime:
  source: "serial12hex"
  source_args:
    port: "/dev/ttyTHS0"
    baudrate: 115200
    head: 255
    tail: 254
    fs: 250.0
    scale_eeg: 1.0
    scale_ecg: 1.0
    eeg_channels: 8
    ecg_channels: 4
```

这是配置片段，不要用它覆盖整个 `config.yaml`。桥接会直接读取该文件，不需要在网页输入 `/dev/ttyTHS0`。

## 3. 每次通电后启动

确认采集板已供电并正在发送数据。先退出其他占用 `/dev/ttyTHS0` 的采集程序或实时查看器，然后在 Jetson 终端执行：

```bash
cd "$HOME/eeg-fatigue/Port-fatigue-dashboard"
.venv/bin/python interface/eeg_bridge.py \
  --collector "$HOME/eeg-fatigue/eeg-ecg-action-dataset-collector"
```

省略 `--port` 即使用 `config.yaml` 中的 `/dev/ttyTHS0`。终端保持运行；按 `Ctrl+C` 停止。此桥接独立读取串口，不与原采集程序共享同一个串口连接。

## 4. 打开页面

在 **Jetson 自己的浏览器**打开：

**http://127.0.0.1:8765/**

- 保持“仿真演示”关闭。
- “脑电接口地址”保持 `./api/eeg/latest`。
- 有串口数据时显示真实8通道数值。
- 无数据或断流时显示“接口暂无数据传入”。
- 开启“仿真演示”后才显示模拟数据；关闭后立即清空模拟值并恢复真实数据读取。

`127.0.0.1` 指正在打开浏览器的那台设备。如果在另一台电脑打开这个地址，并不会访问到 Jetson。当前云端 Sites 页面也不能直接读取 Jetson 的串口；从云端页面接入需要另行提供可访问的 HTTPS/WSS 桥接地址，不能把 `/dev/ttyTHS0` 填成网页接口地址。

## 5. 检查接口是否收到数据

在 Jetson **另一个终端**执行，前一个桥接终端继续运行：

```bash
python3 - <<'PY'
import json
from urllib.request import urlopen

with urlopen('http://127.0.0.1:8765/api/eeg/latest', timeout=5) as response:
    print(json.dumps(json.load(response), ensure_ascii=False, indent=2))
PY
```

`has_data: true` 且包含 `eeg` 和 `timestamp` 表示桥接收到串口数据；`has_data: false` 表示当前没有有效数据。如果出现 `Permission denied`，检查串口权限；如果串口忙，关闭占用串口的进程。

## 当前显示范围

桥接提供真实 EEG 数值和连接状态，尚未自动运行疲劳模型。收到脑电但没有后端推理输出时，页面显示“等待模型推理结果”，风险保持 `--`。实验室电极与现有 SEED-VIG 模型电极不同，不能仅重命名就认为输入匹配。
