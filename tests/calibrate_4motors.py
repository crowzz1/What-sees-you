"""
4电机完整校准程序 - 手动控制版本
步骤：
1. 为每个电机设置中点为 2048
2. 记录每个电机的 min 和 max
3. 测试移动
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
        print(f"尝试连接 {p.device} ({p.description})...")
        driver = None
        try:
            driver = STSServoSerial(p.device, 1000000)
            if driver.ping(1):
                print(f"找到舵机控制器: {p.device}")
                return driver
            else:
                print(f"Motor 1 没有响应")
                driver.close()
        except Exception as e:
            print(f"连接 {p.device} 失败: {e}")
            if driver:
                try:
                    driver.close()
                except:
                    pass
    print("未找到舵机控制器")
    return None

def set_motor_middle(driver, motor_id, name):
    """设置电机中点为 2048"""
    print(f"\n{'='*60}")
    print(f"设置 Motor {motor_id} ({name}) 中点")
    print(f"{'='*60}")
    
    # 检查响应
    if not driver.ping(motor_id):
        print(f"Motor {motor_id} 无响应，跳过")
        return False
    
    print(f"Motor {motor_id} 响应正常")
    print()
    
    # 失能电机
    print("失能电机...")
    driver.set_torque_enable(motor_id, False)
    time.sleep(0.5)
    print("  电机已失能")
    print()
    
    # 等待用户摆好姿态
    print(f"请将 Motor {motor_id} ({name}) 摆到中立姿态（物理零点）")
    input("摆好后按 Enter 继续...")
    print()
    
    # 读取位置
    driver.set_torque_enable(motor_id, True)
    time.sleep(0.2)
    current_pos = driver.get_position(motor_id)
    driver.set_torque_enable(motor_id, False)
    time.sleep(0.2)
    
    if current_pos == -1:
        print("无法读取位置，尝试重试...")
        time.sleep(0.2)
        driver.set_torque_enable(motor_id, True)
        time.sleep(0.2)
        current_pos = driver.get_position(motor_id)
        driver.set_torque_enable(motor_id, False)
        time.sleep(0.2)
    
    if current_pos == -1:
        print("无法读取位置，跳过此电机")
        return False
    
    print(f"  当前位置: {current_pos}")
    print()
    
    # 执行中点校准
    print("设置中点为 2048...")
    driver.set_middle_position(motor_id)
    time.sleep(0.5)
    
    # 验证
    print("验证...")
    time.sleep(1)
    driver.set_torque_enable(motor_id, True)
    time.sleep(0.2)
    verify_pos = driver.get_position(motor_id)
    driver.set_torque_enable(motor_id, False)
    time.sleep(0.2)
    
    if verify_pos == -1:
        print("  无法读取验证位置")
        return False
    
    print(f"  验证位置: {verify_pos}")
    if abs(verify_pos - 2048) < 100:
        print("  中点设置成功！")
        return True
    else:
        print(f"  位置偏差: {abs(verify_pos - 2048)}")
        return True  # 仍然继续

def calibrate_motor_limits(driver, motor_id, name):
    """记录电机的 min 和 max"""
    print(f"\n{'='*60}")
    print(f"校准 Motor {motor_id} ({name}) 极限位置")
    print(f"{'='*60}")
    
    # 检查响应
    if not driver.ping(motor_id):
        print(f"Motor {motor_id} 无响应，跳过")
        return None
    
    # 清除限制
    print("清除位置限制...")
    driver.clear_position_limits(motor_id)
    time.sleep(0.2)
    
    # 失能电机
    print("失能电机...")
    driver.set_torque_enable(motor_id, False)
    time.sleep(0.5)
    print()
    
    # 记录最小位置
    print(f"用手将 Motor {motor_id} ({name}) 转到最小位置（下极限）")
    print("电机已失能，可以手动转动")
    input("摆好后按 Enter 继续...")
    
    driver.serial.reset_input_buffer()
    driver.serial.reset_output_buffer()
    time.sleep(0.1)
    
    driver.set_torque_enable(motor_id, True)
    time.sleep(0.2)
    min_pos = driver.get_position(motor_id)
    driver.set_torque_enable(motor_id, False)
    time.sleep(0.2)
    
    if min_pos == -1:
        print("无法读取最小位置，尝试重试...")
        time.sleep(0.2)
        driver.set_torque_enable(motor_id, True)
        time.sleep(0.2)
        min_pos = driver.get_position(motor_id)
        driver.set_torque_enable(motor_id, False)
        time.sleep(0.2)
    
    if min_pos == -1:
        print("无法读取最小位置，跳过此电机")
        return None
    
    print(f"  最小位置: {min_pos}")
    print()
    
    # 记录最大位置
    print(f"用手将 Motor {motor_id} ({name}) 转到最大位置（上极限）")
    input("摆好后按 Enter 继续...")
    
    driver.serial.reset_input_buffer()
    driver.serial.reset_output_buffer()
    time.sleep(0.1)
    
    driver.set_torque_enable(motor_id, True)
    time.sleep(0.2)
    max_pos = driver.get_position(motor_id)
    driver.set_torque_enable(motor_id, False)
    time.sleep(0.2)
    
    if max_pos == -1:
        print("无法读取最大位置，尝试重试...")
        time.sleep(0.2)
        driver.set_torque_enable(motor_id, True)
        time.sleep(0.2)
        max_pos = driver.get_position(motor_id)
        driver.set_torque_enable(motor_id, False)
        time.sleep(0.2)
    
    if max_pos == -1:
        print("无法读取最大位置，跳过此电机")
        return None
    
    print(f"  最大位置: {max_pos}")
    print()
    
    # 显示结果
    print(f"Motor {motor_id} ({name}) 校准结果:")
    print(f"  center: 2048  (已通过中点设置固定)")
    print(f"  min: {min_pos}")
    print(f"  max: {max_pos}")
    
    # 显示运动范围（中点已设为2048，数值跨越0是正常的）
    if min_pos < max_pos:
        print(f"  范围: {min_pos} -> 2048 -> {max_pos}")
        print(f"  总行程: {max_pos - min_pos} 步")
    else:
        print(f"  范围: {min_pos} -> 2048 -> {max_pos} (编码器数值跨越0，但运动正常)")
        print(f"  总行程: {(4096 - min_pos) + max_pos} 步")
    
    return {
        'center': 2048,
        'min': min_pos,
        'max': max_pos,
        'name': name
    }

def test_movement(driver, motor_id, data):
    """测试电机移动"""
    if not data:
        return
    
    print(f"\n测试 Motor {motor_id} ({data['name']})...")
    driver.set_torque_enable(motor_id, True)
    time.sleep(0.5)
    
    center_actual = 2048
    min_pos = data['min']
    max_pos = data['max']
    
    # 1. 移动到中间位置
    print(f"  -> 中间位置 ({center_actual})")
    driver.set_position(motor_id, center_actual, move_time=100)
    time.sleep(2)
    
    # 2. 移动到最小位置
    print(f"  -> 最小位置 ({min_pos})")
    driver.set_position(motor_id, min_pos, move_time=100)
    time.sleep(2)
    
    # 3. 回到中间位置
    print(f"  -> 中间位置 ({center_actual})")
    driver.set_position(motor_id, center_actual, move_time=100)
    time.sleep(2)
    
    # 4. 移动到最大位置
    print(f"  -> 最大位置 ({max_pos})")
    driver.set_position(motor_id, max_pos, move_time=100)
    time.sleep(2)
    
    # 5. 回到中间位置
    print(f"  -> 中间位置 ({center_actual})")
    driver.set_position(motor_id, center_actual, move_time=100)
    time.sleep(1)
    
    driver.set_torque_enable(motor_id, False)
    print(f"  Motor {motor_id} 测试完成 (已失能)")

def main():
    print("="*60)
    print("4电机完整校准工具 - 手动控制版本")
    print("="*60)
    print()
    print("校准流程：")
    print("  1. 为每个电机设置中点为 2048")
    print("  2. 记录每个电机的 min 和 max")
    print("  3. 测试移动")
    print()
    print("注意：每一步都需要你按 Enter 才会继续")
    print()
    input("按 Enter 开始...")
    
    # 连接
    driver = find_port()
    if not driver:
        print("未找到设备")
        return
    
    print("设备已连接")
    print()
    
    motors = [
        (1, "基座"),
        (2, "肩部"),
        (3, "肘部"),
        (4, "腕部")
    ]
    
    # === 第一步：设置所有电机中点 ===
    print("\n" + "="*60)
    print("第一步：设置所有电机中点为 2048")
    print("="*60)
    print()
    
    middle_set = {}
    for mid, name in motors:
        if set_motor_middle(driver, mid, name):
            middle_set[mid] = True
        else:
            middle_set[mid] = False
        print()
    
    print("\n中点设置完成！")
    print()
    input("按 Enter 继续到下一步...")
    
    # === 第二步：记录所有电机的 min/max ===
    print("\n" + "="*60)
    print("第二步：记录所有电机的 min 和 max")
    print("="*60)
    print()
    
    results = {}
    for mid, name in motors:
        if middle_set.get(mid, False):
            data = calibrate_motor_limits(driver, mid, name)
            if data:
                results[mid] = data
        else:
            print(f"\n跳过 Motor {mid} ({name}) - 中点设置失败")
        print()
    
    # === 显示最终结果 ===
    print("\n" + "="*60)
    print("校准完成！")
    print("="*60)
    print()
    print("请更新配置文件:")
    print()
    print("MOTOR_CALIBRATION = {")
    for mid, data in results.items():
        print(f"    {mid}: {{'center': {data['center']}, 'min': {data['min']}, 'max': {data['max']}, 'name': '{data['name']}'}},")
    print("}")
    print()
    
    # === 测试移动 ===
    if results:
        print("="*60)
        test = input("是否测试已校准电机的移动？(y/n): ").strip().lower()
        if test == 'y':
            print("\n开始测试移动...")
            for mid, data in results.items():
                test_movement(driver, mid, data)
                print()
            print("所有测试完成！")
    
    driver.close()
    print("\n完成")

if __name__ == "__main__":
    main()

