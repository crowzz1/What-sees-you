# 📊 TouchDesigner 数据解析器设置指南

我已经在 TouchDesigner 中创建了 `/project1/parse_camera_data` 节点。

---

## ✅ 已完成

- ✅ 创建了 `parse_camera_data` Text DAT 节点
- ✅ 设置为 Python 模式
- ✅ 准备好解析脚本（`td_parse_camera_data.py`）

---

## 🔧 手动设置步骤（2 分钟）

### 方法 1：复制粘贴脚本（推荐）

1. 在 TouchDesigner 中，双击 `/project1/parse_camera_data` 节点
2. 打开文本编辑器
3. 复制 `td_parse_camera_data.py` 的全部内容
4. 粘贴到 `parse_camera_data` 节点中
5. 关闭编辑器

---

### 方法 2：使用 Textport（高级）

在 TouchDesigner 的 Textport 中执行：

```python
# 读取脚本文件
with open(r'C:\Users\Admin\Desktop\what sees you\td_parse_camera_data.py', 'r', encoding='utf-8') as f:
    script_content = f.read()

# 设置到节点
parse_dat = op('/project1/parse_camera_data')
parse_dat.text = script_content
parse_dat.run()

print("✅ 解析脚本已设置！")
```

---

## 📊 查看解析结果

设置完成后，在 TouchDesigner 中：

1. 启动摄像头程序：
   ```bash
   python main_with_all_attributes.py 0 1
   ```

2. 点击 `parse_camera_data` 节点查看解析后的表格数据

---

## 📋 解析输出格式

| 列名 | 说明 | 示例值 |
|------|------|--------|
| Camera | 摄像头 ID | 1 |
| Person ID | 人物 ID | 1 |
| Gender | 性别 | Male / Female |
| Age | 年龄 | 25 |
| Emotion | 情绪 | Happy / Sad / Angry / Neutral |
| Race | 种族 | Asian / White / Black |
| Body Type | 体型 | Slim / Average / Athletic / Heavy |
| Upper Type | 上装类型 | T-shirt / Shirt / Long Sleeve |
| Lower Type | 下装类型 | Long Pants / Shorts |
| Upper Color | 上装颜色 | RGB(120, 80, 50) |
| Lower Color | 下装颜色 | RGB(30, 30, 30) |
| Keypoints | 关键点数量 | 17 points |
| Description | 自然语言描述 | "A 25-year-old asian male..." |

---

## 🎯 数据使用示例

### 示例 1：获取人数

```python
parse_dat = op('/project1/parse_camera_data')
person_count = parse_dat.numRows - 1  # 减去表头
print(f"检测到 {person_count} 人")
```

### 示例 2：获取第一个人的年龄

```python
parse_dat = op('/project1/parse_camera_data')
if parse_dat.numRows > 1:
    age = parse_dat[1, 3].val  # 第 1 行（数据行），第 3 列（Age）
    print(f"年龄: {age}")
```

### 示例 3：获取所有人的情绪

```python
parse_dat = op('/project1/parse_camera_data')
for i in range(1, parse_dat.numRows):  # 从第 1 行开始（跳过表头）
    emotion = parse_dat[i, 4].val  # 第 4 列（Emotion）
    person_id = parse_dat[i, 1].val
    print(f"Person {person_id}: {emotion}")
```

---

## 🔄 自动刷新

要让数据自动更新，可以：

### 方法 A：使用 Timer CHOP

1. 创建 Timer CHOP
2. 设置 Timer to 30 FPS
3. 在 Timer 的 Execute DAT 中：
   ```python
   def onFrameStart(frame):
       op('/project1/parse_camera_data').run()
   ```

### 方法 B：使用 udpin1 的回调

在 `/project1/udpin1_callbacks` 中添加：

```python
def onReceiveRow(dat, row):
    # 每次收到新数据就刷新解析
    op('/project1/parse_camera_data').run()
```

---

## 🎨 可视化建议

现在数据已经解析成表格，你可以：

1. **创建 Text TOP** - 显示人数、平均年龄等
2. **创建 Circle TOP** - 为每个人绘制圆圈
3. **创建 Rectangle TOP** - 根据情绪改变颜色
4. **使用 CHOP Execute** - 触发事件（如检测到微笑）

---

## 📞 需要帮助？

告诉我你想做什么，比如：
- "创建一个大字体显示检测到的人数"
- "根据情绪改变背景颜色"
- "为每个人创建一个可视化标记"

我可以直接帮你创建节点！🚀







