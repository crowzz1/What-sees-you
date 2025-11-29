"""
示波器人体分割版 - 全息扫描填充效果
使用人体分割而不是骨骼关键点
显示填充的人形轮廓 + 扫描线效果
"""

import numpy as np
import cv2
import pyaudio
import threading
import queue

class SegmentationOscilloscope:
    """基于人体分割的示波器 - 全息扫描效果"""
    
    def __init__(self, width=960, height=540):
        """
        width, height: 示波器窗口大小
        """
        self.width = width
        self.height = height
        
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
        self.trail_fade = 0.90  # 0.85 -> 0.90 稍微持久一点，让波形更明显
        self.canvas = np.zeros((height, width, 3), dtype=np.float32)
        
        # 人体分割数据
        self.current_contour = None  # 人体轮廓
        self.current_mask = None     # 人体蒙版
        
        # 扫描线效果
        self.scan_mode = 'horizontal'  # 'horizontal', 'vertical', 'zigzag', 'circular'
        self.scan_density = 15  # 扫描线密度（像素间隔）- 增加间隔，减少密集度
        self.scan_offset = 0   # 动画偏移
        
    def enable_audio(self, device_index=None):
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
                            print(f"✓ 找到虚拟声卡: [{i}] {info['name']}")
                            break
            
            if device_index is None:
                print("⚠ 未找到虚拟声卡")
                if self.p:
                    self.p.terminate()
                    self.p = None
                return False
            
            info = self.p.get_device_info_by_index(device_index)
            print(f"✓ 音频: [{device_index}] {info['name']}")
            
            self.stream = self.p.open(
                format=pyaudio.paFloat32,
                channels=1,
                rate=self.sample_rate,
                input=True,
                input_device_index=device_index,
                frames_per_buffer=self.buffer_size
            )
            
            self.audio_enabled = True
            self.audio_running = True
            
            # 启动音频分析线程
            self.audio_thread = threading.Thread(target=self._audio_loop, daemon=True)
            self.audio_thread.start()
            
            return True
            
        except Exception as e:
            print(f"✗ 音频失败: {e}")
            if self.stream:
                try:
                    self.stream.close()
                except:
                    pass
            if self.p:
                try:
                    self.p.terminate()
                except:
                    pass
            return False
    
    def _audio_loop(self):
        """音频分析循环"""
        import time as time_module
        while self.audio_running:
            try:
                if self.stream and self.audio_enabled:
                    time_module.sleep(0.01)
                    data = self.stream.read(self.buffer_size, exception_on_overflow=False)
                    audio_data = np.frombuffer(data, dtype=np.float32)
                    
                    audio_data = np.nan_to_num(audio_data, nan=0.0)
                    audio_data = np.clip(audio_data, -1.0, 1.0)
                    
                    if len(audio_data) == 0:
                        continue
                    
                    # FFT
                    fft = np.fft.rfft(audio_data)
                    fft_mag = np.abs(fft)
                    fft_mag = np.nan_to_num(fft_mag)
                    freq_bins = np.fft.rfftfreq(len(audio_data), 1/self.sample_rate)
                    
                    bass = np.mean(fft_mag[(freq_bins >= 20) & (freq_bins < 250)])
                    mid = np.mean(fft_mag[(freq_bins >= 250) & (freq_bins < 4000)])
                    high = np.mean(fft_mag[(freq_bins >= 4000)])
                    volume = np.sqrt(np.clip(np.mean(audio_data ** 2), 0, 1))
                    beat = max(0, volume - 0.03) * 15
                    
                    self.bass = self._smooth(self.bass, np.clip(bass / 60, 0, 1))
                    self.mid = self._smooth(self.mid, np.clip(mid / 30, 0, 1))
                    self.high = self._smooth(self.high, np.clip(high / 15, 0, 1))
                    self.volume = self._smooth(self.volume, np.clip(volume * 10, 0, 1))
                    self.beat = self._smooth(self.beat, np.clip(beat, 0, 1))
                    
            except:
                self.bass *= 0.95
                self.mid *= 0.95
                self.high *= 0.95
                self.volume *= 0.95
                self.beat *= 0.9
    
    def _smooth(self, old, new):
        return old * self.smoothing + new * (1 - self.smoothing)
    
    def update_segmentation_data(self, mask, contour=None):
        """
        更新人体分割数据
        mask: 二值蒙版 (H, W) uint8, 255=人, 0=背景
        contour: 可选的轮廓点 [[x, y], ...]
        """
        self.current_mask = mask
        self.current_contour = contour
    
    def extract_contour_from_mask(self, mask):
        """从蒙版提取轮廓（保持精细）"""
        if mask is None or mask.size == 0:
            return None
        
        # 查找轮廓
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        if len(contours) == 0:
            return None
        
        # 找最大的轮廓（主要人体）
        largest_contour = max(contours, key=cv2.contourArea)
        
        # 适度简化轮廓（保持细节）
        epsilon = 0.005 * cv2.arcLength(largest_contour, True)  # 保持较精细
        approx = cv2.approxPolyDP(largest_contour, epsilon, True)
        
        return approx.reshape(-1, 2)
    
    def generate_scan_lines_horizontal(self, mask):
        """生成水平扫描线（带波形效果）"""
        if mask is None:
            return []
        
        h, w = mask.shape
        lines = []
        
        # 动态调整密度（响应中音）
        density = int(self.scan_density * (1 - self.mid * 0.5))
        density = max(3, density)
        
        # 扫描线动画偏移
        offset = int(self.scan_offset) % density
        
        for y in range(offset, h, density):
            # 找这一行中所有的白色区域
            row = mask[y, :]
            white_pixels = np.where(row > 127)[0]
            
            if len(white_pixels) > 0:
                # 找连续段
                segments = []
                start = white_pixels[0]
                
                for i in range(1, len(white_pixels)):
                    if white_pixels[i] - white_pixels[i-1] > 2:
                        segments.append((start, white_pixels[i-1]))
                        start = white_pixels[i]
                
                segments.append((start, white_pixels[-1]))
                
                # 每段生成波形线（不是直线）
                for x_start, x_end in segments:
                    if x_end - x_start < 5:
                        # 太短，直接直线
                        lines.append([(x_start, y), (x_end, y)])
                    else:
                        # 生成波形点（减少采样点，避免过密）
                        wave_points = []
                        num_points = min(15, (x_end - x_start) // 5)  # 采样点数（减少）
                        for i in range(num_points + 1):
                            t = i / num_points
                            x = int(x_start + t * (x_end - x_start))
                            
                            # 音频波形偏移
                            wave_y = y
                            # 低音：大幅度波动
                            wave_y += int(np.sin(x * 0.1 + self.scan_offset * 0.05) * self.bass * 15)
                            # 中音：快速振荡
                            wave_y += int(np.sin(x * 0.3 + self.scan_offset * 0.1) * self.mid * 8)
                            # 高音：噪声
                            wave_y += int(np.random.uniform(-1, 1) * self.high * 5)
                            
                            wave_y = np.clip(wave_y, 0, h - 1)
                            wave_points.append((x, wave_y))
                        
                        lines.append(wave_points)
        
        return lines
    
    def generate_scan_lines_vertical(self, mask):
        """生成垂直扫描线（带波形效果）"""
        if mask is None:
            return []
        
        h, w = mask.shape
        lines = []
        
        density = int(self.scan_density * (1 - self.mid * 0.5))
        density = max(3, density)
        offset = int(self.scan_offset) % density
        
        for x in range(offset, w, density):
            col = mask[:, x]
            white_pixels = np.where(col > 127)[0]
            
            if len(white_pixels) > 0:
                segments = []
                start = white_pixels[0]
                
                for i in range(1, len(white_pixels)):
                    if white_pixels[i] - white_pixels[i-1] > 2:
                        segments.append((start, white_pixels[i-1]))
                        start = white_pixels[i]
                
                segments.append((start, white_pixels[-1]))
                
                # 生成波形线
                for y_start, y_end in segments:
                    if y_end - y_start < 5:
                        lines.append([(x, y_start), (x, y_end)])
                    else:
                        wave_points = []
                        num_points = min(15, (y_end - y_start) // 5)  # 减少采样点
                        for i in range(num_points + 1):
                            t = i / num_points
                            y = int(y_start + t * (y_end - y_start))
                            
                            # 音频波形偏移（水平方向）
                            wave_x = x
                            wave_x += int(np.sin(y * 0.1 + self.scan_offset * 0.05) * self.bass * 15)
                            wave_x += int(np.sin(y * 0.3 + self.scan_offset * 0.1) * self.mid * 8)
                            wave_x += int(np.random.uniform(-1, 1) * self.high * 5)
                            
                            wave_x = np.clip(wave_x, 0, w - 1)
                            wave_points.append((wave_x, y))
                        
                        lines.append(wave_points)
        
        return lines
    
    def generate_scan_lines_zigzag(self, mask):
        """生成Z字形扫描（带波形效果）"""
        if mask is None:
            return []
        
        h, w = mask.shape
        lines = []
        
        density = int(self.scan_density * (1 - self.mid * 0.5))
        density = max(4, density)
        offset = int(self.scan_offset) % density
        
        for y in range(offset, h, density):
            row = mask[y, :]
            white_pixels = np.where(row > 127)[0]
            
            if len(white_pixels) > 0:
                # Z字形：奇数行反向
                is_reverse = (y // density) % 2 == 1
                if is_reverse:
                    white_pixels = white_pixels[::-1]
                
                segments = []
                start = white_pixels[0]
                
                for i in range(1, len(white_pixels)):
                    gap = abs(white_pixels[i] - white_pixels[i-1])
                    if gap > 2:
                        segments.append((start, white_pixels[i-1]))
                        start = white_pixels[i]
                
                segments.append((start, white_pixels[-1]))
                
                # 生成波形线
                for seg in segments:
                    x_start, x_end = seg if not is_reverse else (seg[1], seg[0])
                    
                    if abs(x_end - x_start) < 5:
                        lines.append([(x_start, y), (x_end, y)])
                    else:
                        wave_points = []
                        num_points = min(15, abs(x_end - x_start) // 5)  # 减少采样点
                        for i in range(num_points + 1):
                            t = i / num_points
                            x = int(x_start + t * (x_end - x_start))
                            
                            # 更有机的波形
                            wave_y = y
                            wave_y += int(np.sin(x * 0.15 + y * 0.1 + self.scan_offset * 0.05) * self.bass * 12)
                            wave_y += int(np.cos(x * 0.25 - y * 0.05) * self.mid * 10)
                            wave_y += int(np.random.uniform(-1, 1) * self.high * 6)
                            
                            wave_y = np.clip(wave_y, 0, h - 1)
                            wave_points.append((x, wave_y))
                        
                        lines.append(wave_points)
        
        return lines
    
    def normalize_and_transform(self, points, src_width, src_height):
        """归一化坐标并应用音频变形"""
        if points is None or len(points) == 0:
            return []
        
        result = []
        for point in points:
            x, y = point
            
            # 归一化到 -1 到 1（修复上下颠倒）
            norm_x = (x / src_width - 0.5) * 2
            norm_y = (y / src_height - 0.5) * 2  # 不需要翻转
            
            # 应用音频变形（大幅增强）
            # 整体缩放（音量）
            scale = 0.75 + self.volume * 0.8  # 0.25 -> 0.8 更夸张
            norm_x *= scale
            norm_y *= scale
            
            # 垂直拉伸（低音）- 大幅增强
            norm_y *= (1 + self.bass * 0.8)  # 0.2 -> 0.8
            
            # 水平波动（中音）- 大幅增强
            wave = np.sin(norm_y * 8 + self.scan_offset * 0.1) * self.mid * 0.25  # 0.06 -> 0.25
            norm_x += wave
            
            # 旋转效果（高音）
            if self.high > 0.2:
                angle = self.high * 0.3  # 旋转角度
                cos_a = np.cos(angle)
                sin_a = np.sin(angle)
                new_x = norm_x * cos_a - norm_y * sin_a
                new_y = norm_x * sin_a + norm_y * cos_a
                norm_x = new_x
                norm_y = new_y
            
            # 抖动（高音）- 增强
            if self.high > 0.3:
                noise = np.random.uniform(-1, 1, 2) * (self.high - 0.3) * 0.15  # 0.04 -> 0.15
                norm_x += noise[0]
                norm_y += noise[1]
            
            # 节拍脉冲 - 大幅增强
            if self.beat > 0.5:
                pulse = 1 + (self.beat - 0.5) * 0.8  # 更夸张的脉冲
                norm_x *= pulse
                norm_y *= pulse
            
            # 转换为像素坐标（不翻转Y）
            px = int((norm_x + 1) * self.width / 2)
            py = int((norm_y + 1) * self.height / 2)  # 去掉负号
            
            # 边界检查
            px = np.clip(px, 0, self.width - 1)
            py = np.clip(py, 0, self.height - 1)
            
            result.append((px, py))
        
        return result
    
    def render(self):
        """渲染一帧"""
        # 余辉衰减
        self.canvas *= self.trail_fade
        
        if self.current_mask is not None:
            h, w = self.current_mask.shape
            
            # 生成扫描线
            if self.scan_mode == 'horizontal':
                scan_lines = self.generate_scan_lines_horizontal(self.current_mask)
            elif self.scan_mode == 'vertical':
                scan_lines = self.generate_scan_lines_vertical(self.current_mask)
            else:  # zigzag
                scan_lines = self.generate_scan_lines_zigzag(self.current_mask)
            
            # 绘制扫描线（带辉光，更粗）
            for line in scan_lines:
                if len(line) >= 2:
                    transformed = self.normalize_and_transform(line, w, h)
                    if len(transformed) >= 2:
                        for i in range(len(transformed) - 1):
                            p1 = transformed[i]
                            p2 = transformed[i + 1]
                            
                            # 多层辉光（更粗更明显）
                            cv2.line(self.canvas, p1, p2, (0, 1.8, 0), 3)  # 最亮层
                            cv2.line(self.canvas, p1, p2, (0, 1.0, 0), 6)  # 中间层
                            cv2.line(self.canvas, p1, p2, (0, 0.5, 0), 10)  # 辉光层
            
            # 绘制轮廓（外边框）- 超级粗超级明显
            if self.current_contour is None:
                self.current_contour = self.extract_contour_from_mask(self.current_mask)
            
            if self.current_contour is not None and len(self.current_contour) > 2:
                contour_transformed = self.normalize_and_transform(
                    self.current_contour, w, h
                )
                
                if len(contour_transformed) > 2:
                    # 绘制轮廓线（超粗超亮，压倒性存在感）
                    for i in range(len(contour_transformed)):
                        p1 = contour_transformed[i]
                        p2 = contour_transformed[(i + 1) % len(contour_transformed)]
                        
                        # 四层辉光（超级粗）
                        cv2.line(self.canvas, p1, p2, (0, 2.5, 0), 5)   # 超亮核心（更粗）
                        cv2.line(self.canvas, p1, p2, (0, 1.5, 0), 10)  # 明亮层（更粗）
                        cv2.line(self.canvas, p1, p2, (0, 0.8, 0), 15)  # 辉光层（更粗）
                        cv2.line(self.canvas, p1, p2, (0, 0.4, 0), 20)  # 外层辉光（新增）
        
        # 更新扫描偏移（动画）- 更快更明显
        self.scan_offset += 1.0 + self.mid * 3.0 + self.beat * 2.0  # 中音和节拍影响扫描速度
        
        # 转换为显示格式
        display = (self.canvas * 255).astype(np.uint8)
        # 更强的模糊，让线条更圆润更粗
        display = cv2.GaussianBlur(display, (9, 9), 2)
        
        return display
    
    def close(self):
        """关闭"""
        self.audio_running = False
        if self.audio_thread:
            self.audio_thread.join(timeout=1)
        if self.stream:
            self.stream.stop_stream()
            self.stream.close()
        if self.p:
            self.p.terminate()


# 使用示例
if __name__ == "__main__":
    import cv2
    from ultralytics import YOLO
    
    print("示波器人体分割测试")
    print("需要摄像头和 YOLO segmentation 模型")
    
    # 加载分割模型
    model = YOLO('yolov8n-seg.pt')
    
    # 创建示波器
    osc = SegmentationOscilloscope(width=960, height=540)
    
    # 启动音频（可选）
    osc.enable_audio()
    
    # 打开摄像头
    cap = cv2.VideoCapture(0)
    
    cv2.namedWindow('Segmentation Oscilloscope', cv2.WINDOW_NORMAL)
    cv2.resizeWindow('Segmentation Oscilloscope', 960, 540)
    
    print("\n控制:")
    print("  1/2/3 - 切换扫描模式")
    print("  +/-   - 调整扫描密度")
    print("  q     - 退出")
    
    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            
            frame = cv2.flip(frame, 1)
            
            # YOLO 分割
            results = model(frame, verbose=False)
            
            # 提取人体蒙版
            person_mask = None
            if len(results) > 0 and results[0].masks is not None:
                masks = results[0].masks.data.cpu().numpy()
                classes = results[0].boxes.cls.cpu().numpy()
                
                # 找到所有人（class 0）
                person_indices = np.where(classes == 0)[0]
                
                if len(person_indices) > 0:
                    # 合并所有人的蒙版
                    h, w = frame.shape[:2]
                    person_mask = np.zeros((h, w), dtype=np.uint8)
                    
                    for idx in person_indices:
                        mask = masks[idx]
                        mask_resized = cv2.resize(mask, (w, h))
                        person_mask = np.maximum(person_mask, (mask_resized * 255).astype(np.uint8))
            
            # 更新示波器
            if person_mask is not None:
                osc.update_segmentation_data(person_mask)
            
            # 渲染
            osc_display = osc.render()
            
            # 显示
            cv2.imshow('Segmentation Oscilloscope', osc_display)
            
            # 键盘控制
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                break
            elif key == ord('1'):
                osc.scan_mode = 'horizontal'
                print("扫描模式: 水平")
            elif key == ord('2'):
                osc.scan_mode = 'vertical'
                print("扫描模式: 垂直")
            elif key == ord('3'):
                osc.scan_mode = 'zigzag'
                print("扫描模式: Z字形")
            elif key == ord('+') or key == ord('='):
                osc.scan_density = max(2, osc.scan_density - 1)
                print(f"扫描密度: {osc.scan_density}")
            elif key == ord('-'):
                osc.scan_density = min(20, osc.scan_density + 1)
                print(f"扫描密度: {osc.scan_density}")
    
    except KeyboardInterrupt:
        print("\n停止")
    finally:
        cap.release()
        osc.close()
        cv2.destroyAllWindows()

