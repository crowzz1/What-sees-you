"""
示波器用户配置
在这里控制是否启用音频
"""

# ==============================================
# 主开关：是否启用音频反应
# ==============================================

# 设置为 False 完全禁用音频（避免与 VCV Rack 冲突）
# 设置为 True 启用音频反应（需要 VCV Rack 正确配置）
ENABLE_OSCILLOSCOPE_AUDIO = False  # 改为 False 禁用音频

# ==============================================
# 其他设置
# ==============================================

# 示波器大小（像素）
OSCILLOSCOPE_WIDTH = 300
OSCILLOSCOPE_HEIGHT = 300

# 示波器位置 ('bottom-right', 'bottom-left', 'top-right', 'top-left')
OSCILLOSCOPE_POSITION = 'bottom-right'

# 音频设备（None = 自动检测）
AUDIO_DEVICE_INDEX = None  # 或者指定设备号，例如 12

# ==============================================
# 说明
# ==============================================
# 
# 如果 VCV Rack 崩溃：
# 1. 设置 ENABLE_OSCILLOSCOPE_AUDIO = False
# 2. 重启程序
# 3. 示波器会显示人体骨骼，但不响应音频
# 
# 如果要启用音频：
# 1. 确保 VCV Rack 已经在运行
# 2. 设置 ENABLE_OSCILLOSCOPE_AUDIO = True
# 3. 启动本程序
#





