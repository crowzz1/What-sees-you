"""
高级手部/人脸追踪测试
优先级：人脸 (多目标轮询) > 人体 (抬头找脸)
优化版本：
1. 智能找脸：无脸时自动上移视角
2. 智能切换：目标丢失时自动切换到其他人，若无人则搜索
3. 丢失搜索：惯性跟随 -> 等待 -> 归位(RESETTING) -> 主动搜索(SEARCHING)
4. 交互模式：稳定对视时进入“部位扫描模式”(OBSERVING)，依次打量各部位
"""
import cv2
import sys
import time
import numpy as np
import math

# 在导入 ultralytics 之前保存原始的 cv2 函数
_cv2_imshow = cv2.imshow
_cv2_waitKey = cv2.waitKey  
_cv2_destroyAllWindows = cv2.destroyAllWindows

sys.path.append('sts_control')
from sts_driver import STSServoSerial
from ultralytics import YOLO

# 恢复原始的 cv2 函数
cv2.imshow = _cv2_imshow
cv2.waitKey = _cv2_waitKey
cv2.destroyAllWindows = _cv2_destroyAllWindows

# 校准数据
# 物理方向定义：
# 电机 2 (肩部): 数值小 = 伸展 (最大活动度)，数值大 = 收缩 (最小活动度)
# 电机 3 (肘部): 数值大 = 伸展 (最大活动度)，数值小 = 收缩 (最小活动度)
# 电机 4 (腕部): 数值小 = 伸展 (最大活动度)，数值大 = 收缩 (最小活动度)
MOTOR_CALIBRATION = {
    1: {'center': 2048, 'home': 2048, 'min': 1141, 'max': 3225, 'name': '基座'},
    2: {'center': 2048, 'home': 3715, 'min': 1687, 'max': 2318, 'name': '肩部(小=伸)'},
    3: {'center': 2048, 'home': 3796, 'min': 1616, 'max': 2302, 'name': '肘部(大=伸)'}, 
    4: {'center': 2048, 'home': 2803, 'min': 1500, 'max': 2600, 'name': '腕部(小=伸)'}, 
}

class AdvancedTracker:
    def __init__(self, port="COM4", camera_id=0, use_internal_camera=True, load_model=True):
        print("="*40)
        print("Advanced Tracker 2.7")
        print("策略: 智能找脸 + 自动补位 + 归位后全域搜索 + 部位扫描")
        print("="*40)
        
        # 初始化驱动
        print("连接电机...")
        try:
            self.driver = STSServoSerial(port, 1000000)
            print("✓ 电机已连接")
        except Exception as e:
            print(f"✗ 电机连接失败: {e}")
            self.driver = None
        
        # 初始化摄像头
        self.cap = None
        if use_internal_camera:
            self.cap = cv2.VideoCapture(camera_id)
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        
        # 加载模型 (可选)
        self.model = None
        if load_model:
            print("加载模型...")
            import os
            model_path = 'models/yolov8n-pose.pt'
            if not os.path.exists(model_path):
                model_path = 'yolov8n-pose.pt'
            self.model = YOLO(model_path)
        else:
            print("跳过模型加载 (使用外部结果模式)")
        
        # 初始化电机
        if self.driver:
            self._init_motors()
        
        # 画面尺寸
        self.frame_width = 640
        self.frame_height = 480
        self.center_x = self.frame_width / 2
        self.center_y = self.frame_height / 2
        
        # --- 追踪参数 ---
        self.target_x = None
        self.target_y = None
        self.smooth_x = None
        self.smooth_y = None
        self.alpha_x = 1.0   
        self.alpha_y = 0.8   
        
        # 电机目标
        self.motor1_target = 2048
        self.motor2_target = 2048
        self.motor3_target = 2048
        self.motor4_target = 2048 
        
        # 控制增益
        self.deadzone = 0.03
        self.K1 = 40.0
        self.K2 = 30.0
        
        # 状态变量
        self.tracking_mode = "NONE" 
        self.active_target_index = None # 当前正在追踪的人物索引 (对外接口)
        self.last_control_time = 0
        self.control_hz = 100
        
        # 多人切换
        self.current_person_index = 0
        self.last_switch_time = time.time()
        self.switch_interval = 15.0 
        
        # --- 智能丢失处理 ---
        self.last_seen_time = 0
        self.last_valid_target = None 
        self.lost_timeout = 3.0       
        self.search_timeout = 5.0     
        self.is_searching = False
        self.search_start_time = 0
        self.search_phase_offset = 0
        
        # --- 主动观察模式 (OBSERVING) ---
        self.stable_since = 0
        self.last_target_id = None
        self.is_scanning_person = False
        self.scan_person_start_time = 0
        self.last_stable_pos = None 
        self.movement_threshold = 0.15 
        
        # 部位扫描序列
        # 0: Nose, 5: L_Shoulder, 6: R_Shoulder, 9: L_Wrist, 10: R_Wrist
        self.scan_parts_sequence = [0, 5, 6, 9, 10] 
        self.scan_part_names = {0: 'FACE', 5: 'L_SHLDR', 6: 'R_SHLDR', 9: 'L_HAND', 10: 'R_HAND'}
        self.current_scan_idx = 0
        self.last_scan_switch_time = 0
        self.scan_switch_interval = 2.0 # 识别到部位后，打量2秒再切换
        
    def _wait_for_stop(self, motor_id, timeout=10.0):
        """等待电机停止移动"""
        start_time = time.time()
        time.sleep(0.1) # 给指令发送一点时间
        while True:
            if time.time() - start_time > timeout:
                print(f"  ⚠️ Motor {motor_id} 等待超时")
                break
            
            is_moving = self.driver.is_moving(motor_id)
            if is_moving is False: # 明确返回 False 才算停止
                break
            if is_moving is None: # 读取失败，忽略本次
                pass
                
            time.sleep(0.1)

    def _init_motors(self):
        print("\n初始化电机...")
        for motor_id in [1, 2, 3, 4]:
            self.driver.set_torque_enable(motor_id, True)
        time.sleep(0.5)
        print("归中 (speed=400, 等待到位)...")
        
        # Motor 1
        self.driver.set_position(1, 2048, speed=400, move_time=0)
        self._wait_for_stop(1)

        # Motor 2
        self.driver.set_position(2, 2048, speed=400, move_time=0)
        self._wait_for_stop(2)

        # Motor 3
        self.driver.set_position(3, 2048, speed=400, move_time=0)
        self._wait_for_stop(3)

        # Motor 4
        self.driver.set_position(4, 2048, speed=400, move_time=0)
        self._wait_for_stop(4)
        
        print("✓ Ready\n")

    def get_tracking_target(self, results):
        """返回目标坐标，同时返回当前人的关键点数据供扫描使用"""
        all_people_keypoints = []
        all_people_conf = [] # 存储每个人(Box)的置信度

        if not results: return (None, None, "NONE", 0.0, None, 0.0)
        
        # 1. 处理 YOLO 原生结果对象
        if hasattr(results[0], 'keypoints'):
            if results[0].keypoints is None or len(results[0].keypoints) == 0:
                return (None, None, "NONE", 0.0, None, 0.0)
            all_people_keypoints = results[0].keypoints.data.cpu().numpy()
            if results[0].boxes is not None:
                all_people_conf = results[0].boxes.conf.cpu().numpy()
            else:
                all_people_conf = [0.0] * len(all_people_keypoints)
        
        # 2. 处理 main_gallery_view 传入的字典列表
        elif isinstance(results, list) and len(results) > 0 and isinstance(results[0], dict):
            valid_people = []
            valid_conf = []
            for r in results:
                if 'keypoints' in r and r['keypoints'] is not None:
                    valid_people.append(r['keypoints'])
                    valid_conf.append(r.get('person_conf', 0.0)) # 获取 person_analyzer 里的 person_conf
            if not valid_people: return (None, None, "NONE", 0.0, None, 0.0)
            all_people_keypoints = valid_people
            all_people_conf = valid_conf
        else:
            return (None, None, "NONE", 0.0, None, 0.0)

        num_people = len(all_people_keypoints)
        if num_people == 0: return (None, None, "NONE", 0.0, None, 0.0)

        current_time = time.time()
        if current_time - self.last_switch_time > self.switch_interval:
            if num_people > 1:
                self.current_person_index = (self.current_person_index + 1) % num_people
                print(f"🔄 定时切换 -> P{self.current_person_index + 1}")
            self.last_switch_time = current_time
            
        if self.current_person_index >= num_people:
            self.current_person_index = 0 
            print(f"⚠️ 目标丢失，自动切换到 P1")
            
        target_idx = self.current_person_index
        
        # === 新增过滤逻辑：检查 Person 置信度是否 > 0.8 ===
        current_person_conf = all_people_conf[target_idx] if target_idx < len(all_people_conf) else 0.0
        
        # 如果当前锁定的人置信度太低，视为无效
        if current_person_conf < 0.8:
            # 尝试寻找其他符合条件的人
            found_new = False
            for i in range(num_people):
                if all_people_conf[i] > 0.8:
                    self.current_person_index = i
                    target_idx = i
                    current_person_conf = all_people_conf[i]
                    print(f"⚠️ P{target_idx+1} 置信度不足，切换到高置信度目标 P{i+1} ({current_person_conf:.2f})")
                    found_new = True
                    break
            
            # 如果所有人都低于 0.8，则全部放弃
            if not found_new:
                return (None, None, "NONE (LOW CONF)", 0.0, None, 0.0)

        kp = all_people_keypoints[target_idx]
        person_label = f"P{target_idx+1}"
        
        # 统一降低阈值到 0.3，提高追踪稳定性
        nose = kp[0]
        # 计算大小因子 (基于肩膀宽度，如果不可用则用默认值)
        # 肩膀: 5, 6
        shoulder_width = 0
        if kp[5][2] > 0.3 and kp[6][2] > 0.3:
            shoulder_width = abs(kp[5][0] - kp[6][0])
        else:
            # 如果肩膀不可见，尝试用髋部
            if kp[11][2] > 0.3 and kp[12][2] > 0.3:
                shoulder_width = abs(kp[11][0] - kp[12][0])
        
        size_factor = shoulder_width / self.frame_width
        # 如果 size_factor 为 0 (没检测到宽度)，给一个默认中等距离值 0.2
        if size_factor == 0: size_factor = 0.2

        if len(nose) >= 3 and nose[2] > 0.3:
            return (nose[0], nose[1], f"FACE {person_label}", nose[2], kp, size_factor)

        shoulders = [kp[5], kp[6]]
        valid_shoulders = [p for p in shoulders if len(p)>=3 and p[2] > 0.3]
        if len(valid_shoulders) >= 1:
            sx = sum(p[0] for p in valid_shoulders) / len(valid_shoulders)
            sy = sum(p[1] for p in valid_shoulders) / len(valid_shoulders)
            offset = 50 
            if len(valid_shoulders) == 2:
                shoulder_width = abs(valid_shoulders[0][0] - valid_shoulders[1][0])
                offset = shoulder_width * 0.8 
            target_y = max(0, sy - offset) 
            return (sx, target_y, f"BODY+UP {person_label}", 0.6, kp, size_factor)
        
        hips = [kp[11], kp[12]]
        valid_hips = [p for p in hips if len(p)>=3 and p[2] > 0.3]
        if len(valid_hips) >= 1:
             hx = sum(p[0] for p in valid_hips) / len(valid_hips)
             hy = sum(p[1] for p in valid_hips) / len(valid_hips)
             return (hx, hy, f"HIPS {person_label}", 0.5, kp, size_factor)
        
        for i in range(num_people):
            if i == target_idx: continue
            # 这里也要检查候选人的置信度
            if i < len(all_people_conf) and all_people_conf[i] < 0.8:
                continue
                
            other_kp = all_people_keypoints[i]
            other_nose = other_kp[0]
            
            # 计算候选人的 size
            other_size = 0.2
            if other_kp[5][2] > 0.3 and other_kp[6][2] > 0.3:
                other_size = abs(other_kp[5][0] - other_kp[6][0]) / self.frame_width
            
            if len(other_nose) >= 3 and other_nose[2] > 0.3:
                self.current_person_index = i
                print(f"⚠️ 当前目标无效，自动切换到 P{i+1}")
                return (other_nose[0], other_nose[1], f"FACE P{i+1} (AUTO)", other_nose[2], other_kp, other_size)
                
        return (None, None, "NONE", 0.0, None, 0.0)

    def calculate_motor_increments(self, target_x, target_y, size_factor=0.25):
        if target_x is None: return None
        dx = (target_x - self.center_x) / self.frame_width
        dy = (target_y - self.center_y) / self.frame_height 
        if abs(dx) < self.deadzone and abs(dy) < self.deadzone: return None
        
        base_gain_x = 40.0
        base_gain_y = 30.0
        speed_factor_x = 1.0 + (abs(dx) * 5.0) 
        speed_factor_y = 1.0 + (abs(dy) * 5.0)
        
        delta1 = -dx * base_gain_x * speed_factor_x
        delta2 = dy * base_gain_y * speed_factor_y
        delta3 = dy * (base_gain_y * 0.6) * speed_factor_y
        delta4 = dy * (base_gain_y * 1.2) * speed_factor_y
        
        # === Z轴 (距离) 修正 ===
        # 标准大小 0.25。
        # 差异 > 0 (人太近) -> 后缩 (M2减小, M3减小)
        # 差异 < 0 (人太远) -> 前伸 (M2增加, M3增加)
        
        z_diff = size_factor - 0.25
        
        # Z轴增益 (不要太大，微调即可)
        z_gain = 15.0 
        
        # 只有当距离变化明显时才调整，避免呼吸效应
        if abs(z_diff) > 0.05:
            z_delta = z_diff * z_gain
            # 人近(z_diff>0) -> z_delta>0 -> 我们希望 M2减小, M3减小
            # 所以要减去 z_delta
            
            # M2 (肩): 减小 = 伸展 (小=伸)
            # 人近(z_diff>0/z_delta>0) -> 我们想收缩(大) -> 需要加
            # 人远(z_diff<0/z_delta<0) -> 我们想伸展(小) -> 需要减
            delta2 += z_delta 
            
            # M3 (肘): 减小 = 收缩 (大=伸)
            # 人近(z_diff>0/z_delta>0) -> 我们想收缩(小) -> 需要减
            # 人远(z_diff<0/z_delta<0) -> 我们想伸展(大) -> 需要加
            delta3 -= z_delta * 1.2 # 肘部动多一点
            
            # M4 (腕): 保持姿态 (反向联动会自动处理，这里不需要额外加)
        
        dynamic_limit_x = 100 + int(abs(dx) * 1000) 
        dynamic_limit_y = 80 + int(abs(dy) * 1000)
        
        delta1 = max(-dynamic_limit_x, min(dynamic_limit_x, delta1))
        delta2 = max(-dynamic_limit_y, min(dynamic_limit_y, delta2))
        delta3 = max(-dynamic_limit_y, min(dynamic_limit_y, delta3))
        delta4 = max(-dynamic_limit_y, min(dynamic_limit_y, delta4))
        
        return delta1, delta2, delta3, delta4

    def update_motor_targets(self, delta1, delta2, delta3, delta4):
        self.motor1_target += delta1
        self.motor2_target += delta2
        self.motor3_target += delta3
        
        # M4 联动逻辑：让手腕随肩膀反向运动，保持姿态自然
        # 当 M2 增加 (放下) 时，M4 应该减小 (上翘) -> 反向联动
        # 联动系数 0.8 (肩膀动 10 度，手腕反向动 8 度)
        linkage_factor = 0.8
        
        # M4 的最终增量 = 自身的追踪增量 - (肩膀的增量 * 系数)
        effective_delta4 = delta4 - (delta2 * linkage_factor)
        
        self.motor4_target += effective_delta4
        
        # --- 电机 2 和 电机 3/4 的互锁逻辑 ---
        # 修正 V6 (完整版): 
        # 当 M2 伸展 (数值小) 时，限制 M3 和 M4 也不能伸展
        # M3 (数值大=伸): 限制 M3 上限 (降低 Upper Limit)
        # M4 (数值小=伸): 限制 M4 下限 (提高 Lower Limit)
        
        cal2 = MOTOR_CALIBRATION[2]
        cal3 = MOTOR_CALIBRATION[3]
        cal4 = MOTOR_CALIBRATION[4]
        
        # M2: 1600(伸) <-> 2400(缩)
        limit_min2 = min(cal2['min'], cal2['max']) 
        limit_max2 = max(cal2['min'], cal2['max']) 
        
        # M3: 1600(缩) <-> 2500(伸)
        limit_min3 = min(cal3['min'], cal3['max'])
        limit_max3 = max(cal3['min'], cal3['max']) 
        center3 = cal3['center'] # 2048

        # M4: 1500(伸) <-> 2600(缩)
        limit_min4 = min(cal4['min'], cal4['max'])
        limit_max4 = max(cal4['min'], cal4['max'])
        center4 = cal4['center'] # 2048
        
        # 检查电机 2 是否接近数值最小值 (伸展极限)
        # 阈值设为 min + 100 (放宽限制：只有在最后 100 行程才介入，减少误触)
        threshold_extend_2 = limit_min2 + 100
        
        # 检查电机 2 是否接近数值最大值 (收缩极限)
        # 阈值设为 max - 100
        threshold_contract_2 = limit_max2 - 100
        
        # 计算动态限制
        dynamic_max3 = limit_max3
        dynamic_min3 = limit_min3 # 新增：M3 下限动态调整
        dynamic_min4 = limit_min4
        
        # 情况1：M2 伸展过度 -> 限制 M3/M4 伸展
        if self.motor2_target < threshold_extend_2:
            ratio = (threshold_extend_2 - self.motor2_target) / (threshold_extend_2 - limit_min2)
            ratio = max(0.0, min(1.0, ratio))
            
            # M3 限制上限 (防止数值太大/伸展)
            dynamic_max3 = limit_max3 - (limit_max3 - center3) * ratio
            dynamic_max3 = int(dynamic_max3)
            
            # M4 限制下限 (防止数值太小/伸展)
            dynamic_min4 = limit_min4 + (center4 - limit_min4) * ratio
            dynamic_min4 = int(dynamic_min4)
            
        # 情况2：M2 收缩过度 -> 限制 M3 收缩 (必须伸出去)
        elif self.motor2_target > threshold_contract_2:
            # 线性过渡：当 M2 从 2200 升到 2400 时
            # M3 的下限从 1600 升到 2048 (中点)
            # 也就是强迫 M3 >= 2048 (保持在伸展侧)
            
            ratio = (self.motor2_target - threshold_contract_2) / (limit_max2 - threshold_contract_2)
            ratio = max(0.0, min(1.0, ratio))
            
            dynamic_min3 = limit_min3 + (center3 - limit_min3) * ratio
            dynamic_min3 = int(dynamic_min3)

        for mid, target in [(1, self.motor1_target), (2, self.motor2_target), 
                           (3, self.motor3_target), (4, self.motor4_target)]:
            
            cal = MOTOR_CALIBRATION[mid]
            limit_min = min(cal['min'], cal['max'])
            limit_max = max(cal['min'], cal['max'])
            
            # 应用动态限制
            if mid == 3:
                limit_max = min(limit_max, dynamic_max3)
                limit_min = max(limit_min, dynamic_min3) # 应用下限限制
            elif mid == 4:
                limit_min = max(limit_min, dynamic_min4)
                
            val = max(limit_min, min(limit_max, target))
            
            if mid == 1: self.motor1_target = val
            elif mid == 2: self.motor2_target = val
            elif mid == 3: self.motor3_target = val
            elif mid == 4: self.motor4_target = val

    def draw_ui(self, frame, x, y, mode, conf=0.0):
        h, w = frame.shape[:2]
        cv2.line(frame, (w//2, 0), (w//2, h), (0, 255, 0), 1)
        cv2.line(frame, (0, h//2), (w, h//2), (0, 255, 0), 1)
        dw = int(w * self.deadzone)
        dh = int(h * self.deadzone)
        cv2.rectangle(frame, (w//2-dw, h//2-dh), (w//2+dw, h//2+dh), (0, 255, 255), 2)
        
        status_text = mode
        if "RESETTING" in mode:
            status_text = "RESETTING TO CENTER..."
            color = (0, 165, 255) 
        elif "SEARCHING" in mode:
            status_text = "FULL SCAN SEARCH..."
            color = (0, 255, 255) 
        elif "OBSERVING" in mode:
            status_text = f"{mode} ({conf:.2f})"
            color = (255, 0, 255) 
        elif mode != "NONE" and x is not None:
            color = (0, 255, 0)
            if "FACE" in mode: color = (255, 0, 0)
            elif "BODY" in mode: color = (255, 0, 255)
            elif "LOST" in mode: color = (200, 200, 0)
            
            cv2.circle(frame, (int(x), int(y)), 15, color, 3)
            cv2.line(frame, (w//2, h//2), (int(x), int(y)), color, 2)
            status_text = f"TRACKING: {mode} ({conf:.2f})"
        else:
            status_text = "WAITING..."
            color = (128, 128, 128)
            
        cv2.putText(frame, status_text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
        return frame

    def process_frame(self, frame, external_results=None):
        # 1. 自动更新画面尺寸和中心点 (适配 1920x1080 或其他分辨率)
        h, w = frame.shape[:2]
        if w != self.frame_width or h != self.frame_height:
            self.frame_width = w
            self.frame_height = h
            self.center_x = w / 2
            self.center_y = h / 2
            # print(f"[Tracker] Resolution updated to {w}x{h}, Center: ({self.center_x}, {self.center_y})")

        current_time = time.time()
        
        if external_results is not None:
            results = external_results
        elif self.model is not None:
            results = self.model(frame, verbose=False)
        else:
            # 没有外部结果，也没有内部模型 -> 无法处理
            results = []
        
        tx, ty, mode, conf, kp, size_factor = self.get_tracking_target(results)
        
        # 更新对外公开的追踪目标索引
        if tx is not None:
            self.active_target_index = self.current_person_index
        else:
            self.active_target_index = None
        
        if tx is not None:
            # 有目标
            self.last_seen_time = current_time
            self.last_valid_target = (tx, ty)
            self.is_searching = False
            self.search_start_time = 0 
            
            # --- 主动观察模式逻辑 ---
            target_id = mode.split()[-1]
            if target_id != self.last_target_id:
                self.stable_since = current_time
                self.last_target_id = target_id
                self.is_scanning_person = False 
                self.last_stable_pos = (tx, ty)
                self.current_scan_idx = 0 # 重置扫描序列
            
            # 检查移动幅度 (防抖)
            if self.last_stable_pos:
                lx, ly = self.last_stable_pos
                lx = 0.95 * lx + 0.05 * tx
                ly = 0.95 * ly + 0.05 * ty
                self.last_stable_pos = (lx, ly)
                
                dx_move = abs(tx - lx) / self.frame_width
                dy_move = abs(ty - ly) / self.frame_height
                
                if dx_move > self.movement_threshold or dy_move > self.movement_threshold:
                    self.is_scanning_person = False
                    self.stable_since = current_time
            else:
                self.last_stable_pos = (tx, ty)

            # 触发扫描
            if not self.is_scanning_person and (current_time - self.stable_since > 3.0):
                print("进入部位扫描模式...")
                self.is_scanning_person = True
                self.scan_person_start_time = current_time
                self.current_scan_idx = 0 
                self.last_scan_switch_time = current_time # 重置计时器，确保第一个部位看满时间
            
            # --- 执行扫描逻辑 ---
            if self.is_scanning_person:
                target_part_id = self.scan_parts_sequence[self.current_scan_idx]
                
                # 1. 尝试获取该部位坐标
                part_x, part_y = None, None
                if kp is not None:
                    point = kp[target_part_id]
                    # 手部识别阈值放宽
                    threshold = 0.2 if target_part_id in [9, 10] else 0.5
                    
                    if len(point) >= 3 and point[2] > threshold:
                        part_x, part_y = point[0], point[1]
                
                # 2. 决策逻辑
                if part_x is not None:
                    # A. 识别到了 -> 盯着看
                    tx, ty = part_x, part_y
                    mode = f"OBSERVING ({self.scan_part_names[target_part_id]})"
                    # 更新 conf 为当前观察部位的置信度
                    if kp is not None:
                        conf = kp[target_part_id][2]
                    
                    # 只有看满了时间才切换
                    if current_time - self.last_scan_switch_time > self.scan_switch_interval:
                        self.current_scan_idx = (self.current_scan_idx + 1) % len(self.scan_parts_sequence)
                        self.last_scan_switch_time = current_time
                else:
                    # B. 没识别到 -> 立即跳过
                    self.current_scan_idx = (self.current_scan_idx + 1) % len(self.scan_parts_sequence)
                    self.last_scan_switch_time = current_time
                    # 这一帧保持原目标(脸/身体)，下一帧处理新部位 

            # 更新平滑坐标
            if self.smooth_x is None:
                self.smooth_x = tx
                self.smooth_y = ty
            else:
                self.smooth_x = self.alpha_x * tx + (1 - self.alpha_x) * self.smooth_x
                self.smooth_y = self.alpha_y * ty + (1 - self.alpha_y) * self.smooth_y

        else:
            # 无目标
            time_lost = current_time - self.last_seen_time
            
            if self.is_scanning_person:
                if time_lost < 5.0:
                    pass
                else:
                    self.is_scanning_person = False
            else:
                self.is_scanning_person = False 
            
            if not self.is_scanning_person:
                if self.last_valid_target and time_lost < self.lost_timeout:
                    mode = "LOST(FOLLOW)"
                    self.smooth_x, self.smooth_y = self.last_valid_target
                    
                elif time_lost > self.search_timeout:
                    self.smooth_x = None 
                    self.is_searching = True
                    
                    reset_targets = {}
                    is_reset = True
                    
                    for mid in [2, 3, 4]:
                        t = 2048
                        reset_targets[mid] = t
                        current_val = [0, 0, self.motor2_target, self.motor3_target, self.motor4_target][mid]
                        if abs(current_val - t) > 80: 
                            is_reset = False
                    
                    if not is_reset:
                        mode = "RESETTING"
                    else:
                        mode = "SEARCHING"
                        if self.search_start_time == 0: 
                            print(">>> SEARCHING MODE STARTED <<<")
                            self.search_start_time = current_time
                            # 计算 Motor 1 的初始相位，实现无缝启动
                            cal1 = MOTOR_CALIBRATION[1]
                            limit_min = min(cal1['min'], cal1['max'])
                            limit_max = max(cal1['min'], cal1['max'])
                            center1 = (limit_min + limit_max) / 2
                            amp1 = (limit_max - limit_min) / 2 * 0.95
                            
                            # 防止除以零或超出范围
                            if amp1 > 1:
                                ratio = (self.motor1_target - center1) / amp1
                                ratio = max(-1.0, min(1.0, ratio)) # 钳位
                                self.search_phase_offset = math.asin(ratio)
                            else:
                                self.search_phase_offset = 0

                else:
                    self.smooth_x = None 
                    mode = "WAITING"

        annotated_frame = self.draw_ui(frame.copy(), self.smooth_x, self.smooth_y, mode, conf)
        
        # 检测从非追踪模式切换到追踪模式 (Soft Start Logic)
        is_tracking_now = any(k in mode for k in ["FACE", "BODY", "HIPS", "OBSERVING", "LOST"])
        last_mode = getattr(self, 'last_mode', "NONE")
        was_searching = any(k in last_mode for k in ["SEARCHING", "RESETTING", "WAITING", "NONE"])
        
        if is_tracking_now and was_searching:
            self.tracking_transition_start = current_time
        
        if self.driver:
            self.last_control_time = current_time
            
            if (tx is not None or mode == "LOST(FOLLOW)") and self.smooth_x is not None:
                # 传入 size_factor (如果丢失目标，使用默认 0.25)
                current_size = size_factor if tx is not None else 0.25
                res = self.calculate_motor_increments(self.smooth_x, self.smooth_y, current_size)
                if res:
                    d1, d2, d3, d4 = res
                    self.update_motor_targets(d1, d2, d3, d4)
            
            elif mode == "RESETTING":
                k_return = 0.15 
                for mid in [2, 3, 4]:
                     target_pos = 2048
                     if mid == 2: self.motor2_target += (target_pos - self.motor2_target) * k_return
                     elif mid == 3: self.motor3_target += (target_pos - self.motor3_target) * k_return
                     elif mid == 4: self.motor4_target += (target_pos - self.motor4_target) * k_return
                     current = [0,0,self.motor2_target,self.motor3_target,self.motor4_target][mid]
                     if abs(current - target_pos) < 100:
                         if mid==2: self.motor2_target = target_pos
                         elif mid==3: self.motor3_target = target_pos
                         elif mid==4: self.motor4_target = target_pos

            elif mode == "SEARCHING":
                self.motor2_target = 2048
                self.motor3_target = 2048
                self.motor4_target = 2048
                
                # --- 优化 Motor 1 巡航：闭环往返 ---
                cal1 = MOTOR_CALIBRATION[1]
                limit_min = min(cal1['min'], cal1['max'])
                limit_max = max(cal1['min'], cal1['max'])
                
                range_span = limit_max - limit_min
                cruise_min = limit_min + range_span * 0.2
                cruise_max = limit_max - range_span * 0.2
                
                # 初始化状态变量 (使用 setattr 避免修改 __init__)
                if not hasattr(self, 'search_target_pos'):
                    self.search_target_pos = cruise_max
                    self.search_stop_start_time = 0
                    self.last_check_time = 0
                
                # 每 0.5 秒检查一次是否到达
                if current_time - getattr(self, 'last_check_time', 0) > 0.5:
                    self.last_check_time = current_time
                    
                    # 检查是否在移动
                    is_moving = False
                    if self.driver:
                        is_moving = self.driver.is_moving(1)
                        # 如果读取失败(None)，假设还在动以防卡死
                        if is_moving is None: is_moving = True
                    
                    if not is_moving:
                        # 已停止
                        if self.search_stop_start_time == 0:
                            self.search_stop_start_time = current_time
                        
                        # 停够 1 秒了吗？
                        if current_time - self.search_stop_start_time > 1.0:
                            # 切换方向
                            if abs(self.search_target_pos - cruise_max) < 100:
                                self.search_target_pos = cruise_min
                            else:
                                self.search_target_pos = cruise_max
                            self.search_stop_start_time = 0 # 重置计时
                    else:
                        # 还在动
                        self.search_stop_start_time = 0
                
                self.motor1_target = self.search_target_pos

            self.update_motor_targets(0, 0, 0, 0)
            
            # 默认追踪速度
            move_time = 0    
            target_speed = 1500
            
            # [NEW] 追踪初期的平滑加速 (Soft Start)
            # 防止从巡航(500)突然切到追踪(1500)时的猛冲
            if is_tracking_now:
                elapsed = current_time - getattr(self, 'tracking_transition_start', 0)
                ramp_duration = 1.5 # 1.5秒缓冲期
                if elapsed < ramp_duration:
                    # 从 500 线性加速到 1500
                    ratio = elapsed / ramp_duration
                    target_speed = 500 + int((1500 - 500) * ratio)
            
            # 如果是 SEARCHING，使用极慢速度实现平滑匀速运动
            if mode == "SEARCHING":
                target_speed = 500 
            
            self.driver.set_position(1, int(self.motor1_target), speed=target_speed, move_time=move_time)
            self.driver.set_position(2, int(self.motor2_target), speed=target_speed, move_time=move_time)
            self.driver.set_position(3, int(self.motor3_target), speed=target_speed, move_time=move_time)
            self.driver.set_position(4, int(self.motor4_target), speed=target_speed, move_time=move_time)
        
        self.last_mode = mode
        return annotated_frame

    def run(self):
        print("开始追踪...")
        if not self.cap: return
        try:
            while True:
                ret, frame = self.cap.read()
                if not ret: break
                frame = cv2.flip(frame, 1)
                annotated_frame = self.process_frame(frame)
                cv2.imshow('Advanced Tracking', annotated_frame)
                if cv2.waitKey(1) & 0xFF == ord('q'): break
        except KeyboardInterrupt: pass
        finally: self.close()

    def close(self):
        print("\n关闭系统...")
        print("="*40)
        
        if not self.driver:
            print("驱动未连接，跳过电机归位")
            if self.cap: self.cap.release()
            cv2.destroyAllWindows()
            print("✓ 系统已关闭")
            return

        print("所有电机 -> 中点 (speed=400)...")
        
        # 并行发送指令让所有电机回中点
        for motor_id in [1, 2, 3, 4]:
            self.driver.set_position(motor_id, 2048, speed=400, move_time=0)
        
        # 等待所有电机停止
        for motor_id in [1, 2, 3, 4]:
            self._wait_for_stop(motor_id)
        
        print("归位到 Home 点...")
        # Motor 4 -> home
        self.driver.set_position(4, MOTOR_CALIBRATION[4]['home'], speed=400, move_time=0)
        self._wait_for_stop(4)
        
        # Motor 3 -> home
        self.driver.set_position(3, MOTOR_CALIBRATION[3]['home'], speed=400, move_time=0)
        self._wait_for_stop(3)
        
        # Motor 2 -> home
        self.driver.set_position(2, MOTOR_CALIBRATION[2]['home'], speed=400, move_time=0)
        self._wait_for_stop(2)
            
        print("失能电机...")
        for motor_id in [1, 2, 3, 4]:
            self.driver.set_torque_enable(motor_id, False)
            
        self.driver.close()
        if self.cap: self.cap.release()
        cv2.destroyAllWindows()
        print("✓ 系统已关闭")

if __name__ == "__main__":
    tracker = AdvancedTracker()
    tracker.run()
