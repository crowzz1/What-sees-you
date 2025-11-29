# 画廊视图使用指南

## 功能概述

画廊视图（Gallery View）是一个全景展示界面，在一个大窗口中同时显示：
- **左上角**：摄像头原始识别画面（带骨架和标注）
- **右上角**：ASCII艺术效果（0和1字符显示人物轮廓）
- **下方区域**：AI生成的详细人物描述和属性信息

## 界面布局

```
┌─────────────────────────────────────────────────────────┐
│                    1920 x 1080                          │
├──────────────────────┬──────────────────────────────────┤
│                      │                                  │
│   CAMERA VIEW        │    ASCII ART VIEW                │
│   (960x648)          │    (960x648)                     │
│                      │                                  │
│   带骨架、标注        │    0和1字符效果                   │
│                      │                                  │
├──────────────────────┴──────────────────────────────────┤
│                                                          │
│   AI ANALYSIS - DETECTED PERSONS                        │
│                                                          │
│   PERSON 1                                              │
│   A young adult person in their 20s, with a slim       │
│   build, wearing a gray t-shirt and black pants.       │
│                                                          │
│   Age: 25 years                                         │
│   Body: Slim / Rectangle                                │
│   Clothing: T-shirt (Gray) + Pants (Black)             │
│   Emotion: Happy (85%)                                  │
│                                                          │
│   (432px高度文本区域)                                    │
└──────────────────────────────────────────────────────────┘
```

## 快速开始

### 1. 运行程序

```bash
python main_gallery_view.py
```

### 2. 控制键

```
'q'   - 退出程序
's'   - 保存当前完整画面截图
'+'   - 增大ASCII字符（更稀疏）
'-'   - 减小ASCII字符（更密集）
'w'   - 提高ASCII亮度阈值（更少字符）
'x'   - 降低ASCII亮度阈值（更多字符）
```

## 自定义窗口尺寸

如果你的屏幕不是1920x1080，可以修改窗口大小：

```python
gallery = GalleryView(
    camera_id=0,
    window_width=1920,  # 修改为你的宽度
    window_height=1080  # 修改为你的高度
)
```

### 常见分辨率示例

**Full HD (默认)**
```python
window_width=1920, window_height=1080
```

**2K**
```python
window_width=2560, window_height=1440
```

**4K**
```python
window_width=3840, window_height=2160
```

**笔记本屏幕**
```python
window_width=1366, window_height=768
```

## 显示内容说明

### 左上角：摄像头视图（Camera View）
- ✅ 实时人体检测
- ✅ 17个关键点可视化（红色）
- ✅ 骨架连线（红色）
- ✅ 人脸边界框（红色）
- ✅ 身体边界框（白色）
- ✅ 实时标注（年龄、情绪、服装等）

### 右上角：ASCII艺术视图（ASCII Art View）
- ✅ 使用0和1字符显示人物轮廓
- ✅ 黑色背景
- ✅ 基于亮度的字符生成
- ✅ 简化的标注（绿色）

### 下方：AI分析区域（AI Analysis）
显示每个检测到的人物的：

1. **自然语言描述**
   - 年龄组（young, young adult, middle-aged, senior）
   - 体型（slim, athletic, average, stocky）
   - 服装描述（颜色和类型）
   - 情绪表现

2. **详细属性**
   - **Age**: 精确年龄（平滑处理）
   - **Body**: 体型和身材形状
   - **Clothing**: 上衣和裤子的类型及颜色
   - **Emotion**: 情绪及置信度

## 显示示例

### 单人场景
```
PERSON 1
A young adult person in their 20s, with an athletic build,
wearing a blue t-shirt and black pants, smiling.

Age: 24 years
Body: Athletic / V-Shape
Clothing: T-shirt (Blue) + Pants (Black)
Emotion: Happy (92%)
```

### 多人场景
```
PERSON 1
A middle-aged person in their 40s, with an average build,
wearing a gray shirt and blue pants, with a neutral expression.

Age: 42 years
Body: Average / Rectangle
Clothing: Shirt (Gray) + Pants (Blue)
Emotion: Neutral (78%)

PERSON 2
A young person in their 20s, with a slim build, wearing
a red t-shirt and black shorts, smiling.

Age: 26 years
Body: Slim / Rectangle
Clothing: T-shirt (Red) + Shorts (Black)
Emotion: Happy (88%)
```

## 技术特点

### 双重处理
- 程序会处理每帧**两次**：
  1. 第一次：关闭特效，获取正常识别画面
  2. 第二次：开启ASCII特效，获取ASCII画面

### 智能缩放
- 两个视图都会自动缩放以适应显示区域
- 保持原始宽高比
- 居中显示

### 实时文本生成
- 使用AI模型生成的自然语言描述
- 自动换行（每行最多80字符）
- 动态调整显示位置

## 性能优化

### 如果遇到卡顿

1. **降低窗口分辨率**
   ```python
   window_width=1366, window_height=768
   ```

2. **增大ASCII字符大小**（按 `+` 键）
   - 减少需要绘制的字符数量

3. **提高亮度阈值**（按 `w` 键）
   - 只显示最亮的区域

### 推荐配置

**高性能设备** (RTX 3060+)
- 1920x1080 全分辨率
- ASCII grid_size: 10-12
- ASCII threshold: 40-50

**中等性能设备**
- 1366x768 或 1600x900
- ASCII grid_size: 14-16
- ASCII threshold: 60-70

**低性能设备**
- 1280x720
- ASCII grid_size: 18-20
- ASCII threshold: 80-90

## 截图功能

按 `s` 键保存完整的画廊视图截图：
- 文件名格式：`gallery_view_<timestamp>.jpg`
- 包含所有三个区域的完整画面
- 保存在程序运行目录

## 常见问题

**Q: 窗口太大/太小？**
A: 修改 `window_width` 和 `window_height` 参数

**Q: ASCII效果看不到字符？**
A: 按 `x` 键降低亮度阈值

**Q: 文本区域显示不完整？**
A: 增大窗口高度，或减少检测到的人数

**Q: FPS太低？**
A: 降低窗口分辨率，增大ASCII grid size

**Q: 想要全屏显示？**
A: 程序会创建一个可调整大小的窗口，你可以手动拉伸到全屏，或修改代码添加：
```python
cv2.setWindowProperty('Gallery View', cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)
```

## 自定义选项

### 修改文本区域高度

在 `__init__` 方法中：

```python
self.cam_height = int(window_height * 0.6)  # 上方60%
# 改为：
self.cam_height = int(window_height * 0.7)  # 上方70%（文本区域更小）
```

### 修改ASCII字符集

在程序开始前添加：

```python
gallery = GalleryView(camera_id=0)
gallery.analyzer.ascii_chars = ['█', '▓', '▒', '░']  # 使用方块字符
gallery.run()
```

### 修改颜色主题

文本区域背景色（在 `draw_text_area` 方法中）：

```python
text_bg = np.full((self.text_height, self.window_width, 3), 20, dtype=np.uint8)
# 改为蓝色背景：
text_bg = np.full((self.text_height, self.window_width, 3), [40, 20, 0], dtype=np.uint8)
```

## 与其他程序对比

| 程序 | 特点 | 适用场景 |
|------|------|----------|
| `main.py` | 单摄像头，可切换特效模式 | 日常测试 |
| `main_sts_tracking.py` | 机械臂追踪，简单视图 | 机械臂控制 |
| `test_ascii_effect.py` | ASCII测试，参数调整 | 效果调试 |
| `main_gallery_view.py` | **画廊视图，多视角展示** | **展览、演示** |

## 应用场景

- 🎨 **艺术装置**：适合画廊、展览展示
- 📊 **数据可视化**：同时查看多个视角
- 🎓 **教学演示**：展示AI识别过程
- 🎬 **内容创作**：录制视频展示AI效果
- 🏢 **商业演示**：向客户展示技术能力

## 未来改进

- [ ] 支持多摄像头画廊（2x2布局）
- [ ] 添加第三个视图（剪影特效）
- [ ] 文本区域支持滚动（显示更多人物）
- [ ] 添加统计图表（人流量、情绪分布等）
- [ ] 录制功能（保存完整视频）
- [ ] 网络流式传输（在其他设备上查看）

---

**开发者**: AI Assistant
**项目**: What Sees You - 画廊视图
**版本**: 1.0
**日期**: 2025-11-27






