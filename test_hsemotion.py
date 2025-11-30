"""
HSEmotion (EmotiEffLib) 测试程序
测试基于 EfficientNet 的高效情绪识别
"""

import cv2
import numpy as np
import torch
import insightface
from insightface.app import FaceAnalysis
# Monkey Patch torch.load to disable weights_only check for HSEmotion
_original_load = torch.load
def _safe_load(*args, **kwargs):
    if 'weights_only' not in kwargs:
        kwargs['weights_only'] = False
    return _original_load(*args, **kwargs)
torch.load = _safe_load

from hsemotion.facial_emotions import HSEmotionRecognizer
import time

def main():
    print("=" * 60)
    print("HSEmotion 情绪识别测试程序")
    print("=" * 60)
    
    device = 'cuda' if torch.cuda.is_available() else 'cpu'
    print(f"Device: {device}")
    if device == 'cuda':
        print(f"GPU: {torch.cuda.get_device_name(0)}")
    
    # 1. 初始化 InsightFace (用于人脸检测)
    print("\n[1] 初始化 InsightFace (人脸检测)...")
    try:
        face_app = FaceAnalysis(
            name='buffalo_l',
            providers=['CUDAExecutionProvider', 'CPUExecutionProvider'] if device == 'cuda' else ['CPUExecutionProvider']
        )
        # 使用 640x640 避免广播错误
        face_app.prepare(ctx_id=0 if device == 'cuda' else -1, det_size=(640, 640))
        print("  ✓ InsightFace 初始化成功")
    except Exception as e:
        print(f"  ✗ InsightFace 初始化失败: {e}")
        return

    # 2. 初始化 HSEmotion (用于情绪分类)
    print("\n[2] 初始化 HSEmotion (情绪分类)...")
    try:
        # model_name='enet_b0_8_best_vgaf' 是推荐的模型
        emotion_recognizer = HSEmotionRecognizer(model_name='enet_b0_8_best_vgaf', device=device)
        print("  ✓ HSEmotion 初始化成功")
    except Exception as e:
        print(f"  ✗ HSEmotion 初始化失败: {e}")
        return
    
    # 3. 打开摄像头
    print("\n[3] 打开摄像头...")
    cap = cv2.VideoCapture(0)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)
    
    if not cap.isOpened():
        print("  ✗ 无法打开摄像头")
        return
        
    print(f"  ✓ 摄像头已打开")
    
    # 4. 主循环
    print("\n[4] 开始检测...")
    print("=" * 60)
    
    frame_count = 0
    fps_start_time = time.time()
    fps = 0
    
    while True:
        ret, frame = cap.read()
        if not ret:
            break
            
        frame = cv2.flip(frame, 1)
        display_frame = frame.copy()
        
        # 计算 FPS
        frame_count += 1
        if frame_count % 30 == 0:
            fps_end_time = time.time()
            fps = 30 / (fps_end_time - fps_start_time)
            fps_start_time = fps_end_time
            print(f"FPS: {fps:.1f}")
        
        # 人脸检测
        try:
            faces = face_app.get(frame)
            
            for face in faces:
                bbox = face.bbox.astype(int)
                x1, y1, x2, y2 = bbox
                
                # 绘制人脸框
                cv2.rectangle(display_frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                
                # 提取人脸区域
                face_img = frame[y1:y2, x1:x2].copy()
                
                if face_img.size > 0:
                    # HSEmotion 预测
                    # predict_emotions 返回 (主要情绪, 分数列表)
                    emotion, scores = emotion_recognizer.predict_emotions(face_img, logits=False)
                    
                    # 绘制情绪文本
                    cv2.putText(display_frame, f"{emotion}", (x1, y1 - 10), 
                                cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 0), 2)
                                
                    # 绘制详细分数
                    y_offset = y2 + 20
                    # HSEmotion emotions list: ['Anger', 'Contempt', 'Disgust', 'Fear', 'Happiness', 'Neutral', 'Sadness', 'Surprise']
                    emotion_list = ['Anger', 'Contempt', 'Disgust', 'Fear', 'Happiness', 'Neutral', 'Sadness', 'Surprise']
                    
                    for i, score in enumerate(scores):
                        label = emotion_list[i]
                        text = f"{label}: {score:.2f}"
                        color = (0, 255, 255) if label == emotion else (200, 200, 200)
                        cv2.putText(display_frame, text, (x1, y_offset), 
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)
                        y_offset += 20

        except Exception as e:
            print(f"Error: {e}")
            
        # 显示画面
        cv2.imshow('HSEmotion Test', display_frame)
        
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
            
    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()

