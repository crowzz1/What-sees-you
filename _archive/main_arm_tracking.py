"""
机械臂追踪主程序
整合：摄像头识别 + 人体追踪 + 机械臂控制
"""

import cv2
import time
from person_analyzer import CompletePersonFaceAnalyzer
from arm_tracker import ArmTracker


class CameraArmSystem:
    """
    摄像头 + 机械臂追踪系统
    """
    
    def __init__(self, camera_id=0, arm_port='COM3'):
        """
        Args:
            camera_id: 摄像头设备ID
            arm_port: ESP32串口端口
        """
        print("\n" + "=" * 60)
        print("摄像头 + 机械臂追踪系统")
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
        self.tracker = ArmTracker(
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
    
    def run(self):
        """运行系统"""
        print("\n" + "=" * 60)
        print("系统启动")
        print("=" * 60)
        print("\n控制键:")
        print("  't' - 开始/停止追踪")
        print("  'e' - 使能/失能电机")
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
                cv2.putText(processed_frame, status_text, (10, 90),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, status_color, 2)
                
                # 显示窗口
                cv2.imshow('Camera + Arm Tracking', processed_frame)
                
                # 处理键盘
                key = cv2.waitKey(1) & 0xFF
                if key == ord('q'):
                    print("\n退出...")
                    break
                elif key == ord('t'):
                    # 切换追踪
                    if self.tracker.tracking_enabled:
                        self.tracker.stop_tracking()
                    else:
                        self.tracker.start_tracking()
                elif key == ord('e'):
                    # 使能/失能电机
                    if self.tracker.arm.connected:
                        # 简单切换（检查第一个电机状态）
                        self.tracker.arm.enable_all()
                        print("电机已使能")
                elif key == ord('d'):
                    # 失能电机
                    if self.tracker.arm.connected:
                        self.tracker.arm.disable_all()
                        print("电机已失能")
                elif key == ord('s'):
                    # 保存截图
                    filename = f'tracking_screenshot_{int(time.time())}.jpg'
                    cv2.imwrite(filename, processed_frame)
                    print(f"✓ 截图已保存: {filename}")
        
        except KeyboardInterrupt:
            print("\n\n中断信号")
        finally:
            self.cleanup()
    
    def _draw_tracking_info(self, frame, results, tracking_data):
        """在画面上绘制追踪信息"""
        if tracking_data.get('status') == 'tracking' and 'center' in tracking_data:
            # 绘制目标中心点
            center = tracking_data['center']
            center_x, center_y = int(center[0]), int(center[1])
            
            # 绘制十字准星
            cv2.circle(frame, (center_x, center_y), 10, (0, 255, 0), 2)
            cv2.line(frame, (center_x - 20, center_y), (center_x + 20, center_y), (0, 255, 0), 2)
            cv2.line(frame, (center_x, center_y - 20), (center_x, center_y + 20), (0, 255, 0), 2)
            
            # 显示角度信息
            if 'angles' in tracking_data:
                angles = tracking_data['angles']
                text_y = center_y - 30
                
                angle_text = f"Base: {angles['base']:.1f}° Arm: {angles['arm1']:.1f}°"
                cv2.putText(frame, angle_text, (center_x - 80, text_y),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
            
            # 显示归一化坐标
            if 'normalized' in tracking_data:
                norm_x, norm_y = tracking_data['normalized']
                norm_text = f"({norm_x:.2f}, {norm_y:.2f})"
                cv2.putText(frame, norm_text, (center_x - 50, text_y - 20),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 0), 1)
        
        # 绘制画面中心线（参考）
        h, w = frame.shape[:2]
        cv2.line(frame, (w//2, 0), (w//2, h), (128, 128, 128), 1)
        cv2.line(frame, (0, h//2), (w, h//2), (128, 128, 128), 1)
    
    def cleanup(self):
        """清理资源"""
        print("\n清理资源...")
        
        # 关闭追踪器
        self.tracker.close()
        
        # 关闭摄像头
        if self.cap:
            self.cap.release()
        
        # 关闭窗口
        cv2.destroyAllWindows()
        
        print("✓ 清理完成")
        print("\n程序退出")


def main():
    """主函数"""
    # 配置
    CAMERA_ID = 0       # 摄像头ID (Windows一般是0, Linux可能是/dev/video0)
    ARM_PORT = 'COM3'   # ESP32串口端口 (根据实际情况修改)
    
    print("=" * 60)
    print("机械臂追踪系统 v1.0")
    print("=" * 60)
    print(f"摄像头: {CAMERA_ID}")
    print(f"ESP32端口: {ARM_PORT}")
    print("=" * 60)
    
    # 创建并运行系统
    system = CameraArmSystem(
        camera_id=CAMERA_ID,
        arm_port=ARM_PORT
    )
    
    if system.cap.isOpened() and system.tracker.arm.connected:
        system.run()
    else:
        print("\n✗ 系统初始化失败")


if __name__ == "__main__":
    main()







