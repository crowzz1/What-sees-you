# 🎥 3 摄像头系统设置指南

## 📊 方案 A：3 个独立 UDP In（推荐）

### 架构图
```
Python 摄像头程序:
├── 摄像头 1 → UDP 端口 7000 → /project1/camera1_udp → camera1_chop
├── 摄像头 2 → UDP 端口 7001 → /project1/camera2_udp → camera2_chop
└── 摄像头 3 → UDP 端口 7002 → /project1/camera3_udp → camera3_chop

CHOP 输出通道:
├── camera1_chop: cam1_p1_age, cam1_p1_pos_x...
├── camera2_chop: cam2_p1_age, cam2_p1_pos_x...
└── camera3_chop: cam3_p1_age, cam3_p1_pos_x...
```

---

## 🚀 快速设置（在 TouchDesigner Textport 中）

### 步骤 1：创建 3 个 UDP In DAT

```python
# 创建 UDP In DAT 节点
ports = [7000, 7001, 7002]
for i, port in enumerate(ports):
    cam_num = i + 1
    udp_name = f'camera{cam_num}_udp'
    
    try:
        udp = parent().create(udpinDAT, udp_name)
        udp.par.port = port
        udp.par.active = True
        udp.par.format = 'permessage'
        udp.par.maxlines = 10
        print(f'✓ 创建 {udp_name} (端口 {port})')
    except:
        # 如果已存在，更新配置
        udp = op(f'/project1/{udp_name}')
        udp.par.port = port
        udp.par.active = True
        udp.par.format = 'permessage'
        print(f'✓ 更新 {udp_name} (端口 {port})')

print('\n✅ UDP In DAT 已创建！')
```

---

### 步骤 2：创建 3 个 Script CHOP

```python
# 创建 Script CHOP 节点
for i in range(3):
    cam_num = i + 1
    chop_name = f'camera{cam_num}_chop'
    
    try:
        chop = parent().create(scriptCHOP, chop_name)
        print(f'✓ 创建 {chop_name}')
    except:
        print(f'✗ {chop_name} 已存在')

print('\n✅ Script CHOP 已创建！')
```

---

### 步骤 3：设置 CHOP 脚本（为每个摄像头）

```python
# 为每个摄像头设置解析脚本
for i in range(3):
    cam_num = i + 1
    udp_path = f'/project1/camera{cam_num}_udp'
    chop_name = f'camera{cam_num}_chop'
    callbacks_name = f'{chop_name}_callbacks'
    
    # 读取脚本模板
    with open(r'C:\Users\Admin\Desktop\what sees you\td_chop_script_latest_only.py', 'r', encoding='utf-8') as f:
        script_template = f.read()
    
    # 替换 UDP 路径（指向对应的摄像头）
    script = script_template.replace(
        "op('/project1/udpin1')", 
        f"op('{udp_path}')"
    )
    
    # 修改通道前缀（cam1_, cam2_, cam3_）
    script = script.replace(
        "prefix = f'p{person_num}_'",
        f"prefix = f'cam{cam_num}_p{{person_num}}_'"
    )
    
    # 设置到 callbacks
    callbacks = op(f'/project1/{callbacks_name}')
    callbacks.text = script
    
    print(f'✓ 设置 {chop_name} 脚本')

print('\n✅ 所有 CHOP 脚本已设置！')
```

---

### 步骤 4：验证设置

```python
# 验证所有节点
for i in range(3):
    cam_num = i + 1
    udp = op(f'/project1/camera{cam_num}_udp')
    chop = op(f'/project1/camera{cam_num}_chop')
    
    print(f'\n摄像头 {cam_num}:')
    print(f'  UDP 端口: {udp.par.port}')
    print(f'  UDP 行数: {udp.numRows}')
    print(f'  CHOP 通道数: {chop.numChans}')
    
    if chop.numChans > 0:
        print(f'  前3个通道: {[chop[j].name for j in range(min(3, chop.numChans))]}')
```

---

## 🎬 启动摄像头程序

### 方法 1：使用现有的批处理文件

```bash
start_all_cameras.bat
```

这会自动启动 3 个摄像头，发送到端口 7000, 7001, 7002。

---

### 方法 2：手动启动（如果需要自定义）

打开 3 个命令行窗口：

**窗口 1 - 摄像头 1:**
```bash
cd "C:\Users\Admin\Desktop\what sees you"
python main_with_all_attributes.py 0 1 127.0.0.1 7000
```

**窗口 2 - 摄像头 2:**
```bash
cd "C:\Users\Admin\Desktop\what sees you"
python main_with_all_attributes.py 1 2 127.0.0.1 7001
```

**窗口 3 - 摄像头 3:**
```bash
cd "C:\Users\Admin\Desktop\what sees you"
python main_with_all_attributes.py 2 3 127.0.0.1 7002
```

---

## 📊 CHOP 输出通道格式

### 摄像头 1 的通道（camera1_chop）:
```
cam1_person_count
cam1_persons_detected
cam1_p1_id
cam1_p1_age
cam1_p1_gender
cam1_p1_emotion
cam1_p1_pos_x
cam1_p1_pos_y
cam1_p1_upper_r/g/b
...
```

### 摄像头 2 的通道（camera2_chop）:
```
cam2_person_count
cam2_persons_detected
cam2_p1_id
cam2_p1_age
...
```

### 摄像头 3 的通道（camera3_chop）:
```
cam3_person_count
cam3_persons_detected
cam3_p1_id
cam3_p1_age
...
```

---

## 🔗 合并所有摄像头的数据（可选）

如果你想把 3 个摄像头的数据合并到一个 CHOP：

```python
# 创建 Merge CHOP
merge = parent().create(mergeCHOP, 'all_cameras_merged')
merge.par.chop0 = '/project1/camera1_chop'
merge.par.chop1 = '/project1/camera2_chop'
merge.par.chop2 = '/project1/camera3_chop'
print(f'✓ 合并 CHOP 已创建: {merge.path}')
print(f'  总通道数: {merge.numChans}')
```

现在 `all_cameras_merged` 包含所有 3 个摄像头的数据！

---

## 🎯 使用示例

### 示例 1：显示每个摄像头的人数

```python
# 创建 3 个 Text TOP 显示人数
for i in range(3):
    cam_num = i + 1
    text = parent().create(textTOP, f'cam{cam_num}_count_text')
    text.par.text = f'chop("camera{cam_num}_chop/cam{cam_num}_person_count")'
    text.par.fontsize = 100
    print(f'✓ 创建 {text.name}')
```

---

### 示例 2：可视化所有人的位置

```python
# 为每个摄像头的每个人创建圆圈
for cam_num in range(1, 4):
    chop = op(f'/project1/camera{cam_num}_chop')
    
    # 获取人数
    if chop.numChans > 0:
        person_count = int(chop[f'cam{cam_num}_person_count'][0])
        
        for p_num in range(1, person_count + 1):
            # 创建圆圈 TOP
            circle = parent().create(circleTOP, f'cam{cam_num}_p{p_num}_circle')
            
            # 绑定位置
            circle.par.tx.expr = f'chop("camera{cam_num}_chop/cam{cam_num}_p{p_num}_pos_x")'
            circle.par.ty.expr = f'chop("camera{cam_num}_chop/cam{cam_num}_p{p_num}_pos_y")'
            
            # 绑定颜色（上装颜色）
            circle.par.colorr.expr = f'chop("camera{cam_num}_chop/cam{cam_num}_p{p_num}_upper_r")'
            circle.par.colorg.expr = f'chop("camera{cam_num}_chop/cam{cam_num}_p{p_num}_upper_g")'
            circle.par.colorb.expr = f'chop("camera{cam_num}_chop/cam{cam_num}_p{p_num}_upper_b")'
            
            print(f'✓ 创建可视化: {circle.name}')
```

---

## 📋 配置检查清单

- [ ] 3 个 UDP In DAT 已创建（端口 7000, 7001, 7002）
- [ ] 3 个 Script CHOP 已创建
- [ ] CHOP 脚本已设置（每个指向对应的 UDP）
- [ ] 通道前缀正确（cam1_, cam2_, cam3_）
- [ ] 摄像头程序已启动（`start_all_cameras.bat`）
- [ ] 每个 UDP In 都有数据（行数 > 1）
- [ ] 每个 CHOP 都有通道输出

---

## 🔧 故障排除

### 问题 1：某个摄像头没有数据

**检查**：
```python
cam_num = 1  # 改成有问题的摄像头编号
udp = op(f'/project1/camera{cam_num}_udp')
print(f'UDP 行数: {udp.numRows}')
print(f'端口: {udp.par.port}')
```

**解决**：确认对应的 Python 程序正在运行。

---

### 问题 2：CHOP 没有通道

**检查**：
```python
cam_num = 1
chop = op(f'/project1/camera{cam_num}_chop')
chop.cook(force=True)
print(f'通道数: {chop.numChans}')
```

**解决**：重新设置脚本（运行步骤 3）。

---

## 🎉 完成！

现在你有：
- ✅ 3 个独立的摄像头数据流
- ✅ 清晰的通道命名（cam1_, cam2_, cam3_）
- ✅ 完全隔离的数据处理
- ✅ 可以独立或合并使用

---

**按顺序运行 Textport 中的 4 个步骤，5 分钟搞定！** 🚀







