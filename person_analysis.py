"""
Person and Face Analysis System
- Body: Pose, Clothing, Color, Body Type, Keypoints
- Face: Age, Emotion, Features
Using YOLOv8-Pose + InsightFace + FER + DeepFace

This module contains the core analyzer class used by the multi-camera system.
"""

import cv2
import numpy as np
import torch
from ultralytics import YOLO
from sklearn.cluster import KMeans
import time
import os
import random

# TensorFlow GPU Memory Growth (Prevent DeepFace from hogging all VRAM)
try:
    import tensorflow as tf
    gpus = tf.config.experimental.list_physical_devices('GPU')
    if gpus:
        for gpu in gpus:
            tf.config.experimental.set_memory_growth(gpu, True)
except ImportError:
    pass
except Exception as e:
    print(f"Warning: Could not set TF memory growth: {e}")

# Depth estimation (optional)
try:
    import torch.nn.functional as F
    DEPTH_AVAILABLE = True
except ImportError:
    DEPTH_AVAILABLE = False

# TouchDesigner transmitter (Moved to integrations/)
TD_AVAILABLE = False

# Oscilloscope & AI Description removed
OSCILLOSCOPE_AVAILABLE = False
ENABLE_OSCILLOSCOPE_AUDIO = False
AI_DESC_AVAILABLE = False

# Suppress warnings
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'

# Suppress libpng warnings (iCCP profile warnings)
# These warnings come from OpenCV/PIL when loading PNG images in model files
# They don't affect functionality, just suppress the output
import warnings
warnings.filterwarnings('ignore', category=UserWarning, message='.*iCCP.*')

# Also suppress stderr output from libpng (if needed)
# This redirects stderr temporarily during model loading
import sys
from contextlib import contextmanager

@contextmanager
def suppress_stderr():
    """Temporarily suppress stderr output"""
    with open(os.devnull, 'w') as devnull:
        old_stderr = sys.stderr
        sys.stderr = devnull
        try:
            yield
        finally:
            sys.stderr = old_stderr

# InsightFace imports
try:
    import insightface
    from insightface.app import FaceAnalysis
    INSIGHTFACE_AVAILABLE = True
except ImportError:
    print("Warning: InsightFace not installed.")
    INSIGHTFACE_AVAILABLE = False

# HSEmotion imports (Primary for Emotion)
try:
    # Monkey Patch torch.load to disable weights_only check for HSEmotion
    _original_load = torch.load
    def _safe_load(*args, **kwargs):
        if 'weights_only' not in kwargs:
            kwargs['weights_only'] = False
        return _original_load(*args, **kwargs)
    torch.load = _safe_load
    
    from hsemotion.facial_emotions import HSEmotionRecognizer
    HSEMOTION_AVAILABLE = True
except ImportError:
    print("Warning: hsemotion not installed.")
    HSEMOTION_AVAILABLE = False

# Clean up DeepFace/FER references
DEEPFACE_AVAILABLE = False
FER_AVAILABLE = False

class CompletePersonFaceAnalyzer:
    """Complete person and face analysis with all attributes"""
    
    def __init__(self, show_keypoints=True, show_skeleton=True):
        print("=" * 60)
        print("Complete Person + Face Analysis System")
        print("ALL ATTRIBUTES: Age, Emotion")
        print("=" * 60)
        
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        print(f"Device: {self.device}")
        
        if self.device.type == 'cuda':
            print(f"  GPU: {torch.cuda.get_device_name(0)}")
        
        self.show_keypoints = show_keypoints
        self.show_skeleton = show_skeleton
        
        # Load YOLOv8-Pose
        print("Loading YOLOv8-Pose for body detection...")
        # Suppress libpng warnings during model loading
        with suppress_stderr():
            pose_path = 'models/yolov8n-pose.pt'
            if not os.path.exists(pose_path): pose_path = 'yolov8n-pose.pt'
            self.yolo_model = YOLO(pose_path)
        if self.device.type == 'cuda':
            self.yolo_model.to(self.device)
        print("  ✓ YOLOv8-Pose loaded!")
        
        # Load YOLOv8-Seg for accurate person segmentation (for visual effects)
        print("Loading YOLOv8-Seg for person segmentation...")
        try:
            with suppress_stderr():
                seg_path = 'models/yolov8n-seg.pt'
                if not os.path.exists(seg_path): seg_path = 'yolov8n-seg.pt'
                self.yolo_seg_model = YOLO(seg_path)
            if self.device.type == 'cuda':
                self.yolo_seg_model.to(self.device)
            print("  ✓ YOLOv8-Seg loaded!")
            self.segmentation_enabled = True
        except Exception as e:
            print(f"  ⚠ YOLOv8-Seg failed to load: {e}")
            print("  → Visual effects will use keypoint-based silhouette")
            self.segmentation_enabled = False
        
        # Load MiDaS for depth estimation (for depth-based visual effects)
        # 深度模式已注释
        # print("Loading MiDaS for depth estimation...")
        # try:
        #     # Check if timm is available (required for MiDaS)
        #     try:
        #         import timm
        #     except ImportError:
        #         print("  ⚠ timm library not found. Install with: pip install timm>=0.9.0")
        #         print("  → Depth effects will be disabled")
        #         self.depth_enabled = False
        #         self.midas = None
        #         self.midas_transform = None
        #         self.depth_cache = None
        #         self.depth_cache_counter = 0
        #         return
        #     
        #     # Use MiDaS small model for real-time performance
        #     print("  → Downloading MiDaS model from PyTorch Hub (first time may take a while)...")
        #     self.midas = torch.hub.load('intel-isl/MiDaS', 'MiDaS_small', trust_repo=True)
        #     self.midas.to(self.device)
        #     self.midas.eval()
        #     
        #     # Load MiDaS transforms
        #     midas_transforms = torch.hub.load('intel-isl/MiDaS', 'transforms', trust_repo=True)
        #     self.midas_transform = midas_transforms.small_transform
        #     
        #     # Initialize depth cache
        #     self.depth_cache = None
        #     self.depth_cache_counter = 0
        #     
        #     print("  ✓ MiDaS depth model loaded!")
        #     self.depth_enabled = True
        # except Exception as e:
        #     print(f"  ⚠ MiDaS failed to load: {e}")
        #     print("  → Depth effects will be disabled")
        #     print("  → Troubleshooting:")
        #     print("    1. Check internet connection (model downloads from PyTorch Hub)")
        #     print("    2. Install timm: pip install timm>=0.9.0")
        #     print("    3. If network issue, try: pip install --upgrade torch torchvision")
        #     self.depth_enabled = False
        #     self.midas = None
        #     self.midas_transform = None
        #     self.depth_cache = None
        #     self.depth_cache_counter = 0
        
        # 深度模式已禁用
        self.depth_enabled = False
        self.midas = None
        self.midas_transform = None
        self.depth_cache = None
        self.depth_cache_counter = 0
        
        # Load InsightFace
        if INSIGHTFACE_AVAILABLE:
            print("Loading InsightFace for face analysis...")
            try:
                self.face_app = FaceAnalysis(
                    name='buffalo_l',
                    providers=['CUDAExecutionProvider', 'CPUExecutionProvider'] if self.device.type == 'cuda' else ['CPUExecutionProvider']
                )
                # Use 640x640 for stability (official recommendation)
                # Square input avoids broadcast shape errors with 1920x1080 frames
                self.face_app.prepare(ctx_id=0 if self.device.type == 'cuda' else -1, det_size=(640, 640))
                print("  ✓ InsightFace loaded! (det_size: 640x640)")
                self.face_enabled = True
            except Exception as e:
                print(f"  ✗ InsightFace failed: {e}")
                self.face_enabled = False
        else:
            self.face_enabled = False
        
        # Load HSEmotion for emotion recognition
        if HSEMOTION_AVAILABLE:
            print("Loading HSEmotion for emotion recognition...")
            try:
                # 使用推荐的模型 (支持 GPU)
                self.emotion_detector = HSEmotionRecognizer(
                    model_name='enet_b0_8_best_vgaf', 
                    device='cuda' if self.device.type == 'cuda' else 'cpu'
                )
                print("  ✓ HSEmotion loaded! (EfficientNet-B0)")
                self.emotion_enabled = True
            except Exception as e:
                print(f"  ✗ HSEmotion failed: {e}")
                self.emotion_enabled = False
        else:
            self.emotion_enabled = False
        
        # DeepFace is only used for emotion detection now
        # No race detection needed
        
        # Keypoint names (COCO format - 17 points)
        self.keypoint_names = [
            'Nose', 'Left Eye', 'Right Eye', 'Left Ear', 'Right Ear',
            'Left Shoulder', 'Right Shoulder', 'Left Elbow', 'Right Elbow',
            'Left Wrist', 'Right Wrist', 'Left Hip', 'Right Hip',
            'Left Knee', 'Right Knee', 'Left Ankle', 'Right Ankle'
        ]
        
        # Skeleton connections
        self.skeleton = [
            [15, 13], [13, 11], [16, 14], [14, 12], [11, 12],
            [5, 11], [6, 12], [5, 6],
            [5, 7], [6, 8], [7, 9], [8, 10],
            [0, 1], [0, 2], [1, 3], [2, 4], [3, 5], [4, 6]
        ]
        
        # Colors for keypoints
        self.keypoint_colors = [
            (255, 0, 0), (255, 128, 0), (255, 255, 0), (128, 255, 0),
            (0, 255, 0), (0, 255, 128), (0, 255, 255), (0, 128, 255),
            (0, 0, 255), (128, 0, 255), (255, 0, 255), (255, 0, 128),
            (255, 128, 128), (255, 128, 0), (128, 128, 0),
            (255, 255, 128), (128, 255, 255)
        ]
        
        # Emotion text mapping (避免终端不支持emoji)
        self.emotion_text = {
            'angry': 'Anger',
            'disgust': 'Disgust',
            'fear': 'Fear',
            'happy': 'Happiness',
            'sad': 'Sadness',
            'surprise': 'Surprise',
            'neutral': 'Neutral',
            # HSEmotion mappings
            'anger': 'Anger',
            'happiness': 'Happiness',
            'sadness': 'Sadness',
            'contempt': 'Contempt'
        }
        
        # Performance settings
        self.process_every_n_frames = 10  # 从5改到10，提升性能
        self.emotion_every_n_frames = 10  # Emotion slower
        self.frame_counter = 0
        self.cached_results = {}
        
        # Age smoothing - 保存最近N次年龄检测结果
        self.age_history = {}  # person_id: [age1, age2, ...]
        self.age_history_size = 5  # 保留最近5次结果
        
        # Emotion smoothing - 保存最近N次情绪检测结果
        self.emotion_history = {}  # person_id: [emotion1, emotion2, ...]
        self.emotion_history_size = 5  # 保留最近5次结果，取众数
        
        # Auto-print descriptions
        self.auto_print_descriptions = False
        
        # AI描述生成器
        if AI_DESC_AVAILABLE:
            # 可以在这里配置使用哪个提供商：'openai', 'claude', 或 'none'
            # 如果设置了API key，会自动启用
            self.ai_generator = AIDescriptionGenerator(provider='openai')
        else:
            self.ai_generator = None
        
        # Visual effects settings
        self.enable_effects = False  # 特效开关
        self.effect_mode = 'silhouette'  # 特效模式: 'silhouette' 或 'ascii'
        # self.enable_depth = True  # 默认开启深度效果（当特效开启时）- 已注释
        self.feather_radius = 15  # 羽化半径
        self.trail_frames = 5  # 残影帧数
        self.trail_history = []  # 残影历史帧
        # self.depth_cache = None  # 缓存深度图以提高性能 - 已注释
        # self.depth_cache_counter = 0  # 深度图更新计数器 - 已注释
        
        # ASCII艺术效果设置
        self.ascii_grid_size = 8  # 字符大小和密度（更小=更密集）
        self.ascii_threshold = 20  # 亮度阈值（更低=更多字符，包括暗色衣服）
        self.ascii_chars = ['0', '1']  # 使用的字符
        
        # 扫描线效果（每个人物独立的扫描线）
        self.scan_line_positions = {}  # person_id: y_position
        self.scan_line_trails = {}  # person_id: [历史位置列表] 用于残影效果
        self.scan_line_speed = 10  # 扫描线移动速度（像素/帧，更快，快两倍）
        self.scan_line_thickness = 1  # 扫描线粗细（1px描边）
        self.scan_line_color = (255, 255, 255)  # 扫描线颜色（白色）
        self.scan_line_trail_frames = 8  # 残影保留帧数
        self.scan_line_blur_radius = 15  # 残影模糊半径
        
        print("=" * 60)
        print("Features:")
        print("  ✓ Body: 17 Keypoints, Clothing, Color, Body Type")
        if self.face_enabled:
            print("  ✓ Face: Age")
        if self.emotion_enabled:
            print("  ✓ Emotion: 8 expressions (via HSEmotion)")
        if self.segmentation_enabled:
            print("  ✓ Visual Effects: Precise Segmentation (YOLOv8-Seg)")
        else:
            print("  ✓ Visual Effects: Keypoint-based Silhouette")
        # if self.depth_enabled:
        #     print("  ✓ Depth Effects: MiDaS depth estimation")  # 已注释
        print("  ✓ Visualization: Keypoints + Skeleton")
        print("=" * 60)
        
        # Initialize Oscilloscope Overlay (Audio-Reactive Visualization)
        # 延迟音频初始化，避免与其他程序冲突
        if OSCILLOSCOPE_AVAILABLE:
            try:
                print("\n初始化音频反应示波器...")
                self.oscilloscope = OscilloscopeOverlay(
                    width=OSCILLOSCOPE_WIDTH,
                    height=OSCILLOSCOPE_HEIGHT,
                    position=OSCILLOSCOPE_POSITION
                )
                
                # 根据配置决定是否启用音频
                if ENABLE_OSCILLOSCOPE_AUDIO:
                    print("  ✓ 示波器已创建 (音频延迟启动)")
                    print("  💡 提示: 示波器音频将在检测到人后自动启动")
                else:
                    print("  ✓ 示波器已创建 (音频已禁用)")
                    print("  💡 提示: 在 oscilloscope_config_user.py 中启用音频")
                
                self.oscilloscope_audio_started = False
                self.oscilloscope_audio_enabled = ENABLE_OSCILLOSCOPE_AUDIO
            except Exception as e:
                print(f"  ✗ 示波器初始化失败: {e}")
                self.oscilloscope = None
                self.oscilloscope_audio_started = False
                self.oscilloscope_audio_enabled = False
        else:
            self.oscilloscope = None
            self.oscilloscope_audio_started = False
            self.oscilloscope_audio_enabled = False
        
        print("=" * 60)
    
    def detect_persons(self, frame):
        """Detect persons with pose"""
        results = self.yolo_model(frame, verbose=False, device=self.device)
        persons = []
        
        for result in results:
            if result.boxes is not None:
                for i, box in enumerate(result.boxes):
                    # 严格过滤：只有置信度 > 0.75 才认为是有效的人
                    if int(box.cls[0]) == 0 and float(box.conf[0]) > 0.75:
                        x1, y1, x2, y2 = map(int, box.xyxy[0])
                        
                        keypoints = None
                        if result.keypoints is not None and len(result.keypoints.data) > i:
                            keypoints = result.keypoints.data[i].cpu().numpy()
                        
                        persons.append({
                            'bbox': (x1, y1, x2, y2),
                            'confidence': float(box.conf[0]),
                            'keypoints': keypoints
                        })
        
        return persons
    
    def analyze_faces(self, frame):
        """Analyze all faces using InsightFace"""
        if not self.face_enabled or not hasattr(self, 'face_app'):
            return []
        
        try:
            faces = self.face_app.get(frame)
            face_results = []
            
            for face in faces:
                bbox = face.bbox.astype(int)
                age = int(face.age)
                embedding = face.embedding
                landmarks = face.kps.astype(int)
                
                face_results.append({
                    'bbox': tuple(bbox),
                    'age': age,
                    'embedding': embedding,
                    'landmarks': landmarks
                })
            
            return face_results
        except Exception as e:
            print(f"InsightFace error: {e}")
            return []
    
    def detect_emotion(self, face_region):
        """Detect emotion using DeepFace or FER"""
        # print(f"DEBUG: detect_emotion called. DeepFace available: {DEEPFACE_AVAILABLE}")
        if not DEEPFACE_AVAILABLE and not self.emotion_enabled:
            return None, None
        
        try:
            # Try DeepFace first (if available)
            if DEEPFACE_AVAILABLE:
                # print("DEBUG: Calling DeepFace...")
                try:
                    result = DeepFace.analyze(
                        img_path=face_region,
                        actions=['emotion'],
                        enforce_detection=False,
                        detector_backend='skip',
                        silent=True
                    )
                    
                    if isinstance(result, list):
                        result = result[0]
                    
                    if 'dominant_emotion' in result:
                        dominant_emotion = result['dominant_emotion']
                        confidence = result['emotion'][dominant_emotion] / 100.0  # Convert to 0-1
                        # print(f"DEBUG: DeepFace success: {dominant_emotion}")
                        return dominant_emotion, confidence
                except Exception as e:
                    print(f"DeepFace runtime error: {e}")
                    pass
            
            # Fallback to FER if available
            if self.emotion_enabled and hasattr(self, 'emotion_detector'):
                # print(f"FER Debug: Input shape {face_region.shape}")
                emotions = self.emotion_detector.detect_emotions(face_region)
                # print(f"FER Debug: Result {emotions}")
                if emotions and len(emotions) > 0:
                    emotion_scores = emotions[0]['emotions']
                    dominant_emotion = max(emotion_scores, key=emotion_scores.get)
                    confidence = emotion_scores[dominant_emotion]
                    return dominant_emotion, confidence
                else:
                    # Try forcing it if detection fails? No direct API for that in simple FER.
                    pass
            
            return None, None
        except Exception as e:
            print(f"Emotion detection error: {e}")
            return None, None
    
    def match_face_to_person(self, person_bbox, face_bbox):
        """Check if face belongs to person (relaxed matching)"""
        px1, py1, px2, py2 = person_bbox
        fx1, fy1, fx2, fy2 = face_bbox
        
        # Calculate face center
        face_cx = (fx1 + fx2) / 2
        face_cy = (fy1 + fy2) / 2
        
        # 放宽判定：只要人脸中心在身体框的水平范围内
        if px1 <= face_cx <= px2:
            person_height = py2 - py1
            # 这里的 0.6 改成 0.9，防止因为抬头或拍摄角度导致人脸位置偏高而被过滤
            if py1 - person_height * 0.2 <= face_cy <= py1 + person_height * 0.9:
                return True
                
        return False
    
    def smooth_age(self, person_id, raw_age):
        """Smooth age using moving average"""
        if person_id not in self.age_history:
            self.age_history[person_id] = []
        
        # Add new age to history
        self.age_history[person_id].append(raw_age)
        
        # Keep only recent N values
        if len(self.age_history[person_id]) > self.age_history_size:
            self.age_history[person_id] = self.age_history[person_id][-self.age_history_size:]
        
        # Return average
        return int(sum(self.age_history[person_id]) / len(self.age_history[person_id]))
    
    def smooth_emotion(self, person_id, raw_emotion):
        """Smooth emotion using voting (mode)"""
        if person_id not in self.emotion_history:
            self.emotion_history[person_id] = []
        
        # Add new emotion to history
        self.emotion_history[person_id].append(raw_emotion)
        
        # Keep only recent N values
        if len(self.emotion_history[person_id]) > self.emotion_history_size:
            self.emotion_history[person_id] = self.emotion_history[person_id][-self.emotion_history_size:]
        
        # Return most frequent emotion (mode)
        from collections import Counter
        counts = Counter(self.emotion_history[person_id])
        return counts.most_common(1)[0][0]
    
    def analyze_body_type(self, keypoints, bbox):
        """Analyze body type from keypoints"""
        if keypoints is None or len(keypoints) < 17:
            return None
        
        try:
            x1, y1, x2, y2 = bbox
            person_height = y2 - y1
            person_width = x2 - x1
            
            # Shoulder width
            left_shoulder = keypoints[5]
            right_shoulder = keypoints[6]
            if left_shoulder[2] > 0.3 and right_shoulder[2] > 0.3:
                shoulder_width = abs(right_shoulder[0] - left_shoulder[0])
            else:
                shoulder_width = person_width * 0.6
            
            # Hip width
            left_hip = keypoints[11]
            right_hip = keypoints[12]
            if left_hip[2] > 0.3 and right_hip[2] > 0.3:
                hip_width = abs(right_hip[0] - left_hip[0])
            else:
                hip_width = person_width * 0.5
            
            # Calculate ratios
            height_width_ratio = person_height / person_width if person_width > 0 else 2.0
            shoulder_hip_ratio = shoulder_width / hip_width if hip_width > 0 else 1.0
            
            # Body type classification
            if height_width_ratio > 2.2 and shoulder_hip_ratio > 1.1:
                build = "Athletic"
            elif height_width_ratio > 2.0:
                build = "Slim"
            elif height_width_ratio < 1.8:
                build = "Broad"
            else:
                build = "Average"
            
            if shoulder_hip_ratio > 1.15:
                shape_type = "V-Shape"
            elif shoulder_hip_ratio < 0.95:
                shape_type = "A-Shape"
            else:
                shape_type = "Rectangle"
            
            return {
                'build': build,
                'shape': shape_type
            }
        except:
            return None
    
    def get_color(self, image_region, mask=None):
        """Extract dominant color using HSV + Mask filtering (More Robust)"""
        if image_region is None or image_region.size == 0:
            return None, 0.0
        
        try:
            # 1. Pre-processing: Resize for speed
            target_size = (64, 64)
            img_small = cv2.resize(image_region, target_size)
            
            # 2. Masking: Only use pixels inside the person silhouette
            if mask is not None:
                mask_small = cv2.resize(mask, target_size)
                # Binarize mask
                _, mask_bin = cv2.threshold(mask_small, 128, 255, cv2.THRESH_BINARY)
                # Extract valid pixels (BGR)
                pixels = img_small[mask_bin > 0]
                
                # If too few pixels (e.g. empty mask), fallback to whole image or return None
                if len(pixels) < 50:
                    # Fallback: use center crop if mask failed
                    h, w = img_small.shape[:2]
                    center_pixels = img_small[h//4:h*3//4, w//4:w*3//4].reshape(-1, 3)
                    pixels = center_pixels
            else:
                # No mask provided, use whole image
                pixels = img_small.reshape(-1, 3)
            
            if len(pixels) == 0:
                return None, 0.0

            # 3. K-Means clustering to find Dominant Color (in BGR space)
            # n_init='auto' is default in newer sklearn, using fixed number for compatibility
            kmeans = KMeans(n_clusters=1, random_state=42, n_init=3)
            kmeans.fit(pixels)
            dominant_bgr = kmeans.cluster_centers_[0].astype(int)
            
            # Calculate confidence based on compactness (inertia)
            # Normalized by number of pixels
            inertia = kmeans.inertia_
            avg_dist = inertia / len(pixels) if len(pixels) > 0 else 0
            # Heuristic: avg_dist < 500 is very pure, > 3000 is mixed
            color_confidence = max(0.0, min(1.0, 1.0 - (avg_dist / 4000.0)))
            
            # 4. Convert Dominant Color to HSV for robust classification
            # Create a 1x1 pixel to convert color space
            pixel_bgr = np.uint8([[dominant_bgr]])
            pixel_hsv = cv2.cvtColor(pixel_bgr, cv2.COLOR_BGR2HSV)[0][0]
            
            h_val, s_val, v_val = int(pixel_hsv[0]), int(pixel_hsv[1]), int(pixel_hsv[2])
            
            # === HSV Color Classification Rules ===
            # OpenCV HSV ranges: H: 0-179, S: 0-255, V: 0-255
            
            # 1. Achromatic Colors (Black, White, Gray)
            # Check saturation and value
            
            # Black: Very low value (dark)
            if v_val < 40: 
                return 'Black', color_confidence
            
            # White: Very low saturation AND high value (bright)
            if s_val < 30 and v_val > 200:
                return 'White', color_confidence
                
            # Gray: Low saturation, medium value
            if s_val < 40:
                return 'Gray', color_confidence
            
            # 2. Chromatic Colors (based on Hue)
            # H values are halved degrees (0-360 -> 0-179)
            
            if (0 <= h_val <= 10) or (160 <= h_val <= 179):
                return 'Red', color_confidence
            elif 11 <= h_val <= 25:
                return 'Orange', color_confidence
            elif 26 <= h_val <= 35:
                return 'Yellow', color_confidence
            elif 36 <= h_val <= 85:
                return 'Green', color_confidence
            elif 86 <= h_val <= 99:
                return 'Cyan', color_confidence
            elif 100 <= h_val <= 130:
                return 'Blue', color_confidence
            elif 131 <= h_val <= 150:
                return 'Purple', color_confidence
            elif 151 <= h_val <= 159:
                return 'Pink', color_confidence
            
            return 'Mixed', color_confidence
            
        except Exception as e:
            # print(f"Color extraction error: {e}")
            return None, 0.0
    
    def classify_clothing_type(self, person_roi, keypoints, upper_roi, lower_roi):
        """Classify clothing type based on visual features"""
        try:
            if person_roi is None or person_roi.size == 0:
                return {'upper': 'Top', 'lower': 'Bottom'}
            
            h, w = person_roi.shape[:2]
            
            # Analyze upper and lower regions
            upper_type = "Top"
            lower_type = "Bottom"
            
            # Check if it's a dress (uniform color from top to bottom)
            if upper_roi is not None and lower_roi is not None:
                upper_gray = cv2.cvtColor(upper_roi, cv2.COLOR_BGR2GRAY) if len(upper_roi.shape) == 3 else upper_roi
                lower_gray = cv2.cvtColor(lower_roi, cv2.COLOR_BGR2GRAY) if len(lower_roi.shape) == 3 else lower_roi
                
                # Calculate color similarity
                upper_mean = np.mean(upper_gray)
                lower_mean = np.mean(lower_gray)
                color_diff = abs(upper_mean - lower_mean)
                
                # If very similar, might be a dress
                if color_diff < 25:
                    return {'upper': 'Dress', 'lower': None}
            
            # Analyze upper clothing
            if keypoints is not None and len(keypoints) >= 17:
                # Check sleeve length based on elbow/wrist visibility
                left_elbow = keypoints[7]
                right_elbow = keypoints[8]
                left_wrist = keypoints[9]
                right_wrist = keypoints[10]
                
                # If wrists are visible, likely short sleeves
                if (left_wrist[2] > 0.5 or right_wrist[2] > 0.5):
                    upper_type = "T-shirt"
                # If elbows visible but not wrists, likely long sleeves
                elif (left_elbow[2] > 0.5 or right_elbow[2] > 0.5):
                    upper_type = "Shirt"
                else:
                    upper_type = "Top"
            
            # Analyze lower clothing
            if keypoints is not None and len(keypoints) >= 17:
                left_knee = keypoints[13]
                right_knee = keypoints[14]
                left_ankle = keypoints[15]
                right_ankle = keypoints[16]
                
                # Check if knees and ankles are visible
                knees_visible = (left_knee[2] > 0.5 or right_knee[2] > 0.5)
                ankles_visible = (left_ankle[2] > 0.5 or right_ankle[2] > 0.5)
                
                if knees_visible and ankles_visible:
                    # Both visible, likely pants
                    lower_type = "Pants"
                elif knees_visible:
                    # Only knees visible, might be shorts
                    lower_type = "Shorts"
                else:
                    lower_type = "Bottom"
            
            return {'upper': upper_type, 'lower': lower_type}
            
        except Exception as e:
            return {'upper': 'Top', 'lower': 'Bottom'}
    
    def generate_person_description(self, result):
        """Generate a natural language description of the person"""
        # 如果启用了AI生成器，使用AI生成更丰富的描述
        if self.ai_generator and self.ai_generator.enabled:
            try:
                # 准备数据
                person_data = {
                    'age': result.get('face', {}).get('smoothed_age', result.get('face', {}).get('age')),
                    'emotion': result.get('emotion'),
                    'body_type': result.get('body_type'),
                    'clothing': result.get('clothing'),
                    'person_id': result.get('person_id')
                }
                
                # 使用AI生成
                ai_desc = self.ai_generator.generate_description(person_data)
                if ai_desc:
                    return ai_desc
            except Exception as e:
                print(f"AI描述生成失败，使用简单版本: {e}")
        
        # Fallback to original simple version (English)
        parts = []
        
        # Age
        if result.get('face'):
            face = result['face']
            age = face.get('smoothed_age', face['age'])
            
            # Age group
            if age < 18:
                age_group = "young"
            elif age < 35:
                age_group = "young adult"
            elif age < 55:
                age_group = "middle-aged"
            else:
                age_group = "senior"
            
            parts.append(f"A {age_group} person in their {age//10*10}s")
        else:
            parts.append("A person")
        
        # Body type
        if result.get('body_type'):
            build = result['body_type']['build'].lower()
            if build != 'average':
                parts.append(f"with a {build} build")
        
        # Clothing
        clothing_parts = []
        if result.get('clothing'):
            clothing = result['clothing']
            clothing_type = clothing.get('type')
            
            if clothing_type:
                upper_type = clothing_type.get('upper', '').lower()
                lower_type = clothing_type.get('lower', '').lower() if clothing_type.get('lower') else None
                
                # 安全获取颜色并转小写
                upper_color_raw = clothing.get('upper_color')
                lower_color_raw = clothing.get('lower_color')
                
                upper_color = upper_color_raw.lower() if upper_color_raw else None
                lower_color = lower_color_raw.lower() if lower_color_raw else None
                
                # Upper clothing
                if upper_type == 'dress':
                    if upper_color:
                        clothing_parts.append(f"wearing a {upper_color} dress")
                    else:
                        clothing_parts.append("wearing a dress")
                else:
                    upper_desc = ""
                    if upper_color:
                        upper_desc = f"a {upper_color} {upper_type if upper_type else 'top'}"
                    elif upper_type:
                        upper_desc = f"a {upper_type}"
                    
                    # Lower clothing
                    lower_desc = ""
                    if lower_type:
                        if lower_color:
                            lower_desc = f"{lower_color} {lower_type}"
                        else:
                            lower_desc = lower_type
                    
                    if upper_desc and lower_desc:
                        clothing_parts.append(f"wearing {upper_desc} and {lower_desc}")
                    elif upper_desc:
                        clothing_parts.append(f"wearing {upper_desc}")
                    elif lower_desc:
                        clothing_parts.append(f"wearing {lower_desc}")
        
        if clothing_parts:
            parts.append(clothing_parts[0])
        
        # Emotion
        if result.get('emotion'):
            emotion = result['emotion'].lower()
            emotion_text_map = {
                'happy': 'smiling',
                'sad': 'looking sad',
                'angry': 'looking angry',
                'surprise': 'looking surprised',
                'fear': 'looking fearful',
                'disgust': 'looking disgusted',
                'neutral': 'with a neutral expression'
            }
            emotion_desc = emotion_text_map.get(emotion, f'feeling {emotion}')
            parts.append(emotion_desc)
        
        # Join all parts
        if len(parts) == 1:
            return parts[0] + "."
        elif len(parts) == 2:
            return f"{parts[0]}, {parts[1]}."
        else:
            # Join with commas and 'and' before last part if it's emotion
            base = ", ".join(parts[:-1])
            return f"{base}, {parts[-1]}."
    
    def draw_keypoints_and_skeleton(self, frame, keypoints):
        """Draw keypoints and skeleton"""
        if keypoints is None or len(keypoints) < 17:
            return
        
        # Draw skeleton
        if self.show_skeleton:
            for connection in self.skeleton:
                pt1_idx, pt2_idx = connection
                
                if pt1_idx < len(keypoints) and pt2_idx < len(keypoints):
                    pt1 = keypoints[pt1_idx]
                    pt2 = keypoints[pt2_idx]
                    
                    if pt1[2] > 0.3 and pt2[2] > 0.3:
                        x1, y1 = int(pt1[0]), int(pt1[1])
                        x2, y2 = int(pt2[0]), int(pt2[1])
                        cv2.line(frame, (x1, y1), (x2, y2), (255, 255, 255), 1)
        
        # Draw keypoints
        if self.show_keypoints:
            for idx, kpt in enumerate(keypoints):
                x, y, conf = kpt
                
                if conf > 0.3:
                    x, y = int(x), int(y)
                    # 4x4 white circle (radius 2)
                    cv2.circle(frame, (x, y), 2, (255, 255, 255), -1)
    
    def get_text_color_for_position(self, person_mask, x, y):
        """
        根据位置判断文本颜色
        在黑色剪影上返回白色，在白色背景上返回黑色
        """
        h, w = person_mask.shape[:2]
        # 确保坐标在范围内
        x = max(0, min(int(x), w-1))
        y = max(0, min(int(y), h-1))
        
        # 检查该位置的mask值
        mask_value = person_mask[y, x]
        
        # 如果mask值 > 128（在黑色剪影区域），返回白色
        # 否则返回黑色（在白色背景上）
        if mask_value > 128:
            return (255, 255, 255)  # 白色文字（在黑色剪影上）
        else:
            return (0, 0, 0)  # 黑色文字（在白色背景上）
    
    def draw_keypoints_skeleton_red(self, frame, keypoints):
        """
        绘制红色的关节点和骨架（特效模式专用，隐藏面部关节点）
        """
        # 面部关键点索引：0=Nose, 1=LeftEye, 2=RightEye, 3=LeftEar, 4=RightEar
        face_keypoint_indices = {0, 1, 2, 3, 4}
        
        # Draw skeleton（跳过涉及面部的连线）
        if self.show_skeleton:
            for connection in self.skeleton:
                pt1_idx, pt2_idx = connection
                
                # 跳过面部连线
                if pt1_idx in face_keypoint_indices or pt2_idx in face_keypoint_indices:
                    continue
                
                if pt1_idx < len(keypoints) and pt2_idx < len(keypoints):
                    pt1 = keypoints[pt1_idx]
                    pt2 = keypoints[pt2_idx]
                    
                    if pt1[2] > 0.3 and pt2[2] > 0.3:
                        x1, y1 = int(pt1[0]), int(pt1[1])
                        x2, y2 = int(pt2[0]), int(pt2[1])
                        cv2.line(frame, (x1, y1), (x2, y2), (0, 0, 255), 1)  # 红色
        
        # Draw keypoints（跳过面部关节点）
        if self.show_keypoints:
            for idx, kpt in enumerate(keypoints):
                # 跳过面部关键点
                if idx in face_keypoint_indices:
                    continue
                
                x, y, conf = kpt
                
                if conf > 0.3:
                    x, y = int(x), int(y)
                    cv2.circle(frame, (x, y), 2, (0, 0, 255), -1)  # 红色
    
    def draw_keypoints_skeleton_adaptive(self, frame, person_mask, keypoints):
        """
        在特效帧上绘制关节点和骨架，颜色根据背景自适应
        """
        if keypoints is None or len(keypoints) < 17:
            return
        
        # Draw skeleton
        if self.show_skeleton:
            for connection in self.skeleton:
                pt1_idx, pt2_idx = connection
                
                if pt1_idx < len(keypoints) and pt2_idx < len(keypoints):
                    pt1 = keypoints[pt1_idx]
                    pt2 = keypoints[pt2_idx]
                    
                    if pt1[2] > 0.3 and pt2[2] > 0.3:
                        x1, y1 = int(pt1[0]), int(pt1[1])
                        x2, y2 = int(pt2[0]), int(pt2[1])
                        
                        # 在中点位置采样颜色
                        mid_x = (x1 + x2) // 2
                        mid_y = (y1 + y2) // 2
                        line_color = self.get_text_color_for_position(person_mask, mid_x, mid_y)
                        
                        cv2.line(frame, (x1, y1), (x2, y2), line_color, 1)
        
        # Draw keypoints
        if self.show_keypoints:
            for idx, kpt in enumerate(keypoints):
                x, y, conf = kpt
                
                if conf > 0.3:
                    x, y = int(x), int(y)
                    # 根据关节点位置选择颜色
                    point_color = self.get_text_color_for_position(person_mask, x, y)
                    # 4x4 circle (radius 2)
                    cv2.circle(frame, (x, y), 2, point_color, -1)
    
    def draw_data_blocks(self, effect_frame, person_mask, results, original_frame, target_result=None):
        """
        在人物剪影上绘制大量数据方块
        Target: 白色轮廓格子 + 黑色背景格子
        Others: 黑色轮廓格子 + 黑色背景格子
        """
        h, w = effect_frame.shape[:2]
        
        for r in results:
            if 'bbox' not in r:
                continue
            
            # Check if this person is the active target
            is_target = (target_result is not None and r is target_result)
            
            x1, y1, x2, y2 = r['bbox']
            
            # === 扩大 Box 范围以包含伸展的手部 ===
            # 左右各扩大 15%，上下各扩大 10%
            w_box = x2 - x1
            h_box = y2 - y1
            pad_w = int(w_box * 0.15)
            pad_h = int(h_box * 0.1)
            
            x1 = max(0, int(x1 - pad_w))
            y1 = max(0, int(y1 - pad_h))
            x2 = min(w, int(x2 + pad_w))
            y2 = min(h, int(y2 + pad_h))
            
            person_width = x2 - x1
            person_height = y2 - y1
            
            # 创建密集的网格方块，几乎铺满人物区域
            # 方块大小和间距固定，确保所有格子间距一致
            base_size = max(4, min(person_width, person_height) // 20)  # 基础大小（更小）
            spacing = base_size + 2  # 方块间距（固定）
            size = base_size  # 固定大小（不根据位置变化）
            
            # 计算网格数量（几乎铺满）
            grid_cols = max(3, person_width // spacing)
            grid_rows = max(3, person_height // spacing)
            
            # 在人物bbox区域内创建网格
            for row in range(grid_rows):
                for col in range(grid_cols):
                    # 计算方块位置（在bbox内，使用固定间距）
                    block_x = x1 + col * spacing + spacing // 2
                    block_y = y1 + row * spacing + spacing // 2
                    
                    # 确保在bbox内
                    if block_x < x1 or block_x >= x2 or block_y < y1 or block_y >= y2:
                        continue
                    
                    # 确保坐标在图像范围内
                    block_x = max(size, min(block_x, w - size))
                    block_y = max(size, min(block_y, h - size))
                    
                    # 计算方块区域
                    block_x1 = block_x - size // 2
                    block_y1 = block_y - size // 2
                    block_x2 = block_x + size // 2
                    block_y2 = block_y + size // 2
                    
                    # 检查方块中心位置是在剪影内还是背景上
                    # 采样方块中心及四个角的mask值
                    sample_points = [
                        (block_x, block_y),  # 中心
                        (block_x1, block_y1),  # 左上
                        (block_x2, block_y1),  # 右上
                        (block_x1, block_y2),  # 左下
                        (block_x2, block_y2),  # 右下
                    ]
                    
                    mask_values = []
                    for px, py in sample_points:
                        px = max(0, min(int(px), w-1))
                        py = max(0, min(int(py), h-1))
                        mask_values.append(person_mask[py, px])
                    
                    # 如果多数点在剪影内（mask > 128），使用白色（如果是目标）；否则使用黑色
                    in_silhouette = sum(1 for v in mask_values if v > 128) >= len(mask_values) // 2
                    
                    if in_silhouette:
                        block_color = (255, 255, 255) if is_target else (0, 0, 0)
                    else:
                        block_color = (0, 0, 0)
                    
                    # 绘制方块（填充，无描边）
                    cv2.rectangle(effect_frame, (block_x1, block_y1), (block_x2, block_y2), 
                                 block_color, -1)
    
    def draw_scan_line(self, effect_frame, results):
        """
        在每个人物的bbox内绘制从上到下的扫描线效果（带模糊拖影）
        使用混合模式单独叠加，不影响下面的内容
        """
        h, w = effect_frame.shape[:2]
        
        # 创建单独的扫描线图层（全透明）
        scan_layer = np.zeros((h, w, 3), dtype=np.uint8)
        
        for r in results:
            if 'bbox' not in r:
                continue
            
            x1, y1, x2, y2 = r['bbox']
            person_id = r.get('person_id', 0)
            
            # 确保bbox坐标在图像范围内
            x1 = max(0, int(x1))
            y1 = max(0, int(y1))
            x2 = min(w, int(x2))
            y2 = min(h, int(y2))
            
            # 为每个人物维护独立的扫描线位置和残影历史
            if person_id not in self.scan_line_positions:
                self.scan_line_positions[person_id] = y1  # 从bbox顶部开始
                self.scan_line_trails[person_id] = []  # 初始化残影列表
            
            # 更新扫描线位置（在bbox内）
            self.scan_line_positions[person_id] += self.scan_line_speed
            
            # 如果扫描线到达bbox底部，重置到bbox顶部
            if self.scan_line_positions[person_id] >= y2:
                self.scan_line_positions[person_id] = y1
                # 重置时清空残影
                self.scan_line_trails[person_id] = []
            
            # 添加当前位置到残影历史
            scan_y = int(self.scan_line_positions[person_id])
            if y1 <= scan_y < y2:  # 确保在bbox内
                self.scan_line_trails[person_id].append({
                    'y': scan_y,
                    'x1': x1,
                    'x2': x2
                })
                
                # 限制残影历史长度
                if len(self.scan_line_trails[person_id]) > self.scan_line_trail_frames:
                    self.scan_line_trails[person_id].pop(0)
            
            # 创建临时图像用于绘制残影（只在bbox区域内）
            bbox_width = x2 - x1
            bbox_height = y2 - y1
            if bbox_width > 0 and bbox_height > 0:
                # 创建临时图像（只包含bbox区域）
                trail_mask = np.zeros((bbox_height, bbox_width, 3), dtype=np.uint8)
                
                # 在临时图像上绘制所有残影线（白色，逐渐变淡）
                trail_list = self.scan_line_trails[person_id]
                for i, trail in enumerate(trail_list):
                    # 计算透明度：越新的残影越亮
                    alpha = (i + 1) / len(trail_list) if trail_list else 1.0
                    # 计算颜色强度（白色）
                    color_intensity = int(255 * alpha)
                    trail_color = (color_intensity, color_intensity, color_intensity)  # BGR格式，白色
                    
                    # 计算在临时图像中的相对位置
                    trail_y_rel = trail['y'] - y1
                    trail_x1_rel = trail['x1'] - x1
                    trail_x2_rel = trail['x2'] - x1
                    
                    # 确保在bbox范围内
                    if 0 <= trail_y_rel < bbox_height:
                        trail_x1_rel = max(0, min(trail_x1_rel, bbox_width - 1))
                        trail_x2_rel = max(0, min(trail_x2_rel, bbox_width - 1))
                        cv2.line(trail_mask, (trail_x1_rel, trail_y_rel), 
                                (trail_x2_rel, trail_y_rel), trail_color, self.scan_line_thickness)
                
                # 对残影应用高斯模糊（创建拖影效果）
                if len(trail_list) > 0:
                    blurred_trail = cv2.GaussianBlur(trail_mask, 
                                                     (self.scan_line_blur_radius * 2 + 1, 
                                                      self.scan_line_blur_radius * 2 + 1), 0)
                    
                    # 将模糊后的残影绘制到扫描线图层（不混合，直接绘制）
                    scan_layer[y1:y2, x1:x2] = np.maximum(scan_layer[y1:y2, x1:x2], blurred_trail)
            
            # 绘制当前扫描线到扫描线图层（白色，不模糊，清晰）
            scan_y = int(self.scan_line_positions[person_id])
            if y1 <= scan_y < y2:  # 确保在bbox内
                cv2.line(scan_layer, (x1, scan_y), (x2, scan_y), 
                        self.scan_line_color, self.scan_line_thickness)
        
        # 使用 Screen 混合模式叠加扫描线图层（只增亮，不影响黑色）
        # Screen 模式：result = 1 - (1 - base) * (1 - overlay)
        # 对于白色扫描线，会增亮下面的内容，但黑色保持不变
        scan_layer_float = scan_layer.astype(np.float32) / 255.0
        effect_frame_float = effect_frame.astype(np.float32) / 255.0
        
        # Screen 混合模式
        blended = 1.0 - (1.0 - effect_frame_float) * (1.0 - scan_layer_float)
        blended = (blended * 255.0).astype(np.uint8)
        
        # 将混合后的结果写回效果帧
        effect_frame[:] = blended
    
    def draw_info_on_effect_frame(self, effect_frame, person_mask, results):
        """
        在特效帧上绘制识别信息（边界框、人脸框、关节点、骨架、文本），根据背景自动调整颜色
        """
        font = cv2.FONT_HERSHEY_SIMPLEX
        h, w = effect_frame.shape[:2]
        
        for idx, r in enumerate(results):
            if 'bbox' not in r:
                continue
                
            x1, y1, x2, y2 = r['bbox']
            
            # === 同步 draw_data_blocks 的扩大逻辑，确保框能包住格子 ===
            w_box = x2 - x1
            h_box = y2 - y1
            pad_w = int(w_box * 0.15)
            pad_h = int(h_box * 0.1)
            
            x1 = max(0, int(x1 - pad_w))
            y1 = max(0, int(y1 - pad_h))
            x2 = min(w, int(x2 + pad_w))
            y2 = min(h, int(y2 + pad_h))
            # ========================================================
            
            # 1. 绘制人体边界框（自适应颜色）
            # 采样边界框四个角的颜色，取多数
            corners = [
                (x1, y1), (x2, y1), (x1, y2), (x2, y2)
            ]
            colors = [self.get_text_color_for_position(person_mask, x, y) for x, y in corners]
            # 统计白色和黑色的数量
            white_count = sum(1 for c in colors if c == (255, 255, 255))
            bbox_color = (255, 255, 255) if white_count >= 2 else (0, 0, 0)
            cv2.rectangle(effect_frame, (x1, y1), (x2, y2), bbox_color, 1)
            
            # 2. 绘制文本信息（从上往下排列：Person -> Age -> Emotion -> Build -> Clothes）
            y_offset = y1 - 10
            
            # Clothing（最后绘制，显示在最下方）
            if r.get('clothing'):
                clothing = r['clothing']
                clothing_type = clothing.get('type', {})
                
                if clothing_type:
                    upper_type = clothing_type.get('upper', 'Top')
                    lower_type = clothing_type.get('lower', 'Bottom')
                    
                    # Lower clothing（格式：Clothes: Pants, Black）- 先绘制，显示在下
                    if lower_type:
                        lower_text = f"Clothes: {lower_type}"
                        if clothing.get('lower_color'):
                            lower_text += f", {clothing['lower_color']}"
                        text_color = (0, 0, 0)  # 改回黑色
                        cv2.putText(effect_frame, lower_text, (x1, y_offset),
                                   font, 1.2, text_color, 2)
                        y_offset -= 35
                    
                    # Upper clothing（格式：Clothes: T-Shirt, Gray）- 后绘制，显示在上
                    upper_text = f"Clothes: {upper_type}"
                    if clothing.get('upper_color'):
                        upper_text += f", {clothing['upper_color']}"
                    text_color = (0, 0, 0)  # 改回黑色
                    cv2.putText(effect_frame, upper_text, (x1, y_offset),
                               font, 1.2, text_color, 2)
                    y_offset -= 35
                else:
                    # Fallback to simple color display（格式：Clothes: Top, Color）
                    if clothing.get('lower_color'):
                        lower_text = f"Clothes: Bottom, {clothing['lower_color']}"
                        text_color = (0, 0, 0)  # 改回黑色
                        cv2.putText(effect_frame, lower_text, (x1, y_offset),
                                   font, 1.2, text_color, 2)
                        y_offset -= 35
                    
                    if clothing.get('upper_color'):
                        upper_text = f"Clothes: Top, {clothing['upper_color']}"
                        text_color = (0, 0, 0)  # 改回黑色
                        cv2.putText(effect_frame, upper_text, (x1, y_offset),
                                   font, 1.2, text_color, 2)
                        y_offset -= 35
            
            # Body type（特效模式下使用黑色）
            if r.get('body_type'):
                body_type = r['body_type']
                build_text = f"Build: {body_type.get('build', 'Unknown')}"
                # 添加置信度（基于关键点可见度）
                if r.get('keypoints') is not None:
                    keypoints = r['keypoints']
                    visible_kpts = sum(1 for kpt in keypoints if kpt[2] > 0.3)
                    body_conf = visible_kpts / 17.0
                    build_text += f" ({body_conf*100:.0f}%)"
                text_color = (0, 0, 0)  # 改回黑色
                cv2.putText(effect_frame, build_text, (x1, y_offset),
                           font, 1.2, text_color, 2)
                y_offset -= 35
            
            # Emotion（特效模式下使用黑色）
            emotion = r.get('emotion')
            emotion_display = self.emotion_text.get(emotion, 'Neutral') if emotion else 'Analyzing...'
            emotion_text = f"Emotion: {emotion_display}"
            if emotion and r.get('emotion_conf'):
                emotion_text += f" ({r['emotion_conf']*100:.0f}%)"
            text_color = (0, 0, 0)  # 改回黑色
            cv2.putText(effect_frame, emotion_text, (x1, y_offset),
                       font, 1.2, text_color, 2)
            y_offset -= 35
            
            # Age（特效模式下使用黑色）
            if r.get('face'):
                face = r['face']
                display_age = face.get('smoothed_age', face.get('age', 0))
                age_text = f"Age: {display_age}y"
                text_color = (0, 0, 0)  # 改回黑色
                cv2.putText(effect_frame, age_text, (x1, y_offset),
                           font, 1.2, text_color, 2)
                y_offset -= 35
            
            # Person ID（最后绘制，显示在最上方）
            person_conf = r.get('person_conf', 0.0)
            person_text = f"Person {r.get('person_id', idx+1)} ({person_conf*100:.0f}%)"
            text_color = (0, 0, 0)  # 改回黑色
            cv2.putText(effect_frame, person_text, (x1, y_offset),
                       font, 1.2, text_color, 2)
            
            # 3. 绘制人脸边界框（红色，最后绘制，显示在最上层）
            # 已根据用户要求移除
            # if r.get('face'):
            #     face = r['face']
            #     if 'bbox' in face:
            #         fx1, fy1, fx2, fy2 = face['bbox']
            #         cv2.rectangle(effect_frame, (fx1, fy1), (fx2, fy2), (0, 0, 255), 1)  # 红色
            
            # 4. 绘制关节点和骨架（红色，最后绘制，显示在最上层）
            # 已根据用户要求移除
            # if 'keypoints' in r and r['keypoints'] is not None:
            #     self.draw_keypoints_skeleton_red(effect_frame, r['keypoints'])
    
    def create_person_silhouette_from_keypoints(self, keypoints, bbox, img_h, img_w):
        """
        从关键点创建精确的人体轮廓
        使用关键点连接和形态学操作来创建更准确的人形
        """
        mask = np.zeros((img_h, img_w), dtype=np.uint8)
        
        if keypoints is None or len(keypoints) < 17:
            # 如果没有关键点，使用bbox创建椭圆
            if bbox:
                x1, y1, x2, y2 = bbox
                center_x = int((x1 + x2) / 2)
                center_y = int((y1 + y2) / 2)
                width = int(x2 - x1)
                height = int(y2 - y1)
                cv2.ellipse(mask, (center_x, center_y), (width//2, height//2), 0, 0, 360, 255, -1)
            return mask
        
        # 提取可见关键点及其索引
        visible_kpts = {}
        for idx, kpt in enumerate(keypoints):
            if len(kpt) >= 3 and kpt[2] > 0.3:  # 置信度 > 0.3
                x, y = int(kpt[0]), int(kpt[1])
                x = max(0, min(x, img_w-1))
                y = max(0, min(y, img_h-1))
                visible_kpts[idx] = (x, y)
        
        if len(visible_kpts) < 5:
            # 关键点太少，使用bbox
            if bbox:
                x1, y1, x2, y2 = bbox
                center_x = int((x1 + x2) / 2)
                center_y = int((y1 + y2) / 2)
                width = int(x2 - x1)
                height = int(y2 - y1)
                cv2.ellipse(mask, (center_x, center_y), (width//2, height//2), 0, 0, 360, 255, -1)
            return mask
        
        # 方法1: 使用关键点连接创建轮廓
        # 定义身体部位的关键点组（用于创建更精确的轮廓）
        body_parts = {
            'head': [0, 1, 2, 3, 4],  # 头部
            'torso': [5, 6, 11, 12],  # 躯干
            'left_arm': [5, 7, 9],  # 左臂
            'right_arm': [6, 8, 10],  # 右臂
            'left_leg': [11, 13, 15],  # 左腿
            'right_leg': [12, 14, 16],  # 右腿
        }
        
        # 为每个身体部位创建轮廓
        for part_name, part_indices in body_parts.items():
            part_points = []
            for idx in part_indices:
                if idx in visible_kpts:
                    part_points.append(visible_kpts[idx])
            
            if len(part_points) >= 2:
                part_points = np.array(part_points, dtype=np.int32)
                
                # 对于头部，使用椭圆
                if part_name == 'head' and len(part_points) >= 3:
                    # 计算头部边界
                    min_x, min_y = part_points.min(axis=0)
                    max_x, max_y = part_points.max(axis=0)
                    center_x = (min_x + max_x) // 2
                    center_y = (min_y + max_y) // 2
                    width = max(20, max_x - min_x)
                    height = max(20, max_y - min_y)
                    cv2.ellipse(mask, (center_x, center_y), (width//2, height//2), 0, 0, 360, 255, -1)
                # 对于躯干，使用凸包
                elif part_name == 'torso' and len(part_points) >= 3:
                    hull = cv2.convexHull(part_points)
                    cv2.fillPoly(mask, [hull], 255)
                # 对于四肢，使用连接线加宽度
                elif len(part_points) >= 2:
                    # 绘制连接线，并加粗
                    for i in range(len(part_points) - 1):
                        pt1 = tuple(part_points[i])
                        pt2 = tuple(part_points[i + 1])
                        # 根据身体部位设置不同的线宽
                        if part_name in ['left_arm', 'right_arm']:
                            thickness = 25
                        elif part_name in ['left_leg', 'right_leg']:
                            thickness = 30
                        else:
                            thickness = 20
                        cv2.line(mask, pt1, pt2, 255, thickness)
                    # 在关键点位置绘制圆
                    for pt in part_points:
                        cv2.circle(mask, tuple(pt), thickness//2, 255, -1)
        
        # 方法2: 使用所有关键点的凸包作为基础，然后细化
        all_points = np.array(list(visible_kpts.values()), dtype=np.int32)
        if len(all_points) >= 3:
            hull = cv2.convexHull(all_points)
            # 创建临时mask用于凸包
            temp_mask = np.zeros((img_h, img_w), dtype=np.uint8)
            cv2.fillPoly(temp_mask, [hull], 255)
            
            # 将凸包与身体部位mask合并
            mask = cv2.bitwise_or(mask, temp_mask)
        
        # 方法3: 使用形态学操作平滑和填充轮廓
        # 先膨胀再腐蚀，填充小洞
        kernel = np.ones((5, 5), np.uint8)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel, iterations=2)
        # 轻微腐蚀以平滑边缘
        mask = cv2.erode(mask, kernel, iterations=1)
        mask = cv2.dilate(mask, kernel, iterations=1)
        
        return mask
    
    # 深度估计函数已注释
    # def estimate_depth(self, frame):
    #     """
    #     使用MiDaS估计场景深度
    #     返回归一化的深度图 (0-255)
    #     """
    #     if not self.depth_enabled:
    #         return None
    #     
    #     try:
    #         # 每3帧更新一次深度图以提高性能
    #         self.depth_cache_counter += 1
    #         if self.depth_cache is not None and self.depth_cache_counter % 3 != 0:
    #             return self.depth_cache
    #         
    #         # 准备输入
    #         img_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    #         input_batch = self.midas_transform(img_rgb).to(self.device)
    #         
    #         # 推理
    #         with torch.no_grad():
    #             prediction = self.midas(input_batch)
    #             
    #             # 调整到原始分辨率
    #             prediction = F.interpolate(
    #                 prediction.unsqueeze(1),
    #                 size=frame.shape[:2],
    #                 mode="bicubic",
    #                 align_corners=False,
    #             ).squeeze()
    #         
    #         # 转换为numpy并归一化到0-255
    #         depth_map = prediction.cpu().numpy()
    #         
    #         # 归一化 (近处高值，远处低值)
    #         depth_min = depth_map.min()
    #         depth_max = depth_map.max()
    #         if depth_max > depth_min:
    #             depth_normalized = (depth_map - depth_min) / (depth_max - depth_min)
    #             depth_normalized = (depth_normalized * 255).astype(np.uint8)
    #         else:
    #             depth_normalized = np.zeros_like(depth_map, dtype=np.uint8)
    #         
    #         # 反转深度值（让近的地方更亮）
    #         depth_normalized = 255 - depth_normalized
    #         
    #         # 缓存深度图
    #         self.depth_cache = depth_normalized
    #         
    #         return depth_normalized
    #         
    #     except Exception as e:
    #         print(f"Depth estimation error: {e}")
    #         return None
    
    def get_segmentation_mask(self, frame, conf_threshold=0.75):
        """
        使用YOLOv8-Seg获取精确的人体分割mask
        Args:
            frame: 输入图像
            conf_threshold: 置信度阈值，只有高于此值的才会被分割 (默认 0.75)
        """
        if not self.segmentation_enabled:
            return None
        
        try:
            # 使用分割模型，直接传入置信度阈值进行过滤
            seg_results = self.yolo_seg_model(frame, verbose=False, conf=conf_threshold)
            
            if seg_results and len(seg_results) > 0:
                seg_result = seg_results[0]
                
                # 检查是否有分割mask
                if seg_result.masks is not None and len(seg_result.masks.data) > 0:
                    h, w = frame.shape[:2]
                    combined_mask = np.zeros((h, w), dtype=np.uint8)
                    
                    # 遍历所有检测到的对象
                    for i, (box, mask_data) in enumerate(zip(seg_result.boxes, seg_result.masks.data)):
                        # 只处理person类别 (class_id = 0 in COCO)
                        class_id = int(box.cls.cpu().numpy()[0])
                        if class_id == 0:  # person
                            # 获取mask并调整到原始图像大小
                            mask = mask_data.cpu().numpy()
                            mask_resized = cv2.resize(mask, (w, h), interpolation=cv2.INTER_LINEAR)
                            
                            # 转换为二值mask (0-255)
                            mask_binary = (mask_resized > 0.5).astype(np.uint8) * 255
                            
                            # 合并到总mask
                            combined_mask = cv2.bitwise_or(combined_mask, mask_binary)
                    
                    return combined_mask
        except Exception as e:
            print(f"Segmentation error: {e}")
        
        return None
    
    def create_ascii_effect(self, frame, person_mask, results):
        """
        创建ASCII艺术效果：使用0和1字符显示人物轮廓
        背景用复杂符号填满（灰色）
        """
        h, w = frame.shape[:2]
        
        # 创建黑色背景
        ascii_frame = np.zeros((h, w, 3), dtype=np.uint8)
        
        # 遍历网格，绘制字符
        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = self.ascii_grid_size / 30.0  # 根据网格大小调整字体
        font_thickness = 1
        
        # 背景字符集（复杂符号）
        background_chars = ['.', ':', '-', '=', '+', '*', '#', '%', '@', '~', '^', '&']
        # 灰色 #666666 = RGB(102, 102, 102)
        background_color = (102, 102, 102)  # BGR格式
        
        for y in range(0, h, self.ascii_grid_size):
            for x in range(0, w, self.ascii_grid_size):
                # 检查当前位置是否在人物mask内
                if x < w and y < h:
                    mask_value = person_mask[y, x]
                    
                    # 如果在人物区域内（mask > 128）
                    if mask_value > 128:
                        # 获取该位置的亮度
                        pixel = frame[y, x]
                        brightness = (int(pixel[0]) + int(pixel[1]) + int(pixel[2])) / 3
                        
                        # 只有当亮度超过阈值时才绘制字符
                        if brightness > self.ascii_threshold:
                            # 随机选择0或1
                            char = random.choice(self.ascii_chars)
                            
                            # 绘制白色字符（人物）
                            cv2.putText(ascii_frame, char, (x, y + self.ascii_grid_size),
                                       font, font_scale, (255, 255, 255), font_thickness)
                    else:
                        # 背景区域：绘制灰色复杂符号
                        char = random.choice(background_chars)
                        cv2.putText(ascii_frame, char, (x, y + self.ascii_grid_size),
                                   font, font_scale, background_color, font_thickness)
        
        # 不绘制任何标注信息，保持纯粹的ASCII艺术效果
        
        return ascii_frame
    
    def draw_info_on_ascii_frame(self, ascii_frame, results):
        """
        在ASCII帧上绘制识别信息（简化版，只显示基本信息）
        """
        font = cv2.FONT_HERSHEY_SIMPLEX
        
        for idx, r in enumerate(results):
            if 'bbox' not in r:
                continue
                
            x1, y1, x2, y2 = r['bbox']
            
            # 绘制边界框（绿色）
            cv2.rectangle(ascii_frame, (x1, y1), (x2, y2), (0, 255, 0), 1)
            
            # 绘制关键信息
            y_offset = y1 - 10
            
            # Age
            if r.get('face'):
                face = r['face']
                display_age = face.get('smoothed_age', face.get('age', 0))
                cv2.putText(ascii_frame, f"Age: {display_age}y", (x1, y_offset),
                           font, 0.4, (0, 255, 0), 1)
                y_offset -= 12
            
            # Person ID
            person_conf = r.get('person_conf', 0.0)
            cv2.putText(ascii_frame, f"Person {r.get('person_id', idx+1)} ({person_conf*100:.0f}%)", 
                       (x1, y_offset), font, 0.4, (0, 255, 0), 1)
    
    def apply_visual_effects(self, frame, results, person_mask=None, target_person_idx=None):
        """
        应用视觉特效：黑色剪影 + 真实背景 + 数据方块 或 ASCII艺术
        """
        if not self.enable_effects:
            return frame
        
        # 1. 过滤结果 (只保留高置信度)
        filtered_results = [r for r in results if r.get('person_conf', 0) > 0.75]
        
        # 2. 确定追踪目标对象
        target_result = None
        if target_person_idx is not None and 0 <= target_person_idx < len(results):
            target_result = results[target_person_idx]
        
        h, w = frame.shape[:2]
        
        # 使用真实摄像头背景
        effect_frame = frame.copy()
        
        # 3. 获取 Mask (所有人)
        if person_mask is None:
            person_mask = self.get_segmentation_mask(frame, conf_threshold=0.75)
        
        if person_mask is None:
            person_mask = np.zeros((h, w), dtype=np.uint8)
            for r in filtered_results:
                bbox = r.get('bbox')
                keypoints = r.get('keypoints')
                person_silhouette = self.create_person_silhouette_from_keypoints(
                    keypoints, bbox, h, w
                )
                person_mask = cv2.bitwise_or(person_mask, person_silhouette)
        
        # 4. 渲染
        if self.effect_mode == 'ascii':
            effect_frame = self.create_ascii_effect(frame, person_mask, filtered_results)
            return effect_frame
        else:
            # 默认剪影模式
            original_mask = person_mask.copy()
            
            if self.feather_radius > 0:
                person_mask = cv2.GaussianBlur(person_mask, 
                                             (self.feather_radius * 2 + 1, self.feather_radius * 2 + 1),
                                             0)
            
            # 绘制数据方块 (传入 target_result 以区分颜色)
            self.draw_data_blocks(effect_frame, original_mask, filtered_results, frame, target_result=target_result)
            
            # 绘制识别信息
            self.draw_info_on_effect_frame(effect_frame, original_mask, filtered_results)
            
            return effect_frame
        
        # 根据特效模式选择不同的渲染方法
        if self.effect_mode == 'ascii':
            # ASCII艺术模式 (使用过滤后的 results)
            effect_frame = self.create_ascii_effect(frame, person_mask, filtered_results)
            return effect_frame
        else:
            # 默认剪影模式
            # 保存原始mask用于文本颜色判断（在羽化之前）
            original_mask = person_mask.copy()
            
            # 应用羽化效果（边缘模糊）
            if self.feather_radius > 0:
                person_mask = cv2.GaussianBlur(person_mask, 
                                             (self.feather_radius * 2 + 1, self.feather_radius * 2 + 1),
                                             0)
            
            # 不绘制纯黑色剪影，只绘制黑色格子
            # effect_frame 保持真实背景，不做任何混合
            
            # 添加残影效果（在绘制完所有内容后应用，避免影响格子颜色）
            # 注意：残影效果会在最后应用，所以不会影响格子的白色
            
            # 在人物剪影上叠加数据方块（马赛克格子效果）
            # 注意：传入 filtered_results 确保只绘制高置信度人物的格子
            self.draw_data_blocks(effect_frame, original_mask, filtered_results, frame)
            
            # 在特效帧上绘制识别信息（使用黑色文本，在格子之后绘制，确保可见）
            self.draw_info_on_effect_frame(effect_frame, original_mask, filtered_results)
            
            # 绘制扫描线效果（在每个人物的bbox内）
            # self.draw_scan_line(effect_frame, filtered_results)  # 已注释
            
            return effect_frame
    
    def process_frame(self, frame):
        """Complete analysis of the frame"""
        self.frame_counter += 1
        
        # Detect persons
        persons = self.detect_persons(frame)
        
        # Analyze faces
        faces = self.analyze_faces(frame)
        
        should_analyze_body = (self.frame_counter % self.process_every_n_frames == 0)
        should_analyze_emotion = (self.frame_counter % self.emotion_every_n_frames == 0)
        
        results = []
        
        for idx, person in enumerate(persons):
            x1, y1, x2, y2 = person['bbox']
            keypoints = person['keypoints']
            person_roi = frame[y1:y2, x1:x2].copy()
            
            person_id = f"{x1//50}_{y1//50}"
            
            # Find matching face
            matching_face = None
            for face in faces:
                if self.match_face_to_person(person['bbox'], face['bbox']):
                    matching_face = face
                    # Smooth age to reduce jumping
                    raw_age = face['age']
                    smoothed_age = self.smooth_age(person_id, raw_age)
                    face['smoothed_age'] = smoothed_age
                    break
            
            # 确保person_id在缓存中（如果不存在，立即初始化并分析一次，避免闪烁）
            is_new_person = person_id not in self.cached_results
            if is_new_person:
                self.cached_results[person_id] = {
                    'body_type': None,
                    'upper_color': None,
                    'lower_color': None,
                    'clothing_type': None,
                    'emotion': None,
                    'emotion_conf': None,
                    'frame': self.frame_counter
                }
                # 新检测到的人物，立即分析一次，避免闪烁
                should_analyze_body_local = True
                should_analyze_emotion_local = True
            else:
                should_analyze_body_local = should_analyze_body
                should_analyze_emotion_local = should_analyze_emotion
            
            # Person 检测置信度（来自YOLO）
            person_conf = person.get('confidence', 0.0)
            
            # 从缓存读取
            cached = self.cached_results[person_id]
            body_type = cached.get('body_type')
            upper_color = cached.get('upper_color')
            upper_color_conf = cached.get('upper_color_conf', 0.0)
            lower_color = cached.get('lower_color')
            lower_color_conf = cached.get('lower_color_conf', 0.0)
            clothing_type = cached.get('clothing_type')
            emotion = cached.get('emotion')
            emotion_conf = cached.get('emotion_conf')
            
            # Analyze face attributes (independent of body analysis)
            if matching_face:
                fx1, fy1, fx2, fy2 = matching_face['bbox']
                
                # Add padding for better emotion detection
                h, w = frame.shape[:2]
                pad_x = int((fx2 - fx1) * 0.2)
                pad_y = int((fy2 - fy1) * 0.2)
                
                fx1_pad = max(0, fx1 - pad_x)
                fy1_pad = max(0, fy1 - pad_y)
                fx2_pad = min(w, fx2 + pad_x)
                fy2_pad = min(h, fy2 + pad_y)
                
                # [关键修改 1] 必须使用 .copy()，否则 TensorFlow 可能会报错
                face_region = frame[fy1_pad:fy2_pad, fx1_pad:fx2_pad].copy()
                
                # Emotion detection - Using HSEmotion (EfficientNet)
                if HSEMOTION_AVAILABLE and self.emotion_enabled and face_region.size > 0 and self.frame_counter % 5 == 0:
                    try:
                        # predict_emotions returns (emotion_label, scores_list)
                        # emotion_label is like 'Happiness', 'Neutral', etc.
                        emotion, scores = self.emotion_detector.predict_emotions(face_region, logits=False)
                        
                        # Find max score for confidence
                        confidence = max(scores)
                        
                        # Normalize to lowercase for consistency
                        emotion_lower = emotion.lower()
                        
                        # Apply smoothing
                        smoothed_emotion = self.smooth_emotion(person_id, emotion_lower)
                        
                        # Update cache
                        self.cached_results[person_id]['emotion'] = smoothed_emotion
                        self.cached_results[person_id]['emotion_conf'] = confidence
                            
                    except Exception as e:
                        print(f"!!! HSEmotion ERROR (Person {idx+1}): {e}")
                        pass
            
            # Analyze body attributes
            if should_analyze_body_local:
                body_type = self.analyze_body_type(keypoints, person['bbox'])
                
                # Generate silhouette mask for accurate color extraction (Remove background)
                # This ensures we only analyze pixels belonging to the person
                full_mask = self.create_person_silhouette_from_keypoints(
                    keypoints, person['bbox'], frame.shape[0], frame.shape[1]
                )
                
                # Crop mask to person ROI
                person_mask_roi = full_mask[y1:y2, x1:x2]
                
                h = person_roi.shape[0]
                mid = h // 2
                upper_roi = person_roi[:mid, :]
                lower_roi = person_roi[mid:, :]
                
                # Split mask for upper/lower
                upper_mask = None
                lower_mask = None
                
                if person_mask_roi.shape[:2] == person_roi.shape[:2]:
                    upper_mask = person_mask_roi[:mid, :]
                    lower_mask = person_mask_roi[mid:, :]
                
                upper_color, upper_color_conf = self.get_color(upper_roi, upper_mask)
                lower_color, lower_color_conf = self.get_color(lower_roi, lower_mask)
                
                # Upper color filtering (Confidence threshold)
                if upper_color and upper_color_conf < 0.6:
                    upper_color = None
                
                # Lower color filtering (Confidence threshold)
                if lower_color and lower_color_conf < 0.6:
                    lower_color = None
                
                # Classify clothing type
                clothing_type = self.classify_clothing_type(person_roi, keypoints, upper_roi, lower_roi)
                
                # Update body cache
                self.cached_results[person_id]['body_type'] = body_type
                self.cached_results[person_id]['upper_color'] = upper_color
                self.cached_results[person_id]['upper_color_conf'] = upper_color_conf
                self.cached_results[person_id]['lower_color'] = lower_color
                self.cached_results[person_id]['lower_color_conf'] = lower_color_conf
                self.cached_results[person_id]['clothing_type'] = clothing_type
                self.cached_results[person_id]['frame'] = self.frame_counter
            
            # ========== DRAW VISUALIZATION ==========
            # 绘制代码已移除，统一在 apply_visual_effects 中绘制
            
            result_data = {
                'person_id': idx + 1,
                'person_conf': person_conf,  # 添加Person置信度
                'bbox': person['bbox'],
                'keypoints': keypoints,
                'body_type': body_type,
                'face': matching_face,
                'emotion': emotion,
                'emotion_conf': emotion_conf,
                'clothing': {
                    'type': clothing_type,
                    'upper_color': upper_color,
                    'upper_color_conf': upper_color_conf,
                    'lower_color': lower_color,
                    'lower_color_conf': lower_color_conf
                }
            }
            
            # Generate natural language description
            description = self.generate_person_description(result_data)
            result_data['description'] = description
            
            results.append(result_data)
        
        # Clean cache
        if self.frame_counter % 30 == 0:
            old_keys = [k for k, v in self.cached_results.items() 
                       if self.frame_counter - v.get('frame', 0) > 30]
            for k in old_keys:
                del self.cached_results[k]
                # Also clean age history
                if k in self.age_history:
                    del self.age_history[k]
        
        # 应用视觉特效
        if self.enable_effects:
            frame = self.apply_visual_effects(frame, results)
        
        # 渲染示波器（右下角）
        if hasattr(self, 'oscilloscope') and self.oscilloscope is not None:
            # 延迟启动音频：只在用户启用且第一次检测到人后才启动
            if (self.oscilloscope_audio_enabled and 
                not self.oscilloscope_audio_started and 
                len(results) > 0):
                print("\n检测到人物，启动示波器音频...")
                if self.oscilloscope.enable_audio():
                    print("  ✓ 示波器音频已启动")
                    self.oscilloscope_audio_started = True
                else:
                    print("  ⚠ 音频启动失败，示波器将无音频反应")
                    # 不设为 None，仍然显示视觉效果
                    self.oscilloscope_audio_started = True  # 标记为已尝试，避免重复
            
            # 如果检测到人，使用第一个人的关键点数据
            if len(results) > 0 and 'keypoints' in results[0]:
                self.oscilloscope.update_person_data(
                    keypoints=results[0]['keypoints']
                )
            
            # 渲染示波器到帧上（会自动放在右下角）
            frame = self.oscilloscope.render(frame)
        
        return frame, results

# Note: This module is used by the multi-camera system (main_3cameras_single.py)
# The single-camera main() function has been removed as we only use the 3-camera version

