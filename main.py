import os
import sys
import threading
import queue

# 自动将 PyTorch 的 bin 目录（包含 cuDNN DLL）添加到系统路径
# 这解决了 onnxruntime 找不到 CUDA 11.8 DLL 的问题
try:
    import torch
    torch_lib_path = os.path.join(os.path.dirname(torch.__file__), 'lib')
    if os.path.exists(torch_lib_path):
        os.add_dll_directory(torch_lib_path)
        # 同时添加到 PATH 环境变量，双重保险
        os.environ['PATH'] = torch_lib_path + os.pathsep + os.environ['PATH']
        print(f"✓ 已注入 PyTorch DLL 路径: {torch_lib_path}")
except Exception as e:
    print(f"⚠ 尝试注入 DLL 路径失败: {e}")

"""
画廊式视图 - 同时显示多个视角
布局：
- 左上：原始摄像头识别画面
- 右上：ASCII艺术效果
- 左下：人物信息
- 右下：手部追踪控制 (原示波器区域)
"""

import cv2
import numpy as np
import time
import warnings

# 过滤 InsightFace 的 FutureWarning
warnings.filterwarnings("ignore", category=FutureWarning, module="insightface")
warnings.filterwarnings("ignore", category=UserWarning, module="pydantic")

from person_analysis import CompletePersonFaceAnalyzer
from tracker import AdvancedTracker # 导入追踪器
from visual_style import GlitchArtEffect # 导入故障艺术效果
from config import ARM_PORT, ARM_BAUDRATE # 导入硬件配置
from osc_control import OscController # 导入OSC控制器

class GalleryView:
    """画廊式视图系统"""
    
    def __init__(self, camera_id=0, window_width=1920, window_height=1080):
        """
        Args:
            camera_id: 摄像头设备ID
            window_width: 窗口宽度 (1920x1080)
            window_height: 窗口高度
        """
        self.window_width = window_width
        self.window_height = window_height
        
        # === 新布局定义 (1920x1080) ===
        # 上半部分高度
        self.top_height = 810
        # 下半部分高度
        self.bottom_height = 1080 - 810 # = 270
        
        # 左上角宽度
        self.left_width = 1440
        # 右上角宽度
        self.right_width = 1920 - 1440 # = 480
        
        # 下半部分分割
        self.bottom_left_width = 960
        self.bottom_mid_width = 480
        self.bottom_right_width = 480
        
        print("=" * 60)
        print("画廊式视图系统 - 自定义 16:9 布局")
        print("=" * 60)
        print(f"窗口尺寸: {window_width}x{window_height}")
        print(f"Top Area: Height {self.top_height}")
        print(f"  - Top Left:  {self.left_width}x{self.top_height}")
        print(f"  - Top Right: {self.right_width}x{self.top_height}")
        print(f"Bottom Area: Height {self.bottom_height}")
        print(f"  - Bot Left:  {self.bottom_left_width}x{self.bottom_height}")
        print(f"  - Bot Mid:   {self.bottom_mid_width}x{self.bottom_height} (Blank)")
        print(f"  - Bot Right: {self.bottom_right_width}x{self.bottom_height} (Tracker)")
        print("=" * 60)
        
        # 打开摄像头
        print("\n打开摄像头...")
        self.cap = cv2.VideoCapture(camera_id)
        
        # 强制设置 MJPG 格式以解锁高帧率 (关键修复)
        # 许多 USB 摄像头在 1080p 下默认使用 YUY2 格式，受限于 USB 带宽只有 5 FPS
        # 切换到 MJPG 可以达到 30 FPS
        self.cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc('M', 'J', 'P', 'G'))
        
        # 尝试设置高清分辨率
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)
        self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        
        # 检查实际设置的分辨率（有些摄像头不支持会回退）
        actual_w = self.cap.get(cv2.CAP_PROP_FRAME_WIDTH)
        actual_h = self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
        print(f"摄像头分辨率: {int(actual_w)}x{int(actual_h)}")
        
        if not self.cap.isOpened():
            print("✗ 无法打开摄像头")
            return
        print("✓ 摄像头已打开")
        
        # 创建分析器
        print("\n加载模型...")
        self.analyzer = CompletePersonFaceAnalyzer(
            show_keypoints=True,
            show_skeleton=True
        )
        
        # --- 性能优化 ---
        # 为了提高追踪流畅度，暂时关闭耗时的分割和人脸功能
        # print("\n[性能模式] 已启用：关闭分割和人脸分析以提高帧率")
        # self.analyzer.segmentation_enabled = False
        self.analyzer.segmentation_enabled = True # 重新开启分割以获得精确轮廓
        self.analyzer.face_enabled = True  # 开启人脸识别
        self.analyzer.emotion_enabled = True # 开启情绪识别 (使用 HSEmotion)
        # ----------------
        
        # 默认开启特效
        self.analyzer.enable_effects = True
        
        print("✓ 模型加载完成")
        
        # 初始化故障艺术效果
        print("\n初始化故障艺术效果 (Glitch Art)...")
        # 右上角使用右侧宽度，上方高度
        self.glitch_effect = GlitchArtEffect(
            canvas_width=self.right_width, 
            canvas_height=self.top_height
        )
        print("✓ 故障艺术引擎已就绪")

        # 初始化 OSC 控制器
        print("\n初始化 OSC 控制器...")
        try:
            self.osc = OscController(ip="127.0.0.1", port=7001)
            
            # 注册通道
            # 背景
            self.osc.add_channel('Bg', '/Bg', initial_value=0.0, smoothing=0.1)
            
            # 情绪 + 颜色
            self.osc.add_channel('Neutral_Green_Cyan', '/Neutral_Green_Cyan', smoothing=0.1)
            self.osc.add_channel('Happiness_Yellow_Orange', '/Happiness_Yellow_Orange', smoothing=0.1)
            self.osc.add_channel('Surprise_White_Pink', '/Surprise_White_Pink', smoothing=0.1)
            self.osc.add_channel('Sadness_Blue_Purple', '/Sadness_Blue_Purple', smoothing=0.1)
            self.osc.add_channel('Fear_Black', '/Fear_Black', smoothing=0.1)
            self.osc.add_channel('Anger_Red', '/Anger_Red', smoothing=0.1)
            self.osc.add_channel('Disgust_Contempt_Gray', '/Disgust_Contempt_Gray', smoothing=0.1)
            
            # 体型
            self.osc.add_channel('Slim', '/Slim', smoothing=0.1)
            self.osc.add_channel('Average', '/Average', smoothing=0.1)
            self.osc.add_channel('Broad', '/Broad', smoothing=0.1)
            
            print("✓ OSC 控制器已启动 (127.0.0.1:7001)")
        except Exception as e:
            print(f"✗ OSC 初始化失败: {e}")
            self.osc = None
        
        # 初始化 AdvancedTracker (用于后台追踪，不显示在UI上)
        print("\n初始化手部追踪器 (AdvancedTracker)...")
        try:
            # AdvancedTracker 不接受 baud_rate 参数，且默认波特率为 1000000
            # 我们需要禁用内部摄像头和模型加载，因为我们在外部处理
            self.tracker = AdvancedTracker(
                port=ARM_PORT, 
                use_internal_camera=False, 
                load_model=False
            )
            print("✓ 追踪器已集成 (后台运行)")
        except Exception as e:
            print(f"✗ 追踪器初始化失败: {e}")
            self.tracker = None
        
        # 运行状态 (必须在启动线程前初始化)
        self.running = True
        
        # === 多线程追踪支持 ===
        # 创建一个队列，仅保留最新的1帧数据，如果处理不过来就丢弃旧的
        self.tracker_queue = queue.Queue(maxsize=1)
        # 存储最新的追踪结果供主线程读取
        self.latest_tracker_result = {
            'frame': None,
            'active_idx': None
        }
        self.tracker_lock = threading.Lock()
        
        # 启动追踪线程
        if self.tracker:
            self.tracker_thread = threading.Thread(target=self._tracker_worker, daemon=True)
            self.tracker_thread.start()
            print("✓ 追踪线程已启动 (异步模式)")

        # FPS计算
        self.fps_start = time.time()
        self.fps_counter = 0
        self.current_fps = 0
        
        # 缓存上一帧的完整结果，用于隔帧优化
        self.last_full_results = []
        
        # 文本显示设置
        self.text_scroll_offset = 0
        self.text_line_height = 35
        self.text_font = cv2.FONT_HERSHEY_SIMPLEX
        self.text_font_scale = 0.8
        self.text_thickness = 2
        
        print("\n" + "=" * 60)
        print("系统初始化完成!")
        print("=" * 60)
    
    def _tracker_worker(self):
        """
        后台追踪线程
        负责执行耗时的 process_frame 和串口通信
        """
        while self.running:
            try:
                # 从队列获取数据，超时等待以免死锁
                # get() 是阻塞的，所以没有数据时线程会挂起，不占CPU
                item = self.tracker_queue.get(timeout=0.1)
                frame_copy, results = item
                
                if self.tracker:
                    # 执行耗时的追踪和控制逻辑
                    tracker_frame = self.tracker.process_frame(frame_copy, external_results=results)
                    active_idx = self.tracker.active_target_index
                    
                    # 更新结果
                    with self.tracker_lock:
                        self.latest_tracker_result['frame'] = tracker_frame
                        self.latest_tracker_result['active_idx'] = active_idx
                        
            except queue.Empty:
                continue
            except Exception as e:
                print(f"Tracker thread error: {e}")
                continue

    def resize_to_fit(self, frame, target_width, target_height):
        """
        快速调整图像大小（直接拉伸填充，不保持比例）
        性能优化：避免额外的画布创建和复制
        """
        if frame is None:
            return np.zeros((target_height, target_width, 3), dtype=np.uint8)
        # 直接拉伸到目标尺寸，避免额外的内存操作
        resized = cv2.resize(frame, (target_width, target_height), interpolation=cv2.INTER_LINEAR)
        return resized
    
    def update_osc(self, results, active_idx):
        """
        更新 OSC 通道状态
        逻辑改进：加入【信号保持】机制
        当检测到目标但当前帧分析不出情绪时，保持上一次的有效值，防止信号中断。
        """
        if not self.osc:
            return

        # 初始化 OSC 缓存 (如果不存在)
        if not hasattr(self, 'osc_cache'):
            self.osc_cache = {
                'emotion': '',
                'colors': set(),
                'build': ''
            }

        # 默认所有通道目标值为 0
        target_values = {
            'Neutral_Green_Cyan': 0.0,
            'Happiness_Yellow_Orange': 0.0,
            'Surprise_White_Pink': 0.0,
            'Sadness_Blue_Purple': 0.0,
            'Fear_Black': 0.0,
            'Anger_Red': 0.0,
            'Disgust_Contempt_Gray': 0.0,
            'Slim': 0.0,
            'Average': 0.0,
            'Broad': 0.0
        }
        
        if active_idx is not None and 0 <= active_idx < len(results):
            person = results[active_idx]
            
            # --- 1. 提取当前帧数据 ---
            curr_emotion = person.get('emotion', '').lower() if person.get('emotion') else ''
            
            curr_colors = set()
            clothing = person.get('clothing', {})
            if clothing.get('upper_color'): curr_colors.add(clothing['upper_color'].lower())
            if clothing.get('lower_color'): curr_colors.add(clothing['lower_color'].lower())
            
            curr_build = ''
            body_type = person.get('body_type', {})
            if body_type:
                curr_build = body_type.get('build', '').lower()

            # --- 2. 更新缓存 (仅当有有效数据时) ---
            if curr_emotion:
                self.osc_cache['emotion'] = curr_emotion
            
            if curr_colors:
                # 颜色比较特殊，可能是空的，如果有新颜色才更新，否则保持
                self.osc_cache['colors'] = curr_colors
                
            if curr_build:
                self.osc_cache['build'] = curr_build

            # --- 3. 使用缓存数据进行映射 (实现信号保持) ---
            # 只要人还在，就用最新的有效数据，确保信号连续
            emotion = self.osc_cache['emotion']
            colors = self.osc_cache['colors']
            build = self.osc_cache['build']
            
            # 映射逻辑: 情绪 OR 颜色
            # Neutral / Green / Cyan
            if emotion == 'neutral' or 'green' in colors or 'cyan' in colors:
                target_values['Neutral_Green_Cyan'] = 1.0
            
            # Happiness / Yellow / Orange
            if emotion == 'happy' or 'happiness' in emotion or 'yellow' in colors or 'orange' in colors:
                target_values['Happiness_Yellow_Orange'] = 1.0
                
            # Surprise / White / Pink
            if emotion == 'surprise' or 'white' in colors or 'pink' in colors:
                target_values['Surprise_White_Pink'] = 1.0
                
            # Sadness / Blue / Purple
            if emotion == 'sad' or 'sadness' in emotion or 'blue' in colors or 'purple' in colors:
                target_values['Sadness_Blue_Purple'] = 1.0
                
            # Fear / Black
            if emotion == 'fear' or 'black' in colors:
                target_values['Fear_Black'] = 1.0
                
            # Anger / Red
            if emotion == 'angry' or 'anger' in emotion or 'red' in colors:
                target_values['Anger_Red'] = 1.0
                
            # Disgust / Contempt / Gray
            if (emotion == 'disgust' or emotion == 'contempt' or 
                'gray' in colors or 'grey' in colors or 'mixed' in colors):
                target_values['Disgust_Contempt_Gray'] = 1.0
            
            # 体型 映射
            if build == 'slim':
                target_values['Slim'] = 1.0
            elif build == 'broad' or build == 'stocky' or build == 'athletic':
                target_values['Broad'] = 1.0
            else: # Average, or others
                target_values['Average'] = 1.0
        
        else:
            # 如果彻底没人了，才清空缓存并归零
            self.osc_cache = {
                'emotion': '',
                'colors': set(),
                'build': ''
            }
        
        # 应用目标值
        for name, val in target_values.items():
            self.osc.set_value(name, val)
            
        # 更新 OSC 控制器 (发送数据)
        self.osc.update()

    def _apply_effect_with_mask(self, frame, person_mask, results):
        """
        使用已有的mask应用silhouette效果（避免重新分割）
        """
        effect_frame = frame.copy()
        original_mask = person_mask.copy()
        
        # 应用羽化
        if self.analyzer.feather_radius > 0:
            person_mask = cv2.GaussianBlur(person_mask, 
                                         (self.analyzer.feather_radius * 2 + 1, 
                                          self.analyzer.feather_radius * 2 + 1), 0)
        
        # 绘制数据方块
        self.analyzer.draw_data_blocks(effect_frame, original_mask, results, frame)
        
        # 绘制识别信息
        self.analyzer.draw_info_on_effect_frame(effect_frame, original_mask, results)
        
        return effect_frame
    
    def create_info_quadrant(self, results):
        """
        创建左下角文本信息区域
        """
        # 创建黑色背景，使用定义的 bottom_left_width
        info_canvas = np.zeros((self.bottom_height, self.bottom_left_width, 3), dtype=np.uint8)
        
        # 找到要显示的目标（优先 Target，否则显示第一个人）
        target_person = None
        if len(results) > 0:
            # 1. 尝试找标记为 Target 的人
            for r in results:
                if r.get('is_target', False):
                    target_person = r
                    break
            
            # 2. 如果没找到 Target，默认显示第一个人
            if target_person is None:
                target_person = results[0]
        
        # --- UI级缓存逻辑 ---
        if not hasattr(self, 'ui_target_cache'):
            self.ui_target_cache = {} # 初始化缓存

        if target_person:
            # 检查当前帧是否有有效信息
            has_emotion = bool(target_person.get('emotion'))
            has_face = bool(target_person.get('face'))
            
            # 如果有有效信息，更新缓存
            if has_emotion or has_face:
                self.ui_target_cache = target_person.copy() # 深度拷贝一份作为快照
            # 如果当前帧信息缺失（如轻量帧或丢失），且缓存里有东西，且我们认为还是同一个人（简单起见，直接用）
            elif self.ui_target_cache:
                 # 强制把缓存里的高级属性贴给当前显示的 target_person
                 cached = self.ui_target_cache
                 if not target_person.get('emotion'):
                     target_person['emotion'] = cached.get('emotion')
                     target_person['emotion_conf'] = cached.get('emotion_conf')
                 if not target_person.get('face'):
                     target_person['face'] = cached.get('face')
                 if not target_person.get('person_id'):
                     target_person['person_id'] = cached.get('person_id')

        if len(results) == 0:
            cv2.putText(info_canvas, "No person detected", 
                       (30, self.bottom_height // 2),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (150, 150, 150), 2)
            return info_canvas
        
        # 显示人物信息
        y_offset = 40
        line_height = 35

        if target_person:
            r = target_person
            
            # 16号字体基准 (0.8)
            font_scale_base = 0.8
            # 14号字体基准 (0.7)
            font_scale_detail = 0.7
            line_height = 35
            
            # 人物标识
            person_id = r.get('person_id', '?')
            # 获取置信度
            person_conf = r.get('person_conf', r.get('conf', 0.0))
            
            # 如果是被追踪的目标，加星号或高亮
            is_target = r.get('is_target', False)
            target_marker = "[TARGET]" if is_target else ""
            color = (0, 255, 0) if is_target else (255, 255, 255)
            
            # Line 1: ID + Conf + Target
            cv2.putText(info_canvas, f"PERSON {person_id} ({person_conf:.0%}) {target_marker}", 
                       (30, y_offset),
                       cv2.FONT_HERSHEY_SIMPLEX, font_scale_base, color, 2)
            y_offset += line_height + 5
            
            # Line 2: Age | Emotion | Build
            line2_parts = []
            
            # Age
            if r.get('face'):
                age = r['face'].get('smoothed_age', r['face'].get('age', 0))
                line2_parts.append(f"Age:{age}")
            
            # Emotion
            if r.get('emotion'):
                emotion = r['emotion'].capitalize()
                conf = r.get('emotion_conf')
                if conf is not None:
                    line2_parts.append(f"Emo:{emotion}({conf:.0%})")
                else:
                    line2_parts.append(f"Emo:{emotion}")
                
            # Build
            if r.get('body_type'):
                build = r['body_type'].get('build', '')
                if build:
                    line2_parts.append(f"Build:{build}")
            
            if line2_parts:
                line2_text = " | ".join(line2_parts)
                cv2.putText(info_canvas, line2_text, 
                           (50, y_offset),
                           cv2.FONT_HERSHEY_SIMPLEX, font_scale_detail, (200, 200, 200), 1)
                y_offset += line_height
            
            # Line 3: Clothing (Type + Color + Conf)
            line3_parts = []
            if r.get('clothing'):
                clothing = r['clothing']
                clothing_type = clothing.get('type', {})
                
                # Upper
                upper_type = clothing_type.get('upper', '')
                upper_color = clothing.get('upper_color', '')
                upper_conf = clothing.get('upper_color_conf')
                
                if upper_type or upper_color:
                    # 构建 "Type(Color,Conf)" 格式
                    u_str = f"Up:{upper_type if upper_type else 'Top'}"
                    
                    extras = []
                    if upper_color: extras.append(upper_color)
                    if upper_conf is not None: extras.append(f"{upper_conf:.0%}")
                    
                    if extras:
                        u_str += f"({','.join(extras)})"
                    line3_parts.append(u_str)
                
                # Lower
                lower_type = clothing_type.get('lower', '')
                lower_color = clothing.get('lower_color', '')
                lower_conf = clothing.get('lower_color_conf')
                
                if lower_type or lower_color:
                    l_str = f"Low:{lower_type if lower_type else 'Bottom'}"
                    
                    extras = []
                    if lower_color: extras.append(lower_color)
                    if lower_conf is not None: extras.append(f"{lower_conf:.0%}")
                    
                    if extras:
                        l_str += f"({','.join(extras)})"
                    line3_parts.append(l_str)
                
            if line3_parts:
                line3_text = " | ".join(line3_parts)
                cv2.putText(info_canvas, line3_text, 
                           (50, y_offset),
                           cv2.FONT_HERSHEY_SIMPLEX, font_scale_detail, (200, 200, 200), 1)
                y_offset += line_height

            # Line 4+: Description (Auto Wrap)
            description = r.get('description', '')
            if description:
                # 计算每行最大字符数 (基于宽度 960px)
                # 14号字体 (0.7) 每个字符约占 14-15px (宽)
                char_width_approx = 15 
                max_chars_per_line = (self.bottom_left_width - 80) // char_width_approx
                
                # 简单的换行逻辑
                words = description.split(' ')
                current_line = ""
                
                for word in words:
                    # 试探性加上这个词
                    test_line = current_line + " " + word if current_line else word
                    
                    if len(test_line) <= max_chars_per_line:
                        current_line = test_line
                    else:
                        # 当前行满了，绘制并换行
                        cv2.putText(info_canvas, current_line, 
                                   (50, y_offset),
                                   cv2.FONT_HERSHEY_SIMPLEX, font_scale_detail, (180, 180, 180), 1)
                        y_offset += line_height
                        current_line = word # 新行的开始
                        
                        # 安全检查：防止画出界
                        if y_offset > self.bottom_height - 10:
                            break
                
                # 绘制最后一行
                if current_line and y_offset <= self.bottom_height - 10:
                    cv2.putText(info_canvas, current_line, 
                               (50, y_offset),
                               cv2.FONT_HERSHEY_SIMPLEX, font_scale_detail, (180, 180, 180), 1)
        
        return info_canvas

    def create_tracker_view(self, frame, results=None, precomputed_frame=None):
        """
        创建右下角追踪器视图
        使用 AdvancedTracker 处理当前帧 (仅运行逻辑，不显示GUI)
        """
        # 使用 bottom_right_width (480)
        target_w = self.bottom_right_width
        target_h = self.bottom_height
        
        # 创建纯黑背景
        canvas = np.zeros((target_h, target_w, 3), dtype=np.uint8)

        # 注意：这里的 precomputed_frame 是从后台线程获取的最新画面
        # 如果它不为空，直接返回（或者画出来）
        # 现在的逻辑里，我们不显示 Tracker GUI，所以其实可以只返回黑屏
        # 为了调试方便，如果线程有产出画面，我们还是可以保留逻辑，但用户要求黑屏
        
        # 始终返回 Track ERROR 或 黑屏，因为控制逻辑移到了后台
        # 如果想看 Tracker 画面用于调试，可以用 precomputed_frame
        
        if not self.tracker:
            cv2.putText(canvas, "TRACKER ERROR", 
                       (target_w//2 - 100, target_h//2),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
            
        return canvas

    def create_composite_view(self, silhouette_frame, glitch_frame, results, frame, precomputed_tracker_frame=None):
        """
        创建组合视图 (1920x1080)
        """
        # 创建主画布
        canvas = np.zeros((self.window_height, self.window_width, 3), dtype=np.uint8)
        
        # --- 1. 上半部分 ---
        # 左上 (Silhouette) - 1440x810
        silhouette_resized = self.resize_to_fit(silhouette_frame, self.left_width, self.top_height)
        canvas[0:self.top_height, 0:self.left_width] = silhouette_resized
        
        # 右上 (Glitch) - 480x810
        glitch_resized = self.resize_to_fit(glitch_frame, self.right_width, self.top_height)
        canvas[0:self.top_height, self.left_width:self.window_width] = glitch_resized
        
        # --- 2. 下半部分 ---
        # 左下 (Info) - 960x270
        info_area = self.create_info_quadrant(results) # 已经在内部使用了 bottom_left_width
        canvas[self.top_height:self.window_height, 0:self.bottom_left_width] = info_area
        
        # 中下 (Blank/Black) - 480x270
        # 默认为黑色，不需要额外操作
        
        # 右下 (Tracker) - 480x270
        # x: 1440 ~ 1920
        tracker_view = self.create_tracker_view(frame, results=results, precomputed_frame=precomputed_tracker_frame)
        start_x_right = self.bottom_left_width + self.bottom_mid_width # 960 + 480 = 1440
        canvas[self.top_height:self.window_height, start_x_right:self.window_width] = tracker_view
        
        # --- 3. 绘制分隔线 ---
        # 颜色
        line_color = (80, 80, 80)
        thickness = 2
        
        # 水平总线 (y=810)
        cv2.line(canvas, (0, self.top_height), (self.window_width, self.top_height), line_color, thickness)
        
        # 垂直线 1: 分割左上/右上 (x=1440, y=0~810)
        cv2.line(canvas, (self.left_width, 0), (self.left_width, self.top_height), line_color, thickness)
        
        # 垂直线 2: 下半部分分割 Info/Mid (x=960, y=810~1080)
        cv2.line(canvas, (self.bottom_left_width, self.top_height), (self.bottom_left_width, self.window_height), line_color, thickness)
        
        # 垂直线 3: 下半部分分割 Mid/Right (x=1440, y=810~1080)
        # 这个x正好等于 left_width，所以视觉上和垂直线1是对齐的，形成贯穿效果
        cv2.line(canvas, (start_x_right, self.top_height), (start_x_right, self.window_height), line_color, thickness)

        return canvas
    
    def run(self):
        """运行系统"""
        print("\n" + "=" * 60)
        print("系统启动")
        print("=" * 60)
        print("\n控制键:")
        print("  'q' - 退出")
        print("=" * 60)
        print()
        
        self.running = True
        
        # 发送 OSC 启动信号
        if self.osc:
            self.osc.set_value('Bg', 1.0)
            self.osc.update()
        
        # 创建全屏窗口
        cv2.namedWindow('Gallery View', cv2.WINDOW_NORMAL)
        cv2.resizeWindow('Gallery View', self.window_width, self.window_height)
        
        try:
            while self.running:
                # --- 性能诊断计时开始 ---
                t_start = time.time()

                # 读取帧
                ret, frame = self.cap.read()
                t_read = time.time()

                if not ret:
                    print("✗ 无法读取帧")
                    break
                
                # 镜像翻转摄像头画面
                frame = cv2.flip(frame, 1)
                
                # 保存一份纯净的帧用于故障艺术效果（避免被 analyzer 的标注污染）
                clean_frame = frame.copy()
                
                # ===== 1. 人物分析 (用于左上、右上、左下) =====
                self.analyzer.enable_effects = False
                
                # --- AI 隔帧优化策略 ---
                # 每 3 帧运行一次耗时的人脸和情绪分析
                run_heavy_ai = (self.fps_counter % 3 == 0)
                
                self.analyzer.face_enabled = run_heavy_ai
                self.analyzer.emotion_enabled = run_heavy_ai
                
                _, results = self.analyzer.process_frame(frame)
                t_analysis = time.time()
                
                # 结果合并逻辑：如果是轻量帧，合并上一帧的人脸信息
                if run_heavy_ai:
                    # 关键修复：如果当前（Heavy AI帧）检测到了人但没检测到情绪（可能是因为运动模糊导致人脸识别失败），
                    # 尝试从上一批缓存结果中继承情绪，而不是让它变成 None (导致显示 "Analyzing...")
                    if hasattr(self, 'last_full_results') and self.last_full_results:
                        for curr_r in results:
                            # 如果当前结果没有情绪信息
                            if not curr_r.get('emotion'):
                                # 尝试在旧结果中找匹配
                                curr_box = curr_r.get('bbox')
                                if not curr_box: continue
                                cx = (curr_box[0] + curr_box[2]) / 2
                                cy = (curr_box[1] + curr_box[3]) / 2
                                
                                best_match = None
                                min_dist = 300.0 
                                
                                for old_r in self.last_full_results:
                                    old_box = old_r.get('bbox')
                                    if not old_box: continue
                                    ox = (old_box[0] + old_box[2]) / 2
                                    oy = (old_box[1] + old_box[3]) / 2
                                    dist = ((cx - ox)**2 + (cy - oy)**2)**0.5
                                    if dist < min_dist:
                                        min_dist = dist
                                        best_match = old_r
                                
                                # 如果找到了之前的匹配，且之前有情绪，就继承过来
                                if best_match and best_match.get('emotion'):
                                    if not curr_r.get('face'): curr_r['face'] = best_match.get('face')
                                    curr_r['emotion'] = best_match['emotion']
                                    curr_r['emotion_conf'] = best_match.get('emotion_conf')
                                    if 'person_id' in best_match and 'person_id' not in curr_r:
                                        curr_r['person_id'] = best_match['person_id']

                    self.last_full_results = results
                elif hasattr(self, 'last_full_results') and self.last_full_results:
                    # 改进的匹配策略：
                    # 1. 如果只有 1 个人，直接无脑继承上一帧的第 1 个结果 (最稳定)
                    # 2. 如果有多人，才使用距离匹配
                    
                    if len(results) == 1 and len(self.last_full_results) >= 1:
                        # 单人模式：直接继承，解决快速移动时的闪烁问题
                        curr_r = results[0]
                        old_r = self.last_full_results[0] # 假设主要目标也是第一个
                        
                        if 'face' in old_r: curr_r['face'] = old_r['face']
                        if 'emotion' in old_r: curr_r['emotion'] = old_r['emotion']
                        if 'emotion_conf' in old_r: curr_r['emotion_conf'] = old_r['emotion_conf']
                        if 'person_id' in old_r and 'person_id' not in curr_r: 
                            curr_r['person_id'] = old_r['person_id']
                    else:
                        # 多人模式：距离匹配
                        for curr_r in results:
                            curr_box = curr_r.get('bbox')
                            if not curr_box: continue
                            
                            cx = (curr_box[0] + curr_box[2]) / 2
                            cy = (curr_box[1] + curr_box[3]) / 2
                            
                            best_match = None
                            min_dist = 300.0 # 像素阈值
                            
                            for old_r in self.last_full_results:
                                old_box = old_r.get('bbox')
                                if not old_box: continue
                                ox = (old_box[0] + old_box[2]) / 2
                                oy = (old_box[1] + old_box[3]) / 2
                                dist = ((cx - ox)**2 + (cy - oy)**2)**0.5
                                if dist < min_dist:
                                    min_dist = dist
                                    best_match = old_r
                            
                            if best_match:
                                if 'face' in best_match: curr_r['face'] = best_match['face']
                                if 'emotion' in best_match: curr_r['emotion'] = best_match['emotion']
                                if 'emotion_conf' in best_match: curr_r['emotion_conf'] = best_match['emotion_conf']
                                if 'person_id' in best_match and 'person_id' not in curr_r: 
                                    curr_r['person_id'] = best_match['person_id']

                h, w = frame.shape[:2]
                person_mask = self.analyzer.get_segmentation_mask(frame)
                
                if person_mask is None:
                    person_mask = np.zeros((h, w), dtype=np.uint8)
                    for r in results:
                        bbox = r.get('bbox')
                        keypoints = r.get('keypoints')
                        person_silhouette = self.analyzer.create_person_silhouette_from_keypoints(
                            keypoints, bbox, h, w
                        )
                        person_mask = cv2.bitwise_or(person_mask, person_silhouette)
                
                t_mask = time.time()

                # ===== 2. 异步追踪器逻辑 =====
                tracker_active_idx = None
                tracker_frame = None
                
                if self.tracker:
                    # 尝试将当前帧和结果放入后台队列
                    # 如果队列满了（后台还没处理完上一帧），则直接丢弃当前帧的追踪任务
                    # 这样可以保证主线程永远不卡顿
                    try:
                        # 放入队列，frame 需要 copy 吗？因为 process_frame 会画图
                        # 为了安全，copy 一份。或者如果 process_frame 只是读取，那就算了
                        # AdvancedTracker.process_frame 会在图上画框，所以必须 copy
                        # 否则会污染主线程显示的画面
                        self.tracker_queue.put_nowait((frame.copy(), results))
                    except queue.Full:
                        # 队列满，说明机械臂忙，跳过
                        pass
                    
                    # 获取最新的追踪结果（哪怕是上一帧的）
                    with self.tracker_lock:
                         tracker_active_idx = self.latest_tracker_result['active_idx']
                         tracker_frame = self.latest_tracker_result['frame']
                    
                    # 标记 results 中的目标
                    if tracker_active_idx is not None:
                        for i, res in enumerate(results):
                            if i == tracker_active_idx:
                                res['is_target'] = True
                            else:
                                res['is_target'] = False

                # 更新 OSC (根据当前追踪目标)
                self.update_osc(results, tracker_active_idx)
                t_tracker = time.time()
                
                # 左侧：黑色格子
                self.analyzer.enable_effects = True
                self.analyzer.effect_mode = 'silhouette'
                # 使用 analyzer.apply_visual_effects 并传入 mask 和 target_idx
                silhouette_frame = self.analyzer.apply_visual_effects(
                    frame, results, 
                    person_mask=person_mask, 
                    target_person_idx=tracker_active_idx
                )
                
                # 右侧：故障艺术 (Glitch Art)
                # 传入 tracker_active_idx，让右上角只显示被追踪的人
                # create_glitch_frame(frame, results, target_person_idx=None)
                glitch_frame = self.glitch_effect.create_glitch_frame(
                    clean_frame, 
                    results, 
                    target_person_idx=tracker_active_idx
                )
                t_effects = time.time()
                
                # ===== 3. 创建组合视图 =====
                # 注意：tracker_frame 已经生成了，传给 create_composite_view 避免重复计算
                composite = self.create_composite_view(silhouette_frame, glitch_frame, results, frame, precomputed_tracker_frame=tracker_frame)
                t_composite = time.time()
                
                # 计算FPS
                self.fps_counter += 1
                if time.time() - self.fps_start > 1.0:
                    self.current_fps = self.fps_counter / (time.time() - self.fps_start)
                    self.fps_counter = 0
                    self.fps_start = time.time()
                
                # 显示画面
                cv2.imshow('Gallery View', composite)
                
                # 键盘控制
                key = cv2.waitKey(1) & 0xFF
                
                if key == ord('q'):
                    break
        
        except KeyboardInterrupt:
            print("\n用户中断")
        finally:
            self.close()
    
    def close(self):
        """关闭系统"""
        self.running = False # 先设置标志位，通知所有线程
        
        # 发送 OSC 关闭信号
        if self.osc:
            print("正在关闭 OSC 通道...")
            # 强制直接发送 0，绕过平滑逻辑，确保归零
            if hasattr(self.osc, 'client'):
                try:
                    # 发送两次以防丢包
                    for _ in range(2):
                        # 1. 背景归零
                        self.osc.client.send_message('/Bg', 0.0)
                        
                        # 2. 所有其他通道归零
                        for name, channel in self.osc.channels.items():
                            if name != 'Bg':
                                self.osc.client.send_message(channel.address, 0.0)
                        
                        time.sleep(0.02)
                            
                except Exception as e:
                    print(f"OSC 关闭发送失败: {e}")

        if self.cap:
            self.cap.release()
            
        # 等待追踪线程结束
        if hasattr(self, 'tracker_thread') and self.tracker_thread.is_alive():
             self.tracker_thread.join(timeout=1.0)
        
        # 关闭追踪器（这会让电机归位）
        if self.tracker:
            self.tracker.close()
            
        cv2.destroyAllWindows()
        print("✓ 系统已关闭")

if __name__ == "__main__":
    # 创建画廊视图
    gallery = GalleryView(
        camera_id=0,
        window_width=1920, # 16:9 比例
        window_height=1080
    )
    gallery.run()
