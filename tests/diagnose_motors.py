"""
电机诊断工具
检查电机状态、电压、温度等信息
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
    for p in ports:
        print(f"尝试 {p.device}...")
        try:
            driver = STSServoSerial(p.device, 1000000)
            if driver.ping(1):
                print(f"✓ 找到控制器: {p.device}")
                return driver
            driver.close()
        except Exception as e:
            print(f"✗ {p.device} 失败: {e}")
    return None

def diagnose_motor(driver, motor_id):
    """诊断单个电机"""
    print(f"\n{'='*60}")
    print(f"诊断 Motor {motor_id}")
    print(f"{'='*60}")
    
    # 1. Ping 测试
    print("\n1. 连接测试...")
    if not driver.ping(motor_id):
        print(f"  ✗ Motor {motor_id} 无响应")
        return False
    print(f"  ✓ Motor {motor_id} 响应正常")
    
    # 2. 读取位置
    print("\n2. 位置信息...")
    pos = driver.get_position(motor_id)
    if pos != -1:
        print(f"  当前位置: {pos}")
    else:
        print(f"  ✗ 无法读取位置")
    
    # 3. 读取电压
    print("\n3. 电压信息...")
    voltage = driver.read_voltage(motor_id)
    if voltage is not None:
        print(f"  当前电压: {voltage:.1f}V")
        if voltage < 6.0:
            print(f"  ⚠ 警告：电压过低！")
        elif voltage > 8.4:
            print(f"  ⚠ 警告：电压过高！")
    else:
        print(f"  ✗ 无法读取电压")
    
    # 4. 读取温度
    print("\n4. 温度信息...")
    temp = driver.read_temperature(motor_id)
    if temp is not None:
        print(f"  当前温度: {temp}°C")
        if temp > 65:
            print(f"  ⚠ 警告：温度过高！")
    else:
        print(f"  ✗ 无法读取温度")
    
    # 5. 读取状态
    print("\n5. 错误状态...")
    status = driver.read_status(motor_id)
    if status is not None:
        has_error = False
        for key, value in status.items():
            if value:
                print(f"  ✗ {key} 错误")
                has_error = True
        if not has_error:
            print(f"  ✓ 无错误")
    else:
        print(f"  ✗ 无法读取状态")
    
    # 6. 检查是否在移动
    print("\n6. 移动状态...")
    moving = driver.is_moving(motor_id)
    if moving is not None:
        if moving:
            print(f"  ○ 正在移动")
        else:
            print(f"  ● 已停止")
    else:
        print(f"  ✗ 无法读取移动状态")
    
    # 7. 测试使能
    print("\n7. 使能测试...")
    print(f"  失能电机...")
    driver.set_torque_enable(motor_id, False)
    time.sleep(0.5)
    
    print(f"  使能电机...")
    driver.set_torque_enable(motor_id, True)
    time.sleep(0.5)
    
    # 读取位置确认使能成功
    pos_after = driver.get_position(motor_id)
    if pos_after != -1:
        print(f"  ✓ 使能成功（位置: {pos_after}）")
    else:
        print(f"  ✗ 使能可能失败")
    
    # 8. 小幅移动测试
    print("\n8. 移动测试...")
    if pos_after != -1:
        target = pos_after + 50  # 移动50步
        print(f"  移动到 {target}...")
        driver.set_position(motor_id, target, move_time=500)
        time.sleep(1.0)
        
        final_pos = driver.get_position(motor_id)
        if final_pos != -1:
            error = abs(final_pos - target)
            print(f"  目标: {target}, 实际: {final_pos}, 误差: {error}")
            if error < 10:
                print(f"  ✓ 移动正常")
            else:
                print(f"  ⚠ 误差较大")
        
        # 回到原位
        print(f"  返回原位...")
        driver.set_position(motor_id, pos_after, move_time=500)
        time.sleep(1.0)
    
    # 失能电机
    driver.set_torque_enable(motor_id, False)
    print(f"\n✓ Motor {motor_id} 诊断完成")
    return True

def main():
    print("="*60)
    print("STS3215 电机诊断工具")
    print("="*60)
    
    # 连接
    driver = find_port()
    if not driver:
        print("\n✗ 未找到控制器")
        return
    
    print("\n请输入要诊断的电机ID（用空格分隔，例如: 1 2 3 4）")
    print("或直接按 Enter 诊断电机 1-4")
    
    user_input = input("电机ID: ").strip()
    
    if user_input:
        motor_ids = [int(x) for x in user_input.split()]
    else:
        motor_ids = [1, 2, 3, 4]
    
    # 诊断每个电机
    for motor_id in motor_ids:
        diagnose_motor(driver, motor_id)
    
    # 总结
    print("\n" + "="*60)
    print("诊断完成")
    print("="*60)
    print("\n建议：")
    print("  1. 确保电压在 6.0-8.4V 之间")
    print("  2. 确保温度低于 65°C")
    print("  3. 如果有错误状态，检查机械负载和电源")
    print("  4. 如果无法读取位置，检查串口连接和波特率")
    
    driver.close()

if __name__ == "__main__":
    main()


