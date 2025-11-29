"""
人体追踪到机械臂控制
将摄像头识别的人体位置映射到机械臂运动
"""

import cv2
import numpy as np
import time
from arm_controller import ArmController


class SmoothFilter:
    """
    平滑滤波器 - 减少抖动
    使用指数移动平均 (EMA)
    """
    
    def __init__(self, alpha=0.3):
        """
        Args:
            alpha: 平滑系数 (0-1)
                  - 0.1: 非常平滑，响应慢
                  - 0.5: 平衡
                  - 0.9: 响应快，但可能抖动
        """
        self.alpha = alpha
        self.last_value = None
    
    def filter(self, value):
        """应用平滑滤波"""
        if self.last_value is None:
            self.last_value = value
            return value
        
        # 指数移动平均
        filtered = self.alpha * value + (1 - self.alpha) * self.last_value
        self.last_value = filtered
        return filtered
    
    def reset(self):
        """重置滤波器"""
        self.last_value = None


class PersonToArmMapper:
    """
    人体位置到机械臂角度的映射器
    """
    
    def __init__(self, frame_width=640, frame_height=480):
        """
        Args:
            frame_width: 摄像头画面宽度
            frame_height: 摄像头画面高度
        """
        self.frame_width = frame_width
        self.frame_height = frame_height
        
        # 平滑滤波器（分别用于x和y）
        self.filter_x = SmoothFilter(alpha=0.3)
        self.filter_y = SmoothFilter(alpha=0.3)
        
        # 映射范围（可调整）
        self.base_angle_range = (-90, 90)    # 基座左右旋转范围
        self.arm_angle_range = (0, 90)       # 大臂上下运动范围
        
        print("=" * 60)
        print("人体追踪映射器")
        print("=" * 60)
        print(f"画面尺寸: {frame_width} x {frame_height}")
        print(f"基座角度范围: {self.base_angle_range}")
        print(f"大臂角度范围: {self.arm_angle_range}")
        print("=" * 60)
    
    def get_person_center(self, person):
        """
        获取人体中心点
        
        Args:
            person: 识别结果 {'bbox': (x1, y1, x2, y2), ...}
        
        Returns:
            (center_x, center_y): 中心点坐标
        """
        bbox = person['bbox']
        x1, y1, x2, y2 = bbox
        
        # 计算边界框中心
        center_x = (x1 + x2) / 2
        center_y = (y1 + y2) / 2
        
        return center_x, center_y
    
    def normalize_position(self, x, y):
        """
        将像素坐标归一化到 [-1, 1]
        
        Args:
            x, y: 像素坐标
        
        Returns:
            (norm_x, norm_y): 归一化坐标
                - norm_x: -1(左) 到 1(右)
                - norm_y: -1(上) 到 1(下)
        """
        norm_x = (x / self.frame_width) * 2 - 1   # -1 到 1
        norm_y = (y / self.frame_height) * 2 - 1  # -1 到 1
        
        return norm_x, norm_y
    
    def map_to_arm_angles(self, norm_x, norm_y):
        """
        将归一化坐标映射到机械臂角度
        
        Args:
            norm_x: 归一化x坐标 (-1 到 1)
            norm_y: 归一化y坐标 (-1 到 1)
        
        Returns:
            (base_angle, arm_angle): 基座和大臂的角度
        """
        # 应用平滑滤波
        smooth_x = self.filter_x.filter(norm_x)
        smooth_y = self.filter_y.filter(norm_y)
        
        # 映射到角度范围
        # X坐标 -> 基座旋转 (-90 到 90)
        base_min, base_max = self.base_angle_range
        base_angle = smooth_x * (base_max - base_min) / 2
        
        # Y坐标 -> 大臂抬升 (0 到 90)
        # y=1(画面下方) -> 0度(水平)
        # y=-1(画面上方) -> 90度(抬起)
        arm_min, arm_max = self.arm_angle_range
        arm_angle = arm_max - ((smooth_y + 1) / 2) * (arm_max - arm_min)
        
        return base_angle, arm_angle
    
    def process_person(self, person):
        """
        处理一个人的位置，返回机械臂角度
        
        Args:
            person: 识别结果
        
        Returns:
            {
                'center': (x, y),
                'normalized': (norm_x, norm_y),
                'angles': {
                    'base': base_angle,
                    'arm1': arm_angle
                }
            }
        """
        # 获取中心点
        center_x, center_y = self.get_person_center(person)
        
        # 归一化
        norm_x, norm_y = self.normalize_position(center_x, center_y)
        
        # 映射到角度
        base_angle, arm_angle = self.map_to_arm_angles(norm_x, norm_y)
        
        return {
            'center': (center_x, center_y),
            'normalized': (norm_x, norm_y),
            'angles': {
                'base': base_angle,
                'arm1': arm_angle,
                'arm2': 0,  # 暂时不用
                'wrist': 0  # 暂时不用
            }
        }


class ArmTracker:
    """
    机械臂追踪系统
    整合：摄像头 -> 人体识别 -> 位置映射 -> 机械臂控制
    """
    
    def __init__(self, arm_port='COM3', camera_id=0, frame_width=640, frame_height=480):
        """
        Args:
            arm_port: ESP32串口端口
            camera_id: 摄像头ID
            frame_width: 画面宽度
            frame_height: 画面高度
        """
        print("\n" + "=" * 60)
        print("机械臂追踪系统初始化")
        print("=" * 60)
        
        # 创建映射器
        self.mapper = PersonToArmMapper(frame_width, frame_height)
        
        # 创建机械臂控制器
        print("\n初始化机械臂控制器...")
        self.arm = ArmController(port=arm_port)
        
        if not self.arm.connected:
            print("✗ 机械臂连接失败")
            return
        
        # 使能电机
        time.sleep(1)
        self.arm.enable_all()
        time.sleep(1)
        
        # 追踪参数
        self.tracking_enabled = False
        self.target_person_id = None  # 追踪特定的人（None = 追踪最近的人）
        self.min_move_threshold = 2.0  # 最小移动阈值（度）
        self.last_angles = {'base': 0, 'arm1': 0}
        
        # 控制速度
        self.move_speed = 80
        
        print("\n✓ 机械臂追踪系统就绪")
        print("=" * 60)
    
    def start_tracking(self):
        """开始追踪"""
        self.tracking_enabled = True
        print("✓ 追踪已启用")
    
    def stop_tracking(self):
        """停止追踪"""
        self.tracking_enabled = False
        self.arm.stop_all()
        print("✓ 追踪已停止")
    
    def select_target_person(self, results):
        """
        选择要追踪的人
        默认选择最近的人（边界框最大的）
        
        Args:
            results: 识别结果列表
        
        Returns:
            选中的人的结果，或None
        """
        if not results:
            return None
        
        # 如果指定了目标ID
        if self.target_person_id is not None:
            for person in results:
                if person.get('person_id') == self.target_person_id:
                    return person
        
        # 否则选择最大的边界框（最近的人）
        largest_person = max(results, key=lambda p: self._bbox_area(p['bbox']))
        return largest_person
    
    def _bbox_area(self, bbox):
        """计算边界框面积"""
        x1, y1, x2, y2 = bbox
        return (x2 - x1) * (y2 - y1)
    
    def should_move(self, new_angles):
        """
        判断是否需要移动（避免微小抖动）
        
        Args:
            new_angles: 新的目标角度
        
        Returns:
            True: 需要移动, False: 不需要移动
        """
        base_diff = abs(new_angles['base'] - self.last_angles['base'])
        arm_diff = abs(new_angles['arm1'] - self.last_angles['arm1'])
        
        return base_diff > self.min_move_threshold or arm_diff > self.min_move_threshold
    
    def update(self, results):
        """
        更新追踪（每帧调用）
        
        Args:
            results: 人体识别结果列表
        
        Returns:
            追踪信息字典
        """
        if not self.tracking_enabled:
            return {'status': 'disabled'}
        
        # 选择目标
        target = self.select_target_person(results)
        
        if target is None:
            # 没有目标，停止电机
            self.arm.stop_all()
            return {'status': 'no_target'}
        
        # 计算目标角度
        tracking_data = self.mapper.process_person(target)
        angles = tracking_data['angles']
        
        # 判断是否需要移动
        if self.should_move(angles):
            # 使用基本的连续旋转控制（暂时不用goto）
            self.arm.move_to_angles(
                base=angles['base'],
                arm1=angles['arm1'],
                speed=self.move_speed
            )
            
            # 更新last_angles
            self.last_angles = {
                'base': angles['base'],
                'arm1': angles['arm1']
            }
            
            tracking_data['status'] = 'tracking'
            tracking_data['moved'] = True
        else:
            # 停止（已经到位）
            self.arm.stop_all()
            tracking_data['status'] = 'tracking'
            tracking_data['moved'] = False
        
        return tracking_data
    
    def close(self):
        """关闭系统"""
        print("\n关闭机械臂追踪系统...")
        self.stop_tracking()
        time.sleep(0.5)
        self.arm.close()
        print("✓ 系统已关闭")


def test_arm_tracker():
    """测试机械臂追踪系统（模拟数据）"""
    print("=" * 60)
    print("测试机械臂追踪系统（模拟数据）")
    print("=" * 60)
    
    # 创建追踪器
    tracker = ArmTracker(arm_port='COM3')  # 修改为你的端口
    
    if not tracker.arm.connected:
        print("无法连接到机械臂")
        return
    
    try:
        # 启动追踪
        tracker.start_tracking()
        
        # 模拟识别结果
        print("\n模拟人体移动...")
        positions = [
            {'bbox': (100, 200, 200, 400)},  # 左侧
            {'bbox': (250, 200, 350, 400)},  # 中间
            {'bbox': (400, 200, 500, 400)},  # 右侧
            {'bbox': (300, 100, 400, 300)},  # 上方
            {'bbox': (300, 300, 400, 500)},  # 下方
        ]
        
        for i, person in enumerate(positions):
            print(f"\n位置 {i+1}:")
            results = [person]
            tracking_data = tracker.update(results)
            print(f"  状态: {tracking_data.get('status')}")
            if 'angles' in tracking_data:
                print(f"  基座: {tracking_data['angles']['base']:.1f}°")
                print(f"  大臂: {tracking_data['angles']['arm1']:.1f}°")
            time.sleep(3)
        
        # 停止追踪
        tracker.stop_tracking()
        
    except KeyboardInterrupt:
        print("\n中断测试")
    finally:
        tracker.close()


if __name__ == "__main__":
    test_arm_tracker()

