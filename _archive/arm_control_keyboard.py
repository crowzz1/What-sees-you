"""
机械臂键盘控制程序
使用键盘直接控制，无需输入命令
"""

import serial
import time
import sys
import threading

try:
    import keyboard
    KEYBOARD_AVAILABLE = True
except ImportError:
    KEYBOARD_AVAILABLE = False
    print("提示: 安装keyboard库以使用键盘控制")
    print("  pip install keyboard")


class KeyboardArmController:
    """键盘控制机械臂"""
    
    def __init__(self, port='COM3', baudrate=115200):
        print("=" * 60)
        print("机械臂键盘控制程序")
        print("=" * 60)
        print(f"\n正在连接到 {port}...")
        
        try:
            self.ser = serial.Serial(port, baudrate, timeout=0.5)
            time.sleep(2)
            self.ser.reset_input_buffer()
            self.ser.reset_output_buffer()
            print("✓ 已连接\n")
            self.connected = True
        except Exception as e:
            print(f"✗ 连接失败: {e}")
            self.connected = False
            return
        
        self.running = False
        self.motor_moving = [False, False, False, False]
        
        # 启动读取线程
        self.read_thread = threading.Thread(target=self._read_loop, daemon=True)
        self.read_thread.start()
    
    def _read_loop(self):
        """读取ESP32响应"""
        while self.connected and self.running:
            try:
                if self.ser.in_waiting > 0:
                    line = self.ser.readline().decode('utf-8', errors='ignore').strip()
                    if line and not line.startswith('→'):
                        print(f"  {line}")
            except:
                pass
            time.sleep(0.05)
    
    def send_command(self, cmd):
        """发送命令"""
        try:
            self.ser.write(f"{cmd}\n".encode())
            return True
        except:
            return False
    
    def print_help(self):
        """打印键盘说明"""
        print("\n" + "=" * 60)
        print("键盘控制说明")
        print("=" * 60)
        print("\n电机1（基座）:")
        print("  Q - 正向    A - 反向")
        print("\n电机2（大臂）:")
        print("  W - 正向    S - 反向")
        print("\n电机3（小臂）:")
        print("  E - 正向    D - 反向")
        print("\n电机4（手腕）:")
        print("  R - 正向    F - 反向")
        print("\n控制:")
        print("  SPACE - 停止所有电机")
        print("  Z - 使能所有")
        print("  X - 失能所有")
        print("  P - 读取位置")
        print("  ESC - 退出")
        print("\n速度:")
        print("  1-9 - 设置速度 (1=慢, 9=快)")
        print("=" * 60)
    
    def run(self):
        """运行键盘控制"""
        if not self.connected:
            return
        
        if not KEYBOARD_AVAILABLE:
            print("\n✗ keyboard库未安装")
            print("  安装: pip install keyboard")
            return
        
        self.running = True
        self.print_help()
        
        print("\n准备就绪！按键控制电机...")
        print("(提示: 程序可能需要管理员权限)\n")
        
        current_speed = 60
        
        try:
            # 使能电机
            print("自动使能所有电机...")
            self.send_command("enable")
            time.sleep(2)
            
            print(f"\n当前速度: {current_speed}")
            print("开始控制！\n")
            
            while self.running:
                # 速度调整 (1-9)
                for i in range(1, 10):
                    if keyboard.is_pressed(str(i)):
                        current_speed = 20 + i * 10
                        print(f"\n速度设置为: {current_speed}")
                        time.sleep(0.3)
                
                # 电机1 (Q/A)
                if keyboard.is_pressed('q'):
                    if not self.motor_moving[0]:
                        print("电机1 正向")
                        self.send_command(f"m1f{current_speed}")
                        self.motor_moving[0] = True
                elif keyboard.is_pressed('a'):
                    if not self.motor_moving[0]:
                        print("电机1 反向")
                        self.send_command(f"m1r{current_speed}")
                        self.motor_moving[0] = True
                else:
                    if self.motor_moving[0]:
                        self.send_command("stop1")
                        self.motor_moving[0] = False
                
                # 电机2 (W/S)
                if keyboard.is_pressed('w'):
                    if not self.motor_moving[1]:
                        print("电机2 正向")
                        self.send_command(f"m2f{current_speed}")
                        self.motor_moving[1] = True
                elif keyboard.is_pressed('s'):
                    if not self.motor_moving[1]:
                        print("电机2 反向")
                        self.send_command(f"m2r{current_speed}")
                        self.motor_moving[1] = True
                else:
                    if self.motor_moving[1]:
                        self.send_command("stop2")
                        self.motor_moving[1] = False
                
                # 电机3 (E/D)
                if keyboard.is_pressed('e'):
                    if not self.motor_moving[2]:
                        print("电机3 正向")
                        self.send_command(f"m3f{current_speed}")
                        self.motor_moving[2] = True
                elif keyboard.is_pressed('d'):
                    if not self.motor_moving[2]:
                        print("电机3 反向")
                        self.send_command(f"m3r{current_speed}")
                        self.motor_moving[2] = True
                else:
                    if self.motor_moving[2]:
                        self.send_command("stop3")
                        self.motor_moving[2] = False
                
                # 电机4 (R/F)
                if keyboard.is_pressed('r'):
                    if not self.motor_moving[3]:
                        print("电机4 正向")
                        self.send_command(f"m4f{current_speed}")
                        self.motor_moving[3] = True
                elif keyboard.is_pressed('f'):
                    if not self.motor_moving[3]:
                        print("电机4 反向")
                        self.send_command(f"m4r{current_speed}")
                        self.motor_moving[3] = True
                else:
                    if self.motor_moving[3]:
                        self.send_command("stop4")
                        self.motor_moving[3] = False
                
                # 空格 - 停止所有
                if keyboard.is_pressed('space'):
                    print("\n停止所有电机")
                    self.send_command("stop")
                    self.motor_moving = [False, False, False, False]
                    time.sleep(0.3)
                
                # Z - 使能
                if keyboard.is_pressed('z'):
                    print("\n使能所有电机")
                    self.send_command("enable")
                    time.sleep(0.5)
                
                # X - 失能
                if keyboard.is_pressed('x'):
                    print("\n失能所有电机")
                    self.send_command("disable")
                    time.sleep(0.5)
                
                # P - 位置
                if keyboard.is_pressed('p'):
                    print("\n读取位置:")
                    self.send_command("position")
                    time.sleep(1)
                
                # ESC - 退出
                if keyboard.is_pressed('esc'):
                    print("\n退出...")
                    break
                
                time.sleep(0.05)
        
        except KeyboardInterrupt:
            print("\n\n检测到 Ctrl+C")
        
        finally:
            self.cleanup()
    
    def cleanup(self):
        """清理"""
        print("\n正在关闭...")
        self.running = False
        
        if self.connected:
            self.send_command("stop")
            time.sleep(0.5)
            self.send_command("disable")
            time.sleep(0.5)
            self.ser.close()
        
        print("✓ 已关闭")


def main():
    port = 'COM3' if len(sys.argv) <= 1 else sys.argv[1]
    
    controller = KeyboardArmController(port=port)
    
    if controller.connected:
        controller.run()


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\n错误: {e}")
        import traceback
        traceback.print_exc()







