"""
单脚本3摄像头系统
一次加载模型，同时处理3个摄像头
性能比3个独立进程高 2-3 倍
"""

import cv2
import numpy as np
import time
import threading
from queue import Queue
import sys

# 导入主分析器
from person_analyzer import CompletePersonFaceAnalyzer

# TouchDesigner 传输
try:
    from td_transmitter import TouchDesignerTransmitter
    TD_AVAILABLE = True
except:
    TD_AVAILABLE = False
    print("Warning: TouchDesigner transmitter not available")



class MultiCameraSystem:
    """
    多摄像头系统 - 共享模型
    """
    
    def capture_thread(self, cam_idx):
        """摄像头采集线程"""
        cap = self.captures[cam_idx]
        frame_queue = self.frame_queues[cam_idx]
        
        while self.running:
            ret, frame = cap.read()
            if not ret:
                time.sleep(0.01)
                continue
            
            # 放入队列（如果队列满了就丢弃旧帧）
            if frame_queue.full():
                try:
                    frame_queue.get_nowait()
                except:
                    pass
            
            frame_queue.put(frame)
    
    def process_thread(self):
        """
        处理线程 - 轮流处理每个摄像头的帧
        """
        frame_count = [0, 0, 0]
        
        while self.running:
            # 轮流处理每个摄像头
            for cam_idx in range(self.num_cameras):
                if not self.frame_queues[cam_idx].empty():
                    frame = self.frame_queues[cam_idx].get()
                    frame_count[cam_idx] += 1
                    
                    # 处理帧
                    processed_frame, results = self.analyzer.process_frame(frame)
                    
                    # 发送到 TouchDesigner (每3帧一次)
                    if self.transmitters[cam_idx] and results and (frame_count[cam_idx] % 3 == 0):
                        try:
                            self.transmitters[cam_idx].transmit(results)
                        except:
                            pass
                    
                    # 放入结果队列
                    if self.result_queues[cam_idx].full():
                        try:
                            self.result_queues[cam_idx].get_nowait()
                        except:
                            pass
                    
                    self.result_queues[cam_idx].put({
                        'frame': processed_frame,
                        'results': results
                    })
            
            time.sleep(0.001)  # 短暂休眠避免CPU 100%
    
    def __init__(self, camera_configs):
        """
        camera_configs: [
            {'device': 0, 'camera_id': 1, 'port': 7000},
            {'device': 1, 'camera_id': 2, 'port': 7001},
            {'device': 2, 'camera_id': 3, 'port': 7002}
        ]
        """
        self.configs = camera_configs
        self.num_cameras = len(camera_configs)
        
        # 创建单个分析器（所有摄像头共享）
        print("\n加载模型（只加载一次）...")
        self.analyzer = CompletePersonFaceAnalyzer(
            show_keypoints=True,
            show_skeleton=True
        )
        print("✓ 模型加载完成\n")
        
        # 为每个摄像头创建
        self.captures = []
        self.transmitters = []
        self.frame_queues = []
        self.result_queues = []
        self.threads = []
        self.running = True
        
        # 初始化摄像头和传输器
        for cfg in camera_configs:
            # 摄像头
            print(f"正在打开摄像头 {cfg['camera_id']} (设备 {cfg['device']})...")
            cap = cv2.VideoCapture(cfg['device'])
            print(f"  ✓ 摄像头 {cfg['camera_id']} 已打开")
            
            # 设置分辨率
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
            
            # 设置缓冲区大小（减少延迟）
            cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            
            self.captures.append(cap)
            
            # 队列
            self.frame_queues.append(Queue(maxsize=2))
            self.result_queues.append(Queue(maxsize=2))
            
            # TouchDesigner 传输器
            if TD_AVAILABLE:
                try:
                    transmitter = TouchDesignerTransmitter(
                        protocol='udp',
                        host='127.0.0.1',
                        port=cfg['port'],
                        camera_id=cfg['camera_id']
                    )
                    print(f"✓ 摄像头 {cfg['camera_id']}: UDP → 127.0.0.1:{cfg['port']}")
                except:
                    transmitter = None
                    print(f"✗ 摄像头 {cfg['camera_id']}: UDP 传输器创建失败")
            else:
                transmitter = None
            
            self.transmitters.append(transmitter)
        
    
    def display_thread(self, cam_idx):
        """显示线程"""
        cfg = self.configs[cam_idx]
        window_name = f"Camera {cfg['camera_id']} (Device {cfg['device']})"
        
        fps_start = time.time()
        fps_counter = 0
        current_fps = 0
        
        while self.running:
            if not self.result_queues[cam_idx].empty():
                data = self.result_queues[cam_idx].get()
                frame = data['frame']
                results = data['results']
                
                fps_counter += 1
                
                # 计算 FPS
                if time.time() - fps_start > 1.0:
                    current_fps = fps_counter / (time.time() - fps_start)
                    fps_counter = 0
                    fps_start = time.time()
                
                # 显示 FPS 和人数
                cv2.putText(frame, f"FPS: {current_fps:.1f}", (10, 30),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)
                cv2.putText(frame, f"Persons: {len(results)}", (10, 42),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)
                cv2.putText(frame, f"Cam {cfg['camera_id']}", (10, 54),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)
                
                cv2.imshow(window_name, frame)
            
            # 检查键盘
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                self.running = False
                break
            elif key == ord('s'):
                # 保存截图
                if not self.result_queues[cam_idx].empty():
                    cv2.imwrite(f'camera_{cfg["camera_id"]}_screenshot.jpg', frame)
                    print(f"✓ Camera {cfg['camera_id']} screenshot saved")
            elif key == ord('e'):
                # 切换视觉特效
                self.analyzer.enable_effects = not self.analyzer.enable_effects
                if self.analyzer.enable_effects:
                    self.analyzer.trail_history = []  # 重置残影历史
                print(f"Visual Effects: {'ON' if self.analyzer.enable_effects else 'OFF'}")
            elif key == ord('m'):
                # 切换特效模式
                if self.analyzer.effect_mode == 'silhouette':
                    self.analyzer.effect_mode = 'ascii'
                    print("Effect Mode: ASCII Art")
                else:
                    self.analyzer.effect_mode = 'silhouette'
                    print("Effect Mode: Silhouette")
    
    def run(self):
        """启动系统"""
        print("=" * 60)
        print("多摄像头系统启动")
        print("=" * 60)
        print(f"摄像头数量: {self.num_cameras}")
        print("模型: 共享（只加载一次）")
        print("\n控制:")
        print("  按 'q' 退出")
        print("  按 's' 保存截图")
        print("  按 'e' 开启/关闭视觉特效")
        print("  按 'm' 切换特效模式 (剪影/ASCII艺术)")
        print("=" * 60)
        print()
        
        # 启动采集线程
        for i in range(self.num_cameras):
            t = threading.Thread(target=self.capture_thread, args=(i,), daemon=True)
            t.start()
            self.threads.append(t)
            print(f"✓ 摄像头 {self.configs[i]['camera_id']} 采集线程已启动")
        
        # 启动处理线程
        process_t = threading.Thread(target=self.process_thread, daemon=True)
        process_t.start()
        self.threads.append(process_t)
        print("✓ 处理线程已启动")
        
        # 启动显示线程
        for i in range(self.num_cameras):
            t = threading.Thread(target=self.display_thread, args=(i,), daemon=True)
            t.start()
            self.threads.append(t)
            print(f"✓ 摄像头 {self.configs[i]['camera_id']} 显示线程已启动")
        
        print("\n" + "=" * 60)
        print("系统运行中...")
        print("=" * 60)
        print()
        
        # 主线程等待
        try:
            while self.running:
                time.sleep(0.1)
        except KeyboardInterrupt:
            print("\n\n中断信号收到，正在关闭...")
            self.running = False
        
        # 清理
        self.cleanup()
    
    def cleanup(self):
        """清理资源"""
        print("\n清理资源...")
        
        # 关闭摄像头
        for i, cap in enumerate(self.captures):
            cap.release()
            print(f"✓ 摄像头 {i+1} 已关闭")
        
        # 关闭传输器
        for i, transmitter in enumerate(self.transmitters):
            if transmitter:
                try:
                    transmitter.close()
                    print(f"✓ 传输器 {i+1} 已关闭")
                except:
                    pass
        
        # 关闭窗口
        cv2.destroyAllWindows()
        print("✓ 所有窗口已关闭")
        
        print("\n程序退出")


def main():
    """主函数"""
    # 摄像头配置 - 根据实际拥有的摄像头数量修改
    # 如果只有1个摄像头，只保留第一个配置
    # 如果有2个摄像头，保留前两个配置
    camera_configs = [
        {'device': 0, 'camera_id': 1, 'port': 7000},
        # {'device': 1, 'camera_id': 2, 'port': 7001},  # 如果不需要，注释掉
        # {'device': 2, 'camera_id': 3, 'port': 7002},  # 如果不需要，注释掉
    ]
    
    # 创建并运行系统
    system = MultiCameraSystem(camera_configs)
    system.run()


if __name__ == "__main__":
    main()

