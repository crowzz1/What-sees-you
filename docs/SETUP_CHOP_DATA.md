# 🎯 设置 CHOP 数据流（摄像头数据 → CHOP 通道）

## ✅ 已创建

- `/project1/camera_data_chop` - Script CHOP（数据输出节点）
- `/project1/camera_data_chop_callbacks` - 回调脚本

---

## 🔧 设置步骤（在 TouchDesigner Textport 中）

### 步骤 1：打开 Textport

按 **Alt + T** 或菜单 **Dialogs → Textport**

### 步骤 2：设置 CHOP 脚本

复制粘贴并按回车：

```python
# 读取 CHOP 脚本
with open(r'C:\Users\Admin\Desktop\what sees you\td_chop_script_fixed.py', 'r', encoding='utf-8') as f:
    script = f.read()

# 设置到 callbacks
callbacks = op('/project1/camera_data_chop_callbacks')
callbacks.text = script

# 强制更新 CHOP
op('/project1/camera_data_chop').cook(force=True)

print("✅ CHOP 已设置！")
chop = op('/project1/camera_data_chop')
print(f"通道数: {chop.numChans}")
if chop.numChans > 0:
    print("前 10 个通道:")
    for i in range(min(10, chop.numChans)):
        print(f"  {chop[i].name} = {chop[i][0]}")
```

---

## 📊 输出的 CHOP 通道

点击 `/project1/camera_data_chop` 节点，你会看到：

### 基础通道

| 通道名 | 说明 | 值范围 |
|--------|------|--------|
| `person_count` | 检测到的人数 | 0-10 |

### 每个人的通道（p1_, p2_, ...）

| 通道名 | 说明 | 值范围 |
|--------|------|--------|
| `p1_age` | 年龄 | 18-80 |
| `p1_age_norm` | 年龄归一化 | 0-1 |
| `p1_gender` | 性别 | 0=男, 1=女 |
| `p1_emotion` | 情绪 | 0-6 |
| `p1_emotion_conf` | 情绪置信度 | 0-1 |
| `p1_race` | 种族 | 0-5 |
| `p1_body_type` | 体型 | 0-3 |
| `p1_pos_x` | X 位置 | 0-1 |
| `p1_pos_y` | Y 位置 | 0-1 |
| `p1_width` | 宽度 | 0-1 |
| `p1_height` | 高度 | 0-1 |
| `p1_upper_r/g/b` | 上装颜色 RGB | 0-1 |
| `p1_lower_r/g/b` | 下装颜色 RGB | 0-1 |
| `p1_upper_type` | 上装类型 | 0-2 |
| `p1_lower_type` | 下装类型 | 0-1 |
| `p1_keypoint_count` | 关键点数 | 0-17 |

---

## 🎨 如何使用 CHOP 数据

### 示例 1：映射到参数

```
1. 创建一个 Constant TOP
2. 在 Constant 的 colorr 参数上，右键 → CHOP Reference
3. 选择 camera_data_chop 的 p1_upper_r 通道
```

现在背景颜色会跟随第一个人的上装颜色！

---

### 示例 2：驱动位置

```
1. 创建一个 Circle TOP
2. 在 tx (translate x) 参数上，CHOP Reference → p1_pos_x
3. 在 ty (translate y) 参数上，CHOP Reference → p1_pos_y
```

圆圈会跟随第一个人移动！

---

### 示例 3：情绪驱动动画

```
1. 创建一个 Math CHOP
2. 输入连接到 camera_data_chop
3. Channel = p1_emotion
4. 用 Select CHOP 选择只要情绪通道
5. 连接到其他节点的参数
```

---

### 示例 4：多人追踪

```
# 使用 Script 自动为每个人创建可视化
for i in range(person_count):
    circle = parent().create(circleTOP, f'person{i+1}_circle')
    circle.par.tx = chop(f'camera_data_chop/p{i+1}_pos_x')
    circle.par.ty = chop(f'camera_data_chop/p{i+1}_pos_y')
    circle.par.colorr = chop(f'camera_data_chop/p{i+1}_upper_r')
    circle.par.colorg = chop(f'camera_data_chop/p{i+1}_upper_g')
    circle.par.colorb = chop(f'camera_data_chop/p{i+1}_upper_b')
```

---

## 🔄 自动更新

要让 CHOP 数据自动刷新，在 Textport 中运行：

```python
# 设置 UDP 回调，每次收到数据就更新 CHOP
callbacks = op('/project1/udpin1_callbacks')
callbacks.text = '''
def onReceiveRow(dat, row):
    op('/project1/camera_data_chop').cook(force=True)
'''
print("✅ 自动更新已设置！")
```

---

## 🎯 数据流总结

```
摄像头程序
    ↓ UDP (JSON)
udpin1 (DAT)
    ↓ 解析
camera_data_chop (CHOP) ← 你现在在这里！
    ↓ 通道
任何 TOP/SOP/CHOP 的参数
    ↓
实时可视化/交互
```

---

## 💡 接下来做什么？

### 选项 A：测试通道数据

在 Textport 中：
```python
chop = op('/project1/camera_data_chop')
print(f"Person count: {chop['person_count'][0]}")
print(f"Person 1 age: {chop['p1_age'][0]}")
print(f"Person 1 emotion: {chop['p1_emotion'][0]}")
```

### 选项 B：创建可视化

告诉我你想要什么效果，比如：
- "用圆圈跟踪每个人的位置"
- "根据情绪改变颜色"
- "显示人数的数字"

我可以帮你创建！

---

**现在数据已经是 CHOP 格式了，可以像处理其他 CHOP 一样使用！** 🚀







