"""
AI描述生成器 - 使用大模型生成更丰富的人物描述
支持：OpenAI API, Claude API, 本地模型
"""

import os
from typing import Dict, Optional

# 尝试导入OpenAI
try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    print("OpenAI not installed. Install with: pip install openai")

# 尝试导入Anthropic (Claude)
try:
    import anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False

class AIDescriptionGenerator:
    """使用大模型生成丰富的人物描述"""
    
    def __init__(self, provider='openai', api_key=None, model=None):
        """
        初始化AI描述生成器
        
        Args:
            provider: 'openai', 'claude', 'local' 或 'none'
            api_key: API密钥（如果需要）
            model: 模型名称
        """
        self.provider = provider
        self.enabled = False
        
        if provider == 'openai' and OPENAI_AVAILABLE:
            self.api_key = api_key or os.getenv('OPENAI_API_KEY')
            if self.api_key:
                self.client = OpenAI(api_key=self.api_key)
                self.model = model or 'gpt-3.5-turbo'  # 或 'gpt-4o-mini' 更便宜
                self.enabled = True
                print(f"✓ OpenAI 描述生成器已启用 (模型: {self.model})")
            else:
                print("⚠ OpenAI API key未设置")
        
        elif provider == 'claude' and ANTHROPIC_AVAILABLE:
            self.api_key = api_key or os.getenv('ANTHROPIC_API_KEY')
            if self.api_key:
                self.client = anthropic.Anthropic(api_key=self.api_key)
                self.model = model or 'claude-3-haiku-20240307'  # 最便宜快速的版本
                self.enabled = True
                print(f"✓ Claude 描述生成器已启用 (模型: {self.model})")
            else:
                print("⚠ Claude API key未设置")
        
        else:
            print("✓ 使用简单描述生成器（不使用大模型）")
    
    def generate_description(self, person_data: Dict) -> str:
        """
        生成人物描述
        
        Args:
            person_data: 包含人物属性的字典
                - age: 年龄
                - emotion: 情绪
                - body_type: 体型
                - clothing: 服装信息
                - person_id: 人物ID
        
        Returns:
            描述文本
        """
        if not self.enabled:
            return self._generate_simple_description(person_data)
        
        try:
            # 构建提示词
            prompt = self._build_prompt(person_data)
            
            if self.provider == 'openai':
                return self._generate_with_openai(prompt)
            elif self.provider == 'claude':
                return self._generate_with_claude(prompt)
            else:
                return self._generate_simple_description(person_data)
        
        except Exception as e:
            print(f"AI描述生成失败: {e}")
            return self._generate_simple_description(person_data)
    
    def _build_prompt(self, person_data: Dict) -> str:
        """构建提示词"""
        # 提取属性
        age = person_data.get('age', 'unknown')
        emotion = person_data.get('emotion', 'neutral')
        body_type = person_data.get('body_type', {})
        build = body_type.get('build', 'average') if body_type else 'average'
        clothing = person_data.get('clothing', {})
        
        # 服装信息
        clothing_type = clothing.get('type', {})
        upper_type = clothing_type.get('upper', 'top') if clothing_type else 'top'
        lower_type = clothing_type.get('lower', 'bottom') if clothing_type else 'bottom'
        upper_color = clothing.get('upper_color', '')
        lower_color = clothing.get('lower_color', '')
        
        prompt = f"""请用一到两句话描述这个人，要求：
1. 自然流畅，像在讲故事
2. 使用生动的形容词和比喻
3. 不要生硬地罗列属性
4. 突出特点，营造画面感

人物属性：
- 年龄：{age}岁
- 情绪：{emotion}
- 体型：{build}
- 上衣：{upper_type}，颜色{upper_color}
- 下装：{lower_type}，颜色{lower_color}

示例（不要照搬）：
"一位神采奕奕的年轻人，身着简约的灰色T恤和深色牛仔裤，脸上洋溢着自信的微笑。"
"这位中年男士穿着一身朴素的黑色衬衫，沉稳的神情中透露出岁月的智慧。"

请生成描述（只要描述文本，不要其他内容）："""
        
        return prompt
    
    def _generate_with_openai(self, prompt: str) -> str:
        """使用OpenAI生成"""
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": "你是一个专业的人物描述作家，擅长用优美的语言描述人物的外貌和气质。用中文回答。"},
                {"role": "user", "content": prompt}
            ],
            max_tokens=150,
            temperature=0.8  # 提高创造性
        )
        return response.choices[0].message.content.strip()
    
    def _generate_with_claude(self, prompt: str) -> str:
        """使用Claude生成"""
        message = self.client.messages.create(
            model=self.model,
            max_tokens=150,
            temperature=0.8,
            system="你是一个专业的人物描述作家，擅长用优美的语言描述人物的外貌和气质。用中文回答。",
            messages=[
                {"role": "user", "content": prompt}
            ]
        )
        return message.content[0].text.strip()
    
    def _generate_simple_description(self, person_data: Dict) -> str:
        """简单描述生成器（不使用大模型）- 增强版"""
        parts = []
        
        # 年龄描述
        age = person_data.get('age')
        if age:
            if age < 18:
                age_desc = "一位充满朝气的少年"
            elif age < 30:
                age_desc = "一位年轻人"
            elif age < 45:
                age_desc = "一位成熟稳重的中年人"
            else:
                age_desc = "一位气质优雅的长者"
            parts.append(age_desc)
        else:
            parts.append("一个人")
        
        # 体型描述
        body_type = person_data.get('body_type', {})
        if body_type:
            build = body_type.get('build', '')
            if build == 'Slim':
                parts.append("身材修长")
            elif build == 'Athletic':
                parts.append("体格健硕")
            elif build == 'Stocky':
                parts.append("体格壮实")
        
        # 服装描述
        clothing = person_data.get('clothing', {})
        if clothing:
            clothing_parts = []
            clothing_type = clothing.get('type', {})
            
            if clothing_type:
                upper_type = clothing_type.get('upper', '')
                upper_color = clothing.get('upper_color', '')
                lower_type = clothing_type.get('lower', '')
                lower_color = clothing.get('lower_color', '')
                
                if upper_type and upper_color:
                    upper_desc = f"{self._color_adj(upper_color)}的{self._clothing_name(upper_type)}"
                    clothing_parts.append(upper_desc)
                
                if lower_type and lower_color:
                    lower_desc = f"{self._color_adj(lower_color)}的{self._clothing_name(lower_type)}"
                    clothing_parts.append(lower_desc)
            
            if clothing_parts:
                parts.append(f"身着{' 和 '.join(clothing_parts)}")
        
        # 情绪描述
        emotion = person_data.get('emotion', '')
        if emotion:
            emotion_desc = self._emotion_desc(emotion)
            if emotion_desc:
                parts.append(emotion_desc)
        
        # 组合成句子
        if len(parts) == 0:
            return "检测到一个人。"
        elif len(parts) == 1:
            return parts[0] + "。"
        elif len(parts) == 2:
            return f"{parts[0]}，{parts[1]}。"
        else:
            return f"{parts[0]}，{parts[1]}，{parts[2]}。"
    
    def _color_adj(self, color: str) -> str:
        """颜色形容词"""
        color_map = {
            'Black': '黑色',
            'White': '白色',
            'Gray': '灰色',
            'Red': '红色',
            'Blue': '蓝色',
            'Green': '绿色',
            'Yellow': '黄色',
            'Mixed': '彩色'
        }
        return color_map.get(color, color.lower())
    
    def _clothing_name(self, clothing: str) -> str:
        """服装名称"""
        clothing_map = {
            'T-shirt': 'T恤',
            'Shirt': '衬衫',
            'Top': '上衣',
            'Dress': '连衣裙',
            'Pants': '长裤',
            'Shorts': '短裤',
            'Bottom': '下装'
        }
        return clothing_map.get(clothing, clothing.lower())
    
    def _emotion_desc(self, emotion: str) -> str:
        """情绪描述"""
        emotion_map = {
            'happy': '脸上洋溢着笑容',
            'sad': '神情略显忧郁',
            'angry': '面带怒容',
            'surprise': '表情惊讶',
            'fear': '神色紧张',
            'disgust': '面露不悦',
            'neutral': '神情平静'
        }
        return emotion_map.get(emotion.lower(), '')


# 全局单例
_generator = None

def get_ai_generator(provider='none', api_key=None, model=None):
    """获取AI描述生成器单例"""
    global _generator
    if _generator is None:
        _generator = AIDescriptionGenerator(provider, api_key, model)
    return _generator

def generate_ai_description(person_data: Dict) -> str:
    """便捷函数：生成AI描述"""
    generator = get_ai_generator()
    return generator.generate_description(person_data)


if __name__ == "__main__":
    # 测试
    test_data = {
        'age': 25,
        'emotion': 'happy',
        'body_type': {'build': 'Slim', 'shape': 'Rectangle'},
        'clothing': {
            'type': {'upper': 'T-shirt', 'lower': 'Pants'},
            'upper_color': 'Blue',
            'lower_color': 'Black'
        }
    }
    
    # 测试简单版本
    generator = AIDescriptionGenerator(provider='none')
    desc = generator.generate_description(test_data)
    print("简单描述:")
    print(desc)
    print()
    
    # 测试OpenAI版本（如果有API key）
    if os.getenv('OPENAI_API_KEY'):
        generator_ai = AIDescriptionGenerator(provider='openai')
        desc_ai = generator_ai.generate_description(test_data)
        print("AI描述:")
        print(desc_ai)






