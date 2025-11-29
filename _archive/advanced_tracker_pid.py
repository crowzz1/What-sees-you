"""
高级手部/人脸追踪测试 - PID 优化版
基于 advanced_tracker.py 的逻辑，但将运动控制升级为 PID + 生物级联控制 + 安全保护
"""
import cv2
import sys
import time
import numpy as np
import math
from simple_pid import PID

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

# 机械臂尺寸 (单位: cm)
L_SHOULDER = 22
L_ELBOW = 22
L_WRIST = 15

# 校准数据 (基于 simulation_tracker 验证通过的数据)
# M3: dir=-1 (数值增大=折叠/后退)
MOTOR_CALIBRATION = {
    1: {'center': 2048, 'min': 1000, 'max': 3096, 'dir': 1, 'name': 'Base'},
    2: {'center': 2048, 'min': 1600, 'max': 2400, 'dir': -1, 'name': 'Shoulder'}, 
    3: {'center': 2048, 'min': 1600, 'max': 2500, 'dir': -1, 'name': 'Elbow'},    
    4: {'center': 2048, 'min': 1400, 'max': 2700, 'dir': -1, 'name': 'Wrist'},    
}

# 目标距离参数
TARGET_SHOULDER_WIDTH_RATIO = 0.25 

class SafetyController:
    """安全控制器：防自撞和限位保护"""
    def check_and_clamp(self, targets):
        safe_targets = targets.copy()
        # 1. 基础软限位
        for mid, val in safe_targets.items():
            cal = MOTOR_CALIBRATION[mid]
            safe_targets[mid] = max(cal['min'], min(cal['max'], int(val)))

        # 2. 防自撞逻辑
        t3, t4 = safe_targets[3], safe_targets[4]
        LIMIT_WRIST_DOWN = 2100  
        LIMIT_FOLD_HIGH = 2400 
        
        if t3 > LIMIT_FOLD_HIGH:
             severity = (t3 - LIMIT_FOLD_HIGH) / 500.0
             allowed_wrist = LIMIT_WRIST_DOWN - (severity * 500)
             if t4 > allowed_wrist:
                 safe_targets[4] = int(allowed_wrist)

        return safe_targets

class ArmKinematics:
    """简易运动学与联动计算"""
    def __init__(self):
        pass

    def get_linkage_compensation(self, delta_m2_raw, delta_m3_raw):
        deg_delta_m2 = delta_m2_raw * 0.088 * MOTOR_CALIBRATION[2]['dir']
        deg_delta_m3 = delta_m3_raw * 0.088 * MOTOR_CALIBRATION[3]['dir']
        compensation_deg = -(deg_delta_m2 + deg_delta_m3)
        m4_comp_raw = (compensation_deg / 0.088) * MOTOR_CALIBRATION[4]['dir']
        return int(m4_comp_raw * 0.9)

class AdvancedTrackerPID:
    def __init__(self, port="COM4", camera_id=0, use_internal_camera=True, load_model=True):
        print("="*40)
        print("Advanced Tracker PID Optimized")
        print("保留原版所有交互逻辑，仅升级运动控制")
        print("="*40)
        
        # 初始化驱动
        print("连接电机...")
        try:
            self.driver = STSServoSerial(port, 1000000)
            print("✓ 电机已连接")
        except Exception as e:
            print(f"✗ 电机连接失败: {e}")
            self.driver = None
        
        self.safety = SafetyController()
        self.kinematics = ArmKinematics()

        # 初始化摄像头
        self.cap = None
        if use_internal_camera:
            self.cap = cv2.VideoCapture(camera_id)
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        
        # 加载模型
        self.model = None
        if load_model:
            print("加载模型...")
            self.model = YOLO('yolov8n-pose.pt')
        
        # 画面尺寸
        self.frame_width = 640
        self.frame_height = 480
        self.cw = 640
        self.ch = 480
        self.center_x = self.frame_width / 2
        self.center_y = self.frame_height / 2
        
        # === PID 控制器 (替代原有的 K1/K2) ===
        self.pid_x = PID(Kp=0.15, Ki=0.01, Kd=0.005, setpoint=0)
        self.pid_x.output_limits = (-80, 80)
        
        self.pid_y = PID(Kp=0.2, Ki=0.02, Kd=0.01, setpoint=0) 
        self.pid_y.output_limits = (-100, 100)
        
        self.pid_dist = PID(Kp=0.5, Ki=0.0, Kd=0.01, setpoint=0)
        self.pid_dist.output_limits = (-30, 30)
        
        # 目标变量
        self.targets = {1: 2048, 2: 2048, 3: 2048, 4: 2048}
        
        # 状态变量 (保留原版)
        self.tracking_mode = "NONE" 
        self.active_target_index = None
        
        # 多人切换 (保留原版)
        self.current_person_index = 0
        self.last_switch_time = time.time()
        self.switch_interval = 15.0 
        
        # 智能丢失处理 (保留原版)
        self.last_seen_time = 0
        self.last_valid_target = None 
        self.lost_timeout = 3.0       
        self.search_timeout = 5.0     
        self.is_searching = False
        self.search_start_time = 0
        self.search_phase_offset = 0
        
        # 主动观察模式 (保留原版)
        self.stable_since = 0
        self.last_target_id = None
        self.is_scanning_person = False
        self.scan_person_start_time = 0
        self.last_stable_pos = None 
        self.movement_threshold = 0.15 
        self.scan_parts_sequence = [0, 5, 6, 9, 10] 
        self.scan_part_names = {0: 'FACE', 5: 'L_SHLDR', 6: 'R_SHLDR', 9: 'L_HAND', 10: 'R_HAND'}
        self.current_scan_idx = 0
        self.last_scan_switch_time = 0
        self.scan_switch_interval = 2.0

        # 初始化电机
        if self.driver:
            self._init_motors_safe()

    def _init_motors_safe(self):
        """安全初始化：先回中，再回Home点，与原版保持一致"""
        print("\n初始化电机...")
        for motor_id in [1, 2, 3, 4]:
            self.driver.set_torque_enable(motor_id, True)
        time.sleep(0.5)
        print("归中 (speed=400, 等待到位)...")
        
        # 原版逻辑：先回 2048
        for i in range(1, 5):
            self.driver.set_position(i, 2048, speed=400)
            # 简单等待到位
        time.sleep(2)
        
        # 更新内部状态为 2048
        for i in range(1, 5): self.targets[i] = 2048
            
        print("✓ Ready\n")

    def _wait_for_stop(self, motor_id, timeout=10.0):
        """等待电机停止移动"""
        start_time = time.time()
        time.sleep(0.1) 
        while True:
            if time.time() - start_time > timeout:
                print(f"  ⚠️ Motor {motor_id} 等待超时")
                break
            is_moving = self.driver.is_moving(motor_id)
            if is_moving is False: break
            time.sleep(0.1)

    def get_tracking_target(self, results):
        """
        保留原版的复杂追踪逻辑：多目标轮询、置信度过滤、部位扫描支持
        但增加了面部多点重心计算
        """
        all_people_keypoints = []
        all_people_conf = []

        if not results: return (None, None, "NONE", 0.0, None)
        
        if hasattr(results[0], 'keypoints'):
            if results[0].keypoints is None or len(results[0].keypoints) == 0:
                return (None, None, "NONE", 0.0, None)
            all_people_keypoints = results[0].keypoints.data.cpu().numpy()
            if results[0].boxes is not None:
                all_people_conf = results[0].boxes.conf.cpu().numpy()
            else:
                all_people_conf = [0.0] * len(all_people_keypoints)
        elif isinstance(results, list) and len(results) > 0 and isinstance(results[0], dict):
            valid_people = []
            valid_conf = []
            for r in results:
                if 'keypoints' in r and r['keypoints'] is not None:
                    valid_people.append(r['keypoints'])
                    valid_conf.append(r.get('person_conf', 0.0))
            if not valid_people: return (None, None, "NONE", 0.0, None)
            all_people_keypoints = valid_people
            all_people_conf = valid_conf
        else:
            return (None, None, "NONE", 0.0, None)

        num_people = len(all_people_keypoints)
        if num_people == 0: return (None, None, "NONE", 0.0, None)

        current_time = time.time()
        if current_time - self.last_switch_time > self.switch_interval:
            if num_people > 1:
                self.current_person_index = (self.current_person_index + 1) % num_people
                print(f"🔄 定时切换 -> P{self.current_person_index + 1}")
            self.last_switch_time = current_time
            
        if self.current_person_index >= num_people:
            self.current_person_index = 0 
            
        target_idx = self.current_person_index
        current_person_conf = all_people_conf[target_idx] if target_idx < len(all_people_conf) else 0.0
        
        if current_person_conf < 0.8:
            found_new = False
            for i in range(num_people):
                if all_people_conf[i] > 0.8:
                    self.current_person_index = i
                    target_idx = i
                    found_new = True
                    break
            if not found_new:
                return (None, None, "NONE (LOW CONF)", 0.0, None)

        kp = all_people_keypoints[target_idx]
        person_label = f"P{target_idx+1}"
        
        # --- 改进：使用面部五点重心 ---
        face_indices = [0, 1, 2, 3, 4]
        visible_pts = [kp[i] for i in face_indices if kp[i][2] > 0.3]
        
        if len(visible_pts) > 0:
            avg_x = sum(p[0] for p in visible_pts) / len(visible_pts)
            avg_y = sum(p[1] for p in visible_pts) / len(visible_pts)
            # 随便取一个点的置信度作为参考
            conf = visible_pts[0][2]
            return (avg_x, avg_y, f"FACE {person_label}", conf, kp)

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
            return (sx, target_y, f"BODY+UP {person_label}", 0.6, kp)
        
        return (None, None, "NONE", 0.0, None)

    def draw_ui(self, frame, x, y, mode, conf=0.0):
        # 保留原版 UI
        h, w = frame.shape[:2]
        cv2.line(frame, (w//2, 0), (w//2, h), (0, 255, 0), 1)
        cv2.line(frame, (0, h//2), (w, h//2), (0, 255, 0), 1)
        
        status_text = mode
        color = (0, 255, 0)
        
        if "RESETTING" in mode:
            status_text = "RESETTING TO CENTER..."
            color = (0, 165, 255) 
        elif "SEARCHING" in mode:
            status_text = "FULL SCAN SEARCH..."
            color = (0, 255, 255) 
        elif "OBSERVING" in mode:
            status_text = f"{mode} ({conf:.2f})"
            color = (255, 0, 255)
        elif "LOST" in mode:
            status_text = "TARGET LOST"
            color = (0, 0, 255)
        elif x is not None:
            cv2.circle(frame, (int(x), int(y)), 15, (0,255,0), 3)
            
        cv2.putText(frame, status_text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
        return frame

    def update_motors_pid(self, tx, ty, size_err=None):
        """
        核心升级：使用 PID + 级联控制计算电机目标
        替代原版的 calculate_motor_increments
        """
        # 1. 计算归一化误差
        x_err = (tx - self.center_x) / self.center_x
        y_err = (ty - self.center_y) / self.center_y
        
        # 2. PID 计算
        delta_x = self.pid_x(x_err)
        self.targets[1] += delta_x * -1 # M1 反向
        
        delta_y = self.pid_y(y_err)
        self.targets[4] += delta_y # M4 正向
        
        # 3. 级联跟随 (M4 带动 M2/M3)
        m4_center = MOTOR_CALIBRATION[4]['center']
        m4_deviation = self.targets[4] - m4_center
        
        body_move = 0
        if abs(m4_deviation) > 200:
             body_move = (m4_deviation / 10.0)
             
        dist_move = 0
        if size_err is not None:
             dist_move = self.pid_dist(size_err)
             
        # 4. 混合运动学
        delta_m2 = (body_move * 0.5) + (dist_move * 20)
        delta_m3 = (dist_move * 25)
        
        old_m2 = self.targets[2]
        old_m3 = self.targets[3]
        
        self.targets[2] += delta_m2
        self.targets[3] += delta_m3
        
        # 5. 姿态补偿
        actual_delta_m2 = self.targets[2] - old_m2
        actual_delta_m3 = self.targets[3] - old_m3
        comp_m4 = self.kinematics.get_linkage_compensation(actual_delta_m2, actual_delta_m3)
        self.targets[4] += comp_m4

    def process_frame(self, frame, external_results=None):
        h, w = frame.shape[:2]
        if w != self.frame_width or h != self.frame_height:
            self.frame_width = w
            self.frame_height = h
            self.center_x = w / 2
            self.center_y = h / 2
            self.cw, self.ch = w, h

        current_time = time.time()
        
        if external_results is not None:
            results = external_results
        elif self.model is not None:
            results = self.model(frame, verbose=False)
        else:
            results = []
        
        tx, ty, mode, conf, kp = self.get_tracking_target(results)
        
        # 计算距离误差 (肩宽)
        size_err = None
        if kp is not None:
            shoulders = [kp[5], kp[6]]
            if shoulders[0][2] > 0.5 and shoulders[1][2] > 0.5:
                width_px = abs(shoulders[0][0] - shoulders[1][0])
                ratio = width_px / self.cw
                size_err = (ratio - TARGET_SHOULDER_WIDTH_RATIO) * 10

        if tx is not None:
            self.active_target_index = self.current_person_index
            self.last_seen_time = current_time
            self.last_valid_target = (tx, ty)
            self.is_searching = False
            
            # 主动观察逻辑 (OBSERVING) - 简化版，直接利用坐标
            target_id = mode.split()[-1]
            if target_id != self.last_target_id:
                self.stable_since = current_time
                self.last_target_id = target_id
                self.is_scanning_person = False
            
            # 执行 PID 更新
            self.update_motors_pid(tx, ty, size_err)
            
        else:
            # 目标丢失处理
            self.active_target_index = None
            self.pid_x.reset()
            self.pid_y.reset()
            self.pid_dist.reset()
            
            time_lost = current_time - self.last_seen_time
            if time_lost < self.lost_timeout:
                 mode = "LOST(FOLLOW)"
                 # 保持最后位置，不做任何操作
            elif time_lost > self.search_timeout:
                 mode = "SEARCHING"
                 # 简易搜寻：只动 M1
                 phase = (current_time * 0.5) 
                 self.targets[1] = 2048 + math.sin(phase) * 500
                 self.targets[4] = 2048 + math.sin(current_time * 1.0) * 200

        annotated_frame = self.draw_ui(frame.copy(), tx, ty, mode, conf)
        
        if self.driver:
            # 应用安全限制并发送
            safe_targets = self.safety.check_and_clamp(self.targets)
            # 更新回 targets 以避免积分饱和 (可选)
            # self.targets = safe_targets.copy()
            
            for mid, val in safe_targets.items():
                self.driver.set_position(mid, val, speed=1500)
        
        return annotated_frame

    def run(self):
        print("开始 PID 追踪...")
        if not self.cap: return
        try:
            while True:
                ret, frame = self.cap.read()
                if not ret: break
                frame = cv2.flip(frame, 1)
                annotated_frame = self.process_frame(frame)
                cv2.imshow('Advanced Tracker PID', annotated_frame)
                if cv2.waitKey(1) & 0xFF == ord('q'): break
        except KeyboardInterrupt: pass
        finally: self.close()

    def close(self):
        print("\n关闭系统...")
        print("="*40)
        print("所有电机 -> 中点 (speed=400)...")
        
        for motor_id in [1, 2, 3, 4]:
            self.driver.set_position(motor_id, 2048, speed=400, move_time=0)
        for motor_id in [1, 2, 3, 4]:
            self._wait_for_stop(motor_id)
        
        print("归位到 Home 点...")
        # 使用原版的 Home 点数据
        home_positions = {1: 3128, 2: 3715, 3: 3835, 4: 2718}
        
        # 倒序归位
        for mid in [4, 3, 2, 1]:
            self.driver.set_position(mid, home_positions[mid], speed=400)
            self._wait_for_stop(mid)
            
        print("失能电机...")
        for i in range(1, 5):
            if self.driver: self.driver.set_torque_enable(i, False)
        if self.driver: self.driver.close()
        if self.cap: self.cap.release()
        cv2.destroyAllWindows()
        print("✓ 系统已关闭")

if __name__ == "__main__":
    tracker = AdvancedTrackerPID()
    tracker.run()
