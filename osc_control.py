from pythonosc import udp_client

class OscChannel:
    def __init__(self, address, initial_value=0.0, smoothing=0.05):
        self.address = address
        self.current_value = float(initial_value)
        self.target_value = float(initial_value)
        self.smoothing = smoothing
        self.last_sent_value = None

    def set_target(self, value):
        self.target_value = float(value)

    def update(self):
        # Simple lerp for smoothing
        # current = current + (target - current) * smoothing
        diff = self.target_value - self.current_value
        if abs(diff) < 0.0001:
            self.current_value = self.target_value
        else:
            self.current_value += diff * self.smoothing
        return self.current_value

class OscController:
    def __init__(self, ip="127.0.0.1", port=7001):
        self.client = udp_client.SimpleUDPClient(ip, port)
        self.channels = {}
        print(f"OSC Controller initialized at {ip}:{port}")

    def add_channel(self, name, address, initial_value=0.0, smoothing=0.05):
        """
        添加一个受控通道
        name: 内部引用名称 (例如 'Bg')
        address: OSC地址 (例如 '/Bg')
        initial_value: 初始值
        smoothing: 平滑系数 (0.0-1.0), 越小越平滑/慢
        """
        self.channels[name] = OscChannel(address, initial_value, smoothing)

    def set_value(self, name, value):
        """设置通道的目标值"""
        if name in self.channels:
            self.channels[name].set_target(value)
        else:
            print(f"Warning: OSC channel '{name}' not found.")

    def update(self):
        """每帧调用，计算平滑值并发送"""
        for name, channel in self.channels.items():
            val = channel.update()
            # 总是发送以保持流的连续性，或者可以优化为只在变化时发送
            # 这里为了平滑过渡效果，只要值在变就发送
            # 如果已经达到目标值且已经发送过，可以减少发送频率（可选）
            
            if channel.last_sent_value is None or abs(val - channel.last_sent_value) > 0.00001:
                try:
                    self.client.send_message(channel.address, val)
                    channel.last_sent_value = val
                except Exception as e:
                    print(f"OSC Send Error: {e}")

    def close(self):
        pass





