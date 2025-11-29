import cv2
import sys
import time
import numpy as np
import math
from simple_pid import PID

sys.path.append('sts_control')
from sts_driver import STSServoSerial
from ultralytics import YOLO

# ================= 硬件尺寸 (cm) =================
L_SHOULDER = 22.0
L_ELBOW = 22.0
L_WRIST = 15.0

# ================= 增强版校准数据 =================
# 务必根据实际情况调整 'min' 和 'max'，这是第一道防线
MOTOR_CALIBRATION = {
    1: {'center': 2048, 'min': 1000, 'max': 3096, 'dir': 1, 'name': 'Base'},
    # M2: 肩部。假设减小是抬起。
    2: {'center': 2048, 'min': 1500, 'max': 2500, 'dir': -1, 'name': 'Shoulder'}, 
    # M3: 肘部。假设增大是伸展。
    3: {'center': 2048, 'min': 1500, 'max': 3000, 'dir': 1, 'name': 'Elbow'},
    # M4: 腕部。假设减小是抬头。
    4: {'center': 2048, 'min': 1000, 'max': 3000, 'dir': -1, 'name': 'Wrist'},
}

class SafetyController:
    """
    安全控制器：负责在指令发送给电机前，检查物理冲突和极限
    """
    def __init__(self):
        # 转换系数: 360度 / 4096步 ≈ 0.088 度/步
        self.step2deg = 0.088
        
    def raw_to_deg(self, motor_id, raw_val):
        """将原始值转换为相对中点的物理角度(度)"""
        cal = MOTOR_CALIBRATION[motor_id]
        diff = raw_val - cal['center']
        # 乘以方向系数，确保物理意义一致（例如：抬头/伸展统一定义为正或负）
        # 这里统一：伸展/抬起方向为正角度处理（方便计算三角函数）
        # 注意：这里的正负取决于你的电机安装方向，以下逻辑基于通用假设
        angle = diff * self.step2deg * cal['dir']
        return angle

    def check_and_clamp(self, targets):
        """
        核心安全检查函数
        输入: 期望的目标字典 {1: val, 2: val...}
        输出: 修正后的安全目标字典
        """
        safe_targets = targets.copy()

        # --- 1. 基础软限位 (Soft Limits) ---
        for mid, val in safe_targets.items():
            cal = MOTOR_CALIBRATION[mid]
            safe_targets[mid] = max(cal['min'], min(cal['max'], int(val)))

        # --- 2. 获取当前规划的角度 (用于几何计算) ---
        # 假设：
        # theta2 = 肩膀角度 (0度垂直向上，90度水平向前)
        # theta3 = 肘部相对角度 (0度与大臂垂直，90度完全伸直)
        # *注意*：这里需要你根据实际电机安装校准角度偏移。
        # 简单起见，我们直接处理 "数值距离"，这在没有绝对编码器时更稳健。
        
        m2_val = safe_targets[2]
        m3_val = safe_targets[3]
        m4_val = safe_targets[4]

        # --- 3. 防完全伸展 (Singularity Protection) ---
        # 危险情况：M2伸展 + M3伸展，两者都接近极限
        # 逻辑：如果 M3 试图伸展到极限，且 M2 也在伸展区，限制 M3。
        
        # 定义什么叫"伸展"：
        # M2: dir=-1 (减小是抬/伸), center=2048. value < 1800 是高抬
        # M3: dir=1 (增大是伸), center=2048. value > 2600 是直臂
        
        # 计算手臂总延伸率 (0.0 - 1.0)
        # 这是一个估算值，用于防止锁死
        ext_m2 = 0
        if m2_val < 2048: # 假设小于2048是抬起
            ext_m2 = (2048 - m2_val) / (2048 - MOTOR_CALIBRATION[2]['min'])
            
        ext_m3 = 0
        if m3_val > 2048: # 假设大于2048是伸直
            ext_m3 = (m3_val - 2048) / (MOTOR_CALIBRATION[3]['max'] - 2048)

        # 如果两个都伸展超过 90%，强制拉回 M3
        if ext_m2 > 0.8 and ext_m3 > 0.9:
            print("[警告] 接近完全伸展死点！限制肘部伸出。")
            # 强制将 M3 限制在 90% 行程处
            limit_val = 2048 + (MOTOR_CALIBRATION[3]['max'] - 2048) * 0.9
            safe_targets[3] = int(limit_val)

        # --- 4. 防自碰撞/折叠 (Self-Collision) ---
        # 危险情况：肘部弯曲过度 (M3数值很小)，导致手腕撞击肩膀
        # 逻辑：如果 M3 < 阈值，禁止 M3 继续减小
        
        FOLD_LIMIT_M3 = 1700 # 假设 1700 是肘部弯曲的安全极限
        if safe_targets[3] < FOLD_LIMIT_M3:
             print("[警告] 肘部弯曲过度，防止撞击底座。")
             safe_targets[3] = FOLD_LIMIT_M3

        # --- 5. 腕部互锁 (Wrist Guard) ---
        # 危险情况：如果肘部弯曲很大，手腕不能大幅度下压
        # 简单的线性互锁
        if safe_targets[3] < 1900: # 肘部弯曲
             # 限制手腕不能太"低头" (假设大数值是低头)
             MAX_WRIST_FLEX = 2400 
             safe_targets[4] = min(safe_targets[4], MAX_WRIST_FLEX)

        return safe_targets

class SafeRobotArmTracker:
    def __init__(self, port="COM4", camera_id=0):
        print("初始化安全追踪系统...")
        self.driver = STSServoSerial(port, 1000000)
        self.safety = SafetyController() # 实例化安全控制器
        
        # 视觉
        self.cap = cv2.VideoCapture(camera_id)
        self.cap.set(3, 640)
        self.cap.set(4, 480)
        self.model = YOLO('yolov8n-pose.pt')
        
        self.cw, self.ch = 640, 480
        
        # PID (参数可微调)
        self.pid_x = PID(Kp=0.12, Ki=0.01, Kd=0.005, output_limits=(-60, 60))
        self.pid_y = PID(Kp=0.15, Ki=0.015, Kd=0.005, output_limits=(-80, 80))
        self.pid_dist = PID(Kp=0.4, Ki=0.0, Kd=0.01, output_limits=(-30, 30))
        
        # 目标状态
        self.targets = {1: 2048, 2: 2048, 3: 2048, 4: 2048}
        self.init_robot()

    def init_robot(self):
        print("归位机械臂 (Safe Mode)...")
        # 1. 使能
        for i in range(1, 5): self.driver.set_torque_enable(i, True)
        
        # 2. 先把手腕和肘部收回来，防止展开时打到东西
        self.driver.set_position(4, 2048, speed=500)
        self.driver.set_position(3, 2048, speed=500)
        time.sleep(1)
        
        # 3. 再动肩膀
        self.driver.set_position(2, 2100, speed=500) 
        self.driver.set_position(1, 2048, speed=500)
        time.sleep(1.5)
        
        # 更新内部状态
        self.targets = {1: 2048, 2: 2100, 3: 2048, 4: 2048}

    def move_safe(self, speed=0):
        """
        所有移动指令必须经过此函数
        """
        # 1. 运行安全检查
        final_targets = self.safety.check_and_clamp(self.targets)
        
        # 2. 只有被修改过（触发安全限制），才更新 self.targets，防止积分饱和后下次突变
        # (这里简单处理：直接用安全值发送，但保留原有的PID累积值可能导致"顶住"限制
        #  更高级的做法是如果触发限制，也重置PID积分，这里暂时忽略以保持简单)
        
        for mid, val in final_targets.items():
            self.driver.set_position(mid, val, speed=speed)
            
        # 可选：将修正后的值写回 targets，防止 PID 继续向不安全方向累积
        # self.targets = final_targets 

    def get_error(self, results):
        if not results or not results[0].keypoints or len(results[0].keypoints) == 0:
            return None, None, None
        
        kp = results[0].keypoints.data[0].cpu().numpy()
        nose = kp[0]
        if nose[2] < 0.5: return None, None, None # 没看到脸
        
        x_err = (nose[0] - self.cw/2) / (self.cw/2)
        y_err = (nose[1] - self.ch/2) / (self.ch/2)
        
        # 距离估算 (基于两肩宽或两眼距)
        size_err = 0
        shoulders = [kp[5], kp[6]]
        if shoulders[0][2] > 0.5 and shoulders[1][2] > 0.5:
            width = abs(shoulders[0][0] - shoulders[1][0])
            size_err = (width/self.cw - 0.25) * 10
            
        return x_err, y_err, size_err

    def run(self):
        print("开始安全追踪...")
        try:
            while True:
                ret, frame = self.cap.read()
                if not ret: break
                frame = cv2.flip(frame, 1)
                
                results = self.model(frame, verbose=False)
                annotated = results[0].plot()
                
                x_err, y_err, size_err = self.get_error(results)
                
                if x_err is not None:
                    # PID 计算
                    dx = self.pid_x(x_err)
                    dy = self.pid_y(y_err)
                    dd = self.pid_dist(size_err)
                    
                    # === 运动学混合策略 ===
                    
                    # 1. 水平轴
                    self.targets[1] -= dx # 注意方向
                    
                    # 2. 垂直轴级联
                    # 先动眼睛(M4)
                    self.targets[4] += dy 
                    
                    # 如果眼睛看太高/太低，动身体(M2)
                    m4_dev = self.targets[4] - 2048
                    if abs(m4_dev) > 300: # 只有眼睛转动很大时才动身体
                        self.targets[2] += m4_dev * 0.05
                        # 同时稍微反向动肘部(M3)以保持末端平稳
                        self.targets[3] -= m4_dev * 0.02
                    
                    # 3. 距离控制 (伸缩)
                    # 距离远(dd<0) -> 伸展: M2减小(抬), M3增大(伸)
                    # 距离近(dd>0) -> 收缩: M2增大(落), M3减小(缩)
                    
                    # 修正系数：M2 对距离影响大，M3 配合
                    self.targets[2] += dd * 5.0
                    self.targets[3] -= dd * 8.0 
                    
                    # 4. 几何姿态补偿 (防抖)
                    # 简单的数值联动：如果肘部伸展了(M3变大)，手腕需要补偿性低头(M4变大)
                    # 这是一个近似线性的关系
                    m3_change = self.targets[3] - 2048
                    # 补偿系数 0.5 需要实测微调
                    linkage_comp = m3_change * 0.5 
                    # 叠加到 M4 上 (注意基准)
                    # 这里不做累加，而是每一帧基于 M3 当前状态计算偏移
                    # (这部分逻辑较复杂，先注释掉，依靠 PID_Y 自动修正即可)
                    # self.targets[4] += linkage_comp 
                    
                else:
                    self.pid_x.reset()
                    self.pid_y.reset()
                    self.pid_dist.reset()
                
                # === 关键：发送前经过安全检查 ===
                self.move_safe(speed=1200)
                
                cv2.imshow('Safety Tracker', annotated)
                if cv2.waitKey(1) == ord('q'): break
                
        except KeyboardInterrupt: pass
        finally: self.close()

    def close(self):
        print("回中...")
        self.targets = {1:2048, 2:2048, 3:2048, 4:2048}
        self.move_safe(speed=400)
        time.sleep(2)
        for i in range(1,5): self.driver.set_torque_enable(i, False)
        self.driver.close()
        self.cap.release()
        cv2.destroyAllWindows()

if __name__ == "__main__":
    tracker = SafeRobotArmTracker()
    tracker.run()

