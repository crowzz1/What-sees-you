"""
机械臂交互式控制程序
完全用Python控制，不需要Arduino串口监视器
"""

import serial
import time
import sys


class SimpleArmController:
    """简单的机械臂控制器"""
    
    def __init__(self, port='COM3', baudrate=115200):
        print("=" * 60)
        print("机械臂交互式控制程序")
        print("=" * 60)
        print(f"\n正在连接到 {port}...")
        
        try:
            self.ser = serial.Serial(port, baudrate, timeout=1)
            time.sleep(2)  # 等待ESP32重启
            
            # 清空缓冲区
            self.ser.reset_input_buffer()
            self.ser.reset_output_buffer()
            
            print("✓ 已连接\n")
            self.connected = True
            
        except Exception as e:
            print(f"✗ 连接失败: {e}")
            self.connected = False
    
    def send_command(self, cmd):
        """发送命令到ESP32"""
        if not self.connected:
            return False
        
        try:
            # 发送命令
            self.ser.write(f"{cmd}\n".encode())
            time.sleep(0.1)
            
            # 读取响应
            response_lines = []
            timeout = time.time() + 2  # 2秒超时
            
            while time.time() < timeout:
                if self.ser.in_waiting > 0:
                    line = self.ser.readline().decode('utf-8', errors='ignore').strip()
                    if line:
                        response_lines.append(line)
                        print(f"  {line}")
                else:
                    time.sleep(0.05)
            
            return True
            
        except Exception as e:
            print(f"✗ 发送失败: {e}")
            return False
    
    def enable_all(self):
        """使能所有电机"""
        print("\n使能所有电机...")
        return self.send_command("enable")
    
    def disable_all(self):
        """失能所有电机"""
        print("\n失能所有电机...")
        return self.send_command("disable")
    
    def stop_all(self):
        """停止所有电机"""
        print("\n停止所有电机...")
        return self.send_command("stop")
    
    def move_motor(self, motor_num, direction, speed=60):
        """
        移动单个电机
        
        Args:
            motor_num: 1-4
            direction: 'f' 或 'r'
            speed: 1-127
        """
        cmd = f"m{motor_num}{direction}{speed}"
        print(f"\n电机{motor_num} {'正向' if direction == 'f' else '反向'} 速度{speed}")
        return self.send_command(cmd)
    
    def stop_motor(self, motor_num):
        """停止单个电机"""
        print(f"\n停止电机{motor_num}...")
        return self.send_command(f"stop{motor_num}")
    
    def read_position(self):
        """读取所有位置"""
        print("\n读取位置...")
        return self.send_command("position")
    
    def set_zero(self, motor_num=None):
        """设置零点"""
        if motor_num:
            print(f"\n设置电机{motor_num}零点...")
            return self.send_command(f"setzero{motor_num}")
        else:
            print("\n设置所有电机零点...")
            return self.send_command("setzero")
    
    def help(self):
        """显示帮助"""
        print("\n" + "=" * 60)
        print("可用命令")
        print("=" * 60)
        print("\n基本控制:")
        print("  enable / en    - 使能所有电机")
        print("  disable / dis  - 失能所有电机")
        print("  stop / s       - 停止所有电机")
        print("\n单个电机:")
        print("  1f / 1r        - 电机1 正向/反向 (默认速度60)")
        print("  2f / 2r        - 电机2 正向/反向")
        print("  3f / 3r        - 电机3 正向/反向")
        print("  4f / 4r        - 电机4 正向/反向")
        print("  1s / 2s / 3s / 4s  - 停止单个电机")
        print("\n速度控制:")
        print("  1f80 / 1r80    - 电机1 正向/反向 速度80")
        print("\n位置和零点:")
        print("  pos            - 读取所有位置")
        print("  zero1 / zero   - 设置零点")
        print("\n其他:")
        print("  help / h / ?   - 显示此帮助")
        print("  quit / q       - 退出程序")
        print("=" * 60)
    
    def parse_command(self, cmd):
        """解析并执行命令"""
        cmd = cmd.strip().lower()
        
        if not cmd:
            return True
        
        # 退出
        if cmd in ['quit', 'q', 'exit']:
            return False
        
        # 帮助
        if cmd in ['help', 'h', '?']:
            self.help()
            return True
        
        # 使能/失能
        if cmd in ['enable', 'en']:
            self.enable_all()
        elif cmd in ['disable', 'dis']:
            self.disable_all()
        elif cmd in ['stop', 's']:
            self.stop_all()
        
        # 位置
        elif cmd in ['pos', 'position']:
            self.read_position()
        
        # 零点
        elif cmd == 'zero':
            self.set_zero()
        elif cmd.startswith('zero'):
            try:
                num = int(cmd[4])
                self.set_zero(num)
            except:
                print("✗ 无效命令")
        
        # 单个电机控制
        elif len(cmd) >= 2 and cmd[0] in '1234':
            motor_num = int(cmd[0])
            
            # 停止
            if cmd[1] == 's':
                self.stop_motor(motor_num)
            
            # 移动
            elif cmd[1] in ['f', 'r']:
                direction = cmd[1]
                
                # 提取速度
                speed = 60  # 默认
                if len(cmd) > 2:
                    try:
                        speed = int(cmd[2:])
                    except:
                        pass
                
                self.move_motor(motor_num, direction, speed)
            else:
                print("✗ 无效命令")
        
        # 直接发送原始命令
        else:
            print(f"\n发送原始命令: {cmd}")
            self.send_command(cmd)
        
        return True
    
    def run(self):
        """运行交互式控制"""
        if not self.connected:
            print("\n无法连接到ESP32")
            return
        
        print("\n" + "=" * 60)
        print("交互式控制已启动")
        print("=" * 60)
        print("\n输入命令（输入 'help' 查看帮助，'quit' 退出）")
        print("提示: 快捷命令 - 1f(电机1正向), 1r(反向), 1s(停止)")
        print("=" * 60)
        
        try:
            while True:
                try:
                    # 读取命令
                    cmd = input("\n命令 > ").strip()
                    
                    # 执行命令
                    if not self.parse_command(cmd):
                        break
                    
                except KeyboardInterrupt:
                    print("\n\n检测到 Ctrl+C")
                    break
                
                except Exception as e:
                    print(f"✗ 错误: {e}")
        
        finally:
            self.cleanup()
    
    def cleanup(self):
        """清理"""
        print("\n" + "=" * 60)
        print("正在关闭...")
        print("=" * 60)
        
        # 停止并失能
        if self.connected:
            print("\n停止所有电机...")
            self.stop_all()
            time.sleep(0.5)
            
            print("失能所有电机...")
            self.disable_all()
            time.sleep(0.5)
        
        # 关闭串口
        if hasattr(self, 'ser') and self.ser.is_open:
            self.ser.close()
        
        print("\n✓ 已关闭")
        print("再见！\n")


def main():
    """主函数"""
    # 检查端口参数
    port = 'COM3'
    
    if len(sys.argv) > 1:
        port = sys.argv[1]
    else:
        print("使用默认端口: COM3")
        print("如需指定端口: python arm_control_interactive.py COM4\n")
    
    # 创建控制器
    controller = SimpleArmController(port=port)
    
    # 运行
    if controller.connected:
        controller.run()


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\n程序错误: {e}")
        import traceback
        traceback.print_exc()







