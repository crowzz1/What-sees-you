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
from person_analysis import CompletePersonFaceAnalyzer
from tracker import AdvancedTracker # 导入追踪器
from visual_style import GlitchArtEffect # 导入故障艺术效果

class GalleryView:
    """画廊式视图系统"""
    
    def __init__(self, camera_id=0, window_width=1440, window_height=1080):
        """
        Args:
            camera_id: 摄像头设备ID
            window_width: 窗口宽度 (默认 1440x1080, 4:3比例)
            window_height: 窗口高度
        """
        self.window_width = window_width
        self.window_height = window_height
        
        # 四宫格布局：不对称
        # 左侧占3/4，右侧占1/4
        self.left_width = int(window_width * 0.75)
        self.right_width = window_width - self.left_width
        
        # 高度调整：为了让左上角保持 16:9 比例 (1080x608)
        # 1080 / (16/9) = 607.5 -> 608
        self.top_height = int(self.left_width / (16/9))
        self.bottom_height = window_height - self.top_height
        
        # self.quad_height 已弃用，使用 top_height 和 bottom_height 替代
        
        print("=" * 60)
        print("画廊式视图系统 - 不对称布局 (16:9 优化)")
        print("=" * 60)
        print(f"窗口尺寸: {window_width}x{window_height}")
        print(f"上方区域高度: {self.top_height} (16:9 aspect for left)")
        print(f"下方区域高度: {self.bottom_height}")
        print(f"左上区域: {self.left_width}x{self.top_height}")
        print(f"右上区域: {self.right_width}x{self.top_height}")
        print("布局: 左上=黑色格子 | 右上=故障艺术 (Glitch Art)")
        print("      左下=人物信息 | 右下=手部追踪(Advanced Tracker)")
        print("=" * 60)
        
        # 打开摄像头
        print("\n打开摄像头...")
        self.cap = cv2.VideoCapture(camera_id)
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
        self.analyzer.face_enabled = False
        self.analyzer.emotion_enabled = False
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
        
        # 初始化 AdvancedTracker (用于后台追踪，不显示在UI上)
        print("\n初始化手部追踪器 (AdvancedTracker)...")
        try:
            # 不使用内部摄像头，只使用电机控制逻辑
            # 不加载模型，使用外部传入的结果
            self.tracker = AdvancedTracker(camera_id=None, use_internal_camera=False, load_model=False)
            print("✓ 追踪器已集成 (后台运行)")
        except Exception as e:
            print(f"✗ 追踪器初始化失败: {e}")
            self.tracker = None
        
        # FPS计算
        self.fps_start = time.time()
        self.fps_counter = 0
        self.current_fps = 0
        
        # 运行状态
        self.running = False
        
        # 文本显示设置
        self.text_scroll_offset = 0
        self.text_line_height = 35
        self.text_font = cv2.FONT_HERSHEY_SIMPLEX
        self.text_font_scale = 0.8
        self.text_thickness = 2
        
        print("\n" + "=" * 60)
        print("系统初始化完成!")
        print("=" * 60)
    
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
        # 创建黑色背景，使用左侧宽度和下方高度
        info_canvas = np.zeros((self.bottom_height, self.left_width, 3), dtype=np.uint8)
        
        if len(results) == 0:
            cv2.putText(info_canvas, "No person detected", 
                       (30, self.bottom_height // 2),
                       cv2.FONT_HERSHEY_SIMPLEX, 1.0, (150, 150, 150), 2)
            return info_canvas
        
        # 显示人物信息
        y_offset = 40
        line_height = 35
        
        # 动态调整字体大小和行高
        num_persons = len(results)
        # 可用高度减去顶部padding和每个人的间隔
        available_height = self.bottom_height - 80 - (num_persons * 20)
        # 每个人所需的基础高度（大约4行文本）
        required_height_per_person = 4 * 35
        
        scale_factor = 1.0
        if (num_persons * required_height_per_person) > available_height:
             scale_factor = available_height / (num_persons * required_height_per_person)
             # 限制最小缩放，避免字太小看不清
             scale_factor = max(0.5, scale_factor)
             
        font_scale_base = 1.0 * scale_factor
        font_scale_detail = 0.7 * scale_factor
        line_height = int(35 * scale_factor)
        
        for idx, r in enumerate(results):
            if y_offset > self.bottom_height - 20:
                break  # 空间不足
            
            # 人物标识
            person_id = r.get('person_id', idx + 1)
            cv2.putText(info_canvas, f"PERSON {person_id}", 
                       (30, y_offset),
                       cv2.FONT_HERSHEY_SIMPLEX, font_scale_base, (255, 255, 255), 2)
            y_offset += line_height + 5
            
            # ... (其他信息显示代码保持逻辑一致，但使用新的宽度限制) ...
            # 简化：为了代码简洁，我直接在这里更新后续的绘制逻辑
            
            # 年龄
            if r.get('face'):
                age = r['face'].get('smoothed_age', r['face'].get('age', 0))
                cv2.putText(info_canvas, f"Age: {age}y", 
                           (50, y_offset),
                           cv2.FONT_HERSHEY_SIMPLEX, font_scale_detail, (200, 200, 200), 1)
                y_offset += line_height
            
            # 情绪
            if r.get('emotion'):
                emotion = r['emotion'].capitalize()
                cv2.putText(info_canvas, f"Emotion: {emotion}", 
                           (50, y_offset),
                           cv2.FONT_HERSHEY_SIMPLEX, font_scale_detail, (200, 200, 200), 1)
                y_offset += line_height
            
            # 体型
            if r.get('body_type'):
                build = r['body_type'].get('build', '')
                if build:
                    cv2.putText(info_canvas, f"Build: {build}", 
                               (50, y_offset),
                               cv2.FONT_HERSHEY_SIMPLEX, font_scale_detail, (200, 200, 200), 1)
                    y_offset += line_height
            
            # 衣服
            if r.get('clothing'):
                clothing = r['clothing']
                upper_color = clothing.get('upper_color', '')
                if upper_color:
                    cv2.putText(info_canvas, f"Clothes: {upper_color}", 
                               (50, y_offset),
                               cv2.FONT_HERSHEY_SIMPLEX, font_scale_detail, (200, 200, 200), 1)
                    y_offset += line_height
            
            # 描述（截断显示）
            description = r.get('description', '')
            if description:
                # 使用新的宽度计算最大字符数
                max_width = self.left_width - 80
                # 估算：每个字符大约占 font_scale * 20 像素
                char_width_approx = max(10, int(font_scale_detail * 20))
                max_chars = max(20, max_width // char_width_approx)
                
                desc_short = description[:max_chars] + "..." if len(description) > max_chars else description
                
                cv2.putText(info_canvas, desc_short, 
                           (50, y_offset),
                           cv2.FONT_HERSHEY_SIMPLEX, font_scale_detail, (180, 180, 180), 1)
                y_offset += line_height
            
            y_offset += int(20 * scale_factor)  # 人物间隔
        
        return info_canvas

    def create_tracker_view(self, frame, results=None, precomputed_frame=None):
        """
        创建右下角追踪器视图
        使用 AdvancedTracker 处理当前帧
        """
        if precomputed_frame is not None:
            tracker_frame = precomputed_frame
        elif self.tracker:
            # 让追踪器处理这一帧（识别+控制电机+绘图）
            # 传入 external_results=results 避免重复推理，提升帧率
            tracker_frame = self.tracker.process_frame(frame, external_results=results)
        else:
             # 如果追踪器未初始化
            canvas = np.zeros((self.bottom_height, self.right_width, 3), dtype=np.uint8)
            cv2.putText(canvas, "TRACKER ERROR", 
                       (self.right_width//2 - 100, self.bottom_height//2),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
            return canvas
            
        # 调整大小以适应右下角区域 (使用右侧宽度，下方高度)
        return self.resize_to_fit(tracker_frame, self.right_width, self.bottom_height)

    def create_composite_view(self, silhouette_frame, glitch_frame, results, frame, precomputed_tracker_frame=None):
        """
        创建组合视图
        左上(3/4, 16:9)=黑色格子, 右上(1/4, 延伸)=故障艺术
        左下(3/4)=人物信息, 右下(1/4)=空(黑色) - 但后台运行追踪器
        """
        # 创建主画布
        canvas = np.zeros((self.window_height, self.window_width, 3), dtype=np.uint8)
        
        # 调整各区域大小
        silhouette_resized = self.resize_to_fit(silhouette_frame, self.left_width, self.top_height)
        glitch_resized = self.resize_to_fit(glitch_frame, self.right_width, self.top_height)
        
        # 生成其他区域
        info_area = self.create_info_quadrant(results)
        
        # 右下角：运行追踪器但不显示其画面
        # 如果 precomputed_tracker_frame 有值，create_tracker_view 会直接使用它
        _ = self.create_tracker_view(frame, results=results, precomputed_frame=precomputed_tracker_frame)
        
        # 放置四个区域
        # 左上角 - 黑色格子
        canvas[0:self.top_height, 0:self.left_width] = silhouette_resized
        
        # 右上角 - 故障艺术
        canvas[0:self.top_height, self.left_width:self.window_width] = glitch_resized
        
        # 左下角 - 人物信息
        canvas[self.top_height:self.window_height, 0:self.left_width] = info_area
        
        # 右下角 - 保持黑色背景 (不显示追踪器画面)
        # 已经是 zeros 初始化了，不需要额外操作
        
        # 绘制分隔线
        # 垂直线
        cv2.line(canvas, (self.left_width, 0), (self.left_width, self.window_height),
                (80, 80, 80), 2)
        # 水平线
        cv2.line(canvas, (0, self.top_height), (self.window_width, self.top_height),
                (80, 80, 80), 2)
        
        # 显示FPS（左上角）
        cv2.putText(canvas, f"FPS: {self.current_fps:.1f}", (20, 50),
                   self.text_font, 0.7, (0, 255, 0), 2)
        cv2.putText(canvas, f"Persons: {len(results)}", (20, 85),
                   self.text_font, 0.7, (0, 255, 0), 2)
        
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
        
        # 创建全屏窗口
        cv2.namedWindow('Gallery View', cv2.WINDOW_NORMAL)
        cv2.resizeWindow('Gallery View', self.window_width, self.window_height)
        
        try:
            while self.running:
                # 读取帧
                ret, frame = self.cap.read()
                if not ret:
                    print("✗ 无法读取帧")
                    break
                
                # 镜像翻转摄像头画面
                frame = cv2.flip(frame, 1)
                
                # 保存一份纯净的帧用于故障艺术效果（避免被 analyzer 的标注污染）
                clean_frame = frame.copy()
                
                # ===== 1. 人物分析 (用于左上、右上、左下) =====
                self.analyzer.enable_effects = False
                _, results = self.analyzer.process_frame(frame)
                
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
                
                # ===== 2. 运行追踪器 (获取当前追踪目标) =====
                # 将追踪器逻辑提前，以便我们可以利用 active_idx 来过滤左上角的显示
                tracker_active_idx = None
                tracker_frame = None
                
                if self.tracker:
                    # 让追踪器处理这一帧
                    tracker_frame = self.tracker.process_frame(frame, external_results=results)
                    # 获取当前追踪的人员索引
                    tracker_active_idx = self.tracker.active_target_index
                
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
                glitch_frame = self.glitch_effect.create_glitch_frame(clean_frame, results, target_person_idx=tracker_active_idx)
                
                # ===== 3. 创建组合视图 =====
                # 注意：tracker_frame 已经生成了，传给 create_composite_view 避免重复计算
                composite = self.create_composite_view(silhouette_frame, glitch_frame, results, frame, precomputed_tracker_frame=tracker_frame)
                
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
        self.running = False
        if self.cap:
            self.cap.release()
        
        # 关闭追踪器（这会让电机归位）
        if self.tracker:
            self.tracker.close()
            
        cv2.destroyAllWindows()
        print("✓ 系统已关闭")

if __name__ == "__main__":
    # 创建画廊视图
    gallery = GalleryView(
        camera_id=0,
        window_width=1440, # 4:3 比例
        window_height=1080
    )
    gallery.run()
