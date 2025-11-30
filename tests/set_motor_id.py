"""
设置舵机 ID 的工具脚本
用法:
    python tests/set_motor_id.py --old_id 1 --new_id 2 --port COM3
"""
import sys
import os
import argparse
import time

# 添加项目根目录到 path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sts_control.sts_driver import STSServoSerial

def main():
    parser = argparse.ArgumentParser(description='设置 STS3215 舵机 ID')
    parser.add_argument('--old_id', type=int, required=True, help='当前舵机 ID (默认通常是 1)')
    parser.add_argument('--new_id', type=int, required=True, help='新舵机 ID')
    parser.add_argument('--port', type=str, default='COM4', help='串口端口 (例如 COM4 或 /dev/ttyUSB0)')
    
    args = parser.parse_args()
    
    print(f"准备连接串口 {args.port}...")
    print(f"将尝试把 ID {args.old_id} 修改为 {args.new_id}")
    print("提示：请确保只连接了一个舵机，或者知道自己在做什么！")
    
    try:
        servo = STSServoSerial(port=args.port)
        
        # 尝试 Ping 旧 ID
        print(f"正在 Ping ID {args.old_id}...")
        if not servo.ping(args.old_id):
            print(f"错误: 无法连接到 ID 为 {args.old_id} 的舵机！")
            print("请检查连接和电源，或确认 ID 是否正确。")
            servo.close()
            return
            
        print(f"成功连接到 ID {args.old_id}")
        
        # 修改 ID
        servo.set_id(args.old_id, args.new_id)
        
        # 验证新 ID
        print(f"正在验证新 ID {args.new_id}...")
        time.sleep(1.0) # 等待生效
        if servo.ping(args.new_id):
            print(f"成功！舵机 ID 已更新为 {args.new_id}")
        else:
            print(f"警告: 无法 Ping 通新 ID {args.new_id}，请手动检查或重启电源。")
            
        servo.close()
        
    except Exception as e:
        print(f"发生错误: {e}")

if __name__ == "__main__":
    main()




