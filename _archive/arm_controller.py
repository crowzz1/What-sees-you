"""
ESP32 机械臂控制器
通过串口发送命令控制4轴机械臂
"""

import serial
import time
import threading
from queue import Queue


class ArmController:
    """
    机械臂控制器 - 串口通信
    """
    
    def __init__(self, port='COM3', baudrate=115200):
        """
        初始化机械臂控制器
        
        Args:
            port: ESP32串口端口 (Windows: 'COM3', Linux/Mac: '/dev/ttyUSB0')
            baudrate: 波特率 (默认115200)
        """
        self.port = port
        self.baudrate = baudrate
        self.serial = None
        self.connected = False
        
        # 命令队列（避免命令冲突）
        self.command_queue = Queue()
        self.running = False
        self.send_thread = None
        
        # 当前位置（角度）
        self.current_angles = [0.0, 0.0, 0.0, 0.0]  # 基座, 大臂, 小臂, 手腕
        
        # 连接
        self.connect()
    
    def connect(self):
        """连接到ESP32"""
        try:
            print(f"正在连接到 ESP32 ({self.port})...")
            self.serial = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                timeout=1
            )
            time.sleep(2)  # 等待ESP32重启
            
            # 清空缓冲区
            self.serial.reset_input_buffer()
            self.serial.reset_output_buffer()
            
            self.connected = True
            print(f"✓ 已连接到 ESP32")
            
            # 启动发送线程
            self.running = True
            self.send_thread = threading.Thread(target=self._send_loop, daemon=True)
            self.send_thread.start()
            
            return True
            
        except Exception as e:
            print(f"✗ 连接失败: {e}")
            self.connected = False
            return False
    
    def _send_loop(self):
        """命令发送循环（在独立线程中）"""
        while self.running:
            if not self.command_queue.empty():
                command = self.command_queue.get()
                self._send_command(command)
            time.sleep(0.01)  # 100Hz
    
    def _send_command(self, command):
        """发送命令到ESP32"""
        if not self.connected:
            return False
        
        try:
            self.serial.write(f"{command}\n".encode())
            time.sleep(0.01)  # 短暂延迟
            return True
        except Exception as e:
            print(f"发送命令失败: {e}")
            return False
    
    def send_command_sync(self, command):
        """同步发送命令（立即发送）"""
        return self._send_command(command)
    
    def send_command_async(self, command):
        """异步发送命令（放入队列）"""
        self.command_queue.put(command)
    
    def enable_all(self):
        """使能所有电机"""
        print("使能所有电机...")
        return self.send_command_sync("enable")
    
    def disable_all(self):
        """失能所有电机（可手动转动）"""
        print("失能所有电机...")
        return self.send_command_sync("disable")
    
    def stop_all(self):
        """停止所有电机"""
        print("停止所有电机...")
        return self.send_command_sync("stop")
    
    def enable_motor(self, motor_num):
        """使能单个电机"""
        print(f"使能电机{motor_num}...")
        return self.send_command_sync(f"en{motor_num}")
    
    def stop_motor(self, motor_num):
        """停止单个电机"""
        return self.send_command_sync(f"stop{motor_num}")
    
    def move_to_angles(self, base=None, arm1=None, arm2=None, wrist=None, speed=80):
        """
        移动到指定角度
        
        Args:
            base: 基座角度 (-180 到 180)
            arm1: 大臂角度
            arm2: 小臂角度
            wrist: 手腕角度
            speed: 速度 (1-127)
        """
        commands = []
        
        if base is not None:
            direction = 'f' if base > 0 else 'r'
            commands.append(f"m1{direction}{speed}")
            self.current_angles[0] = base
        
        if arm1 is not None:
            direction = 'f' if arm1 > 0 else 'r'
            commands.append(f"m2{direction}{speed}")
            self.current_angles[1] = arm1
        
        if arm2 is not None:
            direction = 'f' if arm2 > 0 else 'r'
            commands.append(f"m3{direction}{speed}")
            self.current_angles[2] = arm2
        
        if wrist is not None:
            direction = 'f' if wrist > 0 else 'r'
            commands.append(f"m4{direction}{speed}")
            self.current_angles[3] = wrist
        
        # 发送命令
        for cmd in commands:
            self.send_command_async(cmd)
    
    def read_position(self):
        """读取所有电机位置"""
        return self.send_command_sync("position")
    
    def read_angle(self, motor_num, timeout=1.0):
        """
        读取单个电机的角度
        
        Args:
            motor_num: 电机编号（1-4）
            timeout: 超时时间（秒）
        
        Returns:
            角度值（度），失败返回None
        """
        try:
            # 清空输入缓冲区
            self.serial.reset_input_buffer()
            
            # 发送位置查询命令
            cmd = f"pos{motor_num}\n"
            self.serial.write(cmd.encode())
            
            # 读取响应
            start_time = time.time()
            while time.time() - start_time < timeout:
                if self.serial.in_waiting:
                    line = self.serial.readline().decode('utf-8', errors='ignore').strip()
                    
                    # 查找包含"位置:"的行
                    if "位置:" in line and "相对零点" in line:
                        # 解析: "位置: -11.2° (相对零点)"
                        parts = line.split("位置:")
                        if len(parts) > 1:
                            angle_str = parts[1].split("°")[0].strip()
                            try:
                                return float(angle_str)
                            except ValueError:
                                pass
                time.sleep(0.01)
            
            return None
            
        except Exception as e:
            print(f"读取角度失败: {e}")
            return None
    
    def set_zero_position(self, motor_num=None):
        """
        设置零点位置
        
        Args:
            motor_num: 电机编号（1-4），None表示所有电机
        """
        if motor_num is None:
            print("设置所有电机零点...")
            return self.send_command_sync("setzero")
        else:
            print(f"设置电机{motor_num}零点...")
            return self.send_command_sync(f"setzero{motor_num}")
    
    def goto_angle(self, motor_num, angle, speed=80, closed_loop=True, tolerance=5.0, max_iterations=20, precise_mode=True):
        """
        移动到指定角度（相对零点）
        
        Args:
            motor_num: 电机编号（1-4）
            angle: 目标角度（度），相对于零点
            speed: 速度（1-127）
            closed_loop: 是否使用闭环控制（Python端，不推荐）
            tolerance: 容差（度）
            max_iterations: 最大迭代次数
            precise_mode: 是否使用精确模式（0xFD位置命令，推荐！）
        """
        # 精确模式（推荐） - 使用电机硬件闭环
        if precise_mode:
            cmd = f"pgoto{motor_num}:{angle}:{speed}"
            print(f"电机{motor_num}精确移动到{angle}° (位置模式)...")
            return self.send_command_sync(cmd)
        
        # 开环模式（不准确，不推荐）
        if not closed_loop:
            # 开环模式（旧方式，不准确）
            cmd = f"goto{motor_num}:{angle}:{speed}"
            print(f"电机{motor_num}移动到{angle}°...")
            return self.send_command_sync(cmd)
        
        # 闭环模式（新方式，准确）
        print(f"电机{motor_num}移动到{angle}° (闭环控制)...")
        
        for iteration in range(max_iterations):
            # 停止电机（读取位置前必须停止）
            self.stop_motor(motor_num)
            time.sleep(0.15)  # 等待停稳
            
            # 读取当前角度
            current_angle = self.read_angle(motor_num, timeout=1.0)
            
            if current_angle is None:
                print(f"  ⚠ 无法读取当前角度 (尝试 {iteration+1}/{max_iterations})")
                # 再试一次
                time.sleep(0.2)
                current_angle = self.read_angle(motor_num, timeout=1.0)
                
                if current_angle is None:
                    continue
            
            # 计算误差
            error = angle - current_angle
            
            # 打印进度
            print(f"  当前: {current_angle:.1f}° → 目标: {angle:.1f}° (误差: {error:.1f}°)")
            
            # 检查是否到达
            if abs(error) < tolerance:
                self.stop_motor(motor_num)
                print(f"  ✓ 到达目标: {current_angle:.1f}° (误差: {error:.1f}°)")
                return True
            
            # 确定方向和速度
            direction = 0 if error > 0 else 1  # 0=正向, 1=反向
            
            # 根据误差调整速度（离目标近时减速）
            if abs(error) < 10:
                adjusted_speed = 20  # 非常慢
                move_time = 0.3
            elif abs(error) < 20:
                adjusted_speed = 30  # 慢速
                move_time = 0.4
            elif abs(error) < 40:
                adjusted_speed = max(40, int(speed * 0.6))  # 中速
                move_time = 0.5
            else:
                adjusted_speed = speed  # 全速
                move_time = 0.6
            
            # 发送运动命令
            cmd = f"m{motor_num}{'f' if direction == 0 else 'r'}{adjusted_speed}\n"
            self.serial.write(cmd.encode())
            
            # 运动一段时间
            time.sleep(move_time)
        
        # 超过最大迭代次数
        self.stop_motor(motor_num)
        print(f"  ⚠ 未能到达目标（{max_iterations}次迭代后）")
        return False
    
    def goto_angles(self, base=None, arm1=None, arm2=None, wrist=None, speed=80, closed_loop=True, precise_mode=True):
        """
        多个电机移动到指定角度
        
        Args:
            base: 基座角度
            arm1: 大臂角度
            arm2: 小臂角度
            wrist: 手腕角度
            speed: 速度
            closed_loop: 是否使用闭环控制（不推荐）
            precise_mode: 是否使用精确模式（推荐！）
        """
        if base is not None:
            self.goto_angle(1, base, speed, closed_loop=closed_loop, precise_mode=precise_mode)
        
        if arm1 is not None:
            self.goto_angle(2, arm1, speed, closed_loop=closed_loop, precise_mode=precise_mode)
        
        if arm2 is not None:
            self.goto_angle(3, arm2, speed, closed_loop=closed_loop, precise_mode=precise_mode)
        
        if wrist is not None:
            self.goto_angle(4, wrist, speed, closed_loop=closed_loop, precise_mode=precise_mode)
    
    def close(self):
        """关闭连接"""
        print("\n关闭机械臂控制器...")
        
        # 停止发送线程
        self.running = False
        if self.send_thread:
            self.send_thread.join(timeout=1)
        
        # 停止并失能电机
        if self.connected:
            self.stop_all()
            time.sleep(0.5)
            self.disable_all()
            time.sleep(0.5)
        
        # 关闭串口
        if self.serial:
            self.serial.close()
        
        self.connected = False
        print("✓ 机械臂控制器已关闭")


def test_arm_controller():
    """测试机械臂控制器"""
    print("=" * 60)
    print("测试机械臂控制器")
    print("=" * 60)
    
    # 创建控制器
    arm = ArmController(port='COM3')  # 修改为你的端口
    
    if not arm.connected:
        print("无法连接到ESP32，退出测试")
        return
    
    try:
        # 使能电机
        arm.enable_all()
        time.sleep(2)
        
        # 测试基座旋转
        print("\n测试基座旋转...")
        arm.move_to_angles(base=45, speed=80)
        time.sleep(3)
        arm.stop_all()
        
        # 测试大臂
        print("\n测试大臂...")
        arm.move_to_angles(arm1=30, speed=80)
        time.sleep(3)
        arm.stop_all()
        
        # 读取位置
        print("\n读取位置...")
        arm.read_position()
        time.sleep(1)
        
    except KeyboardInterrupt:
        print("\n中断测试")
    finally:
        arm.close()


if __name__ == "__main__":
    test_arm_controller()

