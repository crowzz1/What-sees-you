"""
Motor 2 简化校准 - 只记录 min/max
先设置中点为 2048，再记录 min 和 max
"""
import sys
sys.path.append('sts_control')
from sts_driver import STSServoSerial
import time

def main():
    print("="*60)
    print("Motor 2 (肩部) 完整校准")
    print("="*60)
    print()
    print("步骤：")
    print("  1. 设置中点为 2048")
    print("  2. 记录 min 和 max")
    print()
    
    # 连接电机
    try:
        driver = STSServoSerial("COM4", 1000000)
        print("✓ 已连接到 COM4")
    except Exception as e:
        print(f"✗ 连接失败: {e}")
        return
    
    # 检查电机响应
    if not driver.ping(2):
        print("✗ Motor 2 无响应")
        driver.close()
        return
    print("✓ Motor 2 响应正常")
    print()
    
    # === 第一步：设置中点 ===
    print("="*60)
    print("第一步：设置中点")
    print("="*60)
    print()
    
    # 失能电机
    print("失能电机...")
    driver.set_torque_enable(2, False)
    time.sleep(0.5)
    print("  ✓ 电机已失能")
    print()
    
    # 等待用户摆好姿态
    print("请将 Motor 2 摆到中立姿态（物理零点）")
    print("等待 5 秒...")
    for i in range(5, 0, -1):
        print(f"  {i}...")
        time.sleep(1)
    print()
    
    # 读取位置
    driver.set_torque_enable(2, True)
    time.sleep(0.1)
    current_pos = driver.get_position(2)
    driver.set_torque_enable(2, False)
    time.sleep(0.1)
    
    if current_pos == -1:
        print("✗ 无法读取位置")
        driver.close()
        return
    
    print(f"当前位置: {current_pos}")
    print()
    
    # 执行中点校准
    print("设置中点为 2048...")
    driver.set_middle_position(2)
    
    print()
    print("验证...")
    time.sleep(1)
    
    # 验证
    driver.set_torque_enable(2, True)
    time.sleep(0.1)
    verify_pos = driver.get_position(2)
    driver.set_torque_enable(2, False)
    
    if verify_pos == -1:
        print("  ✗ 无法读取验证位置")
    else:
        print(f"  验证位置: {verify_pos}")
        if abs(verify_pos - 2048) < 100:
            print("  ✓ 中点设置成功！")
        else:
            print(f"  ⚠ 位置偏差: {abs(verify_pos - 2048)}")
    
    print()
    
    # === 第二步：记录 min/max ===
    print("="*60)
    print("第二步：记录 min 和 max")
    print("="*60)
    print()
    
    # 清除限制
    driver.clear_position_limits(2)
    print()
    
    # 失能电机
    print("失能电机，等待 3 秒...")
    driver.set_torque_enable(2, False)
    time.sleep(3)
    print()
    
    # 记录最小位置
    print("步骤 1: 用手将肩部转到最小位置（下极限）")
    print("        电机已失能，可以手动转动")
    print("        等待 5 秒...")
    for i in range(5, 0, -1):
        print(f"  {i}...")
        time.sleep(1)
    
    driver.set_torque_enable(2, True)
    time.sleep(0.1)
    min_pos = driver.get_position(2)
    driver.set_torque_enable(2, False)
    time.sleep(0.1)
    
    if min_pos == -1:
        print("✗ 无法读取最小位置")
        driver.close()
        return
    
    print(f"  ✓ 最小位置: {min_pos}")
    print()
    
    # 记录最大位置
    print("步骤 2: 用手将肩部转到最大位置（上极限）")
    print("        等待 5 秒...")
    for i in range(5, 0, -1):
        print(f"  {i}...")
        time.sleep(1)
    
    driver.set_torque_enable(2, True)
    time.sleep(0.1)
    max_pos = driver.get_position(2)
    driver.set_torque_enable(2, False)
    time.sleep(0.1)
    
    if max_pos == -1:
        print("✗ 无法读取最大位置")
        driver.close()
        return
    
    print(f"  ✓ 最大位置: {max_pos}")
    print()
    
    # 显示结果
    print("="*60)
    print("校准结果")
    print("="*60)
    print(f"Motor 2 (肩部):")
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
    
    print()
    print("="*60)
    print("更新配置")
    print("="*60)
    print("MOTOR_CALIBRATION = {")
    print(f"    1: {{'center': 2048, 'min': ...}},")
    print(f"    2: {{'center': 2048, 'min': {min_pos}, 'max': {max_pos}, 'name': '肩部'}},")
    print("}")
    print()
    
    # 自动测试移动
    print("5 秒后自动测试移动...")
    time.sleep(5)
    
    print("\n测试移动...")
    driver.set_torque_enable(2, True)
    time.sleep(0.5)
    
    print("  -> 中间位置 (2048)")
    driver.set_position(2, 2048)
    time.sleep(2)
    
    print(f"  -> 最小位置 ({min_pos})")
    driver.set_position(2, min_pos)
    time.sleep(2)
    
    print("  -> 中间位置 (2048)")
    driver.set_position(2, 2048)
    time.sleep(2)
    
    print(f"  -> 最大位置 ({max_pos})")
    driver.set_position(2, max_pos)
    time.sleep(2)
    
    print("  -> 中间位置 (2048)")
    driver.set_position(2, 2048)
    time.sleep(2)
    
    driver.set_torque_enable(2, False)
    print("  ✓ 测试完成")
    
    driver.close()
    print("\n✓ 完成")

if __name__ == "__main__":
    main()

