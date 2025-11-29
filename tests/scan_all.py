"""
扫描所有可能的波特率和电机 ID
"""
import serial
import time

port = "COM4"
baudrates = [1000000, 115200, 57600, 9600]
motor_ids = [1, 2, 3, 4, 5, 6]

print("开始全面扫描...")
print("="*60)

for baudrate in baudrates:
    print(f"\n波特率: {baudrate}")
    print("-"*40)
    
    try:
        ser = serial.Serial(port, baudrate, timeout=0.5)
        
        for motor_id in motor_ids:
            ser.reset_input_buffer()
            ser.reset_output_buffer()
            
            # Ping 包
            length = 2
            instruction = 0x01
            checksum = (~(motor_id + length + instruction)) & 0xFF
            packet = bytes([0xFF, 0xFF, motor_id, length, instruction, checksum])
            
            ser.write(packet)
            time.sleep(0.1)
            
            if ser.in_waiting > 0:
                response = ser.read(ser.in_waiting)
                print(f"  ✓ Motor ID {motor_id} 响应！")
                print(f"    响应: {' '.join([f'{b:02X}' for b in response])}")
        
        ser.close()
    except Exception as e:
        print(f"  ✗ 错误: {e}")

print("\n"+"="*60)
print("扫描完成")




