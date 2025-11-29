"""
TouchDesigner Python DAT Script - 处理分包的 UDP 数据
解析分包发送的摄像头数据（person_count + 多个 person 对象）
"""

import json

# 获取 udpin1 的所有数据
udp_dat = op("/project1/udpin1")

# 清空当前输出
me.clear()

# 添加表头
me.appendRow([
    "Camera", "Person ID", "Gender", "Age", "Emotion", "Race", 
    "Body Type", "Upper Type", "Lower Type", "Upper Color", 
    "Lower Color", "Keypoints", "Description"
])

# 定义映射字典
gender_map = {0: "Male", 1: "Female"}
emotion_map = {
    0: "Angry", 1: "Disgust", 2: "Fear", 3: "Happy", 
    4: "Sad", 5: "Surprise", 6: "Neutral"
}
race_map = {
    0: "White", 1: "Black", 2: "Asian", 
    3: "Indian", 4: "Latino", 5: "Middle Eastern"
}
body_type_map = {0: "Slim", 1: "Average", 2: "Athletic", 3: "Heavy"}
upper_type_map = {0: "T-shirt", 1: "Shirt", 2: "Long Sleeve"}
lower_type_map = {0: "Long Pants", 1: "Shorts"}

if udp_dat.numRows > 1:  # 至少有表头 + 1 行数据
    try:
        # 收集所有的人物数据
        persons_data = []
        camera_id = 1  # 默认值
        
        # 遍历所有行（跳过表头）
        for i in range(1, udp_dat.numRows):
            row_data = udp_dat[i, 0].val
            
            try:
                data = json.loads(row_data)
                
                # 如果包含 camera_id，更新它
                if "camera_id" in data:
                    camera_id = data["camera_id"]
                
                # 如果包含 person 对象，收集它
                if "person" in data:
                    person = data["person"]
                    persons_data.append(person)
                    
            except json.JSONDecodeError:
                continue
        
        # 现在处理所有收集到的人物数据
        for person in persons_data:
            person_id = person.get("id", "N/A")
            
            # 人脸信息
            face = person.get("face", {})
            gender = gender_map.get(face.get("gender", -1), "Unknown")
            age = face.get("age", "N/A")
            
            # 情绪和种族
            emotion = emotion_map.get(person.get("emotion", -1), "Unknown")
            race = race_map.get(person.get("race", -1), "Unknown")
            
            # 体型
            body_type = body_type_map.get(person.get("body_type", -1), "Unknown")
            
            # 服装信息
            clothing = person.get("clothing", {})
            upper_type = upper_type_map.get(clothing.get("upper_type", -1), "Unknown")
            lower_type = lower_type_map.get(clothing.get("lower_type", -1), "Unknown")
            
            upper_color = clothing.get("upper_color", [0, 0, 0])
            lower_color = clothing.get("lower_color", [0, 0, 0])
            upper_color_str = f"RGB({upper_color[0]}, {upper_color[1]}, {upper_color[2]})"
            lower_color_str = f"RGB({lower_color[0]}, {lower_color[1]}, {lower_color[2]})"
            
            # 关键点数量
            keypoints = person.get("keypoints", [])
            keypoints_count = f"{len(keypoints)} points"
            
            # 自然语言描述
            description = person.get("description", "")
            
            # 添加一行数据
            me.appendRow([
                str(camera_id),
                str(person_id),
                gender,
                str(age),
                emotion,
                race,
                body_type,
                upper_type,
                lower_type,
                upper_color_str,
                lower_color_str,
                keypoints_count,
                description
            ])
        
        # 如果没有找到任何人
        if len(persons_data) == 0:
            me.appendRow(["No Person", "Waiting for person data...", "", "", "", "", "", "", "", "", "", "", ""])
    
    except Exception as e:
        me.appendRow(["Error", str(e), "", "", "", "", "", "", "", "", "", "", ""])
else:
    me.appendRow(["No Data", "Waiting for UDP data...", "", "", "", "", "", "", "", "", "", "", ""])







