# ESP32 控制 MKS-SERVO42C 机械臂项目

## 项目简介
本项目使用 ESP32 微控制器通过串口控制 MKS-SERVO42C 闭环步进电机驱动器，用于机械臂控制。

## MKS-SERVO42C 特性
- 内置 FOC (Field-Oriented Control) 算法
- 支持位置/速度/力矩闭环控制
- 串口通信控制
- 工作电压：7-28V
- 可调电流：0-3000mA
- 细分：1-256
- 最大转速：1000RPM
- 角度分辨率：0.08度

## 硬件连接

### ESP32 与 SERVO42C 接线
| ESP32 引脚 | SERVO42C 引脚 | 说明 |
|-----------|--------------|------|
| GPIO17 (TX2) | RX | 串口发送 |
| GPIO16 (RX2) | TX | 串口接收 |
| GND | GND | 共地 |

### 电源
- SERVO42C 需要独立 7-28V 电源供电
- ESP32 可使用 USB 或独立 5V 电源
- **注意：必须共地！**

## 软件环境

### Arduino IDE 方式
1. 安装 ESP32 开发板支持
2. 选择板子：ESP32 Dev Module
3. 安装库：无需额外库（使用 HardwareSerial）

### PlatformIO 方式
```ini
[env:esp32dev]
platform = espressif32
board = esp32dev
framework = arduino
monitor_speed = 115200
```

## 串口命令协议

### 基本命令格式
命令通过串口发送，波特率默认为 38400（可在 SERVO42C 中配置）

### 常用命令示例
```
# 位置控制模式
设置目标位置：P=1000
查询当前位置：?P

# 速度控制模式
设置速度：V=500
查询当前速度：?V

# 电流设置
设置保持电流：H=800
设置运行电流：R=1500
```

详细命令请参考 MKS-SERVO42C 用户手册。

## 使用说明

### 基础测试
1. 上传 `basic_control.ino` 到 ESP32
2. 打开串口监视器（115200 波特率）
3. 输入命令测试电机响应

### 机械臂控制
1. 根据你的机械臂自由度数量配置电机数量
2. 修改 `robotic_arm_control.ino` 中的关节参数
3. 实现运动学解算和轨迹规划

## 注意事项

1. **初次使用建议**：
   - 先使用 MKS SERVO42C CONTROL TOOL 配置电机参数
   - 设置合适的电流值（避免过热）
   - 测试电机方向和行程范围

2. **安全提示**：
   - 调试时使用较低速度和电流
   - 添加限位保护
   - 确保机械臂有足够的活动空间

3. **性能优化**：
   - 合理设置 PID 参数
   - 使用合适的细分值
   - 考虑加速度曲线

## 文件说明

- `basic_control.ino` - 基础串口控制示例
- `robotic_arm_control.ino` - 多轴机械臂控制示例
- `servo42c_command.h` - 命令封装库
- `examples/` - 更多示例代码

## 参考资源

- [MKS-SERVO42C GitHub](https://github.com/makerbase-mks/MKS-SERVO42C)
- [用户手册](https://github.com/makerbase-mks/MKS-SERVO42C/tree/MKS-SERVO42C-V1.1/User%20Manual)
- [控制工具](https://github.com/makerbase-mks/MKS-SERVO42C/tree/MKS-SERVO42C-V1.1/MKS%20SERVO42C%20CONTROL%20TOOL)

## 技术支持

如有问题，请参考：
1. MKS-SERVO42C 官方文档
2. ESP32 官方文档
3. 相关论坛和社区

## 许可证

MIT License




