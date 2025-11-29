import sys
import time
sys.path.append('sts_control')
from sts_driver import STSServoSerial

def check_directions():
    print("连接机械臂...")
    try:
        driver = STSServoSerial("COM4", 1000000) 
    except Exception as e:
        print(f"连接失败: {e}")
        return

    print("\n========================================")
    print("安全方向测试 (基于当前位置)")
    print("此脚本不使用任何限位设置，直接读取当前位置并进行微量移动")
    print("========================================\n")
    
    # 放松力矩以便用户手动调整到安全位置
    print("正在放松所有电机...")
    for i in range(1, 5):
        driver.set_torque_enable(i, False)
    
    input(">>> 请手动将机械臂扶到一个【安全、中间】的姿态，然后按回车键锁定...")
    
    print("正在锁定电机并读取初始位置...")
    current_pos = {}
    for i in range(1, 5):
        driver.set_torque_enable(i, True)
        pos = driver.get_position(i)
        if pos == -1:
            print(f"警告: 读取电机 {i} 失败，使用默认值 2048")
            current_pos[i] = 2048
        else:
            current_pos[i] = pos
            print(f"电机 {i} 当前位置: {pos}")
    
    time.sleep(1)

    # 定义测试步长
    STEP = 150 

    # --- 测试 M2 (肩部) ---
    print("\n----------------------------------------")
    print(f"当前 M2: {current_pos[2]}")
    target = current_pos[2] + STEP
    input(f"按回车键测试 M2: {current_pos[2]} -> {target} (数值增加)...")
    
    driver.set_position(2, target, speed=200)
    time.sleep(2)
    
    print(">>> 观察 M2 运动方向：")
    print(f"   如果是 【前倾/点头】 ->  dir = 1")
    print(f"   如果是 【后仰/抬头】 ->  dir = -1")
    
    input("按回车键复位 M2...")
    driver.set_position(2, current_pos[2], speed=200)
    time.sleep(1)

    # --- 测试 M3 (肘部) ---
    print("\n----------------------------------------")
    print(f"当前 M3: {current_pos[3]}")
    target = current_pos[3] + STEP
    input(f"按回车键测试 M3: {current_pos[3]} -> {target} (数值增加)...")
    
    driver.set_position(3, target, speed=200)
    time.sleep(2)
    
    print(">>> 观察 M3 运动方向：")
    print(f"   如果是 【向前伸展】 ->  dir = 1")
    print(f"   如果是 【向后折叠】 ->  dir = -1") # 注意这里的描述
    
    input("按回车键复位 M3...")
    driver.set_position(3, current_pos[3], speed=200)
    time.sleep(1)

    # --- 测试 M4 (手腕) ---
    print("\n----------------------------------------")
    print(f"当前 M4: {current_pos[4]}")
    target = current_pos[4] + STEP
    input(f"按回车键测试 M4: {current_pos[4]} -> {target} (数值增加)...")
    
    driver.set_position(4, target, speed=200)
    time.sleep(2)
    
    print(">>> 观察 M4 运动方向：")
    print(f"   如果是 【低头】 ->  dir = 1")
    print(f"   如果是 【抬头】 ->  dir = -1")

    input("按回车键复位 M4...")
    driver.set_position(4, current_pos[4], speed=200)
    time.sleep(1)

    # --- 结束 ---
    print("\n========================================")
    input("测试结束，按回车放松电机...")
    for i in range(1, 5):
        driver.set_torque_enable(i, False)
    driver.close()

if __name__ == "__main__":
    check_directions()
