# 赛博朋克故障艺术效果指南

## 🎨 效果概述

这是一个基于YOLOv8-Pose的实时赛博朋克/故障艺术(Glitch Art)视觉效果系统。它可以：

1. ✅ **实时检测人体关键点**（使用YOLOv8-Pose，无需MediaPipe）
2. ✅ **提取身体部位**（眼睛、手、脚等）
3. ✅ **应用故障艺术风格**（高对比度、噪点、RGB偏移）
4. ✅ **重新排版布局**（在黑色背景上分散显示）
5. ✅ **赛博朋克UI**（连接线、标签、闪烁效果）

## 🎬 视觉效果

```
┌─────────────────────────────────────────────┐
│ CORRUPTED_VISION // V4.2                   │
│ SIGNAL INTEGRITY: CRITICAL                 │
├─────────────────────────────────────────────┤
│  [L_EYE]              [CORE_DATA]  [R_EYE] │
│                                             │
│          \            /        \            │
│           \          /          \           │
│            \        /            \          │
│  [L_HAND]   [CENTER]              [R_HAND] │
│                                             │
│  [L_FOOT]                       [R_FOOT]   │
└─────────────────────────────────────────────┘
```

### 特点：
- 🎭 **黑白高对比度**（二值化效果）
- 🌈 **RGB通道偏移**（故障效果）
- ⚡ **扫描线**（老式监控感觉）
- 🔌 **连接线**（数据流可视化）
- 💜 **紫色/青色边框**（赛博朋克风格）
- 📺 **噪点干扰**（信号损坏感）

## 🚀 快速开始

### 1. 运行测试程序

```bash
python test_glitch_effect.py
```

### 2. 控制键

```
'q' - 退出
's' - 保存截图
```

## 📦 文件说明

### `glitch_art_effect.py` - 核心效果生成器

**主要类：** `GlitchArtEffect`

**关键方法：**
- `extract_roi()` - 提取并风格化身体部位
- `create_glitch_frame()` - 生成完整的故障艺术帧
- `draw_background_ui()` - 绘制赛博朋克UI元素

### `test_glitch_effect.py` - 独立测试程序

完整的测试程序，包含：
- YOLOv8-Pose模型加载
- 摄像头捕获
- 实时效果生成
- FPS显示

## 🎯 技术实现

### 1. 关键点检测（YOLOv8-Pose）

使用COCO 17关键点格式：

```python
关键点索引：
0: Nose (鼻子) → CORE_DATA (中心大图)
1: Left Eye → L_EYE (左眼)
2: Right Eye → R_EYE (右眼)
9: Left Wrist → L_HAND (左手)
10: Right Wrist → R_HAND (右手)
15: Left Ankle → L_FOOT (左脚)
16: Right Ankle → R_FOOT (右脚)
```

### 2. ROI提取与风格化

```python
def extract_roi(frame, center_x, center_y, size):
    # 1. 裁剪区域
    crop = frame[y1:y2, x1:x2]
    
    # 2. 转灰度
    gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
    
    # 3. 二值化（高对比度）
    _, thresh = cv2.threshold(gray, 120, 255, cv2.THRESH_BINARY)
    
    # 4. 添加噪点
    noise = np.random.randint(0, 50, thresh.shape)
    
    # 5. RGB通道偏移（故障效果）
    styled[:, offset:, 2] = styled_shifted[:, :-offset, 2]
    
    # 6. 边框和标签
    cv2.rectangle(styled, (0, 0), (size, size), color, 2)
```

### 3. 布局系统

部位在画布上的位置：

```python
布局示例（1920x1080画布）：
L_EYE:      (100, 150)     - 左上角
R_EYE:      (1640, 150)    - 右上角
CORE_DATA:  (820, 400)     - 中心
L_HAND:     (150, 710)     - 左下
R_HAND:     (1550, 710)    - 右下
L_FOOT:     (400, 830)     - 底部左
R_FOOT:     (1360, 830)    - 底部右
```

### 4. 效果参数

可以在 `glitch_art_effect.py` 中调整：

```python
class GlitchArtEffect:
    # 配色
    color_purple = (255, 0, 255)  # 紫色
    color_cyan = (255, 255, 0)    # 青色
    
    # 二值化阈值（影响黑白对比度）
    threshold = 120  # 在extract_roi中
    
    # 噪点概率
    noise_probability = 0.3  # 30%
    
    # RGB偏移概率
    glitch_probability = 0.2  # 20%
```

## 🎨 自定义效果

### 调整对比度

在 `extract_roi()` 方法中修改阈值：

```python
# 更高对比度（更极端的黑白）
_, thresh = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY)

# 更柔和的对比度
_, thresh = cv2.threshold(gray, 80, 255, cv2.THRESH_BINARY)
```

### 调整颜色风格

```python
# 绿色Matrix风格
border_color = (0, 255, 0)

# 红色警告风格
border_color = (0, 0, 255)

# 随机霓虹色
colors = [(255, 0, 255), (255, 255, 0), (0, 255, 255)]
border_color = random.choice(colors)
```

### 调整布局

修改 `create_glitch_frame()` 中的位置：

```python
# 让所有部位更集中
parts_to_extract.append({
    'center': (int(keypoints[1][0]), int(keypoints[1][1])),
    'size': 180,
    'label': 'L_EYE',
    'position': (400, 300)  # 更靠近中心
})
```

### 添加更多部位

可以提取其他关键点：

```python
# 添加肩膀
if keypoints[5][2] > 0.3:  # 左肩
    parts_to_extract.append({
        'center': (int(keypoints[5][0]), int(keypoints[5][1])),
        'size': 200,
        'label': 'L_SHOULDER',
        'position': (300, 500)
    })

# 添加膝盖
if keypoints[13][2] > 0.3:  # 左膝
    parts_to_extract.append({
        'center': (int(keypoints[13][0]), int(keypoints[13][1])),
        'size': 160,
        'label': 'L_KNEE',
        'position': (250, 700)
    })
```

## ⚡ 性能优化

### 当前性能

- **FPS**: 20-25（RTX 4090）
- **延迟**: 40-50ms/帧
- **检测**: YOLOv8n-pose（最快的模型）

### 优化建议

1. **关闭不需要的功能**
```python
analyzer.face_enabled = False      # 不需要人脸
analyzer.emotion_enabled = False   # 不需要情绪
analyzer.segmentation_enabled = False  # 不需要分割
```

2. **减少提取部位数量**
```python
# 只提取眼睛和手
parts = ['L_EYE', 'R_EYE', 'L_HAND', 'R_HAND']
```

3. **降低ROI分辨率**
```python
# 更小的提取尺寸
'size': 120  # 从180降到120
```

## 🎬 进阶效果

### 动态闪烁

已实现，文字会闪烁：

```python
if self.frame_count % 30 < 25:  # 每30帧闪烁5帧
    cv2.putText(canvas, "CRITICAL", ...)
```

### 位置抖动

添加随机位置偏移：

```python
# 在放置ROI时
jitter_x = random.randint(-5, 5)
jitter_y = random.randint(-5, 5)
x, y = part['position']
x += jitter_x
y += jitter_y
canvas[y:y+size, x:x+size] = roi
```

### RGB分离

更强的RGB通道偏移：

```python
# 在extract_roi中
# 红色通道向右偏移
styled[:, 10:, 2] = styled_shifted[:, :-10, 2]
# 蓝色通道向左偏移
styled[:, :-10, 0] = styled_shifted[:, 10:, 0]
```

### 全屏噪点

添加全屏TV噪点效果：

```python
def add_tv_noise(canvas):
    if random.random() > 0.9:  # 10%概率
        noise = np.random.randint(0, 100, canvas.shape, dtype=np.uint8)
        canvas = cv2.add(canvas, noise)
    return canvas
```

## 🔌 集成到画廊视图

如果想集成到 `main_gallery_view.py`：

```python
# 在person_analyzer.py添加新模式
self.effect_mode = 'glitch'  # 新增

# 在main_gallery_view.py
from glitch_art_effect import GlitchArtEffect

self.glitch_generator = GlitchArtEffect()

# 在处理流程中
if self.analyzer.effect_mode == 'glitch':
    glitch_frame = self.glitch_generator.create_glitch_frame(frame, results)
```

## 📊 效果对比

| 特性 | Silhouette | ASCII Art | Glitch Art |
|------|-----------|-----------|-----------|
| 风格 | 极简 | 复古 | 赛博朋克 |
| 背景 | 真实 | 黑色+符号 | 纯黑 |
| 人物 | 完整剪影 | 字符轮廓 | 碎片化 |
| 颜色 | 黑白格子 | 白色字符 | 高对比黑白 |
| 信息 | 完整标注 | 无标注 | 标签框 |
| 性能 | 中 | 中 | 高 |
| 适用场景 | 艺术展览 | 复古风格 | 科技展示 |

## 🐛 故障排除

### 问题1: 看不到任何部位

**原因**: 关键点置信度太低
**解决**:
```python
# 降低置信度阈值
if keypoints[1][2] > 0.1:  # 从0.3降到0.1
```

### 问题2: 部位位置不对

**原因**: 没有镜像翻转摄像头
**解决**:
```python
frame = cv2.flip(frame, 1)  # 确保翻转
```

### 问题3: FPS太低

**原因**: 提取部位太多或尺寸太大
**解决**:
```python
# 减少部位数量
parts = results[:1]  # 只处理第一个人

# 减小尺寸
'size': 120  # 更小的ROI
```

### 问题4: 效果不够"故障"

**原因**: 随机效果概率太低
**解决**:
```python
# 提高噪点概率
if random.random() > 0.3:  # 从0.7提高到0.3

# 提高RGB偏移概率
if random.random() > 0.5:  # 从0.8提高到0.5
```

## 📝 示例代码

### 保存高质量截图

```python
# 在test_glitch_effect.py的主循环中
key = cv2.waitKey(1) & 0xFF
if key == ord('s'):
    # 保存高质量PNG
    filename = f'glitch_{int(time.time())}.png'
    cv2.imwrite(filename, glitch_frame, 
               [cv2.IMWRITE_PNG_COMPRESSION, 0])
```

### 录制视频

```python
# 初始化视频写入器
fourcc = cv2.VideoWriter_fourcc(*'mp4v')
out = cv2.VideoWriter('glitch_art.mp4', fourcc, 30.0, (1920, 1080))

# 在主循环中
out.write(glitch_frame)

# 结束时
out.release()
```

## 🎓 学习资源

### 故障艺术原理
- 二值化：将图像转换为纯黑白
- RGB分离：红绿蓝通道错位
- 噪点：随机像素干扰
- 扫描线：模拟CRT显示器

### 相关技术
- YOLOv8-Pose关键点检测
- OpenCV图像处理
- ROI（感兴趣区域）提取
- 实时视频处理

---

**版本**: 1.0  
**作者**: AI Assistant  
**基于**: YOLOv8-Pose + OpenCV  
**风格**: Cyberpunk / Glitch Art  
**日期**: 2025-11-27

