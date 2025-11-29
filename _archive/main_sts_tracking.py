"""
机械臂追踪主程序 (STS 版本)
整合：摄像头识别 + 人体追踪 + STS 机械臂控制
"""

import cv2
import time
import sys
import os

# 确保可以导入 sts_control
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from person_analyzer import CompletePersonFaceAnalyzer
from sts_control.sts_arm_tracker import STSArmTracker

class STSCameraArmSystem:
    """
    摄像头 + STS 机械臂追踪系统
    """
    
    def __init__(self, camera_id=0, arm_port=None):
        """
        Args:
            camera_id: 摄像头设备ID
            arm_port: STS串口端口 (None=自动)
        """
        print("\n" + "=" * 60)
        print("摄像头 + STS 机械臂追踪系统")
        print("=" * 60)
        
        # 打开摄像头
        print("\n打开摄像头...")
        self.cap = cv2.VideoCapture(camera_id)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)  # 减少延迟
        
        if not self.cap.isOpened():
            print("✗ 无法打开摄像头")
            return
        print("✓ 摄像头已打开")
        
        # 创建人体分析器
        print("\n加载人体分析模型...")
        self.analyzer = CompletePersonFaceAnalyzer(
            show_keypoints=True,
            show_skeleton=True
        )
        print("✓ 模型加载完成")
        
        # 创建机械臂追踪器
        self.tracker = STSArmTracker(
            arm_port=arm_port,
            camera_id=camera_id,
            frame_width=640,
            frame_height=480
        )
        
        # 运行状态
        self.running = False
        
        # FPS计算
        self.fps_start = time.time()
        self.fps_counter = 0
        self.current_fps = 0
        
        print("\n" + "=" * 60)
        print("系统初始化完成!")
        print("=" * 60)
    
    def _draw_tracking_info(self, frame, results, tracking_data):
        """绘制追踪信息"""
        if not tracking_data or tracking_data.get('status') == 'disabled':
            return

        # 获取目标人脸/身体
        target = self.tracker.select_target_person(results)
        if target:
            bbox = target['bbox']
            x1, y1, x2, y2 = map(int, bbox)
            
            # 绘制目标框 (绿色)
            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
            cv2.putText(frame, "TARGET", (x1, y1-10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
            
            # 绘制中心点
            if 'center' in tracking_data:
                cx, cy = map(int, tracking_data['center'])
                cv2.circle(frame, (cx, cy), 5, (0, 0, 255), -1)
                
                # 绘制到画面中心的线
                h, w = frame.shape[:2]
                cv2.line(frame, (cx, cy), (w//2, h//2), (0, 255, 255), 1)

        # 显示角度信息
        if 'angles' in tracking_data:
            base = tracking_data['angles']['base']
            arm1 = tracking_data['angles']['arm1']
            cv2.putText(frame, f"Base: {base:.1f}", (10, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 2)
            cv2.putText(frame, f"Arm1: {arm1:.1f}", (10, 120), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 2)

    def run(self):
        """运行系统"""
        print("\n" + "=" * 60)
        print("系统启动")
        print("=" * 60)
        print("\n控制键:")
        print("  't' - 开始/停止追踪")
        print("  'e' - 使能/失能电机")
        print("  'v' - 开启/关闭视觉特效")
        print("  'm' - 切换特效模式 (剪影/ASCII艺术)")
        print("  's' - 保存截图")
        print("  'q' - 退出")
        print("=" * 60)
        print()
        
        self.running = True
        
        # 启动追踪
        self.tracker.start_tracking()
        print("✓ 追踪已启用")
        
        try:
            while self.running:
                # 读取帧
                ret, frame = self.cap.read()
                if not ret:
                    print("✗ 无法读取帧")
                    break
                
                # 镜像翻转（水平翻转）
                frame = cv2.flip(frame, 1)
                
                # 处理帧（人体识别）
                processed_frame, results = self.analyzer.process_frame(frame)
                
                # 更新机械臂追踪
                tracking_data = self.tracker.update(results)
                
                # 显示追踪信息
                self._draw_tracking_info(processed_frame, results, tracking_data)
                
                # 计算FPS
                self.fps_counter += 1
                if time.time() - self.fps_start > 1.0:
                    self.current_fps = self.fps_counter / (time.time() - self.fps_start)
                    self.fps_counter = 0
                    self.fps_start = time.time()
                
                # 显示FPS和状态
                cv2.putText(processed_frame, f"FPS: {self.current_fps:.1f}", (10, 30),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
                cv2.putText(processed_frame, f"Persons: {len(results)}", (10, 60),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
                
                # 显示追踪状态
                status_text = f"Tracking: {'ON' if self.tracker.tracking_enabled else 'OFF'}"
                status_color = (0, 255, 0) if self.tracker.tracking_enabled else (0, 0, 255)
                cv2.putText(processed_frame, status_text, (frame.shape[1]-200, 30),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, status_color, 2)
                
                # 显示画面
                cv2.imshow('STS Arm Tracking', processed_frame)
                
                # 键盘控制
                key = cv2.waitKey(1) & 0xFF
                if key == ord('q'):
                    break
                elif key == ord('t'):
                    if self.tracker.tracking_enabled:
                        self.tracker.stop_tracking()
                    else:
                        self.tracker.start_tracking()
                elif key == ord('e'):
                    # 切换使能状态（这里简单实现为重新使能）
                    self.tracker.arm.enable_all()
                elif key == ord('v'):
                    # 切换视觉特效
                    self.analyzer.enable_effects = not self.analyzer.enable_effects
                    print(f"Visual Effects: {'ON' if self.analyzer.enable_effects else 'OFF'}")
                elif key == ord('m'):
                    # 切换特效模式
                    if self.analyzer.effect_mode == 'silhouette':
                        self.analyzer.effect_mode = 'ascii'
                        print("Effect Mode: ASCII Art")
                    else:
                        self.analyzer.effect_mode = 'silhouette'
                        print("Effect Mode: Silhouette")
                elif key == ord('s'):
                    cv2.imwrite(f"capture_{int(time.time())}.jpg", frame)
                    print("截图已保存")
                    
        except KeyboardInterrupt:
            print("\n用户中断")
        finally:
            self.close()
    
    def close(self):
        """关闭系统"""
        self.running = False
        if self.cap:
            self.cap.release()
        if self.tracker:
            self.tracker.close()
        cv2.destroyAllWindows()
        print("✓ 系统已关闭")

if __name__ == "__main__":
    # 可以在这里指定端口，例如 arm_port='COM4'
    # 如果为 None，会自动搜索
    system = STSCameraArmSystem(camera_id=0, arm_port=None)
    system.run()

