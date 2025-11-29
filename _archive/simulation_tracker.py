import sys
import time
import math
import numpy as np
from simple_pid import PID

sys.path.append('sts_control')
from sts_driver import STSServoSerial

# ================= 垂直结构定义 (与 vertical_arm_tracker.py 保持一致) =================
# M2: 减小=后仰, 增大=前倾 (dir=1)
# M3: 减小=伸展, 增大=折叠 (dir=-1) <-- 已修正
# M4: 减小=抬头, 增大=低头 (dir=1)
MOTOR_CALIBRATION = {
    1: {'center': 2048, 'min': 500,  'max': 3500, 'dir': 1,  'name': 'Base'},
    2: {'center': 2048, 'min': 1500, 'max': 3000, 'dir': 1,  'name': 'Shoulder(Bottom)'}, 
    3: {'center': 2048, 'min': 1000, 'max': 3000, 'dir': -1,  'name': 'Elbow(Middle)'},
    4: {'center': 2048, 'min': 1200, 'max': 2900, 'dir': 1,  'name': 'Wrist(Top)'},
}

class SafetyController:
    def check_and_clamp(self, targets):
        safe_targets = targets.copy()
        # 1. 基础软限位
        for mid, val in safe_targets.items():
            cal = MOTOR_CALIBRATION[mid]
            safe_targets[mid] = max(cal['min'], min(cal['max'], int(val)))

        # 2. 防自撞逻辑 (从 vertical_arm_tracker.py 复制)
        t3, t4 = safe_targets[3], safe_targets[4]
        LIMIT_ELBOW_FOLD = 1600  
        LIMIT_WRIST_DOWN = 2100  
        
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
             # 如果 t3 是 2700， severity 就是 (2700 - 2400) / 600 = 0.5
             severity = (t3 - LIMIT_FOLD_HIGH) / 600.0
             
             # 如果 low 限制是 2100，severity 0.5， allowed = 2100 - 250 = 1850
             allowed_wrist = LIMIT_WRIST_DOWN - (severity * 500)
             
             if t4 > allowed_wrist:
                 # 这里只是为了调试方便，真正运行时可以把 print 去掉
                 # print(f"[安全介入] 防撞! M3={t3}, 限制 M4: {t4} -> {int(allowed_wrist)}")
                 safe_targets[4] = int(allowed_wrist)

        return safe_targets

class SimulationTracker:
    def __init__(self, port="COM4"):
        self.driver = STSServoSerial(port, 1000000)
        self.safety = SafetyController()
        
        # 模拟的目标坐标 (归一化 -1.0 到 1.0)
        self.sim_target_x = 0.0
        self.sim_target_y = 0.0
        self.sim_target_dist = 0.0 # >0 近, <0 远
        
        # PID (与主程序一致)
        self.pid_x = PID(Kp=0.15, Ki=0.01, Kd=0.005, output_limits=(-60, 60))
        self.pid_y = PID(Kp=0.20, Ki=0.02, Kd=0.01, output_limits=(-80, 80))
        self.pid_dist = PID(Kp=0.3, Ki=0.05, Kd=0.01, output_limits=(-40, 40))
        
        self.targets = {1: 2048, 2: 2048, 3: 2048, 4: 2048}
        self.init_robot()

    def init_robot(self):
        print("连接并读取当前姿态...")
        for i in range(1, 5):
            pos = self.driver.get_position(i)
            if pos != -1:
                self.targets[i] = pos
            else:
                self.targets[i] = 2048
        
        print("使能电机 (原地锁定)...")
        for i in range(1, 5): 
            self.driver.set_torque_enable(i, True)
            self.driver.set_position(i, self.targets[i], speed=0)
        time.sleep(1)

    def update_simulation(self, t):
        """生成模拟信号：画一个 '8' 字"""
        # X轴：左右摆动 (周期 4秒)
        self.sim_target_x = 0.5 * math.sin(t * 0.5)
        
        # Y轴：上下摆动 (周期 2秒)
        self.sim_target_y = 0.3 * math.cos(t * 1.0)
        
        # 距离：前后呼吸 (周期 8秒)
        self.sim_target_dist = 0.2 * math.sin(t * 0.25)
        
        return self.sim_target_x, self.sim_target_y, self.sim_target_dist

    def run(self):
        print("开始模拟追踪... 按 Ctrl+C 退出")
        start_time = time.time()
        
        try:
            while True:
                t = time.time() - start_time
                
                # 1. 生成模拟目标
                tx, ty, tdist = self.update_simulation(t)
                
                print(f"\r[模拟目标] X:{tx:.2f} Y:{ty:.2f} Dist:{tdist:.2f}", end="")
                
                # 2. PID 计算 (完全复用 vertical_arm_tracker 的逻辑)
                dx = self.pid_x(tx)
                self.targets[1] -= dx 
                
                dy = self.pid_y(ty)
                self.targets[4] += dy 
                
                # 身体跟随逻辑
                m4_offset = self.targets[4] - 2048
                if abs(m4_offset) > 200:
                    follow_speed = m4_offset * 0.05
                    self.targets[2] += follow_speed 
                    self.targets[3] -= follow_speed * 0.5 
                
                # 距离控制
                if abs(tdist) > 0.05:
                    dd = self.pid_dist(tdist)
                    # 垂直结构后退策略 (基于您确认的方向: M2增大前倾, M3增大折叠)
                    # 想要后退(距离近tdist>0) -> M2后仰(减小), M3折叠(增大)
                    self.targets[2] -= dd * 3.0
                    self.targets[3] += dd * 5.0 # 注意这里改成了 += 因为 M3 dir=-1
                    self.targets[4] += dd * 2.0

                # 3. 安全限制
                safe_targets = self.safety.check_and_clamp(self.targets)
                
                # 4. 执行
                for mid, val in safe_targets.items():
                    # speed=0 意味着让舵机全速移动到目标（响应最快）
                    # 但为了看起来平滑，我们也可以给一个固定的大数值，比如 1000
                    self.driver.set_position(mid, val, speed=0)
                
                # 调试信息：每 50 次循环 (约1秒) 打印一次电机目标值
                if int(t * 50) % 50 == 0:
                     print(f"\n   -> Motors: {safe_targets}")

                time.sleep(0.02) # 50Hz
                
        except KeyboardInterrupt:
            pass
        finally:
            print("\n停止模拟...")
            for i in range(1, 5): self.driver.set_torque_enable(i, False)
            self.driver.close()

if __name__ == "__main__":
    sim = SimulationTracker()
    sim.run()

