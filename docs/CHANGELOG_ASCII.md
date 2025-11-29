# ASCII 艺术效果更新日志

## 版本 1.0 - 2025-11-27

### 新增功能

✨ **ASCII 艺术视觉效果**
- 使用 0 和 1 字符显示人物轮廓
- Matrix 风格的赛博朋克视觉体验
- 基于 YOLOv8-Seg 精确的人体分割

### 修改的文件

1. **person_analyzer.py**
   - 添加 `effect_mode` 参数（'silhouette' / 'ascii'）
   - 添加 ASCII 效果配置参数：
     - `ascii_grid_size`: 字符密度控制
     - `ascii_threshold`: 亮度阈值
     - `ascii_chars`: 使用的字符集
   - 新增 `create_ascii_effect()` 方法
   - 新增 `draw_info_on_ascii_frame()` 方法
   - 修改 `apply_visual_effects()` 支持模式切换

2. **main.py**
   - 添加 'm' 键切换特效模式
   - 更新帮助信息

3. **main_sts_tracking.py**
   - 添加 'v' 键开关特效
   - 添加 'm' 键切换特效模式
   - 更新帮助信息

### 新增文件

1. **ASCII_EFFECT_GUIDE.md**
   - 完整的使用指南
   - 参数调整说明
   - 常见问题解答

2. **test_ascii_effect.py**
   - 独立测试程序
   - 实时参数调整功能
   - 用于快速测试和调试

3. **CHANGELOG_ASCII.md**
   - 本更新日志

### 使用方法

#### 快速开始

1. 运行主程序：
   ```bash
   python main.py
   ```

2. 按 `e` 开启特效

3. 按 `m` 切换到 ASCII 模式

#### 测试程序

运行测试程序可以实时调整参数：
```bash
python test_ascii_effect.py
```

测试程序额外控制键：
- `+/-`: 调整字符大小
- `w/s`: 调整亮度阈值

### 技术特点

- ✅ **精确分割**: 优先使用 YOLOv8-Seg 获取准确的人体轮廓
- ✅ **后备方案**: 当分割模型不可用时，使用关键点方法
- ✅ **实时性能**: 优化的网格采样算法
- ✅ **可定制**: 丰富的参数配置选项
- ✅ **兼容性**: 与现有所有功能完全兼容

### 性能考虑

- 默认配置 (grid_size=12) 适合大多数场景
- 在低性能设备上，建议增大 `ascii_grid_size` 到 16-20
- 提高 `ascii_threshold` 可以减少字符数量，提升性能

### 自定义选项

#### 字符集示例

```python
# Matrix 风格 (默认)
self.ascii_chars = ['0', '1']

# 渐变符号
self.ascii_chars = ['.', ':', '+', '#', '@']

# 数字
self.ascii_chars = ['0', '1', '2', '3', '4', '5']

# 字母
self.ascii_chars = ['A', 'B', 'C', 'D', 'E', 'F']

# 单字符极简
self.ascii_chars = ['█']
```

#### 效果预设

**高清模式** (性能要求高):
```python
self.ascii_grid_size = 8
self.ascii_threshold = 30
```

**均衡模式** (默认):
```python
self.ascii_grid_size = 12
self.ascii_threshold = 50
```

**流畅模式** (低性能设备):
```python
self.ascii_grid_size = 18
self.ascii_threshold = 70
```

### 未来计划

- [ ] 彩色 ASCII（根据原始图像颜色着色字符）
- [ ] 根据亮度自动选择字符（真正的 ASCII 渐变）
- [ ] Matrix 雨效果（字符下落动画）
- [ ] 可配置的背景颜色
- [ ] 字符闪烁和随机变化效果
- [ ] 边缘检测优化（只在轮廓边缘显示字符）

### 已知限制

- ASCII 模式下信息显示简化（只显示 Person ID 和 Age）
- 字符大小受 OpenCV 字体限制
- 极小的 grid_size 可能导致性能下降

### 致谢

灵感来源：
- Matrix (1999) 电影的视觉风格
- p5.js ASCII art 示例代码
- 经典终端 ASCII 艺术

---

**开发者**: AI Assistant
**项目**: What Sees You - 人体识别追踪系统
**日期**: 2025-11-27






