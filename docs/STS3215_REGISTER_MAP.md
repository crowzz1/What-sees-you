# STS3215 寄存器映射表

根据官方文档和参考库整理

## EEPROM 区域（掉电保存）

| 地址 | 名称 | 字节数 | 默认值 | 范围 | 单位 | 说明 |
|------|------|--------|--------|------|------|------|
| 0x05 | ID | 1 | 1 | 0-253 | - | 舵机ID |
| 0x06 | Baud Rate | 1 | 1 | 0-250 | - | 波特率设置 |
| 0x09 | Min Position Limit | 2 | 0 | 0-4095 | step | 最小位置限制 |
| 0x0B | Max Position Limit | 2 | 4095 | 0-4095 | step | 最大位置限制 |
| 0x0D | Max Temperature | 1 | 85 | 0-100 | °C | 最高温度限制 |
| 0x0E | Max Voltage | 1 | 90 | 60-90 | 0.1V | 最高电压限制 |
| 0x0F | Min Voltage | 1 | 60 | 60-90 | 0.1V | 最低电压限制 |
| 0x10 | Max Torque | 2 | 1000 | 0-1000 | - | 最大扭矩 |
| 0x13 | Unloading Condition | 1 | 0 | 0-3 | - | 卸载条件 |
| 0x14 | LED Alarm Condition | 1 | 0 | 0-255 | - | LED报警条件 |
| 0x15 | P Coefficient | 1 | 32 | 0-254 | - | P系数 |
| 0x16 | D Coefficient | 1 | 32 | 0-254 | - | D系数 |
| 0x17 | I Coefficient | 1 | 0 | 0-254 | - | I系数 |
| 0x18 | Minimum Startup Force | 2 | 0 | 0-1000 | - | 最小启动力 |
| 0x1A | CW Dead Zone | 1 | 0 | 0-10 | step | 顺时针死区 |
| 0x1B | CCW Dead Zone | 1 | 0 | 0-10 | step | 逆时针死区 |
| **0x1F** | **Offset** | **2** | **0** | **-2048~2047** | **step** | **位置修正/中点偏移** ⭐ |
| 0x21 | Mode | 1 | 0 | 0-3 | - | 工作模式 |
| 0x24 | Overload Protection Time | 2 | 500 | 100-30000 | ms | 过载保护时间 |
| 0x26 | Overload Protection Torque | 2 | 700 | 50-1000 | - | 过载保护扭矩 |

## SRAM 区域（掉电不保存）

| 地址 | 名称 | 字节数 | 默认值 | 访问 | 范围 | 单位 | 说明 |
|------|------|--------|--------|------|------|------|------|
| **0x28** | **Torque Enable** | **1** | **0** | **读写** | **0/1/128** | **-** | **扭矩开关 + 一键中点** ⭐ |
| **0x2A** | **Goal Position** | **2** | **0** | **读写** | **0-4095** | **step** | **目标位置** ⭐ |
| **0x2C** | **Goal Time** | **2** | **0** | **读写** | **0-65535** | **ms** | **运行时间** ⭐ |
| **0x2E** | **Goal Speed** | **2** | **0** | **读写** | **0-4095** | **step/s** | **运行速度** ⭐ |
| 0x30 | Torque Limit | 2 | 1000 | 读写 | 0-1000 | - | 扭矩限制 |
| 0x37 | Lock | 1 | 0 | 读写 | 0-1 | - | EEPROM锁定标志 |
| **0x38** | **Present Position** | **2** | **-** | **只读** | **0-4095** | **step** | **当前位置** ⭐ |
| 0x3A | Present Speed | 2 | - | 只读 | - | step/s | 当前速度 |
| 0x3C | Present Load | 2 | - | 只读 | - | - | 当前负载 |
| 0x3E | Present Voltage | 1 | - | 只读 | - | 0.1V | 当前电压 |
| 0x3F | Present Temperature | 1 | - | 只读 | - | °C | 当前温度 |
| 0x40 | Async Write Flag | 1 | 0 | 只读 | - | - | 异步写标志 |
| **0x41** | **Servo Status** | **1** | **-** | **只读** | **0-255** | **-** | **舵机状态** ⭐ |
| **0x42** | **Moving** | **1** | **-** | **只读** | **0-1** | **-** | **移动标志** ⭐ |
| 0x45 | Present Current | 2 | - | 只读 | - | 6.5mA | 当前电流 |

## 状态寄存器 (0x41) 位定义

| 位 | 名称 | 说明 |
|----|------|------|
| Bit 0 | Voltage Error | 电压错误 |
| Bit 1 | Sensor Error | 传感器错误 |
| Bit 2 | Temperature Error | 温度错误 |
| Bit 3 | Current Error | 电流错误 |
| Bit 4 | Angle Error | 角度错误 |
| Bit 5 | Overload Error | 过载错误 |

## 重要说明

### ⭐ 关于中点校准 (0x1F Offset)

**正确方法**（我们已实现）：
```python
# 1. 读取当前位置
current_pos = get_position(servo_id)

# 2. 计算偏移量
offset = 2048 - current_pos

# 3. 解锁EEPROM
write(servo_id, 0x37, 0)

# 4. 写入偏移量到 0x1F
write(servo_id, 0x1F, offset)

# 5. 锁定EEPROM
write(servo_id, 0x37, 1)

# 6. 重新上电生效
```

**错误方法**（之前的实现）：
```python
# ✗ 错误：0x28 是 Torque Enable，不是校准寄存器
write(servo_id, 0x28, 128)
```

### ⭐ 关于位置控制

**完整的位置控制数据包**（6字节）：
```python
# 地址 0x2A: Goal Position (2字节)
# 地址 0x2C: Goal Time (2字节)
# 地址 0x2E: Goal Speed (2字节)

data = [
    position & 0xFF,
    (position >> 8) & 0xFF,
    move_time & 0xFF,
    (move_time >> 8) & 0xFF,
    speed & 0xFF,
    (speed >> 8) & 0xFF
]
write(servo_id, 0x2A, data)
```

### ⭐ 关于使能状态 (0x28)

**0x28 寄存器的三种用法：**

- **0x28 = 0**：失能（电机可以手动转动）
- **0x28 = 1**：使能（电机锁定位置）
- **0x28 = 128**：一键中点校准（将当前位置设为 2048）⭐⭐⭐

**一键中点校准功能：**
```python
# 步骤 1：失能电机，手动摆到物理中点
driver.set_torque_enable(motor_id, False)

# 步骤 2：一键设置中点
driver.write(motor_id, 0x28, 128)  # 当前位置 → 2048

# 步骤 3：立即生效，无需断电！
```

**注意**：某些情况下电机会自动失能：
- 过载保护触发
- 温度过高
- 电压异常
- 通信超时

## 我们的代码验证

✅ **已正确实现的部分**：
- 寄存器地址定义完全正确
- 通信协议正确
- 位置控制正确
- 状态读取正确

✅ **已修正的部分**：
- `set_middle_position` 现在使用正确的 0x1F 寄存器
- EEPROM 锁定/解锁流程正确

✅ **已添加的功能**：
- 电压/温度读取
- 状态诊断
- 移动标志检查
- 定期使能检查

## 参考资料

- [python-st3215](https://github.com/Mickael-Roger/python-st3215)
- [STS_servos (Arduino)](https://github.com/matthieuvigne/STS_servos)
- STS3215 官方文档（extras 目录）

