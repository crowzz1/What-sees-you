"""
TouchDesigner Script CHOP Callbacks (只处理最新数据)
只显示当前帧检测到的人，不会累积历史数据
"""

import json

def safe_float(value, default=0.0):
    """安全地转换为 float，如果是 None 返回默认值"""
    if value is None:
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default

def safe_get(dict_obj, key, default=0):
    """安全地从字典获取值"""
    value = dict_obj.get(key, default)
    return value if value is not None else default

def onCook(scriptOp):
    """
    每次 CHOP 需要更新时调用
    """
    # 清除现有通道
    scriptOp.clear()
    
    # 获取 UDP 数据
    try:
        udp_dat = op('/project1/udpin1')
    except:
        scriptOp.numSamples = 1
        c = scriptOp.appendChan('error')
        c[0] = -1
        return
    
    # 初始化
    person_count = 0
    persons_data = []
    latest_timestamp = 0
    
    # 解析 UDP 数据 - 找到最新的时间戳和对应的数据
    if udp_dat.numRows > 1:
        try:
            # 第一遍：找到最新的 timestamp
            for i in range(1, udp_dat.numRows):
                row_data = udp_dat[i, 0].val
                try:
                    data = json.loads(row_data)
                    if "timestamp" in data:
                        ts = data["timestamp"]
                        if ts > latest_timestamp:
                            latest_timestamp = ts
                except:
                    pass
            
            # 第二遍：只收集最新时间戳的数据
            for i in range(1, udp_dat.numRows):
                row_data = udp_dat[i, 0].val
                try:
                    data = json.loads(row_data)
                    
                    # 检查是否是最新数据（时间戳匹配，或者没有时间戳字段）
                    data_timestamp = data.get("timestamp", latest_timestamp)
                    
                    # 只处理最新的数据（允许 0.1 秒的误差）
                    if abs(data_timestamp - latest_timestamp) < 0.1:
                        if "person_count" in data:
                            person_count = safe_get(data, "person_count", 0)
                        if "person" in data:
                            person = data["person"]
                            # 检查这个人是否已经在列表中（避免重复）
                            person_id = person.get("id", -1)
                            if not any(p.get("id") == person_id for p in persons_data):
                                persons_data.append(person)
                except:
                    pass
        except:
            pass
    
    # 如果没有找到有效的人数，使用实际收集到的人数
    if person_count == 0 and len(persons_data) > 0:
        person_count = len(persons_data)
    
    # 设置样本数
    scriptOp.numSamples = 1
    
    # 添加人数通道
    c = scriptOp.appendChan('person_count')
    c[0] = person_count
    
    # 添加实际人数通道（实际检测到的）
    c = scriptOp.appendChan('persons_detected')
    c[0] = len(persons_data)
    
    # 为每个人创建通道
    for idx, person in enumerate(persons_data):
        person_num = idx + 1
        prefix = f'p{person_num}_'
        
        try:
            # 人物 ID
            person_id = safe_float(safe_get(person, 'id', idx + 1))
            c = scriptOp.appendChan(f'{prefix}id')
            c[0] = person_id
            
            # 年龄
            face = person.get('face', {})
            age = safe_float(safe_get(face, 'age', 0))
            c = scriptOp.appendChan(f'{prefix}age')
            c[0] = age
            
            # 年龄归一化 (0-1)
            age_norm = safe_float(safe_get(face, 'age_normalized', age / 100.0))
            c = scriptOp.appendChan(f'{prefix}age_norm')
            c[0] = age_norm
            
            # 情绪 (0-6)
            emotion = safe_float(safe_get(person, 'emotion', -1))
            c = scriptOp.appendChan(f'{prefix}emotion')
            c[0] = emotion
            
            # 情绪置信度
            emotion_conf = safe_float(safe_get(person, 'emotion_conf', 0))
            c = scriptOp.appendChan(f'{prefix}emotion_conf')
            c[0] = emotion_conf
            
            # 体型 (0-3)
            body_type = safe_float(safe_get(person, 'body_type', -1))
            c = scriptOp.appendChan(f'{prefix}body_type')
            c[0] = body_type
            
            # 位置（bbox 中心）
            bbox = person.get('bbox', {})
            x1 = safe_float(safe_get(bbox, 'x1', 0))
            y1 = safe_float(safe_get(bbox, 'y1', 0))
            x2 = safe_float(safe_get(bbox, 'x2', 0))
            y2 = safe_float(safe_get(bbox, 'y2', 0))
            
            center_x = (x1 + x2) / 2.0
            center_y = (y1 + y2) / 2.0
            width = x2 - x1
            height = y2 - y1
            
            c = scriptOp.appendChan(f'{prefix}pos_x')
            c[0] = center_x
            c = scriptOp.appendChan(f'{prefix}pos_y')
            c[0] = center_y
            c = scriptOp.appendChan(f'{prefix}width')
            c[0] = width
            c = scriptOp.appendChan(f'{prefix}height')
            c[0] = height
            
            # 服装颜色（归一化到 0-1）
            clothing = person.get('clothing', {})
            upper_color = clothing.get('upper_color', [0, 0, 0])
            lower_color = clothing.get('lower_color', [0, 0, 0])
            
            # 确保颜色值有效
            if upper_color is None or len(upper_color) < 3:
                upper_color = [0, 0, 0]
            if lower_color is None or len(lower_color) < 3:
                lower_color = [0, 0, 0]
            
            c = scriptOp.appendChan(f'{prefix}upper_r')
            c[0] = safe_float(upper_color[0]) / 255.0
            c = scriptOp.appendChan(f'{prefix}upper_g')
            c[0] = safe_float(upper_color[1]) / 255.0
            c = scriptOp.appendChan(f'{prefix}upper_b')
            c[0] = safe_float(upper_color[2]) / 255.0
            
            c = scriptOp.appendChan(f'{prefix}lower_r')
            c[0] = safe_float(lower_color[0]) / 255.0
            c = scriptOp.appendChan(f'{prefix}lower_g')
            c[0] = safe_float(lower_color[1]) / 255.0
            c = scriptOp.appendChan(f'{prefix}lower_b')
            c[0] = safe_float(lower_color[2]) / 255.0
            
            # 服装类型
            upper_type = safe_float(safe_get(clothing, 'upper_type', -1))
            lower_type = safe_float(safe_get(clothing, 'lower_type', -1))
            c = scriptOp.appendChan(f'{prefix}upper_type')
            c[0] = upper_type
            c = scriptOp.appendChan(f'{prefix}lower_type')
            c[0] = lower_type
            
            # 关键点数量
            keypoints = person.get('keypoints', [])
            keypoint_count = len(keypoints) if keypoints else 0
            c = scriptOp.appendChan(f'{prefix}keypoint_count')
            c[0] = keypoint_count
            
        except Exception as e:
            # 如果某个人的数据处理失败，跳过继续处理下一个
            c = scriptOp.appendChan(f'{prefix}error')
            c[0] = -1
            continue
    
    return

def onSetupParameters(scriptOp):
    return

def onPulse(par):
    return



