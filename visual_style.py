import cv2
import numpy as np
import random
import time
from ultralytics import YOLO

class GlitchArtEffect:
    def __init__(self, canvas_width=1920, canvas_height=1080):
        self.canvas_width = canvas_width
        self.canvas_height = canvas_height
        
        # 赛博朋克配色
        self.color_purple = (255, 0, 255)  # 紫色边框
        self.color_cyan = (255, 255, 0)    # 青色
        self.color_green = (0, 255, 0)     # 绿色
        self.color_red = (0, 0, 255)       # 红色
        
        # 噪点计数器（用于动画效果）
        self.frame_count = 0
        
        # 状态管理 (用于平滑动画)
        # 结构: {'label': {'x': float, 'y': float, 'size_scale': float, 'target_x': int, 'target_y': int, 'target_scale': float}}
        self.part_states = {}
        self.last_update_time = time.time()
        
    def update_part_state(self, label, default_x, default_y, dt):
        """
        更新部位的运动状态（平滑移动和缩放）
        """
        if label not in self.part_states:
            # 初始化状态
            self.part_states[label] = {
                'x': float(default_x),
                'y': float(default_y),
                'size_scale': 1.0,
                'target_x': default_x,
                'target_y': default_y,
                'target_scale': 1.0,
                'move_speed': random.uniform(20, 70),  # 再减速：20-70像素/秒
                'scale_speed': random.uniform(0.3, 0.8), 
                'wait_time': 0,
                'scale_wait_time': 0
            }
            
        state = self.part_states[label]
        
        # --- 1. 位置更新逻辑 ---
        dx = state['target_x'] - state['x']
        dy = state['target_y'] - state['y']
        dist = (dx**2 + dy**2)**0.5
        
        need_new_pos = False
        if dist < 20 or state['wait_time'] <= 0:
            need_new_pos = True
            
        if need_new_pos:
            # 随机选择全屏范围内的一个新目标位置
            # 允许方框部分出界，以获得更大的活动范围
            # 只要方框还有 1/3 在屏幕内就算有效
            
            # 恢复严格边界限制：绝不允许出界
            # 方框尺寸已减半 (最大约 125)
            max_obj_size = 130
            
            min_x = 0
            max_x = max(0, self.canvas_width - max_obj_size)
            
            min_y = 0
            max_y = max(0, self.canvas_height - max_obj_size)
            
            # === 垂直方向大幅度运动优化 ===
            # 既然水平窄，那就强制垂直方向跑得远
            # 尝试生成一个垂直距离足够远的目标
            min_vertical_dist = self.canvas_height * 0.4 # 至少跨越 40% 的高度
            
            # 尝试 5 次
            for _ in range(5):
                tx = random.randint(min_x, max_x)
                ty = random.randint(min_y, max_y)
                
                dy = abs(ty - state['y'])
                # 垂直距离够远 OR 水平距离够远 (兜底)
                if dy > min_vertical_dist: 
                    state['target_x'] = tx
                    state['target_y'] = ty
                    break
            else:
                # 兜底
                state['target_x'] = tx
                state['target_y'] = ty
                
            state['wait_time'] = random.uniform(4.0, 8.0) # 恢复：4-8秒停顿
        else:
            state['wait_time'] -= dt
            
        # 平滑移动
        lerp_speed_pos = 0.2  # 恢复：0.2 慢速漂浮
        lerp_factor_pos = 1.0 - pow(0.1, dt * lerp_speed_pos)
        
        new_x = state['x'] + dx * lerp_factor_pos
        new_y = state['y'] + dy * lerp_factor_pos
        
        # --- 边界反弹/限制 (防止出界) ---
        # 严格模式：只要碰到边界就反弹
        # 估算当前大小
        max_obj_size = 130
        
        if new_x < 0:
            new_x = 0
            state['target_x'] = random.randint(50, self.canvas_width - max_obj_size)
            
        elif new_x > self.canvas_width - max_obj_size:
            new_x = max(0, self.canvas_width - max_obj_size)
            state['target_x'] = random.randint(0, self.canvas_width - max_obj_size - 50)
            
        if new_y < 0:
            new_y = 0
            # 垂直触底反弹：一定要弹到下面去
            min_bounce_y = int(self.canvas_height * 0.5)
            state['target_y'] = random.randint(min_bounce_y, self.canvas_height - max_obj_size)
            
        elif new_y > self.canvas_height - max_obj_size:
            new_y = max(0, self.canvas_height - max_obj_size)
            # 垂直触顶反弹：一定要弹到上面去
            max_bounce_y = int(self.canvas_height * 0.5)
            state['target_y'] = random.randint(0, max_bounce_y)
            
        state['x'] = new_x
        state['y'] = new_y
        
        # --- 2. 缩放更新逻辑 (独立且更频繁) ---
        if state['scale_wait_time'] <= 0:
            # 随机大小目标 (0.6 - 1.0)
            # 脸部保持稳定
            if 'FACE' in label:
                state['target_scale'] = 1.0
            else:
                state['target_scale'] = random.uniform(0.6, 1.0) # 范围扩大到 60%
            
            # 缩放变化频率：1-2秒变一次，比移动快
            state['scale_wait_time'] = random.uniform(1.0, 2.5)
        else:
            state['scale_wait_time'] -= dt
            
        # 平滑缩放 (可以使用不同的速度)
        d_scale = state['target_scale'] - state['size_scale']
        # 缩放速度稍微快一点，让呼吸感更明显
        lerp_speed_scale = 1.5 
        lerp_factor_scale = 1.0 - pow(0.1, dt * lerp_speed_scale)
        state['size_scale'] += d_scale * lerp_factor_scale
                
        return int(state['x']), int(state['y']), state['size_scale']

    def _resolve_overlaps(self, parts):
        """
        解决重叠问题：已根据用户要求禁用
        允许自由重叠，以获得更自然的穿梭效果
        """
        pass
        # 原有逻辑已移除，让方框自由穿行

    def extract_roi(self, frame, center_x, center_y, size, label="", zoom=1.0, base_size_for_crop=None):
        """
        提取并风格化ROI（感兴趣区域）
        
        Args:
            frame: 原始图像
            center_x, center_y: 中心坐标
            size: 最终显示的方框大小 (会随呼吸效果变化)
            label: 标签文字
            zoom: 缩放倍数（>1.0 为放大特写）
            base_size_for_crop: 用于计算裁剪区域的基础大小 (固定值，不随呼吸变化)
                               如果为 None，则使用 size
        """
        h, w = frame.shape[:2]
        
        # 决定用于裁剪的大小
        # 如果提供了 base_size，则裁剪区域固定，只有最终显示大小在变 -> 产生放大/缩小效果
        target_crop_base = base_size_for_crop if base_size_for_crop is not None else size
        
        # 根据缩放倍数计算实际裁剪大小（zoom越大，裁剪区域越小，显示内容越放大）
        crop_size = int(target_crop_base / zoom)
        half_crop = crop_size // 2
        
        # 计算裁剪区域
        x1 = max(0, center_x - half_crop)
        y1 = max(0, center_y - half_crop)
        x2 = min(w, center_x + half_crop)
        y2 = min(h, center_y + half_crop)
        
        # 安全裁剪逻辑：处理出界情况，使用黑边填充
        desired_x1 = center_x - half_crop
        desired_y1 = center_y - half_crop
        desired_x2 = desired_x1 + crop_size
        desired_y2 = desired_y1 + crop_size
        
        valid_x1 = max(0, desired_x1)
        valid_y1 = max(0, desired_y1)
        valid_x2 = min(w, desired_x2)
        valid_y2 = min(h, desired_y2)
        
        if valid_x2 <= valid_x1 or valid_y2 <= valid_y1:
             return np.zeros((size, size, 3), dtype=np.uint8)
             
        valid_crop = frame[valid_y1:valid_y2, valid_x1:valid_x2]
        
        # 贴到全黑画布上
        full_crop = np.zeros((crop_size, crop_size, 3), dtype=np.uint8)
        offset_x = valid_x1 - desired_x1
        offset_y = valid_y1 - desired_y1
        
        # 确保尺寸匹配（防止计算误差）
        target_h, target_w = valid_crop.shape[:2]
        # 只有在边界内才贴图
        if offset_y >= 0 and offset_x >= 0 and \
           offset_y + target_h <= crop_size and offset_x + target_w <= crop_size:
             full_crop[offset_y:offset_y+target_h, offset_x:offset_x+target_w] = valid_crop
        else:
             # 极端情况 fallback
             if target_h > 0 and target_w > 0:
                 full_crop = cv2.resize(valid_crop, (crop_size, crop_size))
             
        crop = cv2.resize(full_crop, (size, size), interpolation=cv2.INTER_LINEAR)
        
        # --- 故障艺术风格化 ---
        # 保留原始彩色图像
        styled = crop.copy()
        
        # 添加噪点（故障效果）
        if random.random() > 0.7:  # 30%概率添加噪点
            noise = np.random.randint(0, 30, styled.shape, dtype=np.uint8)
            styled = cv2.add(styled, noise)
        
        # 5. 绘制边框 (白色固定)
        border_color = (255, 255, 255)  # 纯白
        cv2.rectangle(styled, (0, 0), (size-1, size-1), border_color, 2)
        
        # 6. 添加标签
        if label:
            # 字体缩小以适应更小的方框
            font_scale = 0.35 # 0.5 -> 0.35
            thickness = 1
            # 稍微调整位置
            cv2.putText(styled, label, (5, 15), 
                       cv2.FONT_HERSHEY_SIMPLEX, font_scale, border_color, thickness)
        
        # 7. 添加扫描线效果
        for i in range(0, size, 4):
            styled[i:i+1, :] = np.clip(styled[i:i+1, :] * 0.8, 0, 255) # 变暗每一行
            
        return styled

    def create_glitch_frame(self, frame, results, target_person_idx=None):
        # 计算时间差 (dt) 用于动画
        current_time = time.time()
        if not hasattr(self, 'last_frame_time'):
            self.last_frame_time = current_time
        
        dt = current_time - self.last_frame_time
        self.last_frame_time = current_time
        
        # 限制dt最大值，避免卡顿后跳跃
        dt = min(dt, 0.1)
        
        # 默认使用黑色背景 (如果没有检测到人)
        canvas = np.zeros((self.canvas_height, self.canvas_width, 3), dtype=np.uint8)
        
        # 寻找最佳人物，用于背景生成和部位提取
        best_person = None
        keypoints = None
        person_idx = 0
        
        if len(results) > 0:
            # 默认逻辑
            r = results[0]
            
            # 兼容性处理：检查 r 是对象还是字典
            if isinstance(r, dict):
                # 如果是字典格式 (CompletePersonFaceAnalyzer 处理后的结果)
                people_list = results # results 本身就是列表
                
                if len(people_list) > 0:
                    # === 优先使用指定的追踪目标 ===
                    if target_person_idx is not None and 0 <= target_person_idx < len(people_list):
                        best_person = people_list[target_person_idx]
                        person_idx = target_person_idx
                    else:
                        # 否则找框置信度最高的 (Fallback)
                        best_person = people_list[0]
                        best_conf = -1
                        for idx, p in enumerate(people_list):
                            conf = 0
                            if 'box' in p and len(p['box']) >= 5:
                                conf = p['box'][4]
                            elif 'conf' in p:
                                conf = p['conf']
                            if conf > best_conf:
                                best_conf = conf
                                best_person = p
                                person_idx = idx
                                
            # YOLO 原生 Results 对象处理
            elif hasattr(r, 'keypoints') and r.keypoints is not None:
                 # 对于原生YOLO结果，这里简化处理
                 if r.keypoints.data is not None and len(r.keypoints.data) > 0:
                    all_boxes = r.boxes.data.cpu().numpy()
                    all_keypoints = r.keypoints.data.cpu().numpy()
                    
                    if len(all_keypoints) > 0:
                        if target_person_idx is not None and 0 <= target_person_idx < len(all_keypoints):
                            best_idx = target_person_idx
                        else:
                            best_idx = np.argmax(all_boxes[:, 4])
                    
                        box = all_boxes[best_idx] 
                        best_person = {'box': box}
                        # 这里只是为了背景，keypoints 在后面提取
                        
        # === 绘制动态背景 ===
        if best_person is not None:
             # 获取人物 BBox
             bbox = None
             if 'bbox' in best_person: # analyzer 格式
                 bbox = best_person['bbox'] # [x1, y1, x2, y2] (或者 [x1, y1, w, h]?) analyzer通常是xyxy
             elif 'box' in best_person: # 上面构造的兼容格式
                 raw_box = best_person['box']
                 if len(raw_box) >= 4:
                     bbox = [int(raw_box[0]), int(raw_box[1]), int(raw_box[2]), int(raw_box[3])]
             
             if bbox is not None:
                 bx1, by1, bx2, by2 = bbox[0], bbox[1], bbox[2], bbox[3]
                 # 边界检查
                 h, w = frame.shape[:2]
                 bx1, by1 = max(0, bx1), max(0, by1)
                 bx2, by2 = min(w, bx2), min(h, by2)
                 
                 if bx2 > bx1 and by2 > by1:
                     # 裁剪人物
                     person_crop = frame[by1:by2, bx1:bx2]
                     if person_crop.size > 0:
                         # 调整大小填满背景
                         bg_img = cv2.resize(person_crop, (self.canvas_width, self.canvas_height))
                         
                         # 变暗处理 (Dimming) - 让背景不抢眼
                         # 创建一个半透明黑色遮罩
                         dark_overlay = np.zeros_like(bg_img)
                         canvas = cv2.addWeighted(bg_img, 0.4, dark_overlay, 0.6, 0) # 40% 原图, 60% 黑
        
        # 绘制背景UI (在背景图之上)
        self.draw_background_ui(canvas)
        
        # 如果没有检测到人，显示"NO SIGNAL"
        if len(results) == 0:
            text = "NO SIGNAL DETECTED"
            font_scale = 0.8
            thickness = 2
            color = (255, 255, 255)  # 白色
            
            # 计算文本大小以精确居中
            (text_w, text_h), _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, font_scale, thickness)
            
            x = (self.canvas_width - text_w) // 2
            y = (self.canvas_height + text_h) // 2
            
            cv2.putText(canvas, text, 
                       (x, y),
                       cv2.FONT_HERSHEY_SIMPLEX, font_scale, color, thickness)
            return canvas
        
        # 处理每个检测到的人
        # self.last_update_time = time.time()  # 这个已经被上面的 dt 计算取代了，删除
        
        # 清空状态
        parts_to_extract = []
        
        # 过滤掉重叠严重的人员框，只处理置信度最高的一个人（单人模式）
        if len(results) > 0:
            r = results[0]
            
            # 兼容性处理：检查 r 是对象还是字典
            if isinstance(r, dict):
                # 如果是字典格式 (CompletePersonFaceAnalyzer 处理后的结果)
                # 假设结构: {'keypoints': np.array, 'box': [x1,y1,x2,y2,conf,cls], ...}
                # 或者 analyzer 返回的是一个列表，每个元素是一个人的字典信息
                
                # 这里我们需要确认 process_frame 返回的具体结构
                # 通常是 [{'keypoints': ..., 'box': ...}, ...]
                
                # 获取所有人的列表
                people_list = results # results 本身就是列表
                
                if len(people_list) > 0:
                    # best_person 已经在上面背景逻辑里找过了，这里直接用
                    if best_person is None:
                         # 防御性代码，理论上上面已经找了
                        best_person = people_list[0]
                            
                    # 获取关键点
                    if 'keypoints' in best_person:
                        keypoints = best_person['keypoints']
                        # 确保是 numpy array
                        if hasattr(keypoints, 'cpu'):
                            keypoints = keypoints.cpu().numpy()
                        if isinstance(keypoints, list):
                            keypoints = np.array(keypoints)
                            
                        # 确保形状是 (17, 3)
                        if keypoints.ndim == 3: # (1, 17, 3)
                            keypoints = keypoints[0]
                            
                        person_idx = 0
                        
                        # --- 开始提取部位 (使用 best keypoints) ---
                        # (后续代码通用，只需要 keypoints 变量存在且为 (17, 3) 格式)
                        
            # YOLO 原生 Results 对象处理
            elif hasattr(r, 'keypoints') and r.keypoints is not None:
                if r.keypoints.data is not None:
                    all_keypoints = r.keypoints.data.cpu().numpy()
                    all_boxes = r.boxes.data.cpu().numpy()
                    
                    if len(all_keypoints) > 0:
                        best_idx = np.argmax(all_boxes[:, 4])
                        keypoints = all_keypoints[best_idx]
                        person_idx = 0
            
            # 确保 keypoints 已定义
            if 'keypoints' in locals() and keypoints is not None and len(keypoints) >= 17:
                    
                    # 1. 左耳 (index 4) - 左上
                    if keypoints[4][2] > 0.3:
                        parts_to_extract.append({
                            'center': (int(keypoints[4][0]), int(keypoints[4][1])),
                            'size': 75,
                            'label': f'L_EAR_{person_idx}',
                            'zoom': 2.0,
                            'position': (int(self.canvas_width * 0.15), int(self.canvas_height * 0.1))
                        })

                    # 2. 左眼 (index 2) - 左上偏中
                    if keypoints[2][2] > 0.3:
                        parts_to_extract.append({
                            'center': (int(keypoints[2][0]), int(keypoints[2][1])),
                            'size': 90,
                            'label': f'L_EYE_{person_idx}',
                            'zoom': 2.5,
                            'position': (int(self.canvas_width * 0.35), int(self.canvas_height * 0.15))
                        })
                    
                    # 3. 右眼 (index 1) - 右上偏中
                    if keypoints[1][2] > 0.3:
                        parts_to_extract.append({
                            'center': (int(keypoints[1][0]), int(keypoints[1][1])),
                            'size': 90,
                            'label': f'R_EYE_{person_idx}',
                            'zoom': 2.5,
                            'position': (int(self.canvas_width * 0.65), int(self.canvas_height * 0.15))
                        })

                    # 4. 右耳 (index 3) - 右上
                    if keypoints[3][2] > 0.3:
                        parts_to_extract.append({
                            'center': (int(keypoints[3][0]), int(keypoints[3][1])),
                            'size': 75,
                            'label': f'R_EAR_{person_idx}',
                            'zoom': 2.0,
                            'position': (int(self.canvas_width * 0.85), int(self.canvas_height * 0.1))
                        })
                    
                    # 5. 鼻子 - 中上
                    if keypoints[0][2] > 0.3:
                        parts_to_extract.append({
                            'center': (int(keypoints[0][0]), int(keypoints[0][1])),
                            'size': 100,
                            'label': f'NOSE_SCAN_{person_idx}',
                            'zoom': 2.5,
                            'position': (int(self.canvas_width * 0.5), int(self.canvas_height * 0.3))
                        })
                        
                    # 6. 整体人脸 - 正中
                    face_points = [keypoints[i] for i in [0, 1, 2, 3, 4] if keypoints[i][2] > 0.3]
                    if len(face_points) >= 3:
                        xs = [p[0] for p in face_points]
                        ys = [p[1] for p in face_points]
                        face_cx = int(sum(xs) / len(xs))
                        face_cy = int(sum(ys) / len(ys))
                        
                        parts_to_extract.append({
                            'center': (face_cx, face_cy),
                            'size': 150,
                            'label': f'FACE_ID_{person_idx}',
                            'zoom': 0.8,
                            'position': (int(self.canvas_width * 0.5), int(self.canvas_height * 0.5))
                        })
                    
                    # 7. 左手 (index 10) - 左下
                    if keypoints[10][2] > 0.3:
                        cx, cy = keypoints[10][0], keypoints[10][1]
                        if keypoints[8][2] > 0.3:
                            ex, ey = keypoints[8][0], keypoints[8][1]
                            cx = cx + (cx - ex) * 0.7
                            cy = cy + (cy - ey) * 0.7
                        
                        parts_to_extract.append({
                            'center': (int(cx), int(cy)),
                            'size': 120,
                            'label': f'L_HAND_{person_idx}',
                            'zoom': 0.5, # 缩小 zoom 以扩大视野
                            'position': (int(self.canvas_width * 0.2), int(self.canvas_height * 0.7))
                        })
                    
                    # 8. 右手 (index 9) - 右下
                    if keypoints[9][2] > 0.3:
                        cx, cy = keypoints[9][0], keypoints[9][1]
                        if keypoints[7][2] > 0.3:
                            ex, ey = keypoints[7][0], keypoints[7][1]
                            cx = cx + (cx - ex) * 0.7
                            cy = cy + (cy - ey) * 0.7
                            
                        parts_to_extract.append({
                            'center': (int(cx), int(cy)),
                            'size': 120,
                            'label': f'R_HAND_{person_idx}',
                            'zoom': 0.5, # 缩小 zoom 以扩大视野
                            'position': (int(self.canvas_width * 0.8), int(self.canvas_height * 0.7))
                        })
                    
                    # 9. 左脚 (index 16) - 底部左
                    if keypoints[16][2] > 0.3:
                        parts_to_extract.append({
                            'center': (int(keypoints[16][0]), int(keypoints[16][1])),
                            'size': 80,
                            'label': f'L_FOOT_{person_idx}',
                            'zoom': 1.0,
                            'position': (int(self.canvas_width * 0.3), int(self.canvas_height * 0.85))
                        })
                    
                    # 10. 右脚 (index 15) - 底部右
                    if keypoints[15][2] > 0.3:
                        parts_to_extract.append({
                            'center': (int(keypoints[15][0]), int(keypoints[15][1])),
                            'size': 80,
                            'label': f'R_FOOT_{person_idx}',
                            'zoom': 1.0,
                            'position': (int(self.canvas_width * 0.7), int(self.canvas_height * 0.85))
                        })

            # --- 绘制逻辑 ---
            
            # 预先更新所有状态
            final_parts = []
            for part in parts_to_extract:
                default_x, default_y = part['position']
                base_size = part['size']
                label = part['label']
                
                x, y, scale_factor = self.update_part_state(label, default_x, default_y, dt)
                current_size = int(base_size * scale_factor)
                
                # 居中
                center_offset = (base_size - current_size) // 2
                x += center_offset
                y += center_offset
                
                part['final_x'] = x
                part['final_y'] = y
                part['final_size'] = current_size
                part['final_center'] = (x + current_size//2, y + current_size//2)
                
                final_parts.append(part)
            
            # 解决重叠冲突
            self._resolve_overlaps(final_parts)
            
            # 1. 确定连接中心
            face_center_pos = None
            for part in final_parts:
                # 重新计算中心点，因为位置可能在 resolve_overlaps 中改变了
                # 确保坐标是整数
                part['final_x'] = int(part['final_x'])
                part['final_y'] = int(part['final_y'])
                
                part['final_center'] = (int(part['final_x'] + part['final_size']//2), 
                                      int(part['final_y'] + part['final_size']//2))
                                      
                if part['label'].startswith('FACE_ID'):
                    face_center_pos = part['final_center']
                    break
            
            if face_center_pos is None:
                for part in final_parts:
                    if part['label'].startswith('NOSE_SCAN'):
                        face_center_pos = part['final_center']
                        break
            
            # 2. 画线 (Layer 1)
            if face_center_pos is not None:
                for part in final_parts:
                    is_center = part['label'].startswith('FACE_ID') or \
                               (face_center_pos is not None and part['label'].startswith('NOSE_SCAN') and not any(p['label'].startswith('FACE_ID') for p in final_parts))
                    
                    if not is_center:
                        if random.random() > 0.1:
                             cv2.line(canvas, 
                                    part['final_center'],
                                    face_center_pos,
                                    (255, 255, 255), 1, cv2.LINE_AA)
            
            # 3. 画图 (Layer 2)
            for part in final_parts:
                # 去掉ID后缀显示: LEFT_EYE_0 -> LEFT_EYE
                display_label = part['label'].rsplit('_', 1)[0]
                
                # 关键修改：传入 base_size (固定) 而不是 final_size (动态)
                # 这样裁剪的视野范围 (FOV) 是固定的，不会随着方框变大而看到更多内容
                # extract_roi 内部需要同时处理 base_size (计算裁剪) 和 final_size (最终缩放)
                
                roi = self.extract_roi(
                    frame, 
                    part['center'][0], 
                    part['center'][1], 
                    part['final_size'], # 最终显示大小
                    display_label, 
                    part.get('zoom', 1.0),
                    base_size_for_crop=part['size'] # 传入基础大小用于计算固定裁剪区域
                )
                
                x, y = part['final_x'], part['final_y']
                size = part['final_size']
                
                # 严格显示：只在完全不出界时显示（双重保险）
                # 虽然上面update_part_state已经做了限制，但缩放可能会导致瞬间微小出界
                # 这里做一个强制截断，保证显示完整或至少显示在界面内
                
                # 目标区域 (Canvas)
                # 确保坐标是整数，防止切片报错
                x = int(x)
                y = int(y)
                
                target_x1 = max(0, x)
                target_y1 = max(0, y)
                target_x2 = min(self.canvas_width, x + size)
                target_y2 = min(self.canvas_height, y + size)
                
                target_w = target_x2 - target_x1
                target_h = target_y2 - target_y1
                
                if target_w > 0 and target_h > 0:
                    # 源区域 (ROI)
                    src_x1 = max(0, -x)
                    src_y1 = max(0, -y)
                    src_x2 = src_x1 + target_w
                    src_y2 = src_y1 + target_h
                    
                    try:
                        if src_y2 <= roi.shape[0] and src_x2 <= roi.shape[1]:
                            canvas[target_y1:target_y2, target_x1:target_x2] = roi[src_y1:src_y2, src_x1:src_x2]
                    except Exception as e:
                        pass
        
        self.frame_count += 1
        return canvas
    
    def draw_background_ui(self, canvas):
        """绘制背景UI元素"""
        # 文字元素已根据用户要求移除
        
        # 主标题（带闪烁效果）
        # if self.frame_count % 30 < 25:  # 闪烁
        #     cv2.putText(canvas, "CORRUPTED_VISION // V4.2", 
        #                (50, 60),
        #                cv2.FONT_HERSHEY_SIMPLEX, 1.2, self.color_cyan, 2)
        
        # 状态信息
        # status_color = self.color_red if self.frame_count % 60 < 30 else self.color_purple
        # cv2.putText(canvas, "SIGNAL INTEGRITY: CRITICAL", 
        #            (50, 100),
        #            cv2.FONT_HERSHEY_SIMPLEX, 0.6, status_color, 1)
        
        # cv2.putText(canvas, f"FRAME: {self.frame_count:06d}", 
        #            (50, 130),
        #            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (150, 150, 150), 1)
        
        # 右上角时间戳
        # timestamp = time.strftime("%H:%M:%S", time.localtime())
        # cv2.putText(canvas, f"TIMESTAMP: {timestamp}", 
        #            (self.canvas_width - 350, 60),
        #            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (100, 100, 100), 1)
        
        # 绘制装饰性边框
        cv2.rectangle(canvas, (20, 20), (self.canvas_width - 20, self.canvas_height - 20),
                     (80, 80, 80), 1)
        
        # 绘制网格线（轻微）
        for i in range(0, self.canvas_width, 100):
            if random.random() > 0.7:
                cv2.line(canvas, (i, 0), (i, self.canvas_height), (30, 30, 30), 1)
        
        # 绘制网格线（轻微）
        for i in range(0, self.canvas_height, 100):
            if random.random() > 0.7:
                cv2.line(canvas, (0, i), (self.canvas_width, i), (30, 30, 30), 1)
        
        # 添加随机噪点（模拟信号干扰）
        if random.random() > 0.95:
            for _ in range(20):
                x = random.randint(0, self.canvas_width - 1)
                y = random.randint(0, self.canvas_height - 1)
                canvas[y, x] = (255, 255, 255)


# 测试函数
if __name__ == "__main__":
    print("Glitch Art Effect - 测试模式")
    print("需要配合YOLOv8-Pose使用")
    print("请运行 test_glitch_effect.py 进行完整测试")