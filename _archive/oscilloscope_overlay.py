"""
示波器覆盖层模块
可以直接绘制在现有的 OpenCV 窗口上（例如右下角）
使用来自 YOLO Pose 的人体姿态数据
"""

import numpy as np
import cv2
import pyaudio
import threading
import queue

class OscilloscopeOverlay:
    """示波器覆盖层 - 可以绘制在任何 OpenCV 帧上"""
    
    def __init__(self, width=300, height=300, position='bottom-right'):
        """
        width, height: 示波器窗口大小（像素）
        position: 位置 ('bottom-right', 'bottom-left', 'top-right', 'top-left')
        """
        self.width = width
        self.height = height
        self.position = position
        
        # 音频
        self.p = None
        self.stream = None
        self.sample_rate = 44100
        self.buffer_size = 512
        self.audio_enabled = False
        
        # 音频参数
        self.bass = 0.0
        self.mid = 0.0
        self.high = 0.0
        self.volume = 0.0
        self.beat = 0.0
        self.smoothing = 0.75
        
        # 音频线程
        self.audio_thread = None
        self.audio_running = False
        
        # 辉光画布
        self.trail_fade = 0.88
        self.canvas = np.zeros((height, width, 3), dtype=np.float32)
        
        # 人体数据缓存
        self.current_keypoints = None
        self.person_contour = None
        
    def enable_audio(self, device_index=None, retry_on_fail=True):
        """启动音频分析"""
        try:
            self.p = pyaudio.PyAudio()
            
            # 自动查找虚拟声卡
            if device_index is None:
                for i in range(self.p.get_device_count()):
                    info = self.p.get_device_info_by_index(i)
                    if info['maxInputChannels'] > 0:
                        name = info['name'].lower()
                        if 'cable' in name and 'output' in name:
                            device_index = i
                            print(f"✓ 自动找到虚拟声卡: [{i}] {info['name']}")
                            break
            
            if device_index is None:
                print("⚠ 未找到虚拟声卡，音频反应将禁用")
                if self.p:
                    self.p.terminate()
                    self.p = None
                return False
            
            info = self.p.get_device_info_by_index(device_index)
            print(f"✓ 示波器音频: [{device_index}] {info['name']}")
            
            # 使用非独占模式，避免与其他程序冲突
            self.stream = self.p.open(
                format=pyaudio.paFloat32,
                channels=1,
                rate=self.sample_rate,
                input=True,
                input_device_index=device_index,
                frames_per_buffer=self.buffer_size,
                stream_callback=None  # 使用阻塞模式，更安全
            )
            
            self.audio_enabled = True
            self.audio_running = True
            
            # 启动音频分析线程
            self.audio_thread = threading.Thread(target=self._audio_loop, daemon=True)
            self.audio_thread.start()
            
            return True
            
        except Exception as e:
            print(f"✗ 示波器音频启动失败: {e}")
            print(f"  提示: 请确保 VCV Rack 已经在运行")
            print(f"  建议: 先启动 VCV Rack，再启动本程序")
            
            # 清理
            if self.stream:
                try:
                    self.stream.close()
                except:
                    pass
                self.stream = None
            
            if self.p:
                try:
                    self.p.terminate()
                except:
                    pass
                self.p = None
            
            return False
    
    def _audio_loop(self):
        """音频分析循环（在独立线程中运行）"""
        import time as time_module
        while self.audio_running:
            try:
                if self.stream and self.audio_enabled:
                    # 添加小延迟，避免过于频繁读取
                    time_module.sleep(0.01)
                    data = self.stream.read(self.buffer_size, exception_on_overflow=False)
                    audio_data = np.frombuffer(data, dtype=np.float32)
                    
                    # 清理数据
                    audio_data = np.nan_to_num(audio_data, nan=0.0, posinf=0.0, neginf=0.0)
                    audio_data = np.clip(audio_data, -1.0, 1.0)
                    
                    if len(audio_data) == 0:
                        continue
                    
                    # FFT 分析
                    fft = np.fft.rfft(audio_data)
                    fft_mag = np.abs(fft)
                    fft_mag = np.nan_to_num(fft_mag, nan=0.0)
                    freq_bins = np.fft.rfftfreq(len(audio_data), 1/self.sample_rate)
                    
                    # 频段提取
                    bass = np.mean(fft_mag[(freq_bins >= 20) & (freq_bins < 250)])
                    mid = np.mean(fft_mag[(freq_bins >= 250) & (freq_bins < 4000)])
                    high = np.mean(fft_mag[(freq_bins >= 4000)])
                    volume = np.sqrt(np.clip(np.mean(audio_data ** 2), 0, 1))
                    beat = max(0, volume - 0.03) * 15
                    
                    # 平滑
                    self.bass = self._smooth(self.bass, np.clip(bass / 60, 0, 1))
                    self.mid = self._smooth(self.mid, np.clip(mid / 30, 0, 1))
                    self.high = self._smooth(self.high, np.clip(high / 15, 0, 1))
                    self.volume = self._smooth(self.volume, np.clip(volume * 10, 0, 1))
                    self.beat = self._smooth(self.beat, np.clip(beat, 0, 1))
                    
            except Exception as e:
                # 衰减
                self.bass *= 0.95
                self.mid *= 0.95
                self.high *= 0.95
                self.volume *= 0.95
                self.beat *= 0.9
    
    def _smooth(self, old, new):
        return old * self.smoothing + new * (1 - self.smoothing)
    
    def update_person_data(self, keypoints=None, contour=None):
        """
        更新人体数据
        keypoints: YOLO pose 17个关键点 [[x, y, conf], ...] 或字典
        contour: 人体轮廓点 [[x, y], ...]
        """
        self.current_keypoints = keypoints
        self.person_contour = contour
    
    def _normalize_keypoints(self, keypoints, frame_width, frame_height):
        """归一化关键点到 -1 到 1"""
        if keypoints is None:
            return None
        
        # YOLO pose 17 个关键点
        kp_names = [
            'nose', 'left_eye', 'right_eye', 'left_ear', 'right_ear',
            'left_shoulder', 'right_shoulder', 'left_elbow', 'right_elbow',
            'left_wrist', 'right_wrist', 'left_hip', 'right_hip',
            'left_knee', 'right_knee', 'left_ankle', 'right_ankle'
        ]
        
        normalized = {}
        for i, (x, y, conf) in enumerate(keypoints):
            if i < len(kp_names) and conf > 0.3:  # 只使用置信度高的点
                norm_x = (x / frame_width - 0.5) * 2
                norm_y = (y / frame_height - 0.5) * 2
                normalized[kp_names[i]] = (norm_x, norm_y)
        
        return normalized
    
    def _apply_audio_deformation(self, keypoints_dict):
        """对关键点应用音频变形"""
        if not keypoints_dict:
            return keypoints_dict
        
        deformed = {}
        for key, (x, y) in keypoints_dict.items():
            # 1. 整体缩放（音量）
            scale = 0.85 + self.volume * 0.3
            x *= scale
            y *= scale
            
            # 2. 垂直拉伸（低音）
            y *= (1 + self.bass * 0.25)
            
            # 3. 水平波动（中音）
            wave = np.sin(y * 8) * self.mid * 0.08
            x += wave
            
            # 4. 抖动（高音）
            if self.high > 0.3:
                noise = np.random.uniform(-1, 1, 2) * (self.high - 0.3) * 0.05
                x += noise[0]
                y += noise[1]
            
            # 5. 脉冲（节拍）
            if self.beat > 0.7:
                pulse = 1 + (self.beat - 0.7) * 0.3
                x *= pulse
                y *= pulse
            
            deformed[key] = (x, y)
        
        return deformed
    
    def _draw_skeleton(self, keypoints_dict):
        """绘制骨骼"""
        if not keypoints_dict:
            return
        
        # 骨骼连接
        connections = [
            ('left_shoulder', 'right_shoulder'),
            ('left_shoulder', 'left_elbow'), ('left_elbow', 'left_wrist'),
            ('right_shoulder', 'right_elbow'), ('right_elbow', 'right_wrist'),
            ('left_shoulder', 'left_hip'), ('right_shoulder', 'right_hip'),
            ('left_hip', 'right_hip'),
            ('left_hip', 'left_knee'), ('left_knee', 'left_ankle'),
            ('right_hip', 'right_knee'), ('right_knee', 'right_ankle')
        ]
        
        for p1_name, p2_name in connections:
            if p1_name in keypoints_dict and p2_name in keypoints_dict:
                x1, y1 = keypoints_dict[p1_name]
                x2, y2 = keypoints_dict[p2_name]
                
                # 转换为像素坐标
                px1 = int((x1 + 1) * self.width / 2)
                py1 = int((-y1 + 1) * self.height / 2)
                px2 = int((x2 + 1) * self.width / 2)
                py2 = int((-y2 + 1) * self.height / 2)
                
                # 检查边界
                if (0 <= px1 < self.width and 0 <= py1 < self.height and
                    0 <= px2 < self.width and 0 <= py2 < self.height):
                    
                    # 绘制辉光线条
                    cv2.line(self.canvas, (px1, py1), (px2, py2), (0, 1, 0), 2)
                    cv2.line(self.canvas, (px1, py1), (px2, py2), (0, 0.6, 0), 4)
                    
                    # 节拍时绘制关节点
                    if self.beat > 0.6:
                        radius = int(5 * self.beat)
                        cv2.circle(self.canvas, (px1, py1), radius, (0, 0.8, 0), -1)
    
    def render(self, frame):
        """
        在给定的帧上渲染示波器
        frame: OpenCV BGR 图像
        返回: 带有示波器覆盖的帧
        """
        h, w = frame.shape[:2]
        
        # 计算位置
        if self.position == 'bottom-right':
            x = w - self.width - 10
            y = h - self.height - 10
        elif self.position == 'bottom-left':
            x = 10
            y = h - self.height - 10
        elif self.position == 'top-right':
            x = w - self.width - 10
            y = 10
        else:  # top-left
            x = 10
            y = 10
        
        # 确保位置有效
        if x < 0 or y < 0 or x + self.width > w or y + self.height > h:
            return frame  # 如果窗口太小，不绘制
        
        # 余辉衰减
        self.canvas *= self.trail_fade
        
        # 如果有人体数据，绘制骨骼
        if self.current_keypoints is not None:
            # 归一化关键点
            keypoints_dict = self._normalize_keypoints(
                self.current_keypoints, w, h
            )
            
            # 应用音频变形
            if self.audio_enabled:
                keypoints_dict = self._apply_audio_deformation(keypoints_dict)
            
            # 绘制骨骼
            self._draw_skeleton(keypoints_dict)
        
        # 转换画布为显示格式
        display = (self.canvas * 255).astype(np.uint8)
        display = cv2.GaussianBlur(display, (5, 5), 0)
        
        # 添加半透明黑色背景
        overlay = frame.copy()
        cv2.rectangle(overlay, (x, y), (x + self.width, y + self.height), 
                     (0, 0, 0), -1)
        frame = cv2.addWeighted(frame, 1, overlay, 0.5, 0)
        
        # 叠加示波器
        roi = frame[y:y+self.height, x:x+self.width]
        # 只叠加绿色通道（示波器效果）
        roi[:, :, 1] = np.maximum(roi[:, :, 1], display[:, :, 1])
        
        # 绘制边框
        cv2.rectangle(frame, (x, y), (x + self.width, y + self.height), 
                     (0, 255, 0), 1)
        
        # 显示状态
        if self.audio_enabled:
            # 音频条
            bar_y = y + 10
            bar_height = 8
            bar_width = self.width - 20
            
            # 低音
            filled = int(bar_width * self.bass)
            if filled > 0:
                cv2.rectangle(frame, (x + 10, bar_y), 
                            (x + 10 + filled, bar_y + bar_height), 
                            (0, 0, 255), -1)
            
            # 中音
            bar_y += bar_height + 2
            filled = int(bar_width * self.mid)
            if filled > 0:
                cv2.rectangle(frame, (x + 10, bar_y), 
                            (x + 10 + filled, bar_y + bar_height), 
                            (0, 255, 0), -1)
            
            # 高音
            bar_y += bar_height + 2
            filled = int(bar_width * self.high)
            if filled > 0:
                cv2.rectangle(frame, (x + 10, bar_y), 
                            (x + 10 + filled, bar_y + bar_height), 
                            (255, 0, 0), -1)
            
            # 标题
            cv2.putText(frame, "OSCILLOSCOPE", (x + 10, y + self.height - 10),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 0), 1)
        else:
            cv2.putText(frame, "OSC (No Audio)", (x + 10, y + self.height - 10),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.3, (100, 100, 100), 1)
        
        return frame
    
    def close(self):
        """关闭音频流"""
        self.audio_running = False
        if self.audio_thread:
            self.audio_thread.join(timeout=1)
        if self.stream:
            self.stream.stop_stream()
            self.stream.close()
        if self.p:
            self.p.terminate()

