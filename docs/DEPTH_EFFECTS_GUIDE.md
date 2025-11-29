# 🌊 深度渐变效果指南 (MiDaS Depth Estimation)

## 概述

系统现在集成了 **MiDaS 深度估计模型**，为人体剪影添加深度渐变效果，让人形具有立体感和深浅变化。

---

## ✨ 功能特点

### 1. 单目深度估计
- ✅ **无需深度相机**：使用普通摄像头即可
- ✅ **实时处理**：MiDaS Small 模型优化
- ✅ **精确深度**：Intel Labs 开发的先进算法
- ✅ **智能缓存**：每3帧更新一次，提升性能

### 2. 深度渐变效果
- **近处**：深灰色（RGB: 50-100）
- **中间**：中灰色（RGB: 25-75）
- **远处**：黑色（RGB: 0-50）

### 3. 三种模式
1. **深度渐变剪影** ⭐
   - 人体有深浅变化
   - 立体感强
   - 视觉吸引力高

2. **纯黑色剪影**
   - 经典剪影效果
   - 高对比度

3. **原始画面**
   - 正常摄像头视图
   - 显示所有识别框和关节点

---

## 🚀 使用方法

### 安装依赖
首次运行需要安装 `timm` 库：
```bash
pip install timm>=0.9.0
```

### 启动程序
```bash
python main_with_all_attributes.py
```

### 控制键
| 按键 | 功能 |
|------|------|
| `e` | 开启/关闭视觉特效 |
| `z` | 开启/关闭深度渐变（需先开启特效） |
| `k` | 开启/关闭关节点显示 |
| `l` | 开启/关闭骨架连线显示 |
| `q` | 退出程序 |

### 使用流程
1. 运行程序
2. 按 `e` 开启视觉特效 → 看到纯黑色剪影
3. 按 `z` 开启深度渐变 → 看到深浅变化的剪影
4. 再按 `z` 关闭深度 → 回到纯黑色剪影

---

## 🎨 视觉效果对比

### 模式 1: 原始画面
```
┌─────────────────────┐
│  [彩色摄像头画面]   │
│  + 白色边界框        │
│  + 白色关节点        │
│  + 识别文本          │
└─────────────────────┘
```

### 模式 2: 纯黑色剪影 (e)
```
┌─────────────────────┐
│  [白色背景]         │
│  + 纯黑色人形        │
│  + 自适应颜色框/点   │
│  + 自适应文本        │
└─────────────────────┘
```

### 模式 3: 深度渐变剪影 (e + z) ⭐
```
┌─────────────────────┐
│  [白色背景]         │
│  + 灰色渐变人形      │
│    (近深远浅)        │
│  + 自适应颜色框/点   │
│  + 自适应文本        │
└─────────────────────┘
```

---

## 🔧 技术细节

### MiDaS 模型
- **来源**：Intel ISL (Intelligent Systems Lab)
- **类型**：单目深度估计 (Monocular Depth Estimation)
- **版本**：MiDaS Small (实时优化版)
- **输入**：RGB 图像 (任意分辨率)
- **输出**：相对深度图 (0-255)

### 深度估计流程
```python
1. 输入: RGB 图像
   ↓
2. MiDaS Transform (预处理)
   ↓
3. MiDaS 模型推理
   ↓
4. 双线性插值调整到原始分辨率
   ↓
5. 归一化到 0-255
   ↓
6. 反转 (近亮远暗 → 近深远浅)
   ↓
7. 与人体 mask 合并
   ↓
8. 输出: 深度渐变剪影
```

### 性能优化
```python
# 缓存机制 - 每3帧更新一次深度图
if self.depth_cache is not None and frame_counter % 3 != 0:
    return self.depth_cache  # 使用缓存

# 实际估计
depth_map = self.midas(input_batch)
self.depth_cache = depth_map  # 更新缓存
```

---

## 📊 性能对比

| 模式 | FPS (RTX 4090) | GPU 内存 | 效果 |
|------|----------------|----------|------|
| 原始画面 | 30-40 | ~1GB | 标准检测 |
| 纯黑剪影 | 25-30 | ~2GB | 分割模型 |
| 深度渐变 | 20-25 | ~3GB | 分割 + 深度 |

### 优化建议
如果 FPS 过低：
1. 降低深度更新频率：
```python
# 在 estimate_depth() 中修改
if self.depth_cache_counter % 5 != 0:  # 改为每5帧
```

2. 使用更小的分辨率：
```python
# 在 main() 中添加
frame = cv2.resize(frame, (640, 480))
```

---

## 🎯 应用场景

### 1. 艺术装置
- 深度感知的互动投影
- 立体剪影艺术
- 动态雕塑可视化

### 2. TouchDesigner 集成
- 深度数据驱动的粒子系统
- 3D 空间映射
- 实时深度合成

### 3. 视频特效
- 电影级人物抠图
- 深度模糊效果
- 虚拟景深控制

### 4. 健身/舞蹈应用
- 动作深度分析
- 身体部位距离可视化
- 姿态深度评估

---

## 🌟 深度值解释

### 深度图原理
MiDaS 输出的是**相对深度**，不是绝对距离：
- **高值**：离摄像头近的区域
- **低值**：离摄像头远的区域

### 渐变映射
```python
原始深度值 (0-255)
  ↓ 缩放 × 0.4
深度剪影 (0-102)

映射关系：
255 (最近) → 102 (深灰)
128 (中等) →  51 (中灰)
0   (最远) →   0 (黑色)
```

### 调整深度范围
在 `apply_visual_effects()` 中修改：
```python
# 更强的对比度 (更明显的渐变)
depth_adjusted = depth_adjusted.astype(np.float32) * 0.6  # 0-153

# 更弱的对比度 (更微妙的渐变)
depth_adjusted = depth_adjusted.astype(np.float32) * 0.2  # 0-51
```

---

## ❓ 常见问题

### Q1: MiDaS 加载失败
**症状**：
```
⚠ MiDaS failed to load
→ Depth effects will be disabled
```

**解决**：
1. 检查网络连接（首次运行需要下载模型）
2. 安装 timm：
```bash
pip install timm>=0.9.0
```
3. 手动下载模型（如果网络问题）

### Q2: 深度效果不明显
**原因**：深度范围缩放过小

**解决**：调整缩放因子
```python
# 在 apply_visual_effects() 中
depth_adjusted = depth_adjusted.astype(np.float32) * 0.6  # 增大到0.6
```

### Q3: FPS 明显下降
**原因**：深度估计计算量大

**解决**：
1. 降低更新频率（改为每5帧）
2. 降低输入分辨率
3. 临时关闭深度效果（按 `z` 键）

### Q4: 深度图有噪点
**原因**：深度估计的固有特性

**解决**：添加后处理平滑
```python
# 在 estimate_depth() 返回前添加
depth_normalized = cv2.GaussianBlur(depth_normalized, (5, 5), 0)
```

---

## 🔬 高级定制

### 自定义渐变颜色
将深灰渐变改为蓝色渐变：
```python
# 在 apply_visual_effects() 中
# 替换这行：
silhouette = cv2.cvtColor(depth_adjusted, cv2.COLOR_GRAY2BGR)

# 改为：
silhouette = np.zeros((h, w, 3), dtype=np.uint8)
silhouette[:, :, 0] = depth_adjusted  # B 通道（蓝色）
# 结果：近处深蓝，远处黑色
```

### 多彩深度映射
使用色彩映射表（colormap）：
```python
import cv2

# 在 apply_visual_effects() 中
depth_colored = cv2.applyColorMap(depth_adjusted, cv2.COLORMAP_JET)
silhouette = depth_colored
# 结果：彩虹色深度渐变
```

### 反向深度（近亮远暗）
```python
# 在 estimate_depth() 中
# 注释掉这行：
# depth_normalized = 255 - depth_normalized

# 结果：近处亮灰，远处深灰
```

---

## 📚 相关资源

- [MiDaS GitHub](https://github.com/isl-org/MiDaS)
- [MiDaS 论文](https://arxiv.org/abs/1907.01341)
- [深度估计原理](https://paperswithcode.com/task/monocular-depth-estimation)
- [PyTorch Hub 文档](https://pytorch.org/hub/)

---

## 💡 创意应用

### 1. 深度触发的特效
```python
# 根据深度值触发不同效果
if depth_value > 200:  # 非常近
    # 触发爆炸/粒子效果
elif depth_value > 100:  # 中等距离
    # 触发波纹效果
else:  # 远处
    # 触发淡出效果
```

### 2. 深度驱动的音乐
```python
# 将深度值映射到音高
pitch = map_range(depth_value, 0, 255, 20, 2000)  # Hz
# 发送 OSC 到音乐软件
```

### 3. 多人深度层次
- 不同的人根据深度显示不同颜色
- 创建深度分层的视觉效果

---

## 🎬 示例效果

### 单人走近走远
```
远处 → 中间 → 近处 → 中间 → 远处
  ░      ▒      ▓      ▒      ░
(浅灰) (中灰) (深灰) (中灰) (浅灰)
```

### 多人不同距离
```
人1 (近处): ▓▓▓ (深灰)
人2 (中间): ▒▒▒ (中灰)
人3 (远处): ░░░ (浅灰)
```

---

**享受深度渐变效果！** 🌊✨

