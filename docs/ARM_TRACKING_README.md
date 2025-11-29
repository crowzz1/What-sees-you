# 🤖 4轴机械臂人体追踪系统

## 📋 项目简介

一个基于计算机视觉的机械臂追踪系统，能够：
- 📷 使用摄像头实时识别人体位置
- 🎯 将2D图像坐标映射到机械臂3D空间
- 🤖 控制4轴机械臂实时跟随人体移动
- 🔧 平滑滤波避免抖动

---

## 🏗️ 系统架构

```
┌─────────────┐      ┌──────────────┐      ┌──────────┐
│  摄像头      │─────>│ Python程序   │─────>│  ESP32   │
│  (USB相机)  │      │ 人体识别+映射 │ 串口 │  控制器  │
└─────────────┘      └──────────────┘      └──────────┘
                                                  │
                                                  ▼
                                         ┌──────────────┐
                                         │ 4轴机械臂    │
                                         │ SERVO42C ×4  │
                                         └──────────────┘
```

---

## 📁 文件说明

| 文件 | 说明 |
|------|------|
| `main_arm_tracking.py` | **主程序** - 启动完整追踪系统 |
| `arm_tracker.py` | 追踪控制模块（坐标映射+平滑滤波） |
| `arm_controller.py` | ESP32通信模块（串口命令） |
| `person_analyzer.py` | 人体识别模块（YOLOv8） |
| `esp32_servo42c_control/robotic_arm_4axis/` | ESP32固件 |

---

## 🔧 硬件要求

### 必需硬件

1. **ESP32 开发板** ×1
2. **SERVO42C 步进电机** ×4（带1:8减速器）
3. **USB摄像头** ×1
4. **24V电源** ×1（供电给电机）
5. **USB数据线** ×1（连接ESP32到电脑）

### 接线说明

```
ESP32 接线:
├─ GPIO16 (RX2) ──> 所有电机的 TX (并联)
├─ GPIO17 (TX2) ──> 所有电机的 RX (并联)
└─ GND          ──> 所有电机的 GND (共地)

电机地址:
├─ 0xE0: 基座（Motor 1）
├─ 0xE1: 大臂（Motor 2）
├─ 0xE2: 小臂（Motor 3）
└─ 0xE3: 手腕（Motor 4）
```

---

## 💻 软件要求

### Python 环境

```bash
# Python 3.8+ (推荐 3.10)

# 安装依赖
pip install opencv-python
pip install numpy
pip install torch torchvision  # PyTorch
pip install ultralytics         # YOLOv8
pip install pyserial           # 串口通信
pip install scikit-learn
```

### ESP32 固件

使用 Arduino IDE 上传 `robotic_arm_4axis.ino`

---

## 🚀 快速开始

### 步骤1: 上传ESP32固件

1. 打开 Arduino IDE
2. 打开 `esp32_servo42c_control/robotic_arm_4axis/robotic_arm_4axis.ino`
3. 选择板子: **ESP32 Dev Module**
4. 选择端口 (例如 COM3)
5. 上传

### 步骤2: 测试机械臂连接

```bash
# 测试ESP32串口通信
python arm_controller.py
```

应该看到：
```
✓ 已连接到 ESP32
使能所有电机...
测试基座旋转...
```

### 步骤3: 测试摄像头识别

```bash
# 测试人体识别（不连接机械臂）
python main.py
```

应该看到摄像头画面和人体识别框。

### 步骤4: 运行完整追踪系统

```bash
# 运行机械臂追踪
python main_arm_tracking.py
```

---

## 🎮 使用说明

### 启动后的控制键

| 按键 | 功能 |
|------|------|
| **t** | 开始/停止追踪 |
| **e** | 使能电机（通电锁定） |
| **d** | 失能电机（断电可转） |
| **s** | 保存当前截图 |
| **q** | 退出程序 |

### 追踪模式

系统会自动：
1. 检测画面中的人
2. 选择**最近的人**（边界框最大）
3. 提取人体中心坐标
4. 映射到机械臂角度
5. 控制机械臂移动

---

## 📊 坐标映射说明

### 摄像头坐标 → 机械臂角度

```
画面中心 (320, 240)
     ↓
归一化 (-1~1, -1~1)
     ↓
映射到角度:
  X方向 → 基座旋转 (-90° ~ 90°)
  Y方向 → 大臂抬升 (0° ~ 90°)
```

### 示例

| 人的位置 | 归一化坐标 | 基座角度 | 大臂角度 |
|---------|-----------|---------|---------|
| 画面左侧 | (-0.8, 0) | -72° | 45° |
| 画面中心 | (0, 0) | 0° | 45° |
| 画面右侧 | (0.8, 0) | +72° | 45° |
| 画面上方 | (0, -0.8) | 0° | 81° |
| 画面下方 | (0, 0.8) | 0° | 9° |

---

## ⚙️ 配置参数

### 修改串口端口

编辑 `main_arm_tracking.py`:

```python
ARM_PORT = 'COM3'  # Windows
# 或
ARM_PORT = '/dev/ttyUSB0'  # Linux
```

### 调整追踪灵敏度

编辑 `arm_tracker.py`:

```python
# 平滑滤波系数 (0-1)
SmoothFilter(alpha=0.3)
# 0.1 = 非常平滑，响应慢
# 0.5 = 平衡
# 0.9 = 响应快，可能抖动

# 最小移动阈值（度）
self.min_move_threshold = 2.0
```

### 调整角度范围

编辑 `arm_tracker.py`:

```python
self.base_angle_range = (-90, 90)  # 基座左右范围
self.arm_angle_range = (0, 90)     # 大臂上下范围
```

### 调整速度

编辑 `arm_tracker.py`:

```python
self.move_speed = 80  # 1-127
# 考虑1:8减速器，实际输出速度 = 80÷8 = 10
```

---

## 🐛 故障排除

### 问题1: 无法连接到ESP32

**症状：** `✗ 连接失败: could not open port`

**解决：**
1. 检查ESP32是否已连接USB
2. 确认端口号（设备管理器 / `ls /dev/tty*`）
3. 关闭Arduino串口监视器
4. 检查驱动（CP2102/CH340）

### 问题2: 摄像头无法打开

**症状：** `✗ 无法打开摄像头`

**解决：**
1. 检查摄像头是否连接
2. 尝试修改 `CAMERA_ID`（0, 1, 2...）
3. 关闭其他占用摄像头的程序

### 问题3: 机械臂不动

**症状：** 识别正常，但机械臂不响应

**解决：**
1. 检查电机是否使能（按 `e` 键）
2. 检查24V电源是否接通
3. 打开Arduino串口监视器，查看ESP32是否收到命令
4. 检查电机地址是否正确

### 问题4: 机械臂抖动严重

**症状：** 机械臂频繁小幅度移动

**解决：**
1. 增大平滑系数 `alpha`（例如 0.2）
2. 增大最小移动阈值 `min_move_threshold`（例如 5.0）
3. 降低处理帧率（`process_every_n_frames`）

### 问题5: 追踪延迟

**症状：** 机械臂反应慢

**解决：**
1. 减小平滑系数 `alpha`（例如 0.5）
2. 减小最小移动阈值 `min_move_threshold`（例如 1.0）
3. 提高移动速度 `move_speed`（注意：考虑减速器）

---

## 📈 性能优化

### 提高帧率

1. **降低模型处理频率**
   ```python
   self.process_every_n_frames = 2  # 每2帧处理一次
   ```

2. **使用GPU加速**
   ```bash
   # 安装CUDA版本的PyTorch
   pip install torch torchvision --index-url https://download.pytorch.org/whl/cu118
   ```

3. **降低摄像头分辨率**
   ```python
   self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 320)  # 从640降到320
   self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 240)
   ```

### 提高追踪精度

1. **使用关键点代替边界框中心**
   - 修改 `get_person_center()` 使用鼻子/颈部关键点
   
2. **追踪特定部位**
   ```python
   # 追踪头部
   keypoints = person['keypoints']
   nose = keypoints[0]  # 鼻子坐标
   ```

---

## 🔬 进阶功能

### 功能1: 深度估计（Z轴）

添加深度信息，控制小臂前后移动：

```python
# 根据边界框大小估计距离
bbox_area = (x2 - x1) * (y2 - y1)
distance_ratio = bbox_area / (640 * 480)  # 归一化
arm2_angle = distance_ratio * 90  # 映射到0-90度
```

### 功能2: 手势识别

结合手部关键点，实现手势控制：

```python
# 检测举手 → 停止追踪
left_wrist_y = keypoints[9][1]
left_shoulder_y = keypoints[5][1]
if left_wrist_y < left_shoulder_y:
    tracker.stop_tracking()
```

### 功能3: 多人选择

UI界面选择追踪目标：

```python
# 点击画面选择人
def mouse_callback(event, x, y, flags, param):
    if event == cv2.EVENT_LBUTTONDOWN:
        # 查找点击位置的人
        for person in results:
            x1, y1, x2, y2 = person['bbox']
            if x1 < x < x2 and y1 < y < y2:
                tracker.target_person_id = person['person_id']
```

---

## 📝 API 参考

### ArmController

```python
arm = ArmController(port='COM3', baudrate=115200)

# 使能/失能
arm.enable_all()
arm.disable_all()
arm.stop_all()

# 移动控制
arm.move_to_angles(
    base=45,    # 基座角度
    arm1=30,    # 大臂角度
    arm2=0,     # 小臂角度
    wrist=0,    # 手腕角度
    speed=80    # 速度 (1-127)
)

# 读取位置
arm.read_position()

# 关闭
arm.close()
```

### ArmTracker

```python
tracker = ArmTracker(
    arm_port='COM3',
    camera_id=0,
    frame_width=640,
    frame_height=480
)

# 追踪控制
tracker.start_tracking()
tracker.stop_tracking()

# 更新追踪（每帧调用）
tracking_data = tracker.update(results)

# 关闭
tracker.close()
```

---

## 📜 许可证

MIT License

---

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

---

## 📞 联系方式

如有问题，请创建 Issue。

---

**祝你使用愉快！** 🎉







