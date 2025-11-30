"""
FER (Facial Expression Recognition) 测试程序
测试 FER 库是否能正常识别情绪
"""

import cv2
import numpy as np
from fer import FER
import time

def main():
    print("=" * 60)
    print("FER 情绪识别测试程序")
    print("=" * 60)
    
    # 1. 初始化 FER
    print("\n[1] 初始化 FER...")
    try:
        # mtcnn=True: 使用 MTCNN 人脸检测（更准确但更慢）
        # mtcnn=False: 使用 OpenCV Haar Cascade（更快但可能不准确）
        detector = FER(mtcnn=True)
        print("  ✓ FER 初始化成功 (使用 MTCNN 人脸检测)")
    except Exception as e:
        print(f"  ✗ FER 初始化失败: {e}")
        return
    
    # 2. 打开摄像头
    print("\n[2] 打开摄像头...")
    cap = cv2.VideoCapture(0)
    
    # 设置分辨率为 1920x1080
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)
    
    if not cap.isOpened():
        print("  ✗ 无法打开摄像头")
        return
    
    actual_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    actual_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    print(f"  ✓ 摄像头已打开: {actual_width}x{actual_height}")
    
    # 3. 主循环
    print("\n[3] 开始检测...")
    print("=" * 60)
    print("操作说明:")
    print("  - 按 'q' 退出")
    print("  - 按 's' 保存当前帧")
    print("=" * 60)
    
    frame_count = 0
    fps_start_time = time.time()
    fps = 0
    
    # 用于消除闪烁：保存上一帧的检测结果
    last_results = []
    # 用于平滑情绪：保存每个人的最近N次情绪
    emotion_history = [] 
    
    while True:
        ret, frame = cap.read()
        if not ret:
            print("无法读取摄像头画面")
            break
        
        # 水平翻转（镜像）
        frame = cv2.flip(frame, 1)
        
        # 计算 FPS
        frame_count += 1
        if frame_count % 30 == 0:
            fps_end_time = time.time()
            fps = 30 / (fps_end_time - fps_start_time)
            fps_start_time = fps_end_time
        
        # 每 5 帧检测一次情绪（提高性能）
        if frame_count % 5 == 0:
            try:
                # FER 检测
                # 返回格式: [{'box': [x, y, w, h], 'emotions': {'angry': 0.01, ...}}]
                results = detector.detect_emotions(frame)
                
                if results:
                    last_results = results  # 更新缓存结果
                else:
                    # 如果这帧没检测到人脸，可以选择清空，或者保留一小会儿（防丢）
                    # 这里为了实时性，如果真没脸就清空
                    last_results = []
                    
            except Exception as e:
                print(f"!!! FER ERROR: {e}")
        
        # --- 绘制部分（每一帧都执行）---
        if last_results:
            for face in last_results:
                # 获取人脸框
                box = face['box']
                x, y, w, h = box
                
                # 获取情绪
                emotions = face['emotions']
                
                # 找到最强的情绪
                dominant_emotion = max(emotions, key=emotions.get)
                confidence = emotions[dominant_emotion]
                
                # 绘制人脸框（绿色）
                cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 2)
                
                # 绘制情绪文本
                label = f"{dominant_emotion}: {confidence*100:.1f}%"
                cv2.putText(frame, label, (x, y-10), 
                            cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 0), 2)
                
                # 绘制所有情绪的详细信息
                y_offset = y + h + 25
                for emotion, score in emotions.items():
                    text = f"{emotion}: {score*100:.1f}%"
                    color = (0, 255, 255) if emotion == dominant_emotion else (255, 255, 255)
                    thickness = 2 if emotion == dominant_emotion else 1
                    cv2.putText(frame, text, (x, y_offset), 
                                cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, thickness)
                    y_offset += 20
                
                # 打印到控制台 (降低频率)
                if frame_count % 30 == 0:
                    print(f"Frame {frame_count}: {dominant_emotion} ({confidence*100:.1f}%)")
        else:
             # 没有检测到人脸 (使用缓存也没有)
            if frame_count % 5 == 0 and not last_results:
                 cv2.putText(frame, "No face detected", (50, 50), 
                            cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 255), 2)
        
        # 显示 FPS
        cv2.putText(frame, f"FPS: {fps:.1f}", (frame.shape[1] - 150, 30), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
        
        # 显示帧数
        cv2.putText(frame, f"Frame: {frame_count}", (frame.shape[1] - 150, 60), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
        
        # 显示画面
        cv2.imshow('FER Emotion Test', frame)
        
        # 按键处理
        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            print("\n用户退出")
            break
        elif key == ord('s'):
            filename = f"fer_test_frame_{frame_count}.jpg"
            cv2.imwrite(filename, frame)
            print(f"已保存: {filename}")
    
    # 4. 清理
    cap.release()
    cv2.destroyAllWindows()
    print("\n测试结束")
    print("=" * 60)

if __name__ == "__main__":
    main()

