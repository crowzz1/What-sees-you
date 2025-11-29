# 🚀 快速入门指南

## ⚡ 5分钟开始使用

###  步骤1: 检查硬件连接

```
✓ ESP32 已通过USB连接到电脑
✓ 4个SERVO42C电机已连接到ESP32
✓ 电机已接24V电源
✓ USB摄像头已连接
```

### 步骤2: 上传ESP32固件

1. 打开 Arduino IDE
2. 打开 `esp32_servo42c_control/robotic_arm_4axis/robotic_arm_4axis.ino`
3. 选择板子: **ESP32 Dev Module**
4. 选择端口 (例如 COM3)
5. 点击"上传"

### 步骤3: 配置端口

编辑 `config.py`:

```python
# 修改为你的ESP32端口
ARM_PORT = 'COM3'  # Windows
# 或
ARM_PORT = '/dev/ttyUSB0'  # Linux/Mac
```

### 步骤4: 安装Python依赖

```bash
pip install opencv-python numpy torch torchvision ultralytics pyserial scikit-learn
```

### 步骤5: 测试系统

```bash
python test_system.py
```

按照提示测试各个组件。

### 步骤6: 运行追踪系统

**Windows:**
```bash
双击 start_tracking.bat
选择 "1" (完整追踪系统)
```

**或直接运行Python:**
```bash
python main_arm_tracking.py
```

---

## 🎮 控制键说明

| 按键 | 功能 |
|------|------|
| `t` | 开始/停止追踪 |
| `e` | 使能电机（通电锁定） |
| `d` | 失能电机（断电可转） |
| `s` | 保存截图 |
| `q` | 退出 |

---

## 🎯 使用技巧

### 1. 初次使用

1. 运行程序后，先按 `e` 使能电机
2. 站在摄像头前，慢慢左右移动
3. 观察机械臂是否跟随

### 2. 调整灵敏度

如果机械臂抖动：
- 编辑 `config.py`
- 增大 `SMOOTH_ALPHA` (例如 0.2)
- 增大 `MIN_MOVE_THRESHOLD` (例如 5.0)

如果机械臂反应慢：
- 减小 `SMOOTH_ALPHA` (例如 0.5)
- 减小 `MIN_MOVE_THRESHOLD` (例如 1.0)

### 3. 调整速度

编辑 `config.py`:
```python
ARM_SPEED = 80  # 1-127

# 注意: 有减速器的实际速度 = ARM_SPEED ÷ 减速比
# 例如: 80 ÷ 8 = 10 (实际输出速度)
```

### 4. 调整追踪范围

编辑 `config.py`:
```python
# 基座左右旋转范围
BASE_ANGLE_MIN = -90  # 最左
BASE_ANGLE_MAX = 90   # 最右

# 大臂上下运动范围
ARM_ANGLE_MIN = 0     # 最低
ARM_ANGLE_MAX = 90    # 最高
```

---

## 🐛 常见问题

### ❌ 无法连接ESP32

**解决方法:**
1. 检查USB线是否连接
2. 打开设备管理器，查看端口号
3. 关闭Arduino串口监视器
4. 修改 `config.py` 中的 `ARM_PORT`

### ❌ 摄像头无法打开

**解决方法:**
1. 检查摄像头是否连接
2. 修改 `config.py` 中的 `CAMERA_ID` (尝试 0, 1, 2...)
3. 关闭其他占用摄像头的程序

### ❌ 机械臂不动

**解决方法:**
1. 按 `e` 键使能电机
2. 检查24V电源是否接通
3. 打开Arduino串口监视器，查看是否收到命令
4. 检查电机地址是否正确 (0xE0-0xE3)

### ❌ 识别不到人

**解决方法:**
1. 确保光线充足
2. 站在摄像头正前方
3. 保持1-3米距离
4. 降低 `PROCESS_EVERY_N_FRAMES` 提高识别频率

---

## 📊 系统工作流程

```
1. 摄像头捕获画面
      ↓
2. YOLOv8 识别人体
      ↓
3. 提取人体中心坐标 (x, y)
      ↓
4. 归一化坐标到 [-1, 1]
      ↓
5. 应用平滑滤波
      ↓
6. 映射到机械臂角度
   - X坐标 → 基座旋转
   - Y坐标 → 大臂抬升
      ↓
7. 串口发送命令到ESP32
      ↓
8. ESP32控制电机移动
      ↓
9. 机械臂跟随人移动
```

---

## 🎨 进阶功能

### 1. 只追踪上半身

修改 `arm_tracker.py` 的 `get_person_center()`:

```python
def get_person_center(self, person):
    """使用鼻子关键点代替边界框中心"""
    keypoints = person['keypoints']
    nose = keypoints[0]  # 鼻子
    return nose[0], nose[1]
```

### 2. 添加Z轴（深度）

根据边界框大小估计距离：

```python
bbox = person['bbox']
area = (bbox[2] - bbox[0]) * (bbox[3] - bbox[1])
distance_ratio = area / (640 * 480)
arm2_angle = distance_ratio * 90  # 映射到小臂角度
```

### 3. 手势控制

检测举手动作停止追踪：

```python
keypoints = person['keypoints']
wrist_y = keypoints[9][1]   # 左手腕
shoulder_y = keypoints[5][1] # 左肩膀

if wrist_y < shoulder_y:
    tracker.stop_tracking()  # 举手 = 停止
```

---

## 📞 需要帮助？

1. 查看 `ARM_TRACKING_README.md` 完整文档
2. 运行 `python test_system.py` 诊断问题
3. 检查 `config.py` 配置是否正确

---

**祝你玩得开心！** 🎉







