import cv2
import numpy as np
import sys
import os

# Ensure we can import local modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from person_analysis import CompletePersonFaceAnalyzer

def main():
    print("初始化全功能分析器 (包括新的颜色识别逻辑)...")
    # Initialize analyzer (disable face/emotion to speed up start if desired, but let's keep defaults)
    analyzer = CompletePersonFaceAnalyzer(show_keypoints=True, show_skeleton=True)
    
    # Temporarily disable face/emotion if we only care about color (optional, but faster)
    analyzer.face_enabled = False 
    analyzer.emotion_enabled = False
    
    cap = cv2.VideoCapture(0)
    
    # Set resolution
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)
    
    print("\n=== 开始颜色识别测试 (基于 HSV + 蒙版) ===")
    print("现在使用人体关键点轮廓进行背景剔除，并使用 HSV 空间进行颜色分类")
    print("按 'q' 退出")
    
    while True:
        ret, frame = cap.read()
        if not ret: break
        
        # Flip for mirror effect
        frame = cv2.flip(frame, 1)
        display_frame = frame.copy()
        
        # Process frame using the updated analyzer
        # This calls the new get_color with HSV and Masking
        _, results = analyzer.process_frame(frame)
        
        h_disp, w_disp = display_frame.shape[:2]
        
        for r in results:
            if 'bbox' not in r: continue
            
            x1, y1, x2, y2 = r['bbox']
            cv2.rectangle(display_frame, (x1, y1), (x2, y2), (255, 255, 255), 1)
            
            # Get color info from results
            clothing = r.get('clothing', {})
            upper_color = clothing.get('upper_color', 'None')
            upper_conf = clothing.get('upper_color_conf', 0.0)
            lower_color = clothing.get('lower_color', 'None')
            lower_conf = clothing.get('lower_color_conf', 0.0)
            
            # Display Upper Color Info
            u_status = "VALID" if upper_conf > 0.6 else "IGNORED"
            u_color_disp = (0, 255, 0) if upper_conf > 0.6 else (0, 0, 255)
            
            cv2.putText(display_frame, f"Up: {upper_color}", (x2+10, y1+30), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.8, u_color_disp, 2)
            cv2.putText(display_frame, f"Conf: {upper_conf:.2f} [{u_status}]", (x2+10, y1+60), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 1)
            
            # Display Lower Color Info
            l_status = "VALID" if lower_conf > 0.6 else "IGNORED"
            l_color_disp = (0, 255, 0) if lower_conf > 0.6 else (0, 0, 255)
            
            cv2.putText(display_frame, f"Low: {lower_color}", (x2+10, y1+100), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.8, l_color_disp, 2)
            cv2.putText(display_frame, f"Conf: {lower_conf:.2f} [{l_status}]", (x2+10, y1+130), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 1)

            # Draw segmentation/silhouette mask debug (optional)
            # To visualize the mask, we would need to return it from process_frame or re-generate it
            
        cv2.imshow('New Color Detection Logic', display_frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
            
    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
