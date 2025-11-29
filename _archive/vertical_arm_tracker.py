import cv2
import sys
import time
import numpy as np
from simple_pid import PID

sys.path.append('sts_control')
from sts_driver import STSServoSerial
from ultralytics import YOLO

# ================= 垂直结构定义 =================
# 假设 2048 为垂直中位（机械臂像旗杆一样笔直向上）
# 请根据实际情况调整 dir (1 或 -1)
# 这里的配置假设：
# M2: 减小=后仰, 增大=前倾 (0-4095)
# M3: 减小=向后折叠, 增大=向前伸展
# M4: 减小=抬头, 增大=低头
MOTOR_CALIBRATION = {
    1: {'center': 2048, 'min': 500,  'max': 3500, 'dir': 1,  'name': 'Base'},
    2: {'center': 2048, 'min': 1500, 'max': 3000, 'dir': 1,  'name': 'Shoulder(Bottom)'}, 
    3: {'center': 2048, 'min': 1000, 'max': 3000, 'dir': -1,  'name': 'Elbow(Middle)'},
    4: {'center': 2048, 'min': 1200, 'max': 2900, 'dir': 1,  'name': 'Wrist(Top)'},
}

class SafetyController:
    def check_and_clamp(self, targets):
        """
        针对【垂直串联结构】的防碰撞逻辑
        """
        safe_targets = targets.copy()

        # 1. 基础软限位
        for mid, val in safe_targets.items():
            cal = MOTOR_CALIBRATION[mid]
            safe_targets[mid] = max(cal['min'], min(cal['max'], int(val)))

        # 获取当前规划值
        t2 = safe_targets[2]
        t3 = safe_targets[3]
        t4 = safe_targets[4]

        # === 2. 防自撞逻辑 (Self-Collision) ===
        # 场景：M2前倾 + M3后折 + M4低头 = 摄像头撞肚子
        # 假设：M3 < 1600 是向后严重折叠，M4 > 2200 是大幅度低头
        
        # 注意：M3 dir=-1，所以数值越大越折叠，数值越小越伸展
        # 之前的逻辑是 t3 < 1600 (小数值危险)，现在反过来了吗？
        # 根据之前的测试：M3数值增大是“后退/折叠”。
        # 所以现在的逻辑应该是：如果 M3 很大 (折叠)，M4 不能太大 (低头)。
        
        # 让我们重新校准这个逻辑：
        # 假设 2048 是直的。
        # 想要折叠，M3 变大 (例如 2500)。
        # 所以如果 t3 > 2400 (严重折叠)，t4 不能 > 2100 (低头)。
        
        LIMIT_FOLD_HIGH = 2400
        if t3 > LIMIT_FOLD_HIGH:
             severity = (t3 - LIMIT_FOLD_HIGH) / 500.0
             allowed_wrist = LIMIT_WRIST_DOWN - (severity * 500)
             if t4 > allowed_wrist:
                 # print(f"[安全介入] 防撞! M3={t3}, 限制 M4: {t4} -> {int(allowed_wrist)}")
                 safe_targets[4] = int(allowed_wrist)

        return safe_targets

        # === 3. 防完全垂直死点 (Singularity) ===
        # 防止 M2 和 M3 同时处于 2048 (笔直)，PID 可能会在平衡点震荡
        # 强制给一点点微小的偏置，让它保持 "弓" 形
        if abs(t2 - 2048) < 20 and abs(t3 - 2048) < 20:
             # 如果太直了，强制弯曲一点点肘部
             safe_targets[3] = 2080 

        # === 4. 地面/桌面保护 ===
        # 如果 M2 大幅度前倾 (例如 > 2800)，M3 又大幅度前伸 (> 2500)
        # 可能会撞到桌子。简单限制 M2 的最大前倾角。
        MAX_LEAN_FORWARD = 2900
        if t2 > MAX_LEAN_FORWARD:
            safe_targets[2] = MAX_LEAN_FORWARD

        return safe_targets

class VerticalArmTracker:
    def __init__(self, port="COM4"):
        self.driver = STSServoSerial(port, 1000000)
        self.safety = SafetyController()
        
        self.cap = cv2.VideoCapture(0)
        self.model = YOLO('yolov8n-pose.pt')
        
        # === PID 参数调整 (针对垂直重力) ===
        # M1 (水平): 惯性一般
        self.pid_x = PID(Kp=0.15, Ki=0.01, Kd=0.005, output_limits=(-60, 60))
        
        # M4 (手腕): 响应最快，负责修正视野
        self.pid_y = PID(Kp=0.20, Ki=0.02, Kd=0.01, output_limits=(-80, 80))
        
        # M2 (肩部-最底下): 承受最大力矩，需要较大的 Ki 来对抗重力
        # 当手臂前伸时，重力会把它往下拉，Ki 会自动增加输出把它"提"住
        self.pid_dist = PID(Kp=0.3, Ki=0.05, Kd=0.01, output_limits=(-40, 40))
        
        # 初始姿态：读取当前位置，而不是强制归零
        self.targets = {1: 2048, 2: 2048, 3: 2048, 4: 2048}
        self.init_robot()

    def init_robot(self):
        print("连接并读取当前姿态...")
        # 1. 读取当前实际位置作为起始点，防止上电猛冲
        for i in range(1, 5):
            pos = self.driver.get_position(i)
            if pos != -1:
                self.targets[i] = pos
                print(f"电机 {i} 初始位置: {pos}")
            else:
                print(f"警告: 无法读取电机 {i}，使用默认值 2048")
                self.targets[i] = 2048
        
        # 2. 使能电机 (原地锁定)
        print("使能电机...")
        for i in range(1, 5): 
            self.driver.set_torque_enable(i, True)
            # 立即发送当前位置，确保锁死在原地
            self.driver.set_position(i, self.targets[i], speed=0)
            
        time.sleep(1)
        
        # 3. 缓慢移动到垂直状态 (可选，如果不需要可以注释掉)
        # print("缓慢立起...")
        # target_pose = {1:2048, 2:2048, 3:2048, 4:2048}
        # for mid, target in target_pose.items():
        #    self.driver.set_position(mid, target, speed=200)
        #    self.targets[mid] = target
        # time.sleep(2)

    def run(self):
        try:
            while True:
                ret, frame = self.cap.read()
                if not ret: break
                frame = cv2.flip(frame, 1)
                h, w = frame.shape[:2]
                
                results = self.model(frame, verbose=False)
                annotated = results[0].plot()
                
                # 获取人脸中心
                target_x, target_y, size_err = None, None, None
                
                if results[0].keypoints and len(results[0].keypoints) > 0:
                    kp = results[0].keypoints.data[0].cpu().numpy()
                    nose = kp[0]
                    if nose[2] > 0.5:
                        target_x = (nose[0] - w/2) / (w/2)
                        target_y = (nose[1] - h/2) / (h/2)
                        
                        # 距离估算
                        shoulders = [kp[5], kp[6]]
                        if shoulders[0][2] > 0.5:
                            width = abs(shoulders[0][0] - shoulders[1][0])
                            # 目标是让人脸保持一定大小，size_err > 0 表示太近
                            size_err = (width/w - 0.20) * 10

                if target_x is not None:
                    # 1. 水平旋转
                    dx = self.pid_x(target_x)
                    self.targets[1] -= dx # 视电机方向可能需要改为 +=
                    
                    # 2. 垂直追踪 (眼球先行)
                    dy = self.pid_y(target_y)
                    self.targets[4] += dy # M4 快速调整视角
                    
                    # 3. 身体跟随 (Body Follows Eyes)
                    # 如果手腕(M4)为了看下面(>2048)弯得太厉害
                    # 让肩膀(M2)前倾一点，肘部(M3)配合，把手腕解放回来
                    m4_offset = self.targets[4] - 2048
                    
                    if abs(m4_offset) > 300: # 死区
                        follow_speed = m4_offset * 0.05
                        self.targets[2] += follow_speed # 肩膀同向运动
                        self.targets[3] -= follow_speed * 0.5 # 肘部反向一点维持平衡
                    
                    # 4. 距离控制 (伸缩)
                    # size_err > 0 (太近) -> 需要后退 -> M2后仰(减小), M3收缩(减小)
                    if size_err is not None:
                        dd = self.pid_dist(size_err)
                        # 垂直结构后退策略：
                        # M2 减小 (往后仰)
                        # M3 减小 (折叠)
                        self.targets[2] -= dd * 3.0
                        self.targets[3] -= dd * 5.0
                        
                        # 姿态补偿：身体后仰时，手腕要低头才能保持盯着人
                        self.targets[4] += dd * 2.0

                else:
                    # 丢失目标：缓慢复位到 "稍息" 姿态
                    # 不要完全垂直(2048)，稍微前倾一点点比较自然
                    target_rest = {1:2048, 2:2100, 3:2000, 4:2048}
                    for m in [1,2,3,4]:
                        err = target_rest[m] - self.targets[m]
                        self.targets[m] += err * 0.05 # 惯性归位
                    
                    self.pid_x.reset()
                    self.pid_y.reset()
                    self.pid_dist.reset()

                # === 安全过滤与执行 ===
                safe_targets = self.safety.check_and_clamp(self.targets)
                
                # 写入电机 (速度动态调整)
                for mid, val in safe_targets.items():
                    # M2 承重大，速度给慢点；M4 承重小，速度给快点
                    spd = 1500 if mid == 4 else 800
                    self.driver.set_position(mid, val, speed=spd)
                
                cv2.imshow('Vertical Arm Tracker', annotated)
                if cv2.waitKey(1) == ord('q'): break
                
        except KeyboardInterrupt: pass
        finally:
            # 退出时，缓慢回到垂直状态
            print("复位...")
            self.driver.set_position(2, 2048, speed=200)
            time.sleep(2)
            for i in range(1,5): self.driver.set_torque_enable(i, False)
            self.driver.close()
            self.cap.release()
            cv2.destroyAllWindows()

if __name__ == "__main__":
    app = VerticalArmTracker()
    app.run()

