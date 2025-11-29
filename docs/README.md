# 🎥 Multi-Camera AI Vision System for TouchDesigner

**3摄像头实时人体分析系统** - 为 TouchDesigner 提供完整的人体检测、姿态识别、人脸分析和服装识别功能。

---

## ✨ 功能特性

### 🧍 人体检测与姿态分析
- **YOLOv8-Pose** 17个关键点检测
- 身体尺寸测量（身高、肩宽、臀宽）
- 体型分类（Slim/Average/Broad）
- 实时骨架可视化

### 👤 人脸属性分析
- **年龄估计**（带平滑处理）
- **表情识别**（Happy, Sad, Angry, Surprise, Fear, Disgust, Neutral）
- **512维人脸特征向量**（用于识别和追踪）

### 👕 服装分析
- **颜色检测**（上衣/下装主色调）
- **服装类型识别**
  - 上装：T-shirt, Shirt, Dress（连衣裙）
  - 下装：Pants, Shorts
- 基于关键点和颜色相似度的智能分类

### 🎨 视觉特效
- **精确人体分割**（YOLOv8-Seg）
- **黑白格子效果**（剪影内白色，背景黑色）
- **ASCII艺术效果**（使用0和1字符显示轮廓）✨ **新增**
- **画廊视图**（多视角同时展示）✨ **新增**
- **深度渐变效果**（MiDaS深度估计）
- **自适应颜色文本**（根据背景自动调整）

### 🎯 TouchDesigner 集成
- **UDP JSON** 数据传输（多人、多摄像头支持）
- 实时 CHOP 通道输出
- 自然语言描述生成
- 数据量化和标准化

---

## 🚀 快速开始

### 1️⃣ 安装依赖

```bash
pip install -r requirements.txt
```

**确保安装 CUDA 版本的 PyTorch**（RTX 4090）：
```bash
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
```

### 2️⃣ 连接摄像头

确保3个摄像头已连接并可以被系统识别。

### 3️⃣ 启动系统

**多摄像头系统 (Windows):**
```bash
start_3cameras_unified.bat
```

**或直接运行:**
```bash
python main.py
```

**画廊视图 (推荐用于展示):**
```bash
python main_gallery_view.py
```
同时显示摄像头画面、ASCII艺术效果和AI分析描述

**ASCII效果测试:**
```bash
python test_ascii_effect.py
```
可实时调整参数的测试程序

---

## 📁 项目结构

```
.
├── main.py                       # 单摄像头主程序
├── main_gallery_view.py          # 画廊视图（多视角展示）✨ 新增
├── test_ascii_effect.py          # ASCII效果测试程序 ✨ 新增
├── person_analyzer.py            # 核心分析器类（支持ASCII效果）
├── td_transmitter.py             # TouchDesigner 数据传输
├── td_chop_script_latest_only.py # TouchDesigner CHOP 脚本
├── start_3cameras_unified.bat    # 启动脚本
├── requirements.txt              # Python 依赖
├── ASCII_EFFECT_GUIDE.md         # ASCII效果使用指南 ✨ 新增
├── GALLERY_VIEW_GUIDE.md         # 画廊视图使用指南 ✨ 新增
└── td_mcp/                       # TouchDesigner MCP 服务器
```

---

## 🎮 控制键

### 基本控制（main.py）
| 按键 | 功能 |
|------|------|
| `q` | 退出程序 |
| `s` | 保存截图 |
| `e` | 开启/关闭视觉特效 |
| `m` | 切换特效模式（剪影 ⇄ ASCII艺术）✨ |

### 画廊视图（main_gallery_view.py）
| 按键 | 功能 |
|------|------|
| `q` | 退出程序 |
| `s` | 保存完整画面截图 |
| `+/-` | 调整ASCII字符大小 |
| `w/x` | 调整ASCII亮度阈值 |

---

## 📊 性能参数

### 3摄像头统一模式
- **FPS**: 25-35（每个摄像头，RTX 4090）
- **GPU 内存**: ~3GB
- **延迟**: <80ms
- **模型共享**: 所有摄像头共享同一个模型实例（节省内存）

### 优化设置
```python
# 在 person_analyzer.py 中修改
self.process_every_n_frames = 5    # 身体分析间隔
self.emotion_every_n_frames = 10   # 表情识别间隔
```

---

## 📡 TouchDesigner 数据格式

### UDP JSON 结构

```json
{
  "timestamp": 1699123456.789,
  "frame_number": 123,
  "camera_id": 1,
  "person_count": 2,
  "persons": [
    {
      "person_id": 1,
      "bbox": {"x1": 100, "y1": 200, "x2": 300, "y2": 600},
      "age": 28,
      "emotion": "Happy",
      "emotion_confidence": 0.85,
      "body_type": "Average",
      "upper_color": "Blue",
      "lower_color": "Black",
      "clothing_type": {
        "upper": "T-shirt",
        "lower": "Pants"
      },
      "description": "A 28-year-old person with an average build, wearing a blue t-shirt and black pants, appears happy.",
      "keypoints": [[x, y, conf], ...],  // 17个关键点
      "face_embedding": [512维向量]
    }
  ]
}
```

### CHOP 输出通道

每个人会输出以下通道：
```
person{N}_id              # 人物ID
person{N}_age             # 年龄
person{N}_age_norm        # 年龄归一化 (0-1)
person{N}_emotion         # 表情 (0-6)
person{N}_emotion_conf    # 表情置信度
person{N}_body_type       # 体型 (0-3)
person{N}_pos_x           # 边界框中心X
person{N}_pos_y           # 边界框中心Y
person{N}_width           # 边界框宽度
person{N}_height          # 边界框高度
```

---

## 🔧 摄像头配置

在 `main_3cameras_single.py` 的 `main()` 函数中修改：

```python
camera_configs = [
    {'device': 0, 'camera_id': 1, 'port': 7000},  # 摄像头1
    {'device': 1, 'camera_id': 2, 'port': 7001},  # 摄像头2
    {'device': 2, 'camera_id': 3, 'port': 7002}, # 摄像头3
]
```

如果只有1个或2个摄像头，注释掉不需要的配置即可。

---

## 🎨 视觉特效说明

### 黑白格子效果
- 按 `e` 键开启/关闭
- 剪影内：白色格子
- 背景：黑色格子
- 使用 YOLOv8-Seg 精确分割人体轮廓

### 深度渐变效果
- 需要先开启视觉特效（按 `e`）
- 使用 MiDaS 深度估计模型
- 在剪影上显示深度信息（近处深灰，远处黑色）

---

## 🔧 常见问题

### ❓ 摄像头无法打开
```bash
# 检查摄像头
python -c "import cv2; cap=cv2.VideoCapture(0); print('OK' if cap.read()[0] else 'FAIL'); cap.release()"
```

**解决方案**：
1. 拔掉所有摄像头，等5秒，重新插入
2. 使用不同的 USB 端口（USB 3.0）
3. 检查设备管理器是否有驱动问题

### ❓ FPS 太低
1. 降低处理频率（修改 `process_every_n_frames`）
2. 降低摄像头分辨率（已在代码中设置为 640x480）
3. 关闭视觉特效（按 `e`）

### ❓ TouchDesigner 收不到数据
1. 检查 UDP 端口是否正确（7000, 7001, 7002）
2. 检查防火墙设置
3. 查看 TouchDesigner 的 UDP In DAT 是否配置正确

---

## 📝 技术栈

- **YOLOv8-Pose**: 人体姿态检测
- **YOLOv8-Seg**: 精确人体分割
- **InsightFace**: 人脸分析和年龄估计
- **FER**: 表情识别
- **MiDaS**: 单目深度估计
- **TouchDesigner**: 实时可视化

---

## 📄 许可证

MIT License

---

## 🙏 致谢

- Ultralytics (YOLOv8)
- InsightFace
- FER
- MiDaS
