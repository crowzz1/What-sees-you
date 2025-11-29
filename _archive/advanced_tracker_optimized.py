import cv2
import sys
import time
import numpy as np
import math
from simple_pid import PID

sys.path.append('sts_control')
from sts_driver import STSServoSerial
from ultralytics import YOLO

# ================= 配置区域 =================
# 机械臂尺寸 (单位: cm)
L_SHOULDER = 22
L_ELBOW = 22
L_WRIST = 15

# 校准数据 (基于实测修正)
# M3: dir=-1 (数值增大=折叠/后退)
MOTOR_CALIBRATION = {
    1: {'center': 2048, 'min': 1000, 'max': 3096, 'dir': 1, 'name': 'Base'},
    2: {'center': 2048, 'min': 1600, 'max': 2400, 'dir': -1, 'name': 'Shoulder'}, # 减小=抬起/伸展 (前倾?)
    # 修正 M3 方向: 之前测得 M3 增大是折叠(后退)，所以 dir=-1 (减小是伸展)
    3: {'center': 2048, 'min': 1600, 'max': 2500, 'dir': -1, 'name': 'Elbow'},    
    4: {'center': 2048, 'min': 1400, 'max': 2700, 'dir': -1, 'name': 'Wrist'},    # 减小=抬起
}

# 目标距离参数 (基于肩膀宽度的像素占比)
TARGET_SHOULDER_WIDTH_RATIO = 0.25  # 人在画面中肩膀宽度占画面的 25%

class SafetyController:
    def check_and_clamp(self, targets):
        safe_targets = targets.copy()
        # 1. 基础软限位
        for mid, val in safe_targets.items():
            cal = MOTOR_CALIBRATION[mid]
            safe_targets[mid] = max(cal['min'], min(cal['max'], int(val)))

        # 2. 防自撞逻辑 (修正版)
        t3, t4 = safe_targets[3], safe_targets[4]
        LIMIT_WRIST_DOWN = 2100  
        
        # M3 增大 = 折叠
        LIMIT_FOLD_HIGH = 2400 
        if t3 > LIMIT_FOLD_HIGH:
             # 越折叠 (t3越大)，手腕越不能低头 (t4不能大)
             severity = (t3 - LIMIT_FOLD_HIGH) / 500.0
             allowed_wrist = LIMIT_WRIST_DOWN - (severity * 500)
             
             if t4 > allowed_wrist:
                 # print(f"[安全介入] 防撞! M3={t3}, 限制 M4: {t4} -> {int(allowed_wrist)}")
                 safe_targets[4] = int(allowed_wrist)

        return safe_targets

class ArmKinematics:
    """简易运动学与联动计算"""
    def __init__(self):
        self.last_angles = {1: 2048, 2: 2048, 3: 2048, 4: 2048}

    def get_linkage_compensation(self, delta_m2_raw, delta_m3_raw):
        """
        计算几何补偿 (鸡头防抖模式)
        """
        deg_delta_m2 = delta_m2_raw * 0.088 * MOTOR_CALIBRATION[2]['dir']
        deg_delta_m3 = delta_m3_raw * 0.088 * MOTOR_CALIBRATION[3]['dir']
        
        # 摄像头角度补偿 = -(M2变化 + M3变化)
        compensation_deg = -(deg_delta_m2 + deg_delta_m3)
        
        m4_comp_raw = (compensation_deg / 0.088) * MOTOR_CALIBRATION[4]['dir']
        return int(m4_comp_raw * 0.9)

class RobotArmTracker:
    def __init__(self, port="COM4", camera_id=0):
        print("初始化系统...")
        self.driver = STSServoSerial(port, 1000000)
        self.kinematics = ArmKinematics()
        self.safety = SafetyController()
        
        # 视觉初始化
        self.cap = cv2.VideoCapture(camera_id)
        self.cap.set(3, 640)
        self.cap.set(4, 480)
        self.model = YOLO('yolov8n-pose.pt')
        
        self.cw = 640
        self.ch = 480
        
        # === PID 控制器配置 ===
        self.pid_x = PID(Kp=0.15, Ki=0.01, Kd=0.005, setpoint=0)
        self.pid_x.output_limits = (-80, 80)
        
        self.pid_y = PID(Kp=0.2, Ki=0.02, Kd=0.01, setpoint=0) 
        self.pid_y.output_limits = (-100, 100)
        
        self.pid_dist = PID(Kp=0.5, Ki=0.0, Kd=0.01, setpoint=0)
        self.pid_dist.output_limits = (-30, 30)
        
        # 初始姿态：读取当前位置，不强制归位
        self.targets = {1: 2048, 2: 2048, 3: 2048, 4: 2048}
        self.init_robot()

    def init_robot(self):
        print("读取当前姿态...")
        for i in range(1, 5):
            pos = self.driver.get_position(i)
            if pos != -1:
                self.targets[i] = pos
            else:
                self.targets[i] = 2048
                
        print("原地使能电机...")
        for i in range(1, 5):
            self.driver.set_torque_enable(i, True)
            self.driver.set_position(i, self.targets[i], speed=0)
        time.sleep(1)

    def _sync_motors(self, speed=0):
        """发送指令给电机，包含安全限制"""
        # 先通过安全控制器修正
        safe_targets = self.safety.check_and_clamp(self.targets)
        
        # 更新 self.targets 以防误差累积 (可选，这里只执行 safe_targets)
        # self.targets = safe_targets 

        for mid, val in safe_targets.items():
            run_speed = speed if speed > 0 else 0
            self.driver.set_position(mid, val, speed=run_speed)

    def get_target_error(self, results):
        """解析视觉结果，返回归一化的误差 (x_err, y_err, size_err)"""
        if not results or not results[0].keypoints or len(results[0].keypoints) == 0:
            return None, None, None
        kp = results[0].keypoints.data[0].cpu().numpy()
        
        # 改进：使用面部关键点 (鼻子0, 眼1/2, 耳3/4) 的重心，而不仅仅是鼻子
        # 这样即使侧脸或鼻子被遮挡也能持续追踪
        face_indices = [0, 1, 2, 3, 4]
        visible_pts = [kp[i] for i in face_indices if kp[i][2] > 0.4] # 阈值稍微放宽
        
        if len(visible_pts) == 0:
            return None, None, None
            
        # 计算平均坐标
        avg_x = sum(p[0] for p in visible_pts) / len(visible_pts)
        avg_y = sum(p[1] for p in visible_pts) / len(visible_pts)
        
        x_err = (avg_x - self.cw/2) / (self.cw/2)
        y_err = (avg_y - self.ch/2) / (self.ch/2)
        
        # 2. 找肩膀 (ID 5, 6) 计算宽度/距离
        size_err = 0
        shoulders = [kp[5], kp[6]]
        # 如果肩膀不可见，尝试用耳朵距离代替 (大概是肩膀的 1/3)
        if shoulders[0][2] > 0.5 and shoulders[1][2] > 0.5:
            width_px = abs(shoulders[0][0] - shoulders[1][0])
            ratio = width_px / self.cw
            size_err = (ratio - TARGET_SHOULDER_WIDTH_RATIO) * 10 
        
        return x_err, y_err, size_err

    def run(self):
        print("开始智能追踪...按 'q' 退出")
        try:
            while True:
                start_time = time.time()
                ret, frame = self.cap.read()
                if not ret: break
                
                frame = cv2.flip(frame, 1) 
                results = self.model(frame, verbose=False)
                annotated_frame = results[0].plot()
                
                x_err, y_err, size_err = self.get_target_error(results)
                
                if x_err is not None:
                    # 绘制锁定框 (绿色)
                    cv2.circle(annotated_frame, (int(x_err * self.cw/2 + self.cw/2), int(y_err * self.ch/2 + self.ch/2)), 10, (0, 255, 0), -1)
                    
                    # === 1. PID 计算 ===
                    delta_x = self.pid_x(x_err) 
                    self.targets[1] += delta_x * -1 
                    
                    delta_y = self.pid_y(y_err)
                    self.targets[4] += delta_y 
                    
                    # === 2. 级联控制策略 ===
                    # M4 偏离中位 -> 带动 M2/M3
                    m4_center = MOTOR_CALIBRATION[4]['center']
                    m4_deviation = self.targets[4] - m4_center
                    
                    body_move = 0
                    if abs(m4_deviation) > 200: 
                        body_move = (m4_deviation / 10.0)
                    
                    dist_move = 0
                    if size_err is not None:
                         dist_move = self.pid_dist(size_err)
                    
                    # === 3. 混合运动学计算 ===
                    # 计算 M2 (肩) 的运动
                    delta_m2 = (body_move * 0.5) + (dist_move * 20)
                    
                    # 计算 M3 (肘) 的运动
                    # 注意 M3 dir=-1 (减小是伸展)，所以要想伸远，需要减小数值
                    # dist_move > 0 (太近，要退)，需要折叠(增大) -> M3 += ...
                    # dist_move < 0 (太远，要进)，需要伸展(减小) -> M3 -= ...
                    delta_m3 = (dist_move * 25) # 正负号修正
                    
                    # 应用 M2/M3
                    old_m2 = self.targets[2]
                    old_m3 = self.targets[3]
                    
                    self.targets[2] += delta_m2
                    self.targets[3] += delta_m3
                    
                    # === 4. 姿态补偿 (鸡头防抖) ===
                    actual_delta_m2 = self.targets[2] - old_m2
                    actual_delta_m3 = self.targets[3] - old_m3
                    
                    comp_m4 = self.kinematics.get_linkage_compensation(actual_delta_m2, actual_delta_m3)
                    self.targets[4] += comp_m4
                    
                else:
                    # 目标丢失
                    cv2.putText(annotated_frame, "TARGET LOST", (20, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
                    self.pid_x.reset()
                    self.pid_y.reset()
                
                # 执行电机控制
                self._sync_motors(speed=1500)
                
                cv2.imshow('Optimized Arm Tracker', annotated_frame)
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break
                    
        except KeyboardInterrupt:
            pass
        finally:
            self.close()

    def close(self):
        print("关闭...")
        # 退出时不强制回中，防止打架，只松劲
        time.sleep(1)
        for i in range(1, 5):
            self.driver.set_torque_enable(i, False)
        self.driver.close()
        self.cap.release()
        cv2.destroyAllWindows()

if __name__ == "__main__":
    tracker = RobotArmTracker()
    tracker.run()
