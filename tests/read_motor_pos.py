import sys
import time
import signal

sys.path.append('sts_control')
from sts_driver import STSServoSerial

def main():
    try:
        # 连接电机
        driver = STSServoSerial("COM4", 1000000)
        print("连接成功")
    except Exception as e:
        print(f"连接失败: {e}")
        return

    # 失能所有电机，允许手动移动
    print("正在关闭扭矩，请手动移动电机到极限位置...")
    for i in [1, 2, 3, 4]:
        driver.set_torque_enable(i, False)
    
    print("\n开始读取位置 (按 Ctrl+C 退出)...")
    print("-" * 50)
    print(f"{'Motor 1':<10} | {'Motor 2':<10} | {'Motor 3':<10} | {'Motor 4':<10}")
    print("-" * 50)

    try:
        while True:
            # 读取所有位置
            p1 = driver.get_position(1)
            p2 = driver.get_position(2)
            p3 = driver.get_position(3)
            p4 = driver.get_position(4)

            # 打印 (覆盖当前行)
            print(f"\r{p1:<10} | {p2:<10} | {p3:<10} | {p4:<10}", end="", flush=True)
            time.sleep(0.1)

    except KeyboardInterrupt:
        print("\n\n已停止。")
    finally:
        driver.close()

if __name__ == "__main__":
    main()


