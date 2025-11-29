# 3个摄像头快速启动指南

## ✅ 已完成的修改

`main_with_all_attributes.py` 现在支持：
- 选择摄像头设备（0, 1, 2）
- 设置 Camera ID（1, 2, 3）
- 多摄像头数据会发送到不同路径

---

## 🚀 启动3个摄像头

### 方式1：自动启动（推荐）

双击运行：
```
start_all_cameras.bat
```

会自动打开3个窗口，分别运行3个摄像头。

### 方式2：手动启动

#### Terminal 1 - 摄像头1
双击 `start_camera1.bat`
或命令行：
```bash
python main_with_all_attributes.py 0 1
```

#### Terminal 2 - 摄像头2
双击 `start_camera2.bat`
或命令行：
```bash
python main_with_all_attributes.py 1 2
```

#### Terminal 3 - 摄像头3
双击 `start_camera3.bat`
或命令行：
```bash
python main_with_all_attributes.py 2 3
```

### 方式3：自定义参数

完整命令格式：
```bash
python main_with_all_attributes.py [camera_index] [camera_id] [td_host] [td_port]
```

示例：
```bash
# 摄像头1，发送到不同IP
python main_with_all_attributes.py 0 1 192.168.1.100 7000

# 摄像头2，使用不同端口
python main_with_all_attributes.py 1 2 192.168.0.89 7001
```

---

## 📡 TouchDesigner 配置

### 设置1：创建 OSC In CHOP

1. 在 TouchDesigner 中按 `TAB`
2. 输入 `oscin` 选择 `OSC In CHOP`
3. 参数设置：
   ```
   Network:
     - Port: 7000
     - Network Address: 0.0.0.0
   
   Channels:
     - Auto Create Channels: ON ✓
     - Delete Unused Channels: OFF ✗  (重要！)
     - Time Slice: OFF ✗
   ```

### 设置2：查看接收到的数据

你会看到这些通道：

```
摄像头1的数据：
  camera1_person_count
  camera1_person_1_age
  camera1_person_1_gender
  camera1_person_1_emotion
  camera1_person_2_age     ← 如果有第2个人
  
摄像头2的数据：
  camera2_person_count
  camera2_person_1_age
  camera2_person_1_gender
  
摄像头3的数据：
  camera3_person_count
  camera3_person_1_age
  camera3_person_1_gender
```

### 设置3：分离不同摄像头的数据

#### 方法A：使用 Select CHOP

创建3个 Select CHOP：

**Select CHOP 1**（摄像头1）:
```
Pattern: camera1_*
```

**Select CHOP 2**（摄像头2）:
```
Pattern: camera2_*
```

**Select CHOP 3**（摄像头3）:
```
Pattern: camera3_*
```

#### 方法B：筛选特定数据

```
所有摄像头的所有人的年龄:
  Pattern: camera*_person_*_age

摄像头1的所有人的情绪:
  Pattern: camera1_person_*_emotion

所有摄像头的第1个人:
  Pattern: camera*_person_1_*
```

---

## 🧪 测试步骤

### 步骤1：测试单个摄像头

```bash
python main_with_all_attributes.py 0 1
```

检查：
- 摄像头画面是否正常
- 控制台是否显示 "Camera ID: 1"
- TouchDesigner 是否收到 `camera1_person_count`

### 步骤2：测试第二个摄像头

在另一个终端：
```bash
python main_with_all_attributes.py 1 2
```

检查 TouchDesigner 是否同时显示：
- `camera1_person_count`
- `camera2_person_count`

### 步骤3：启动第三个摄像头

```bash
python main_with_all_attributes.py 2 3
```

检查 TouchDesigner 是否显示所有3个摄像头的数据。

### 步骤4：测试多人检测

让每个摄像头看到多个人，检查 TouchDesigner 是否显示：
```
camera1_person_1_age
camera1_person_2_age  ← 摄像头1的第2个人
camera2_person_1_age
camera2_person_2_age  ← 摄像头2的第2个人
```

---

## 🎛️ 命令说明

### 参数1: camera_index（摄像头设备索引）
- `0` = 第一个摄像头（通常是笔记本内置摄像头）
- `1` = 第二个摄像头（第一个外接摄像头）
- `2` = 第三个摄像头（第二个外接摄像头）

如何找到正确的索引？运行：
```bash
# 测试摄像头0
python main_with_all_attributes.py 0

# 测试摄像头1
python main_with_all_attributes.py 1

# 测试摄像头2
python main_with_all_attributes.py 2
```

### 参数2: camera_id（摄像头ID）
- 用于在 TouchDesigner 中区分不同摄像头
- 建议：`1`, `2`, `3`
- 会生成路径：`/camera1/...`, `/camera2/...`, `/camera3/...`

### 参数3: td_host（TouchDesigner IP）
- 默认：`192.168.0.89`
- 本机：`127.0.0.1`

### 参数4: td_port（TouchDesigner 端口）
- 默认：`7000`
- 可以为每个摄像头设置不同端口：7000, 7001, 7002

---

## 🛠️ 故障排除

### 问题1：某个摄像头无法打开
**错误**：黑屏或 "Failed to open camera"

**解决**：
1. 检查摄像头是否连接
2. 尝试不同的 camera_index（0, 1, 2）
3. 关闭其他使用摄像头的程序（如 Zoom, Skype）

### 问题2：TouchDesigner 只收到一个摄像头的数据
**检查**：
1. 确认所有摄像头程序都在运行
2. 检查防火墙是否阻止
3. 确认 TD_HOST IP 地址正确

### 问题3：帧率太低
**优化**：
1. 降低分辨率（改为 640x480）
2. 减少检测频率（修改 `process_every_n_frames`）
3. 使用更强的 GPU

### 问题4：摄像头画面卡顿
**原因**：3个摄像头同时运行，CPU/GPU 负载高

**解决**：
- 只运行需要的摄像头
- 升级硬件
- 使用更轻量的模型

---

## 📊 性能参考

| 配置 | 1个摄像头 | 3个摄像头 |
|------|----------|----------|
| GPU: RTX 3060 | 30-40 FPS | 15-20 FPS |
| GPU: RTX 4070 | 50-60 FPS | 25-35 FPS |
| CPU Only | 5-10 FPS | 2-5 FPS |

---

## 下一步

1. ✅ 双击 `start_camera1.bat` 测试摄像头1
2. ✅ 检查 TouchDesigner 是否收到 `camera1_person_*` 数据
3. ✅ 双击 `start_camera2.bat` 启动摄像头2
4. ✅ 检查是否同时看到 `camera1_*` 和 `camera2_*`
5. ✅ 双击 `start_camera3.bat` 启动摄像头3
6. ✅ 或直接双击 `start_all_cameras.bat` 一次启动全部

准备好了吗？试试双击 `start_camera1.bat`！🎥








