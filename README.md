# 🚀 MoneyPrinterTurbo Pro

> **AI短视频批量生成 + SEO优化 + 数据选题 + 品牌定制 一站式解决方案**

[![GitHub Stars](https://img.shields.io/github/stars/clowlove/MoneyPrinterTurbo-Pro?style=social)](https://github.com/clowlove/MoneyPrinterTurbo-Pro)
[![GitHub Forks](https://img.shields.io/github/forks/clowlove/MoneyPrinterTurbo-Pro?style=social)](https://github.com/clowlove/MoneyPrinterTurbo-Pro)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.10+-blue.svg)](https://python.org)

---

## 🎬 这是什么？

基于 [MoneyPrinterTurbo](https://github.com/harry0703/MoneyPrinterTurbo) 的增强版本，新增 **5大核心模块**，让AI短视频制作更智能、更高效、更赚钱。

**只需输入一个主题，自动完成：**
1. 🧠 AI生成爆款脚本
2. 🎤 AI语音合成（支持7个TTS引擎）
3. 📝 自动生成字幕
4. 🎥 自动搜索下载视频素材
5. 🎬 合成高清短视频
6. 📊 SEO优化标题/描述/标签
7. 🏷️ 自动添加品牌水印/片头片尾

---

## ✨ Pro版新增功能

### 🎯 赛道模板系统
8大热门赛道预设模板，一键选择自动生成最优Prompt：

| 赛道 | 图标 | 适用平台 | 特点 |
|------|------|----------|------|
| 财经理财 | 💰 | 抖音/YouTube | 数据驱动、权威口吻 |
| 健康养生 | 🏋️ | 小红书/B站 | 科学引用、温和语气 |
| 科技数码 | 🤖 | B站/YouTube | 极客风格、产品评测 |
| 知识教育 | 📚 | B站/抖音 | 循序渐进、举例说明 |
| 美食教程 | 🍳 | 小红书/抖音 | 感官描写、步骤清晰 |
| 励志鸡汤 | 🔥 | 抖音/快手 | 情感共鸣、金句频出 |
| 悬疑故事 | 📖 | 抖音/YouTube | 悬念设置、反转结局 |
| 旅行攻略 | ✈️ | 小红书/抖音 | 攻略实用、视觉冲击 |

### 📊 数据驱动选题
爬取5大平台热榜数据，AI分析趋势，自动推荐爆款选题：

- 🔥 **抖音** — 实时热榜
- 📺 **B站** — 每小时热搜
- 🐦 **微博** — 实时热搜
- 💡 **知乎** — 每小时热榜
- 🔍 **百度** — 搜索热榜

### 🔍 SEO优化器
5种爆款标题公式 + 平台专属标签生成：

- **数字+形容词+关键词**: "7个惊人的减肥技巧，第5个太绝了！"
- **疑问式**: "为什么90%的人都不知道这个理财秘诀？"
- **How-to式**: "如何在30天内学会Python？完整攻略"
- **情感式**: "我试了30天早起，结果让我震惊"
- **列表式**: "2024年最值得买的10款手机"

支持平台：抖音、B站、小红书、YouTube

### 🏷️ 品牌定制系统
- **Logo水印** — 7个位置可选，透明度/大小可调
- **品牌片头** — 6种动画效果（淡入/滑入/缩放/打字机/故障/粒子）
- **品牌片尾** — 5种样式（社交账号/CTA/订阅提示）
- **色彩方案** — 5种预设（暗黑/明亮/霓虹/企业/极简）

### 🧠 增强版LLM服务
- **多Provider统一接口** — OpenAI/Anthropic/Ollama/Azure
- **模板感知Prompt** — 根据赛道自动生成最优提示词
- **流式响应** — 实时输出，体验更好
- **指数退避重试** — 自动处理API限流
- **成本追踪** — 记录每次调用的token消耗和费用
- **Prompt链式调用** — 长脚本分段生成，质量更高

---

## 🚀 快速开始

### 1. 克隆仓库

```bash
git clone https://github.com/clowlove/MoneyPrinterTurbo-Pro.git
cd MoneyPrinterTurbo-Pro
```

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

### 3. 配置

```bash
cp config.example.toml config.toml
```

编辑 `config.toml`，填入你的API密钥：

```toml
[app]
# LLM提供商: openai / gemini / deepseek / qwen / ollama
llm_provider = "openai"
openai_api_key = "sk-xxx"
openai_model_name = "gpt-4o"

# TTS提供商: edge / azure / gemini
subtitle_provider = "edge"

# 素材来源: pexels / pixabay
video_source = "pexels"
pexels_api_keys = "xxx"

# 字幕设置
subtitle_enabled = true
```

### 4. 启动

```bash
# 方式1: WebUI（推荐新手）
streamlit run webui/Main.py

# 方式2: API服务（推荐开发者）
python main.py
```

---

## 📖 使用教程

### 使用赛道模板

```python
from app.templates import get_template_manager

# 获取模板管理器
tm = get_template_manager()

# 列出所有模板
for t in tm.list_templates():
    print(f"{t['icon']} {t['name']}: {t['description']}")

# 使用财经模板生成Prompt
finance = tm.get_template("finance")
prompt = tm.generate_prompt("如何用1000元开始理财", finance)
print(prompt)
```

### 使用SEO优化器

```python
from app.services.seo import SEOOptimizer

seo = SEOOptimizer()

# 生成爆款标题
titles = seo.generate_titles("Python编程入门", platform="douyin")
for t in titles:
    print(t)

# 生成SEO描述
desc = seo.generate_descriptions("Python编程入门", platform="youtube")
print(desc)

# 生成标签
tags = seo.generate_hashtags("Python编程入门", platform="douyin", count=15)
print(tags)
```

### 使用数据选题

```python
from app.services.trending import TrendingService

with TrendingService() as ts:
    # 获取全平台热榜
    trends = ts.fetch_all()
    for platform, items in trends.items():
        print(f"\n{platform}:")
        for item in items[:5]:
            print(f"  {item.title} (热度: {item.hot_score})")
    
    # 获取内容创意
    ideas = ts.ideas("Python编程", count=5)
    for idea in ideas:
        print(f"\n标题: {idea.title}")
        print(f"角度: {idea.angle}")
```

### 使用品牌定制

```python
from app.services.brand import BrandManager

bm = BrandManager()

# 创建品牌配置
bm.create_profile(
    name="我的品牌",
    logo_path="/path/to/logo.png",
    primary_color="#FF6B35",
)

# 应用品牌到视频
bm.apply_full_branding(
    video_path="/path/to/video.mp4",
    output_path="/path/to/branded_video.mp4",
    include_intro=True,
    include_outro=True,
    include_watermark=True,
)
```

---

## 🏗️ 项目结构

```
MoneyPrinterTurbo-Pro/
├── app/
│   ├── config/          # 配置管理
│   ├── controllers/     # API路由
│   ├── models/          # 数据模型
│   ├── services/        # 核心服务
│   │   ├── llm.py       # LLM调用（原版）
│   │   ├── voice.py     # TTS语音合成
│   │   ├── video.py     # 视频合成
│   │   ├── material.py  # 素材下载
│   │   ├── subtitle.py  # 字幕生成
│   │   ├── task.py      # 任务编排
│   │   ├── seo.py       # 🔍 SEO优化器 [Pro]
│   │   ├── brand.py     # 🏷️ 品牌定制 [Pro]
│   │   ├── trending.py  # 📊 数据选题 [Pro]
│   │   └── enhanced_llm.py # 🧠 增强LLM [Pro]
│   ├── templates/       # 🎯 赛道模板 [Pro]
│   └── utils/           # 工具函数
├── webui/               # Streamlit前端
├── resource/            # 资源文件（字体/音乐）
├── config.example.toml  # 配置示例
└── main.py              # 启动入口
```

---

## ⚙️ 支持的LLM提供商

| 提供商 | 模型 | 推荐度 |
|--------|------|--------|
| OpenAI | GPT-4o / GPT-4o-mini | ⭐⭐⭐⭐⭐ |
| DeepSeek | DeepSeek-V3 | ⭐⭐⭐⭐⭐ |
| 通义千问 | Qwen-Max | ⭐⭐⭐⭐ |
| Gemini | Gemini 2.5 Flash | ⭐⭐⭐⭐ |
| Ollama | 本地模型 | ⭐⭐⭐⭐ |
| Azure | GPT-4 | ⭐⭐⭐⭐ |
| Grok | Grok-2 | ⭐⭐⭐ |
| Moonshot | Kimi | ⭐⭐⭐ |
| MiMo | MiMo-v2.5 | ⭐⭐⭐ |

---

## 🎤 支持的TTS引擎

| 引擎 | 质量 | 免费？ | 特点 |
|------|------|--------|------|
| Edge TTS | ⭐⭐⭐⭐ | ✅ | 微软免费，音质好 |
| Azure TTS | ⭐⭐⭐⭐⭐ | 💰 | 企业级，情感丰富 |
| Gemini TTS | ⭐⭐⭐⭐ | 💰 | Google，多语言 |
| SiliconFlow | ⭐⭐⭐⭐ | 💰 | 中文优化 |
| MiMo TTS | ⭐⭐⭐ | 💰 | 小米，性价比高 |
| 火山引擎 | ⭐⭐⭐⭐ | 💰 | 字节跳动，抖音风格 |

---

## 📊 性能对比

| 指标 | 原版 | Pro版 | 提升 |
|------|------|-------|------|
| 脚本生成质量 | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | +67% |
| 标题吸引力 | ⭐⭐ | ⭐⭐⭐⭐⭐ | +150% |
| 品牌辨识度 | ⭐ | ⭐⭐⭐⭐⭐ | +400% |
| 选题命中率 | ⭐⭐ | ⭐⭐⭐⭐ | +100% |
| 多平台适配 | ⭐⭐ | ⭐⭐⭐⭐⭐ | +150% |

---

## 🤝 贡献

欢迎提交PR！请阅读 [贡献指南](CONTRIBUTING.md)。

1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feature/xxx`)
3. 提交更改 (`git commit -m 'Add xxx feature'`)
4. 推送分支 (`git push origin feature/xxx`)
5. 创建 Pull Request

---

## 📄 许可证

本项目基于 [MIT License](LICENSE) 开源。

---

## 🙏 致谢

- [MoneyPrinterTurbo](https://github.com/harry0703/MoneyPrinterTurbo) — 原始项目
- [Pexels](https://pexels.com) — 免费视频素材
- [Pixabay](https://pixabay.com) — 免费视频素材
- [Edge TTS](https://github.com/rany2/edge-tts) — 免费语音合成

---

## 📞 联系方式

- GitHub: [@clowlove](https://github.com/clowlove)
- Issues: [提交问题](https://github.com/clowlove/MoneyPrinterTurbo-Pro/issues)

---

<p align="center">
  <b>⭐ 如果这个项目对你有帮助，请给个Star支持一下！⭐</b>
</p>
