# 🎯 TouchDesigner Textport 配置命令

在 TouchDesigner 中按 **Alt + T** 打开 Textport，然后**逐段**复制粘贴运行：

---

## 步骤 1：配置 UDP In 端口

```python
# 设置 3 个 UDP In 的端口
op('/project1/udpin1').par.port = 7000
op('/project1/udpin1').par.active = True
op('/project1/udpin1').par.format = 'permessage'

op('/project1/udpin2').par.port = 7001
op('/project1/udpin2').par.active = True
op('/project1/udpin2').par.format = 'permessage'

op('/project1/udpin3').par.port = 7002
op('/project1/udpin3').par.active = True
op('/project1/udpin3').par.format = 'permessage'

print('✓ UDP 端口已配置')
```

---

## 步骤 2：为摄像头 1 设置脚本

```python
# 读取脚本模板
with open(r'C:\Users\Admin\Desktop\what sees you\td_chop_script_latest_only.py', 'r', encoding='utf-8') as f:
    script_template = f.read()

# 修改为摄像头1的配置
script1 = script_template.replace("op('/project1/udpin1')", "op('/project1/udpin1')")
script1 = script1.replace("prefix = f'p{person_num}_'", "prefix = f'cam1_p{person_num}_'")

# 设置脚本
op('/project1/camera_data_chop_callbacks').text = script1
op('/project1/camera_data_chop').cook(force=True)

print('✓ 摄像头1 CHOP 已配置')
```

---

## 步骤 3：为摄像头 2 设置脚本

```python
# 修改为摄像头2的配置
script2 = script_template.replace("op('/project1/udpin1')", "op('/project1/udpin2')")
script2 = script2.replace("prefix = f'p{person_num}_'", "prefix = f'cam2_p{person_num}_'")

# 设置脚本
op('/project1/camera_data_chop_callbacks1').text = script2
op('/project1/camera_data_chop1').cook(force=True)

print('✓ 摄像头2 CHOP 已配置')
```

---

## 步骤 4：为摄像头 3 设置脚本

```python
# 修改为摄像头3的配置
script3 = script_template.replace("op('/project1/udpin1')", "op('/project1/udpin3')")
script3 = script3.replace("prefix = f'p{person_num}_'", "prefix = f'cam3_p{person_num}_'")

# 设置脚本
op('/project1/camera_data_chop_callbacks2').text = script3
op('/project1/camera_data_chop2').cook(force=True)

print('✓ 摄像头3 CHOP 已配置')
```

---

## 步骤 5：验证配置

```python
# 检查所有配置
configs = [
    ('摄像头1', 'udpin1', 'camera_data_chop', 7000),
    ('摄像头2', 'udpin2', 'camera_data_chop1', 7001),
    ('摄像头3', 'udpin3', 'camera_data_chop2', 7002)
]

for name, udp_name, chop_name, port in configs:
    udp = op(f'/project1/{udp_name}')
    chop = op(f'/project1/{chop_name}')
    print(f'\n{name}:')
    print(f'  UDP: {udp_name} (端口 {port})')
    print(f'  UDP 行数: {udp.numRows}')
    print(f'  CHOP 通道数: {chop.numChans}')
```

---

## ✅ 配置完成后

### 启动摄像头程序
在命令行中运行：
```bash
start_all_cameras.bat
```

### 查看数据（在 Textport）
```python
# 查看摄像头1的数据
chop1 = op('/project1/camera_data_chop')
print(f"摄像头1 人数: {chop1['cam1_person_count'][0]}")
print(f"前5个通道: {[chop1[i].name for i in range(min(5, chop1.numChans))]}")

# 查看摄像头2的数据
chop2 = op('/project1/camera_data_chop1')
print(f"摄像头2 人数: {chop2['cam2_person_count'][0]}")

# 查看摄像头3的数据
chop3 = op('/project1/camera_data_chop2')
print(f"摄像头3 人数: {chop3['cam3_person_count'][0]}")
```

---

## 📊 预期输出格式

### 摄像头 1 (`camera_data_chop`)
```
cam1_person_count
cam1_persons_detected
cam1_p1_id
cam1_p1_age
cam1_p1_gender
cam1_p1_pos_x
cam1_p1_pos_y
...
```

### 摄像头 2 (`camera_data_chop1`)
```
cam2_person_count
cam2_persons_detected
cam2_p1_id
cam2_p1_age
...
```

### 摄像头 3 (`camera_data_chop2`)
```
cam3_person_count
cam3_persons_detected
cam3_p1_id
cam3_p1_age
...
```

---

## 🔧 故障排除

### 如果某个 CHOP 没有通道

```python
# 手动刷新
op('/project1/camera_data_chop').cook(force=True)
op('/project1/camera_data_chop1').cook(force=True)
op('/project1/camera_data_chop2').cook(force=True)
```

### 如果某个 UDP 没有数据

1. 检查摄像头程序是否运行
2. 检查端口是否正确
3. 在 Textport 中运行：
```python
print(f"udpin1 行数: {op('/project1/udpin1').numRows}")
print(f"udpin2 行数: {op('/project1/udpin2').numRows}")
print(f"udpin3 行数: {op('/project1/udpin3').numRows}")
```

---

**按顺序运行步骤 1-5，3 分钟搞定！** 🚀







