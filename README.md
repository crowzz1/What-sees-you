# What Sees You 👁️

一个基于深度学习的实时人体追踪与视觉分析系统，集成了多摄像头支持、机械臂控制、TouchDesigner集成和多种视觉特效。

![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)
![PyTorch](https://img.shields.io/badge/PyTorch-2.0+-orange.svg)
![OpenCV](https://img.shields.io/badge/OpenCV-4.8+-green.svg)
![License](https://img.shields.io/badge/License-MIT-yellow.svg)

---

## ✨ 核心功能

### 🧍 人体检测与分析
- **YOLOv8-Pose** 17个关键点实时检测
- 身体尺寸测量（身高、肩宽、臀宽）
- 体型分类（Slim/Average/Broad）
- 多人同时追踪与识别

### 👤 人脸属性分析
- **年龄估计**（带平滑处理，减少抖动）
- **表情识别**（7种情绪：Happy, Sad, Angry, Surprise, Fear, Disgust, Neutral）
- **512维人脸特征向量**（用于身份识别和追踪）
- 基于 InsightFace 的高精度人脸分析

### 👕 服装识别
- **颜色检测**（上衣/下装主色调）
- **服装类型识别**（T-shirt, Shirt, Dress, Pants, Shorts）
- 基于关键点和颜色相似度的智能分类

### 🎨 视觉特效系统
- **精确人体分割**（YOLOv8-Seg）
- **黑白格子效果**（剪影内白色，背景黑色）
- **ASCII艺术效果**（使用字符显示轮廓）
- **故障艺术效果**（Glitch Art）
- **深度渐变效果**（MiDaS深度估计）
- **画廊视图**（多视角同时展示）

### 🤖 机械臂追踪控制
- **4轴STS伺服电机控制**
- 实时人体追踪与跟随
- 智能找脸算法（自动上移视角）
- 多目标轮询追踪
- 部位扫描模式（稳定对视时依次打量各部位）

### 📡 TouchDesigner 集成
- **UDP JSON** 数据传输（多人、多摄像头支持）
- 实时 CHOP 通道输出
- 自然语言描述生成
- MCP服务器支持

### 📹 多摄像头支持
- 同时支持最多3个摄像头
- 统一模型实例（节省GPU内存）
- 独立UDP端口配置
- 高性能优化（RTX 4090: 25-35 FPS/摄像头）

---

## 🚀 快速开始

### 环境要求

- **Python**: 3.8+
- **CUDA**: 11.8+ (推荐，用于GPU加速)
- **操作系统**: Windows 10/11, Linux, macOS
- **硬件**: 
  - GPU: NVIDIA GPU (推荐 RTX 4090 或更高)
  - 摄像头: USB摄像头（支持多摄像头）
  - 机械臂: STS3215伺服电机 × 4 (可选)

### 安装步骤

1. **克隆仓库**
```bash
git clone https://github.com/crowzz1/What-sees-you.git
cd What-sees-you
```

2. **安装依赖**
```bash
pip install -r requirements.txt
```

3. **安装 PyTorch (GPU版本)**
```bash
# CUDA 11.8
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118

# 或 CPU 版本
pip install torch torchvision torchaudio
```

4. **下载模型** (首次运行会自动下载)
   - YOLOv8-Pose: 自动下载
   - YOLOv8-Seg: 自动下载
   - InsightFace: 自动下载

---

## 📖 使用指南

### 基础使用

**单摄像头模式:**
```bash
python main.py
```

**画廊视图模式 (推荐):**
```bash
python main.py
# 或使用启动脚本
run.bat
```

**多摄像头模式:**
```bash
# Windows
start_3cameras_unified.bat

# Linux/macOS
python main.py --cameras 3
```

### 控制键

| 按键 | 功能 |
|------|------|
| `q` | 退出程序 |
| `s` | 保存截图 |
| `e` | 开启/关闭视觉特效 |
| `m` | 切换特效模式（剪影 ⇄ ASCII艺术） |
| `+/-` | 调整ASCII字符大小 |
| `w/x` | 调整ASCII亮度阈值 |

### 机械臂控制

**首次使用需要校准:**
```bash
# 校准所有电机
python tests/calibrate_4motors.py

# 或单独校准
python tests/calibrate_motor1_simple.py
python tests/calibrate_motor2_simple.py
```

**运行追踪:**
```bash
python main.py
# 系统会自动连接机械臂并开始追踪
```

**配置端口** (编辑 `config.py` 或 `tracker.py`):
```python
# 修改串口端口
port = "COM4"  # Windows
# 或
port = "/dev/ttyUSB0"  # Linux
```

---

## 📁 项目结构

```
What-sees-you/
├── main.py                 # 主程序（画廊视图）
├── person_analysis.py      # 核心分析器（人体+人脸+服装）
├── tracker.py              # 高级追踪器（机械臂控制）
├── visual_style.py         # 视觉特效模块
├── config.py               # 配置文件
├── requirements.txt        # Python依赖
│
├── docs/                   # 详细文档
│   ├── QUICK_START.md      # 快速入门指南
│   ├── GALLERY_VIEW_GUIDE.md    # 画廊视图指南
│   ├── ASCII_EFFECT_GUIDE.md    # ASCII效果指南
│   ├── GLITCH_ART_GUIDE.md      # 故障艺术指南
│   ├── ARM_TRACKING_README.md   # 机械臂追踪文档
│   └── ...
│
├── sts_control/            # STS伺服电机控制
│   ├── sts_driver.py       # 电机驱动
│   └── STS_servos_doc/     # 官方文档
│
├── esp32_servo42c_control/ # ESP32固件（可选）
│   └── robotic_arm_4axis/  # 4轴机械臂固件
│
├── td_mcp/                 # TouchDesigner MCP服务器
│   └── modules/            # MCP模块
│
├── tests/                  # 测试脚本
│   ├── calibrate_4motors.py
│   ├── diagnose_motors.py
│   └── ...
│
├── models/                 # 模型文件（自动下载）
│   ├── yolov8n-pose.pt
│   ├── yolov8n-seg.pt
│   └── ...
│
└── _archive/               # 历史版本代码
```

---

## 🎯 功能演示

### 画廊视图布局

```
┌─────────────────────┬──────────┐
│                     │          │
│   原始摄像头画面      │ 故障艺术  │
│   (黑白格子效果)     │ (Glitch) │
│                     │          │
├─────────────────────┼──────────┤
│                     │          │
│   人物信息面板       │ 手部追踪  │
│   (年龄/表情/服装)   │ (后台)   │
│                     │          │
└─────────────────────┴──────────┘
```

### 数据输出格式

**UDP JSON (TouchDesigner):**
```json
{
  "timestamp": 1699123456.789,
  "camera_id": 1,
  "person_count": 2,
  "persons": [
    {
      "person_id": 1,
      "age": 28,
      "emotion": "Happy",
      "body_type": "Average",
      "upper_color": "Blue",
      "clothing_type": {
        "upper": "T-shirt",
        "lower": "Pants"
      },
      "keypoints": [[x, y, conf], ...],
      "face_embedding": [512维向量]
    }
  ]
}
```

---

## ⚙️ 配置说明

### 摄像头配置

在 `main.py` 中修改:
```python
gallery = GalleryView(
    camera_id=0,           # 摄像头设备ID
    window_width=1440,     # 窗口宽度
    window_height=1080     # 窗口高度
)
```

### 性能优化

在 `person_analysis.py` 中调整:
```python
self.process_every_n_frames = 5    # 身体分析间隔
self.emotion_every_n_frames = 10   # 表情识别间隔
```

### 机械臂配置

在 `tracker.py` 中修改:
```python
MOTOR_CALIBRATION = {
    1: {'center': 2048, 'home': 3128, ...},  # 基座
    2: {'center': 2048, 'home': 3715, ...},  # 肩部
    3: {'center': 2048, 'home': 3835, ...},  # 肘部
    4: {'center': 2048, 'home': 2718, ...},  # 腕部
}
```

---

## 🔧 常见问题

### ❓ 摄像头无法打开

**解决方案:**
1. 检查摄像头是否被其他程序占用
2. 尝试不同的USB端口（推荐USB 3.0）
3. 在设备管理器中检查驱动

**测试命令:**
```bash
python -c "import cv2; cap=cv2.VideoCapture(0); print('OK' if cap.read()[0] else 'FAIL'); cap.release()"
```

### ❓ FPS 太低

**优化建议:**
1. 降低处理频率（修改 `process_every_n_frames`）
2. 关闭不必要的特效
3. 使用GPU加速（确保安装了CUDA版本的PyTorch）
4. 降低摄像头分辨率

### ❓ 机械臂不响应

**检查清单:**
1. 串口端口是否正确（`COM4` 或 `/dev/ttyUSB0`）
2. 电机是否已校准（运行 `calibrate_4motors.py`）
3. 电机是否已使能（按 `e` 键）
4. 检查串口连接和波特率（115200）

### ❓ TouchDesigner 收不到数据

**解决方案:**
1. 检查UDP端口是否正确（默认 7000, 7001, 7002）
2. 检查防火墙设置
3. 确认 TouchDesigner 的 UDP In DAT 配置正确
4. 查看控制台是否有错误信息

---

## 📊 性能指标

### 单摄像头模式
- **FPS**: 30-45 (RTX 4090)
- **GPU 内存**: ~2GB
- **延迟**: <50ms

### 多摄像头模式 (3个)
- **FPS**: 25-35 (每个摄像头, RTX 4090)
- **GPU 内存**: ~3GB (模型共享)
- **延迟**: <80ms

### 机械臂追踪
- **追踪精度**: ±2°
- **响应延迟**: <100ms
- **平滑系数**: 可调 (0.1-0.9)

---

## 🛠️ 技术栈

### 深度学习框架
- **PyTorch** - 深度学习框架
- **Ultralytics YOLOv8** - 人体检测、姿态估计、分割
- **InsightFace** - 人脸分析和年龄估计
- **DeepFace** - 表情识别和属性分析
- **MiDaS** - 单目深度估计

### 计算机视觉
- **OpenCV** - 图像处理和摄像头采集
- **NumPy** - 数值计算
- **scikit-learn** - 机器学习工具

### 硬件控制
- **PySerial** - 串口通信
- **STS3215** - 伺服电机驱动

### 集成
- **TouchDesigner** - 实时可视化
- **UDP** - 网络数据传输
- **MCP** - Model Context Protocol

---

## 📚 文档

详细文档请查看 `docs/` 目录:

- [快速入门指南](docs/QUICK_START.md)
- [画廊视图指南](docs/GALLERY_VIEW_GUIDE.md)
- [ASCII效果指南](docs/ASCII_EFFECT_GUIDE.md)
- [故障艺术指南](docs/GLITCH_ART_GUIDE.md)
- [机械臂追踪文档](docs/ARM_TRACKING_README.md)
- [3摄像头设置](docs/SETUP_3_CAMERAS.md)
- [性能优化指南](docs/PERFORMANCE_OPTIMIZATION_3CAM.md)

---

## 🎓 项目特点

- ✅ **模块化设计** - 各功能模块独立，易于扩展
- ✅ **高性能优化** - GPU加速，多摄像头模型共享
- ✅ **实时处理** - 低延迟，高帧率
- ✅ **易于配置** - 丰富的配置选项和文档
- ✅ **完整集成** - TouchDesigner、机械臂、多摄像头支持
- ✅ **视觉特效** - 多种艺术效果，适合展示

---

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

---

## 📄 许可证

MIT License

---

## 🙏 致谢

- [Ultralytics](https://github.com/ultralytics/ultralytics) - YOLOv8
- [InsightFace](https://github.com/deepinsight/insightface) - 人脸分析
- [DeepFace](https://github.com/serengil/deepface) - 表情识别
- [MiDaS](https://github.com/isl-org/MiDaS) - 深度估计

---

## 📮 联系方式

- **GitHub**: [@crowzz1](https://github.com/crowzz1)
- **项目地址**: https://github.com/crowzz1/What-sees-you

---

**⭐ 如果这个项目对你有帮助，请给个 Star！**
