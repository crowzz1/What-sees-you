"""
测试赛博朋克故障艺术效果
"""

import cv2
import time
import sys
import os

# 添加根目录到路径，以便导入模块
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from person_analysis import CompletePersonFaceAnalyzer
from visual_style import GlitchArtEffect

def main():
    print("=" * 60)
    print("赛博朋克故障艺术效果测试")
    print("=" * 60)
    
    # 打开摄像头
    cap = cv2.VideoCapture(0)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    
    if not cap.isOpened():
        print("✗ 无法打开摄像头")
        return
    
    print("✓ 摄像头已打开")
    
    # 创建分析器（只需要关键点检测）
    print("\n加载YOLOv8-Pose模型...")
    analyzer = CompletePersonFaceAnalyzer(
        show_keypoints=False,
        show_skeleton=False
    )
    
    # 关闭不需要的功能以提升性能
    analyzer.face_enabled = False
    analyzer.emotion_enabled = False
    
    print("✓ 模型加载完成")
    
    # 创建故障艺术效果生成器
    glitch = GlitchArtEffect(canvas_width=1920, canvas_height=1080)
    
    print("\n" + "=" * 60)
    print("控制键:")
    print("  'q' - 退出")
    print("  's' - 保存截图")
    print("=" * 60)
    print()
    
    # FPS计算
    fps_start = time.time()
    fps_counter = 0
    current_fps = 0
    
    # 创建窗口
    cv2.namedWindow('Corrupted Vision - Glitch Art', cv2.WINDOW_NORMAL)
    cv2.resizeWindow('Corrupted Vision - Glitch Art', 1920, 1080)
    
    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                print("✗ 无法读取帧")
                break
            
            # 镜像翻转
            frame = cv2.flip(frame, 1)
            
            # 备份一份纯净的 frame 用于提取 ROI，防止 analyzer 在原图上绘图污染
            clean_frame = frame.copy()
            
            # 人体检测（只需要关键点）
            analyzer.enable_effects = False
            _, results = analyzer.process_frame(frame)
            
            # 生成故障艺术效果 (使用纯净画面)
            glitch_frame = glitch.create_glitch_frame(clean_frame, results)
            
            # 计算FPS
            fps_counter += 1
            if time.time() - fps_start > 1.0:
                current_fps = fps_counter / (time.time() - fps_start)
                fps_counter = 0
                fps_start = time.time()
            
            # 显示FPS
            cv2.putText(glitch_frame, f"FPS: {current_fps:.1f}", 
                       (50, glitch_frame.shape[0] - 30),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 1)
            
            # 显示画面
            cv2.imshow('Corrupted Vision - Glitch Art', glitch_frame)
            
            # 键盘控制
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                break
            elif key == ord('s'):
                timestamp = int(time.time())
                filename = f'glitch_art_{timestamp}.jpg'
                cv2.imwrite(filename, glitch_frame)
                print(f"✓ 截图已保存: {filename}")
    
    except KeyboardInterrupt:
        print("\n用户中断")
    finally:
        cap.release()
        cv2.destroyAllWindows()
        print("✓ 程序退出")

if __name__ == "__main__":
    main()

