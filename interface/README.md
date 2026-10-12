# 真实脑电接口与仿真演示

Jetson Nano 使用已测试可接收数据的 `/dev/ttyTHS0`：先看 [可复制的安装、启动与检查步骤](JETSON_QUICKSTART.md)。

前端默认关闭“仿真演示”。没有真实数据、请求失败、返回空数据或数据时间戳超过10秒时，显示“接口暂无数据传入”，清除模拟指标与轨迹。开启开关后暂停接口读取并展示仿真；再次关闭立即清除仿真并恢复真实接口。

## 连接实验室采集项目

已核实 [eeg-ecg-action-dataset-collector](https://github.com/Garyneil/eeg-ecg-action-dataset-collector) 使用 `Serial12HexReader` 读取串口：FF头、12个大端有符号16位值、FE尾；前8个为EEG、后4个为ECG。其现有代码没有网页HTTP/WebSocket接口。

本桥接直接复用该项目的 `serial_reader.py` 及 `config.yaml`，读取真实串口并提供HTTP接口，同时提供同一份仪表盘。它不生成仿真数据，也不伪造疲劳概率。

在连接帽子的电脑，从仪表盘仓库根目录运行：

```powershell
python -m pip install -r interface/requirements.txt
python interface/eeg_bridge.py --collector "实际采集项目目录" --port COM3
```

将 `COM3` 换成设备实际串口；Jetson可省略 `--port` 使用配置中的 `/dev/ttyTHS0`。打开 **http://127.0.0.1:8765/**。默认接口 `./api/eeg/latest` 无需改动。设备未连接时桥接会重试，页面显示暂无数据。桥接和原采集程序不能同时独占同一串口，运行桥接前关闭占用该串口的程序。

托管网页无法直接读取用户电脑串口。若要从托管页面连接，需提供浏览器可访问的HTTPS/WSS桥接地址，在“脑电接口地址”填入。跨域HTTP服务需配置精确允许的页面Origin；本桥接支持 `--allow-origin https://port-riemann-fatigue-monitor.garyneil.chatgpt.site`，HTTPS需由受信任反向代理提供。不要在HTTPS页面使用远端明文HTTP/WS地址。

## 数据契约

HTTP每2秒读取JSON；WebSocket每条消息为相同JSON。支持相对HTTP地址和HTTP/HTTPS/WS/WSS完整地址。必填 `source: "real"`、`has_data: true`、ISO 8601 `timestamp`。数据包含8个有限数值的 `eeg`，或者后端实际模型输出的 `fatigue_probability`（0–1）。时钟应同步，超过10秒的数据不展示。

```json
{
  "source": "real",
  "has_data": true,
  "timestamp": "设备实际数据接收时间的ISO 8601值",
  "sample_rate_hz": 250,
  "channels": ["eeg_1", "eeg_2", "eeg_3", "eeg_4", "eeg_5", "eeg_6", "eeg_7", "eeg_8"],
  "eeg": [1, 2, 3, 4, 5, 6, 7, 8],
  "calibrated": false
}
```

以上仅是格式示意，不是实测结果。无数据返回 `{"source":"real","has_data":false}`。可选真实推理字段：`fatigue_probability`、`distance`、`attention`、`duration`、`quality`、`response_ms`、`work_seconds`、`velocity`、`operator`、`calibrated`。缺失字段显示 `--`；不使用随机数据补充。

原采集端8个电极与SEED-VIG模型的8个电极不同，单位、参考与完整预处理仍未确认。因此桥接只显示真实EEG和连接状态，收到原始EEG时显示“等待模型推理结果”，不自动套用该模型。只有后端提供实际推理结果时才展示风险。

## 3D脑电帽与头皮热图

头部旋转扫描为结构示意动画；热图表示8通道当前采样点的绝对幅值相对当前最大值（零至一），不是频带功率、源定位或黎曼距离。电极间颜色为逆距离平方插值，8通道覆盖有限。

仿真模式使用示意电极及模拟值。真实模式要求 `channels` 提供与8个 `eeg` 数值一一对应的已核实物理电极名称；`eeg_1` 等未映射名称不会生成热图。无数据或断流时清空热图。

串口桥接增加可选参数 `--channel-names`。仅在物理接线顺序已核实时指定，例如 `--channel-names "F3,Fz,F4,C3,Cz,C4,P3,P4"`；这个顺序只是格式示例，不代表已确认实验室接线。该参数仅用于空间展示，不改变模型兼容性。
