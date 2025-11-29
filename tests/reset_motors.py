"""
重置电机偏移量 (Offset) 为 0
将电机恢复到出厂默认的中点设置
"""
import sys
sys.path.append('sts_control')
from sts_driver import STSServoSerial
import time
import serial.tools.list_ports

def find_port():
    """自动查找端口"""
    print("正在扫描端口...")
    ports = list(serial.tools.list_ports.comports())
    print(f"发现 {len(ports)} 个端口: {[p.device for p in ports]}")
    for p in ports:
        print(f"尝试连接 {p.device}...")
        try:
            driver = STSServoSerial(p.device, 1000000)
            if driver.ping(1):
                print(f"找到舵机控制器: {p.device}")
                return driver
            driver.close()
        except:
            pass
    return None

def reset_offset(driver, motor_id):
    print(f"重置 Motor {motor_id}...")
    
    # 解锁
    driver._send_packet(motor_id, driver.INST_WRITE, [driver.REG_LOCK, 0])
    time.sleep(0.05)
    
    # 将 Offset (地址 31, 32) 写为 0
    # Offset 是有符号 16 位整数，0 就是 0x00 0x00
    driver._send_packet(motor_id, driver.INST_WRITE, [driver.REG_OFFSET_L, 0, 0])
    time.sleep(0.1)
    
    # 锁定
    driver._send_packet(motor_id, driver.INST_WRITE, [driver.REG_LOCK, 1])
    time.sleep(0.05)
    
    print(f"  ✓ Motor {motor_id} 偏移量已清除")

def main():
    print("="*50)
    print("电机复位工具 - 清除所有偏移量")
    print("="*50)
    
    driver = find_port()
    if not driver:
        print("未找到设备")
        return
    
    print("\n正在清除偏移量...")
    for motor_id in [1, 2, 3, 4]:
        if driver.ping(motor_id):
            reset_offset(driver, motor_id)
        else:
            print(f"Motor {motor_id} 无响应")
            
    print("\n" + "="*50)
    print("偏移量已清除！")
    print("请务必：")
    print("1. 断开舵机电源")
    print("2. 等待几秒")
    print("3. 重新连接电源")
    print("4. 然后再运行校准程序")
    print("="*50)
    
    driver.close()

if __name__ == "__main__":
    main()

