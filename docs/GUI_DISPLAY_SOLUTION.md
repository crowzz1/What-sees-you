# GUI 显示问题解决方案

## 问题原因

你当前安装的 `opencv-python` 版本**没有 GUI 支持**。

错误信息：
```
The function is not implemented. Rebuild the library with Windows, GTK+ 2.x or Cocoa support
```

## 为什么 main_gallery_view.py 能显示？

可能的原因：
1. 那个项目使用了不同的 Python 环境
2. 那个项目安装了 `opencv-contrib-python`（有 GUI 支持）
3. 那个项目使用了不同的虚拟环境

## 解决方案

### 方案 1：安装有 GUI 支持的 OpenCV（推荐）

```bash
# 卸载当前版本
pip uninstall opencv-python opencv-python-headless

# 安装带 GUI 支持的版本
pip install opencv-contrib-python
```

**注意**：`opencv-contrib-python` 包含所有功能，包括 GUI 支持。

### 方案 2：使用图像保存模式（当前已实现）

如果不想重装 OpenCV，程序会自动切换到图像保存模式：

```bash
python test_hand_tracking.py
```

程序会：
1. 尝试使用 GUI
2. 如果失败，自动切换到图像保存模式
3. 每 2 秒保存一张带标注的图像到 `tracking_snapshots/` 目录
4. 你可以打开这些图像查看追踪效果

### 方案 3：使用专门的图像保存版本

```bash
python test_hand_tracking_save_images.py
```

这个版本从一开始就使用图像保存模式。

## 测试 OpenCV GUI 支持

运行测试脚本：

```bash
python test_opencv_gui.py
```

如果显示 "✓ GUI 支持正常"，说明 OpenCV 有 GUI 支持。
如果显示错误，需要重装 OpenCV。

## 推荐配置

### 完整功能（包括 GUI）

```bash
pip install opencv-contrib-python
pip install ultralytics
pip install pyserial
```

### 无 GUI 环境（服务器、Docker）

```bash
pip install opencv-python-headless
pip install ultralytics
pip install pyserial
```

然后使用 `test_hand_tracking_save_images.py`

## 当前程序特性

`test_hand_tracking.py` 现在支持：

✅ **自动检测 GUI 支持**
- 如果 GUI 可用 → 显示窗口
- 如果 GUI 不可用 → 自动切换到图像保存模式

✅ **图像保存模式**
- 每 2 秒保存一张带标注的图像
- 保存到 `tracking_snapshots/` 目录
- 图像包含所有 UI 元素（十字线、死区、手的位置等）

✅ **终端输出**
- 实时显示追踪状态
- 显示电机位置
- 显示 FPS

## 使用建议

1. **如果你需要实时查看画面**：
   ```bash
   pip install opencv-contrib-python
   python test_hand_tracking.py
   ```

2. **如果你只需要监控追踪效果**：
   ```bash
   # 使用当前的图像保存模式
   python test_hand_tracking.py
   # 查看 tracking_snapshots/ 目录中的图像
   ```

3. **如果你想同时看到多个视角**：
   ```bash
   # 参考你的 main_gallery_view.py
   # 那个环境肯定有 GUI 支持
   ```


