"""
STS3215 舵机驱动 - 基于 Feetech 协议
"""
import serial
import time

class STSServoSerial:
    """STS 舵机串口通信类"""
    
    # 指令
    INST_PING = 0x01
    INST_READ = 0x02
    INST_WRITE = 0x03
    
    # 寄存器地址（参考 STS3215 官方文档）
    REG_TORQUE_ENABLE = 0x28       # 扭矩开关
    REG_GOAL_POSITION_L = 0x2A     # 目标位置
    REG_GOAL_TIME_L = 0x2C         # 运行时间
    REG_GOAL_SPEED_L = 0x2E        # 运行速度
    REG_TORQUE_LIMIT_L = 0x30      # 扭矩限制
    REG_LOCK = 0x37                # 锁定标志
    REG_PRESENT_POSITION_L = 0x38  # 当前位置
    REG_PRESENT_SPEED_L = 0x3A     # 当前速度
    REG_PRESENT_LOAD_L = 0x3C      # 当前负载
    REG_PRESENT_VOLTAGE = 0x3E     # 当前电压
    REG_PRESENT_TEMPERATURE = 0x3F # 当前温度
    REG_ASYNC_WRITE_FLAG = 0x40    # 异步写标志
    REG_SERVO_STATUS = 0x41        # 舵机状态
    REG_MOVING_FLAG = 0x42         # 移动标志
    REG_PRESENT_CURRENT_L = 0x45   # 当前电流
    REG_MIN_POSITION_L = 0x09      # 最小位置限制
    REG_MAX_POSITION_L = 0x0B      # 最大位置限制
    REG_OFFSET_L = 0x1F            # 位置修正（中点偏移）
    
    def __init__(self, port, baudrate=1000000, timeout=0.5):
        """初始化串口"""
        self.serial = serial.Serial(
            port=port,
            baudrate=baudrate,
            bytesize=serial.EIGHTBITS,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            timeout=timeout
        )
        time.sleep(0.1)
    
    def _calculate_checksum(self, packet_id, length, instruction, params):
        """计算校验和"""
        checksum = packet_id + length + instruction
        for p in params:
            checksum += p
        return (~checksum) & 0xFF
    
    def _send_packet(self, servo_id, instruction, params):
        """发送数据包"""
        length = len(params) + 2
        checksum = self._calculate_checksum(servo_id, length, instruction, params)
        packet = bytes([0xFF, 0xFF, servo_id, length, instruction] + params + [checksum])
        
        try:
            self.serial.reset_input_buffer()
            self.serial.reset_output_buffer()
            self.serial.write(packet)
            self.serial.flush()
            time.sleep(0.01)
        except Exception as e:
            print(f"发送失败: {e}")
            return False
        return True
    
    def _read_response(self, expected_length=6):
        """读取响应"""
        try:
            if self.serial.in_waiting < expected_length:
                time.sleep(0.05)
            
            if self.serial.in_waiting >= expected_length:
                response = self.serial.read(expected_length)
                if len(response) >= expected_length:
                    return response
        except Exception as e:
            print(f"读取失败: {e}")
        return None
    
    def ping(self, servo_id):
        """Ping 舵机"""
        for attempt in range(3):
            self.serial.reset_input_buffer()
            self.serial.reset_output_buffer()
            time.sleep(0.05)
            
            if self._send_packet(servo_id, self.INST_PING, []):
                response = self._read_response(6)
                if response and len(response) >= 6:
                    if response[0] == 0xFF and response[1] == 0xFF and response[2] == servo_id:
                        return True
            time.sleep(0.1)
        return False
    
    def set_torque_enable(self, servo_id, enable):
        """使能/失能舵机"""
        value = 1 if enable else 0
        self.serial.reset_input_buffer()
        self.serial.reset_output_buffer()
        self._send_packet(servo_id, self.INST_WRITE, [self.REG_TORQUE_ENABLE, value])
        time.sleep(0.05)
    
    def set_position(self, servo_id, position, move_time=0, speed=0):
        """设置目标位置"""
        position = max(0, min(4095, int(position)))
        move_time = max(0, min(65535, int(move_time)))
        speed = max(0, min(4095, int(speed)))
        
        self.serial.reset_input_buffer()
        self.serial.reset_output_buffer()
        
        pos_bytes = [position & 0xFF, (position >> 8) & 0xFF]
        time_bytes = [move_time & 0xFF, (move_time >> 8) & 0xFF]
        speed_bytes = [speed & 0xFF, (speed >> 8) & 0xFF]
        
        values = pos_bytes + time_bytes + speed_bytes
        self._send_packet(servo_id, self.INST_WRITE, [self.REG_GOAL_POSITION_L] + values)
        time.sleep(0.01)
    
    def get_position(self, servo_id):
        """读取当前位置"""
        self.serial.reset_input_buffer()
        self.serial.reset_output_buffer()
        time.sleep(0.05)
        
        if self._send_packet(servo_id, self.INST_READ, [self.REG_PRESENT_POSITION_L, 2]):
            response = self._read_response(8)
            if response and len(response) >= 8:
                pos_l = response[5]
                pos_h = response[6]
                position = pos_l | (pos_h << 8)
                return position
        return -1
    
    def clear_position_limits(self, servo_id):
        """清除位置限制（设为 0-4095）"""
        print(f"清除 Motor {servo_id} 位置限制...")
        # 设置最小位置为 0
        self._send_packet(servo_id, self.INST_WRITE, [self.REG_MIN_POSITION_L, 0x00, 0x00])
        time.sleep(0.1)
        # 设置最大位置为 4095
        self._send_packet(servo_id, self.INST_WRITE, [self.REG_MAX_POSITION_L, 0xFF, 0x0F])
        time.sleep(0.1)
        print(f"  ✓ Motor {servo_id} 限制已清除 (0-4095)")
    
    def set_middle_position(self, servo_id):
        """
        一键设置当前位置为中点 (2048)
        
        STS3215 特殊功能：
        往地址 40 (0x28 = REG_TORQUE_ENABLE) 写入 128，
        会触发"一键中点校准"，将当前角度记为 2048
        
        注意：
        - 写入 0 = 失能扭矩
        - 写入 1 = 使能扭矩
        - 写入 128 = 一键设置中点（特殊功能）
        
        立即生效，无需断电！
        """
        print(f"设置 Motor {servo_id} 中点为 2048...")
        
        # 使用 STS3215 的一键中点校准功能
        # 地址 40 (0x28) 写入 128 = 将当前位置设为 2048
        self._send_packet(servo_id, self.INST_WRITE, [self.REG_TORQUE_ENABLE, 128])
        time.sleep(0.5)  # 等待校准完成
        
        print(f"  ✓ Motor {servo_id} 中点已设置为 2048")
        print(f"  提示：立即生效，无需断电")
        return True
    
    def is_moving(self, servo_id):
        """检查电机是否正在移动"""
        self.serial.reset_input_buffer()
        self.serial.reset_output_buffer()
        time.sleep(0.05)
        
        if self._send_packet(servo_id, self.INST_READ, [self.REG_MOVING_FLAG, 1]):
            response = self._read_response(7)
            if response and len(response) >= 7:
                return response[5] == 1
        return None
    
    def read_voltage(self, servo_id):
        """读取电压（单位：0.1V）"""
        self.serial.reset_input_buffer()
        self.serial.reset_output_buffer()
        time.sleep(0.05)
        
        if self._send_packet(servo_id, self.INST_READ, [self.REG_PRESENT_VOLTAGE, 1]):
            response = self._read_response(7)
            if response and len(response) >= 7:
                voltage = response[5] * 0.1  # 转换为伏特
                return voltage
        return None
    
    def read_temperature(self, servo_id):
        """读取温度（单位：°C）"""
        self.serial.reset_input_buffer()
        self.serial.reset_output_buffer()
        time.sleep(0.05)
        
        if self._send_packet(servo_id, self.INST_READ, [self.REG_PRESENT_TEMPERATURE, 1]):
            response = self._read_response(7)
            if response and len(response) >= 7:
                return response[5]
        return None
    
    def read_status(self, servo_id):
        """
        读取舵机状态
        返回: {'Voltage': bool, 'Sensor': bool, 'Temperature': bool, 
               'Current': bool, 'Angle': bool, 'Overload': bool}
        """
        self.serial.reset_input_buffer()
        self.serial.reset_output_buffer()
        time.sleep(0.05)
        
        if self._send_packet(servo_id, self.INST_READ, [self.REG_SERVO_STATUS, 1]):
            response = self._read_response(7)
            if response and len(response) >= 7:
                status_byte = response[5]
                return {
                    'Voltage': bool(status_byte & 0x01),
                    'Sensor': bool(status_byte & 0x02),
                    'Temperature': bool(status_byte & 0x04),
                    'Current': bool(status_byte & 0x08),
                    'Angle': bool(status_byte & 0x10),
                    'Overload': bool(status_byte & 0x20)
                }
        return None
    
    def close(self):
        """关闭串口"""
        if self.serial and self.serial.is_open:
            self.serial.close()
