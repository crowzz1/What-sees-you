# AI描述生成器配置指南

## 功能介绍

系统现在支持使用大模型生成更丰富、更自然的人物描述。

### 对比效果

**简单版本（不使用大模型）：**
> 一位年轻人，身材修长，身着蓝色的T恤 和 黑色的长裤，脸上洋溢着笑容。

**AI增强版本（使用大模型）：**
> 一位神采奕奕的年轻人，身着简约的蓝色T恤配深色牛仔裤，举手投足间流露出自信与活力，脸上挂着温暖的笑容。

## 支持的大模型

### 1. OpenAI GPT (推荐)
- ✅ 模型：`gpt-3.5-turbo` 或 `gpt-4o-mini`
- ✅ 速度快，效果好
- ✅ 价格便宜（gpt-3.5-turbo: $0.0005/1K tokens）
- ✅ 国内可用（需要代理）

### 2. Claude (Anthropic)
- ✅ 模型：`claude-3-haiku-20240307`
- ✅ 速度快，价格便宜
- ✅ 效果优秀

### 3. 本地模型 (规划中)
- 🚧 Llama 2/3
- 🚧 ChatGLM
- 🚧 无需联网

## 快速开始

### 方案1: 使用OpenAI (推荐)

#### 1. 安装依赖
```bash
pip install openai
```

#### 2. 获取API Key
访问 https://platform.openai.com/api-keys
创建一个API密钥

#### 3. 设置环境变量

**Windows (临时):**
```cmd
set OPENAI_API_KEY=sk-your-api-key-here
python main_gallery_view.py
```

**Windows (永久):**
```cmd
setx OPENAI_API_KEY "sk-your-api-key-here"
```

**Linux/Mac:**
```bash
export OPENAI_API_KEY='sk-your-api-key-here'
python main_gallery_view.py
```

或者创建 `.env` 文件：
```
OPENAI_API_KEY=sk-your-api-key-here
```

#### 4. 运行程序
```bash
python main_gallery_view.py
```

程序启动时会显示：
```
✓ OpenAI 描述生成器已启用 (模型: gpt-3.5-turbo)
```

### 方案2: 使用Claude

#### 1. 安装依赖
```bash
pip install anthropic
```

#### 2. 获取API Key
访问 https://console.anthropic.com/
创建API密钥

#### 3. 修改代码
在 `person_analyzer.py` 第264行左右：
```python
# 修改这一行：
self.ai_generator = AIDescriptionGenerator(provider='openai')
# 改为：
self.ai_generator = AIDescriptionGenerator(provider='claude')
```

#### 4. 设置环境变量
```bash
# Windows
set ANTHROPIC_API_KEY=sk-ant-your-api-key-here

# Linux/Mac
export ANTHROPIC_API_KEY='sk-ant-your-api-key-here'
```

### 方案3: 不使用大模型（默认）

如果不设置API key，系统会自动使用增强的简单描述生成器：
- ✅ 不需要网络
- ✅ 完全免费
- ✅ 速度最快
- ✅ 已优化为中文描述

## 配置选项

### 选择模型

在 `person_analyzer.py` 修改初始化代码：

```python
# OpenAI GPT-3.5 (便宜快速)
self.ai_generator = AIDescriptionGenerator(
    provider='openai',
    model='gpt-3.5-turbo'
)

# OpenAI GPT-4 (效果最好但贵)
self.ai_generator = AIDescriptionGenerator(
    provider='openai',
    model='gpt-4o-mini'  # 或 'gpt-4o'
)

# Claude Haiku (快速便宜)
self.ai_generator = AIDescriptionGenerator(
    provider='claude',
    model='claude-3-haiku-20240307'
)

# Claude Sonnet (效果更好)
self.ai_generator = AIDescriptionGenerator(
    provider='claude',
    model='claude-3-5-sonnet-20241022'
)

# 不使用大模型
self.ai_generator = AIDescriptionGenerator(provider='none')
```

### 手动指定API Key

如果不想用环境变量，可以直接在代码中指定：

```python
self.ai_generator = AIDescriptionGenerator(
    provider='openai',
    api_key='sk-your-api-key-here'  # 直接指定
)
```

**⚠️ 注意：不要把API key提交到代码仓库！**

## 价格参考

### OpenAI (按tokens计费)

每次描述大约使用 150 tokens

| 模型 | 输入价格 | 输出价格 | 每次描述成本 |
|------|---------|---------|-------------|
| gpt-3.5-turbo | $0.0005/1K | $0.0015/1K | ~$0.0003 |
| gpt-4o-mini | $0.00015/1K | $0.0006/1K | ~$0.0001 |
| gpt-4o | $0.0025/1K | $0.01/1K | ~$0.002 |

**示例：**
- 1000次描述 (gpt-3.5-turbo) ≈ $0.30 (约2元)
- 1000次描述 (gpt-4o-mini) ≈ $0.10 (约0.7元)

### Claude (按tokens计费)

| 模型 | 输入价格 | 输出价格 | 每次描述成本 |
|------|---------|---------|-------------|
| claude-3-haiku | $0.00025/1K | $0.00125/1K | ~$0.00015 |
| claude-3.5-sonnet | $0.003/1K | $0.015/1K | ~$0.0025 |

## 性能影响

### 延迟对比

| 模式 | 每次描述耗时 | FPS影响 |
|------|-------------|---------|
| 不使用大模型 | <1ms | 无 |
| OpenAI API | 200-500ms | -2~5 FPS |
| Claude API | 200-400ms | -2~5 FPS |

**优化建议：**
- 描述生成是异步的，不会阻塞主线程
- 只在新检测到人物时生成，不是每帧都生成
- 可以缓存描述结果

## 测试AI描述生成器

独立测试脚本：

```bash
python ai_description_generator.py
```

测试输出：
```
简单描述:
一位年轻人，身材修长，身着蓝色的T恤 和 黑色的长裤，脸上洋溢着笑容。

AI描述:
一位神采奕奕的年轻人，身着简约的蓝色T恤配深色牛仔裤，举手投足间流露出自信与活力，脸上挂着温暖的笑容。
```

## 常见问题

### Q: 启动时没有看到"OpenAI 描述生成器已启用"？
A: 检查：
1. 是否安装了 `openai` 库
2. 是否设置了 `OPENAI_API_KEY` 环境变量
3. API key 是否正确

### Q: 描述还是很简单？
A: 确认：
1. 控制台显示 "✓ OpenAI 描述生成器已启用"
2. 检查网络连接（需要能访问OpenAI API）
3. 查看控制台是否有错误信息

### Q: 报错 "Rate limit exceeded"？
A: OpenAI API有速率限制：
- 免费账号：3 RPM (每分钟3次请求)
- 付费账号：更高限制
- 解决：降低描述生成频率

### Q: 报错 "Connection timeout"？
A: 网络问题：
- 确保能访问OpenAI API
- 国内可能需要代理
- 可以切换到 Claude 或不使用大模型

### Q: 想用其他语言？
A: 修改 `ai_description_generator.py` 中的system prompt：
```python
{"role": "system", "content": "You are a professional character describer. Respond in English."}
```

### Q: 能自定义描述风格吗？
A: 可以！修改 `_build_prompt()` 中的提示词，例如：
```python
prompt = f"""请用诗意的语言描述这个人，
像一首优美的诗歌...
```

## 进阶配置

### 缓存描述结果

为了避免重复调用API，可以缓存：

```python
# 在 CompletePersonFaceAnalyzer 添加
self.description_cache = {}  # person_id: description

# 在生成描述时
person_id = result.get('person_id')
if person_id not in self.description_cache:
    desc = self.generate_person_description(result)
    self.description_cache[person_id] = desc
else:
    desc = self.description_cache[person_id]
```

### 降低API调用频率

只在新人物出现时生成：

```python
# 检测新人物
if person_id not in self.seen_persons:
    # 生成描述
    desc = self.generate_person_description(result)
    self.seen_persons.add(person_id)
```

## 未来计划

- [ ] 支持本地大模型（Llama, ChatGLM）
- [ ] 异步API调用（不阻塞主线程）
- [ ] 描述缓存机制
- [ ] 批量生成（一次请求多个描述）
- [ ] 自定义描述风格模板
- [ ] 支持更多大模型平台

---

**版本**: 1.0  
**最后更新**: 2025-11-27  
**维护者**: AI Assistant






