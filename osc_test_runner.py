import time
import sys
import threading
from osc_control import OscController

# 全局变量用于在线程间通信
running = True

def input_thread_func(osc):
    global running
    print("\n[指令列表]")
    print(" --- 情绪 ---")
    print(" '1': 开启 /Neutral_Green_Cyan")
    print(" '2': 关闭 /Neutral_Green_Cyan")
    print(" '3': 开启 /Happiness_Yellow_Orange")
    print(" '4': 关闭 /Happiness_Yellow_Orange")
    print(" '5': 开启 /Surprise_White_Pink")
    print(" '6': 关闭 /Surprise_White_Pink")
    print(" '7': 开启 /Sadness_Blue_Purple")
    print(" '8': 关闭 /Sadness_Blue_Purple")
    print(" '9': 开启 /Fear_Black")
    print(" 'a': 关闭 /Fear_Black")
    print(" 'b': 开启 /Anger_Red")
    print(" 'c': 关闭 /Anger_Red")
    print(" 'd': 开启 /Disgust_Contempt_Gray")
    print(" 'e': 关闭 /Disgust_Contempt_Gray")
    print(" --- 体型 ---")
    print(" 'f': 开启 /Slim")
    print(" 'g': 关闭 /Slim")
    print(" 'h': 开启 /Average")
    print(" 'i': 关闭 /Average")
    print(" 'j': 开启 /Broad")
    print(" 'k': 关闭 /Broad")
    
    print(" 'q': 退出")
    
    while running:
        try:
            user_input = input()
            cmd = user_input.strip()
            
            # 情绪
            if cmd == '1': osc.set_value('Neutral_Green_Cyan', 1.0)
            elif cmd == '2': osc.set_value('Neutral_Green_Cyan', 0.0)
            elif cmd == '3': osc.set_value('Happiness_Yellow_Orange', 1.0)
            elif cmd == '4': osc.set_value('Happiness_Yellow_Orange', 0.0)
            elif cmd == '5': osc.set_value('Surprise_White_Pink', 1.0)
            elif cmd == '6': osc.set_value('Surprise_White_Pink', 0.0)
            elif cmd == '7': osc.set_value('Sadness_Blue_Purple', 1.0)
            elif cmd == '8': osc.set_value('Sadness_Blue_Purple', 0.0)
            elif cmd == '9': osc.set_value('Fear_Black', 1.0)
            elif cmd == 'a': osc.set_value('Fear_Black', 0.0)
            elif cmd == 'b': osc.set_value('Anger_Red', 1.0)
            elif cmd == 'c': osc.set_value('Anger_Red', 0.0)
            elif cmd == 'd': osc.set_value('Disgust_Contempt_Gray', 1.0)
            elif cmd == 'e': osc.set_value('Disgust_Contempt_Gray', 0.0)
            
            # 体型
            elif cmd == 'f': osc.set_value('Slim', 1.0)
            elif cmd == 'g': osc.set_value('Slim', 0.0)
            elif cmd == 'h': osc.set_value('Average', 1.0)
            elif cmd == 'i': osc.set_value('Average', 0.0)
            elif cmd == 'j': osc.set_value('Broad', 1.0)
            elif cmd == 'k': osc.set_value('Broad', 0.0)
            
            elif cmd == 'q':
                running = False
                break
        except EOFError:
            break

def run_test():
    global running
    print("="*50)
    print("OSC 手动步进测试 (发送至 127.0.0.1:7001)")
    print("="*50)
    
    osc = OscController(ip="127.0.0.1", port=7001)
    
    # 注册所有通道
    channels = [
        # 基础
        'Bg',
        # 情绪 (带颜色后缀)
        'Neutral_Green_Cyan', 'Happiness_Yellow_Orange', 'Surprise_White_Pink', 'Sadness_Blue_Purple', 
        'Fear_Black', 'Anger_Red', 'Disgust_Contempt_Gray',
        # 体型
        'Slim', 'Average', 'Broad'
    ]
    
    for ch in channels:
        osc.add_channel(ch, f'/{ch}', initial_value=0.0, smoothing=0.1)
    
    # Bg 默认开启
    time.sleep(0.5)
    osc.set_value('Bg', 1.0)
    
    # 启动输入监听线程
    t = threading.Thread(target=input_thread_func, args=(osc,), daemon=True)
    t.start()
    
    try:
        while running:
            osc.update()
            time.sleep(0.016)
            
    except KeyboardInterrupt:
        running = False

    print("\n[状态] 正在归零并退出...")
    # 全部归零
    for ch in channels:
        osc.set_value(ch, 0.0)
    
    # 简单等待归零
    for _ in range(30):
        osc.update()
        time.sleep(0.016)
    print("Done.")

if __name__ == "__main__":
    run_test()
