import os
import sys
import webbrowser
from uuid import UUID, uuid4

import streamlit as st
from loguru import logger

# Add the root directory of the project to the system path to allow importing modules from the project
root_dir = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
if root_dir not in sys.path:
    sys.path.append(root_dir)
    print("******** sys.path ********")
    print(sys.path)
    print("")

from app.config import config
from app.models.schema import (
    MaterialInfo,
    VideoAspect,
    VideoConcatMode,
    VideoParams,
    VideoTransitionMode,
)
from app.services import llm, voice
from app.services import task as tm
from app.templates import get_template_manager
from app.services.trending import TrendingService
from app.utils import utils

# 赛道自动匹配关键词映射
TEMPLATE_KEYWORDS = {
    "finance": ["理财", "投资", "股票", "基金", "经济", "财富", "钱", "赚钱", "省钱",
                "保险", "房产", "财经", "金融", "美元", "比特币", "黄金", "消费", "收入", "工资", "物价"],
    "health": ["健康", "养生", "健身", "运动", "减肥", "饮食", "睡眠", "中医", "身体",
               "医疗", "药", "瑜伽", "跑步", "营养", "保健", "湿气", "体质", "免疫力"],
    "tech": ["科技", "数码", "手机", "电脑", "AI", "人工智能", "软件", "编程", "互联网",
             "游戏", "芯片", "机器人", "5G", "应用", "APP", "数据", "算法", "自动驾驶"],
    "education": ["教育", "学习", "考试", "知识", "科普", "学校", "大学", "高考",
                  "英语", "读书", "阅读", "留学", "考研", "育儿", "培训"],
    "food": ["美食", "菜谱", "做饭", "烹饪", "食材", "餐厅", "零食", "饮料", "咖啡",
             "茶", "烘焙", "早餐", "晚餐", "小吃", "端午", "粽子"],
    "motivation": ["励志", "成功", "人生", "心态", "成长", "坚持", "奋斗", "自律",
                   "改变", "梦想", "勇气", "自信", "逆境", "努力"],
    "story": ["故事", "悬疑", "真相", "揭秘", "恐怖", "小说", "案件", "秘密",
              "经历", "遭遇", "传闻", "内幕", "反转"],
    "travel": ["旅游", "旅行", "攻略", "景点", "酒店", "机票", "签证", "出行",
               "自驾", "度假", "探险", "民宿", "打卡"],
}


def auto_match_template(topic: str) -> str | None:
    """根据话题关键词自动匹配最佳赛道"""
    topic_lower = topic.lower()
    scores = {}
    for tmpl_id, keywords in TEMPLATE_KEYWORDS.items():
        score = sum(1 for kw in keywords if kw in topic)
        if score > 0:
            scores[tmpl_id] = score
    if not scores:
        return None
    return max(scores, key=scores.get)

st.set_page_config(
    page_title="MoneyPrinterTurbo",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="auto",
    menu_items={
        "Report a bug": "https://github.com/harry0703/MoneyPrinterTurbo/issues",
        "About": "# MoneyPrinterTurbo\nSimply provide a topic or keyword for a video, and it will "
        "automatically generate the video copy, video materials, video subtitles, "
        "and video background music before synthesizing a high-definition short "
        "video.\n\nhttps://github.com/harry0703/MoneyPrinterTurbo",
    },
)


streamlit_style = """
<style>
h1 {
    padding-top: 0 !important;
}
</style>
"""
st.markdown(streamlit_style, unsafe_allow_html=True)

# 定义资源目录
font_dir = os.path.join(root_dir, "resource", "fonts")
song_dir = os.path.join(root_dir, "resource", "songs")
i18n_dir = os.path.join(root_dir, "webui", "i18n")
config_file = os.path.join(root_dir, "webui", ".streamlit", "webui.toml")
system_locale = utils.get_system_locale()


if "video_subject" not in st.session_state:
    st.session_state["video_subject"] = ""
if "video_script" not in st.session_state:
    st.session_state["video_script"] = ""
if "video_terms" not in st.session_state:
    st.session_state["video_terms"] = ""
if "video_script_prompt" not in st.session_state:
    st.session_state["video_script_prompt"] = ""
if "custom_system_prompt" not in st.session_state:
    st.session_state["custom_system_prompt"] = llm.DEFAULT_SCRIPT_SYSTEM_PROMPT
if "use_custom_system_prompt" not in st.session_state:
    st.session_state["use_custom_system_prompt"] = False
if "ui_language" not in st.session_state:
    st.session_state["ui_language"] = config.ui.get("language", system_locale)
if "local_video_materials" not in st.session_state:
    # 记住用户最近一次已经落盘的本地素材，避免仅修改文案后二次生成时丢失素材列表。
    st.session_state["local_video_materials"] = []

# 加载语言文件
locales = utils.load_locales(i18n_dir)

# 创建一个顶部栏，包含标题和语言选择
title_col, lang_col = st.columns([3, 1])

with title_col:
    st.title(f"MoneyPrinterTurbo v{config.project_version}")

with lang_col:
    display_languages = []
    selected_index = 0
    for i, code in enumerate(locales.keys()):
        display_languages.append(f"{code} - {locales[code].get('Language')}")
        if code == st.session_state.get("ui_language", ""):
            selected_index = i

    selected_language = st.selectbox(
        "Language / 语言",
        options=display_languages,
        index=selected_index,
        key="top_language_selector",
        label_visibility="collapsed",
    )
    if selected_language:
        code = selected_language.split(" - ")[0].strip()
        st.session_state["ui_language"] = code
        config.ui["language"] = code

support_locales = [
    "zh-CN",
    "zh-HK",
    "zh-TW",
    "de-DE",
    "en-US",
    "fr-FR",
    "vi-VN",
    "th-TH",
    "tr-TR",
]


def get_all_fonts():
    fonts = []
    for root, dirs, files in os.walk(font_dir):
        for file in files:
            if file.endswith(".ttf") or file.endswith(".ttc"):
                fonts.append(file)
    fonts.sort()
    return fonts


def get_all_songs():
    songs = []
    for root, dirs, files in os.walk(song_dir):
        for file in files:
            if file.endswith(".mp3"):
                songs.append(file)
    return songs


def open_task_folder(task_id):
    try:
        # task_id 应始终是服务端生成的 UUID。这里先做格式校验，避免异常值
        # 通过路径拼接访问任务目录之外的位置，也避免后续打开目录时触发
        # 平台 shell 对特殊字符的解释。
        normalized_task_id = str(UUID(str(task_id)))
        tasks_root = os.path.abspath(os.path.join(root_dir, "storage", "tasks"))
        path = os.path.abspath(os.path.join(tasks_root, normalized_task_id))

        # 即使 UUID 校验通过，也再次确认最终路径仍在任务根目录内，避免
        # 未来调用方调整 task_id 来源时引入路径穿越风险。
        if not path.startswith(tasks_root + os.sep):
            logger.warning(f"invalid task folder path: {path}")
            return

        if os.path.isdir(path):
            webbrowser.open(f"file://{path}")
    except Exception as e:
        logger.error(e)


def scroll_to_bottom():
    js = """
    <script>
        console.log("scroll_to_bottom");
        function scroll(dummy_var_to_force_repeat_execution){
            var sections = parent.document.querySelectorAll('section.main');
            console.log(sections);
            for(let index = 0; index<sections.length; index++) {
                sections[index].scrollTop = sections[index].scrollHeight;
            }
        }
        scroll(1);
    </script>
    """
    st.components.v1.html(js, height=0, width=0)


def init_log():
    logger.remove()
    _lvl = "DEBUG"

    def format_record(record):
        # 获取日志记录中的文件全路径
        file_path = record["file"].path
        # 将绝对路径转换为相对于项目根目录的路径
        relative_path = os.path.relpath(file_path, root_dir)
        # 更新记录中的文件路径
        record["file"].path = f"./{relative_path}"
        # 返回修改后的格式字符串
        # 您可以根据需要调整这里的格式
        record["message"] = record["message"].replace(root_dir, ".")

        _format = (
            "<green>{time:%Y-%m-%d %H:%M:%S}</> | "
            + "<level>{level}</> | "
            + '"{file.path}:{line}":<blue> {function}</> '
            + "- <level>{message}</>"
            + "\n"
        )
        return _format

    logger.add(
        sys.stdout,
        level=_lvl,
        format=format_record,
        colorize=True,
    )


init_log()

locales = utils.load_locales(i18n_dir)


def tr(key):
    loc = locales.get(st.session_state["ui_language"], {})
    return loc.get("Translation", {}).get(key, key)


# 创建基础设置折叠框
if not config.app.get("hide_config", False):
    with st.expander(tr("Basic Settings"), expanded=False):
        config_panels = st.columns(3)
        left_config_panel = config_panels[0]
        middle_config_panel = config_panels[1]
        right_config_panel = config_panels[2]

        # 左侧面板 - 日志设置
        with left_config_panel:
            # 是否隐藏配置面板
            hide_config = st.checkbox(
                tr("Hide Basic Settings"), value=config.app.get("hide_config", False)
            )
            config.app["hide_config"] = hide_config

            # 是否禁用日志显示
            hide_log = st.checkbox(
                tr("Hide Log"), value=config.ui.get("hide_log", False)
            )
            config.ui["hide_log"] = hide_log

        # 中间面板 - LLM 设置

        with middle_config_panel:
            st.write(tr("LLM Settings"))
            llm_providers = [
                "OpenAI",
                "Moonshot",
                "Azure",
                "Qwen",
                "DeepSeek",
                "ModelScope",
                "Gemini",
                "Grok",
                "Ollama",
                "G4f",
                "OneAPI",
                "Cloudflare",
                "ERNIE",
                "MiMo",
                "Pollinations",
                "LiteLLM",
            ]
            saved_llm_provider = config.app.get("llm_provider", "OpenAI").lower()
            saved_llm_provider_index = 0
            for i, provider in enumerate(llm_providers):
                if provider.lower() == saved_llm_provider:
                    saved_llm_provider_index = i
                    break

            llm_provider = st.selectbox(
                tr("LLM Provider"),
                options=llm_providers,
                index=saved_llm_provider_index,
            )
            llm_helper = st.container()
            llm_provider = llm_provider.lower()
            config.app["llm_provider"] = llm_provider

            llm_api_key = config.app.get(f"{llm_provider}_api_key", "")
            llm_secret_key = config.app.get(
                f"{llm_provider}_secret_key", ""
            )  # only for baidu ernie
            llm_base_url = config.app.get(f"{llm_provider}_base_url", "")
            llm_model_name = config.app.get(f"{llm_provider}_model_name", "")
            llm_account_id = config.app.get(f"{llm_provider}_account_id", "")

            tips = ""
            if llm_provider == "ollama":
                if not llm_model_name:
                    llm_model_name = "qwen:7b"
                if not llm_base_url:
                    llm_base_url = config.get_default_ollama_base_url()

                with llm_helper:
                    docker_hint = ""
                    if config.is_running_in_container():
                        docker_hint = "\n                            > 检测到容器环境，未配置 Base Url 时会默认使用 `http://host.docker.internal:11434/v1`\n"
                    tips = f"""
                            ##### Ollama配置说明
                            - **API Key**: 随便填写，比如 123
                            - **Base Url**: 一般为 http://localhost:11434/v1
                                - 如果 `MoneyPrinterTurbo` 和 `Ollama` **不在同一台机器上**，需要填写 `Ollama` 机器的IP地址
                                - 如果 `MoneyPrinterTurbo` 是 `Docker` 部署，建议填写 `http://host.docker.internal:11434/v1`{docker_hint}
                            - **Model Name**: 使用 `ollama list` 查看，比如 `qwen:7b`
                            """

            if llm_provider == "openai":
                if not llm_model_name:
                    llm_model_name = "gpt-3.5-turbo"
                with llm_helper:
                    tips = """
                            ##### OpenAI 配置说明
                            > 需要VPN开启全局流量模式
                            - **API Key**: [点击到官网申请](https://platform.openai.com/api-keys)
                            - **Base Url**: 官方 OpenAI 可留空；如果使用 OpenAI 兼容供应商（例如 OpenRouter），请填写对应的兼容接口地址
                            - **Model Name**: 填写**有权限**的模型；如果使用兼容供应商，请填写该平台支持的模型 ID
                            """

            if llm_provider == "moonshot":
                if not llm_model_name:
                    llm_model_name = "moonshot-v1-8k"
                with llm_helper:
                    tips = """
                            ##### Moonshot 配置说明
                            - **API Key**: [点击到官网申请](https://platform.moonshot.cn/console/api-keys)
                            - **Base Url**: 固定为 https://api.moonshot.cn/v1
                            - **Model Name**: 比如 moonshot-v1-8k，[点击查看模型列表](https://platform.moonshot.cn/docs/intro#%E6%A8%A1%E5%9E%8B%E5%88%97%E8%A1%A8)
                            """
            if llm_provider == "oneapi":
                if not llm_model_name:
                    llm_model_name = (
                        "claude-3-5-sonnet-20240620"  # 默认模型，可以根据需要调整
                    )
                with llm_helper:
                    tips = """
                        ##### OneAPI 配置说明
                        - **API Key**: 填写您的 OneAPI 密钥
                        - **Base Url**: 填写 OneAPI 的基础 URL
                        - **Model Name**: 填写您要使用的模型名称，例如 claude-3-5-sonnet-20240620
                        """

            if llm_provider == "qwen":
                if not llm_model_name:
                    llm_model_name = "qwen-max"
                with llm_helper:
                    tips = """
                            ##### 通义千问Qwen 配置说明
                            - **API Key**: [点击到官网申请](https://dashscope.console.aliyun.com/apiKey)
                            - **Base Url**: 留空
                            - **Model Name**: 比如 qwen-max，[点击查看模型列表](https://help.aliyun.com/zh/dashscope/developer-reference/model-introduction#3ef6d0bcf91wy)
                            """

            if llm_provider == "g4f":
                if not llm_model_name:
                    llm_model_name = "gpt-3.5-turbo"
                with llm_helper:
                    tips = """
                            ##### gpt4free 配置说明
                            > [GitHub开源项目](https://github.com/xtekky/gpt4free)，可以免费使用GPT模型，但是**稳定性较差**
                            - **API Key**: 随便填写，比如 123
                            - **Base Url**: 留空
                            - **Model Name**: 比如 gpt-3.5-turbo，[点击查看模型列表](https://github.com/xtekky/gpt4free/blob/main/g4f/models.py#L308)
                            """
            if llm_provider == "azure":
                with llm_helper:
                    tips = """
                            ##### Azure 配置说明
                            > [点击查看如何部署模型](https://learn.microsoft.com/zh-cn/azure/ai-services/openai/how-to/create-resource)
                            - **API Key**: [点击到Azure后台创建](https://portal.azure.com/#view/Microsoft_Azure_ProjectOxford/CognitiveServicesHub/~/OpenAI)
                            - **Base Url**: 留空
                            - **Model Name**: 填写你实际的部署名
                            """

            if llm_provider == "gemini":
                if not llm_model_name:
                    llm_model_name = "gemini-1.0-pro"

                with llm_helper:
                    tips = """
                            ##### Gemini 配置说明
                            > 需要VPN开启全局流量模式
                            - **API Key**: [点击到官网申请](https://ai.google.dev/)
                            - **Base Url**: 留空
                            - **Model Name**: 比如 gemini-1.0-pro
                            """

            if llm_provider == "grok":
                if not llm_model_name:
                    llm_model_name = "grok-4.3"
                if not llm_base_url:
                    llm_base_url = "https://api.x.ai/v1"

                with llm_helper:
                    tips = """
                            ##### Grok 配置说明
                            - **API Key**: 填写您的 GrokAPI 密钥
                            - **Base Url**: 填写 GrokAPI 的基础 URL
                            - **Model Name**: 比如 grok-4.3
                            """

            if llm_provider == "deepseek":
                if not llm_model_name:
                    llm_model_name = "deepseek-chat"
                if not llm_base_url:
                    llm_base_url = "https://api.deepseek.com"
                with llm_helper:
                    tips = """
                            ##### DeepSeek 配置说明
                            - **API Key**: [点击到官网申请](https://platform.deepseek.com/api_keys)
                            - **Base Url**: 固定为 https://api.deepseek.com
                            - **Model Name**: 固定为 deepseek-chat
                            """

            if llm_provider == "mimo":
                if not llm_model_name:
                    llm_model_name = "mimo-v2.5-pro"
                if not llm_base_url:
                    llm_base_url = "https://api.xiaomimimo.com/v1"
                with llm_helper:
                    tips = """
                            ##### Xiaomi MiMo 配置说明
                            - **API Key**: [点击到官网申请](https://platform.xiaomimimo.com/docs/zh-CN/quick-start/first-api-call)
                            - **Base Url**: 固定为 https://api.xiaomimimo.com/v1
                            - **Model Name**: 默认 mimo-v2.5-pro，也可以按官方文档填写其它可用模型
                            """

            if llm_provider == "modelscope":
                if not llm_model_name:
                    llm_model_name = "Qwen/Qwen3-32B"
                if not llm_base_url:
                    llm_base_url = "https://api-inference.modelscope.cn/v1/"
                with llm_helper:
                    tips = """
                            ##### ModelScope 配置说明
                            - **API Key**: [点击到官网申请](https://modelscope.cn/docs/model-service/API-Inference/intro)
                            - **Base Url**: 固定为 https://api-inference.modelscope.cn/v1/
                            - **Model Name**: 比如 Qwen/Qwen3-32B，[点击查看模型列表](https://modelscope.cn/models?filter=inference_type&page=1)
                            """

            if llm_provider == "ernie":
                with llm_helper:
                    tips = """
                            ##### 百度文心一言 配置说明
                            - **API Key**: [点击到官网申请](https://console.bce.baidu.com/qianfan/ais/console/applicationConsole/application)
                            - **Secret Key**: [点击到官网申请](https://console.bce.baidu.com/qianfan/ais/console/applicationConsole/application)
                            - **Base Url**: 填写 **请求地址** [点击查看文档](https://cloud.baidu.com/doc/WENXINWORKSHOP/s/jlil56u11#%E8%AF%B7%E6%B1%82%E8%AF%B4%E6%98%8E)
                            """

            if llm_provider == "pollinations":
                if not llm_model_name:
                    llm_model_name = "default"
                with llm_helper:
                    tips = """
                            ##### Pollinations AI Configuration
                            - **API Key**: Optional - Leave empty for public access
                            - **Base Url**: Default is https://text.pollinations.ai/openai
                            - **Model Name**: Use 'openai-fast' or specify a model name
                            """

            if llm_provider == "litellm":
                if not llm_model_name:
                    llm_model_name = "openai/gpt-4o-mini"
                with llm_helper:
                    tips = """
                            ##### LiteLLM Configuration
                            > [LiteLLM](https://github.com/BerriAI/litellm) routes to 100+ LLM providers via a unified interface.
                            > Set your provider's API key as an env var: `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `GEMINI_API_KEY`, `AWS_ACCESS_KEY_ID`, etc.
                            - **Model Name**: LiteLLM format — `openai/gpt-4o`, `anthropic/claude-sonnet-4-20250514`, `bedrock/anthropic.claude-3-5-sonnet-20241022-v2:0`, `gemini/gemini-2.5-flash`. See [full provider list](https://docs.litellm.ai/docs/providers)
                            """

            if tips and config.ui["language"] == "zh":
                st.warning(
                    "中国用户建议使用 **DeepSeek** 或 **Moonshot** 作为大模型提供商\n- 国内可直接访问，不需要VPN \n- 注册就送额度，基本够用"
                )
                st.info(tips)

            st_llm_api_key = st.text_input(
                tr("API Key"), value=llm_api_key, type="password"
            )
            st_llm_base_url = st.text_input(tr("Base Url"), value=llm_base_url)
            st_llm_model_name = ""
            if llm_provider != "ernie":
                st_llm_model_name = st.text_input(
                    tr("Model Name"),
                    value=llm_model_name,
                    key=f"{llm_provider}_model_name_input",
                )
                if st_llm_model_name:
                    config.app[f"{llm_provider}_model_name"] = st_llm_model_name
            else:
                st_llm_model_name = None

            if st_llm_api_key:
                config.app[f"{llm_provider}_api_key"] = st_llm_api_key
            if st_llm_base_url:
                config.app[f"{llm_provider}_base_url"] = st_llm_base_url
            if st_llm_model_name:
                config.app[f"{llm_provider}_model_name"] = st_llm_model_name
            if llm_provider == "ernie":
                st_llm_secret_key = st.text_input(
                    tr("Secret Key"), value=llm_secret_key, type="password"
                )
                config.app[f"{llm_provider}_secret_key"] = st_llm_secret_key

            if llm_provider == "cloudflare":
                st_llm_account_id = st.text_input(
                    tr("Account ID"), value=llm_account_id
                )
                if st_llm_account_id:
                    config.app[f"{llm_provider}_account_id"] = st_llm_account_id

        # 右侧面板 - API 密钥设置
        with right_config_panel:

            def get_keys_from_config(cfg_key):
                api_keys = config.app.get(cfg_key, [])
                if isinstance(api_keys, str):
                    api_keys = [api_keys]
                api_key = ", ".join(api_keys)
                return api_key

            def save_keys_to_config(cfg_key, value):
                value = value.replace(" ", "")
                if value:
                    config.app[cfg_key] = value.split(",")

            st.write(tr("Video Source Settings"))

            pexels_api_key = get_keys_from_config("pexels_api_keys")
            pexels_api_key = st.text_input(
                tr("Pexels API Key"), value=pexels_api_key, type="password"
            )
            save_keys_to_config("pexels_api_keys", pexels_api_key)

            pixabay_api_key = get_keys_from_config("pixabay_api_keys")
            pixabay_api_key = st.text_input(
                tr("Pixabay API Key"), value=pixabay_api_key, type="password"
            )
            save_keys_to_config("pixabay_api_keys", pixabay_api_key)

# ============================================================
# 工作流步骤导航
# ============================================================
STEPS = ["🎯 选题", "🎨 赛道", "📝 脚本", "⚙️ 设置", "🎬 生成"]
STEP_KEYS = ["topic", "template", "script", "settings", "generate"]

if "wizard_step" not in st.session_state:
    st.session_state["wizard_step"] = 0

current_step = st.session_state["wizard_step"]

# 步骤进度条
step_progress = (current_step + 1) / len(STEPS)
st.progress(step_progress)

# 步骤导航按钮
step_cols = st.columns(len(STEPS))
for i, (label, key) in enumerate(zip(STEPS, STEP_KEYS)):
    with step_cols[i]:
        if i == current_step:
            st.markdown(f"**<font color='#FF4B4B'>{'●'} {label}</font>**", unsafe_allow_html=True)
        elif i < current_step:
            if st.button(f"✅ {label}", key=f"nav_to_{key}"):
                st.session_state["wizard_step"] = i
                st.rerun()
        else:
            st.markdown(f"○ {label}")

st.divider()

# 全局初始化
_template_mgr = get_template_manager()
_available_templates = _template_mgr.list_templates()

params = VideoParams(video_subject="")
uploaded_files = []
uploaded_audio_file = None

# ============================================================
# Step 1: 🎯 选题
# ============================================================
if current_step == 0:
    st.subheader(STEPS[0])
    st.caption("从各平台热榜选题，或手动输入视频主题")

    # 热点选题（折叠）
    with st.expander("🔥 " + tr("Trending Topics"), expanded=True):
        platform_labels = {
            "douyin": "抖音", "weibo": "微博", "bilibili": "B站",
            "zhihu": "知乎", "baidu": "百度",
        }
        trend_cols = st.columns(5)
        selected_platforms = []
        for i, (plat_key, plat_label) in enumerate(platform_labels.items()):
            with trend_cols[i]:
                if st.checkbox(plat_label, value=True, key=f"trend_plat_{plat_key}"):
                    selected_platforms.append(plat_key)

        if not selected_platforms:
            selected_platforms = list(platform_labels.keys())

        fetch_col, idea_col = st.columns([1, 1])
        with fetch_col:
            fetch_clicked = st.button("📊 " + tr("Fetch Trending Data"), type="primary", use_container_width=True)
        with idea_col:
            idea_clicked = st.button("💡 " + tr("Generate Content Ideas"), use_container_width=True)

        if fetch_clicked:
            with st.spinner(tr("Fetching trending data from platforms...")):
                try:
                    svc = TrendingService()
                    items = svc.fetch_all(platforms=selected_platforms, limit=20)
                    if items:
                        analyses = svc.analyse(top_n=15)
                        ideas = svc.ideas(count=8)
                        st.session_state["trend_items"] = items
                        st.session_state["trend_analyses"] = analyses
                        st.session_state["trend_ideas"] = ideas
                        st.success(f"✅ 从 {len(selected_platforms)} 个平台获取了 {len(items)} 条热榜数据")
                    else:
                        st.warning(tr("Failed to fetch trending data"))
                except Exception as e:
                    st.error(f"爬取失败: {e}")

        if idea_clicked and st.session_state.get("trend_analyses"):
            analyses = st.session_state["trend_analyses"]
            svc = TrendingService()
            ideas = svc.ideas(count=8, analyses=analyses)
            st.session_state["trend_ideas"] = ideas
            st.success(f"✅ 生成了 {len(ideas)} 个选题建议")

        if st.session_state.get("trend_items") or st.session_state.get("trend_analyses"):
            tab1, tab2, tab3 = st.tabs([tr("Trending List"), tr("Trend Analysis"), tr("Content Ideas")])

            with tab1:
                items = st.session_state.get("trend_items", [])
                if items:
                    for plat in selected_platforms:
                        plat_items = [it for it in items if it.platform == plat]
                        if plat_items:
                            label = platform_labels.get(plat, plat)
                            st.write(f"**{label}** ({len(plat_items)}条)")
                            for it in plat_items[:15]:
                                c1, c2 = st.columns([0.1, 0.9])
                                with c1:
                                    st.write(f"#{it.rank}")
                                with c2:
                                    st.write(it.title)

            with tab2:
                analyses = st.session_state.get("trend_analyses", [])
                if analyses:
                    for i, ta in enumerate(analyses[:12]):
                        platforms_str = ", ".join(platform_labels.get(p, p) for p in ta.platforms)
                        score_disp = f"{ta.composite_score:.0f}"
                        with st.container(border=True):
                            cols = st.columns([0.6, 0.2, 0.2])
                            with cols[0]:
                                st.write(f"**{i+1}. {ta.keyword}**")
                                st.caption(f"平台: {platforms_str}")
                            with cols[1]:
                                st.write(f"热度: {score_disp}")
                            with cols[2]:
                                if st.button(tr("Select"), key=f"trend_apply_{i}", use_container_width=True):
                                    st.session_state["video_subject"] = ta.keyword
                                    matched = auto_match_template(ta.keyword)
                                    if matched:
                                        st.session_state["niche_template_id"] = matched
                                        st.success(f"✅ 已选: {ta.keyword} + {tr('template_%s_name' % matched)}")
                                    else:
                                        st.success(f"已选选题: {ta.keyword}")

            with tab3:
                ideas = st.session_state.get("trend_ideas", [])
                if ideas:
                    for i, idea in enumerate(ideas):
                        with st.container(border=True):
                            st.write(f"**{i+1}. {idea.title}**")
                            st.caption(f"📝 {idea.hook}")
                            tags_str = ", ".join(idea.tags)
                            st.write(f"🏷️ {tags_str}")
                            en_level = {"high": "🔥 高", "medium": "📊 中", "low": "📉 低"}
                            st.write(f"📈 预估互动: {en_level.get(idea.estimated_engagement, idea.estimated_engagement)}")
                            act_cols = st.columns([1, 1])
                            with act_cols[0]:
                                if st.button(tr("Apply as Subject"), key=f"idea_apply_{i}", use_container_width=True):
                                    st.session_state["video_subject"] = idea.title
                                    st.session_state["video_script_prompt"] = idea.hook
                                    matched = auto_match_template(idea.title)
                                    if matched:
                                        st.session_state["niche_template_id"] = matched
                                        st.success(f"✅ 已选 + 赛道: {tr('template_%s_name' % matched)}")
                                    else:
                                        st.success(f"✅ 已选选题: {idea.title}")
                            with act_cols[1]:
                                if st.button("🚀 " + tr("One-Click Generate Video"), key=f"idea_quick_{i}", type="primary", use_container_width=True):
                                    import requests as _req, time as _time
                                    subject = idea.title
                                    st.session_state["video_subject"] = subject
                                    matched = auto_match_template(subject)
                                    tmpl_prompt = ""
                                    if matched:
                                        st.session_state["niche_template_id"] = matched
                                        tmpl_data = _template_mgr.generate_prompt(matched, subject)
                                        tmpl_prompt = tmpl_data.get("script_prompt", "")
                                    with st.container(border=True):
                                        _progress = st.progress(0, text="🎬 正在生成视频...")
                                        st.write("📝 步骤 1/4: AI 生成脚本...")
                                        sr = _req.post("http://127.0.0.1:8080/api/v1/scripts",
                                            json={"video_subject": subject, "video_script_prompt": tmpl_prompt,
                                                   "paragraph_number": 1, "custom_system_prompt": ""}, timeout=120).json()
                                        script = sr.get("data", {}).get("video_script", "")
                                        if not script:
                                            st.error("❌ 脚本生成失败")
                                            st.stop()
                                        st.success("   ✅ 脚本 (%d 字)" % len(script))
                                        _progress.progress(25, text="🔍 生成搜索关键词...")
                                        tr_ = _req.post("http://127.0.0.1:8080/api/v1/terms",
                                            json={"video_subject": subject, "video_script": script, "amount": 5}, timeout=30).json()
                                        terms = tr_.get("data", {}).get("video_terms", [])
                                        terms_str = ", ".join(terms[:5]) if isinstance(terms, list) else terms
                                        st.success("   ✅ 关键词: %s" % terms_str)
                                        _progress.progress(50, text="🎬 提交视频合成...")
                                        vn = config.ui.get("voice_name", "zh-CN-YunxiNeural-Male")
                                        vr = _req.post("http://127.0.0.1:8080/api/v1/videos",
                                            json={"video_subject": subject, "video_script": script,
                                                   "video_terms": terms_str, "video_aspect": "9:16", "video_count": 1,
                                                   "video_source": "pexels", "voice_name": vn,
                                                   "voice_volume": 1.0, "voice_rate": 1.0, "bgm_type": "random",
                                                   "bgm_volume": 0.2, "subtitle_enabled": True,
                                                   "font_name": config.ui.get("font_name", "MicrosoftYaHeiBold.ttc"),
                                                   "text_fore_color": config.ui.get("text_fore_color", "#FFFFFF"),
                                                   "font_size": config.ui.get("font_size", 60)}, timeout=30).json()
                                        task_id = vr.get("data", {}).get("task_id", "")
                                        if not task_id:
                                            st.error("❌ 视频任务提交失败")
                                            st.stop()
                                        st.success("   ✅ 任务已提交")
                                        _progress.progress(60, text="⏳ 等待视频合成...")
                                        last_progress = ""
                                        for _ in range(120):
                                            poll = _req.get(f"http://127.0.0.1:8080/api/v1/tasks/{task_id}", timeout=15).json()
                                            task = poll.get("data", {})
                                            state = task.get("state")
                                            progress = task.get("progress", "")
                                            if progress and progress != last_progress:
                                                _progress.progress(min(int(progress) + 60, 95), text="视频合成中 %s%%..." % progress)
                                                last_progress = progress
                                            if state in (1, -1):
                                                videos = task.get("videos", []) or task.get("combined_videos", [])
                                                if videos:
                                                    url = videos[0] if videos[0].startswith("http") else f"http://127.0.0.1:8080{videos[0]}"
                                                    _progress.progress(100, text="✅ 视频生成完成!")
                                                    st.video(url)
                                                    st.success(f"🎉 视频已生成!")
                                                else:
                                                    st.error("⚠️ 已完成但未找到视频")
                                                break
                                            if state in (2, 3):
                                                st.error(f"❌ 生成失败: {task.get('error', '未知错误')}")
                                                break
                                            _time.sleep(5)

    # 手动输入主题
    st.divider()
    st.write("### 或手动输入主题")
    params.video_subject = st.text_input(
        tr("Video Subject"),
        key="video_subject",
        placeholder="输入视频主题，如：如何理财、端午养生小技巧...",
    ).strip()

    if st.button("下一步 → 🎨 选择赛道", type="primary", use_container_width=True):
        if params.video_subject:
            st.session_state["wizard_step"] = 1
            st.rerun()
        else:
            st.warning("请先输入或选择一个视频主题")

# ============================================================
# Step 2: 🎨 赛道
# ============================================================
elif current_step == 1:
    st.subheader(STEPS[1])
    st.caption("根据视频主题选择赛道模板，AI 将自动优化脚本风格")

    with st.container(border=True):
        template_options = []
        template_ids = []
        for t in _available_templates:
            template_ids.append(t["id"])
            _tname = tr("template_%s_name" % t["id"])
            template_options.append(f"{t['icon']} {_tname}")

        if "niche_template_id" not in st.session_state:
            st.session_state["niche_template_id"] = template_ids[0]

        subject = st.session_state.get("video_subject", "")
        if subject:
            matched = auto_match_template(subject)
            if matched:
                st.info(f"💡 根据主题推荐赛道: **{tr('template_%s_name' % matched)}**")
                if "niche_template_id" not in st.session_state or st.session_state["niche_template_id"] != matched:
                    st.session_state["niche_template_id"] = matched

        selected_idx = st.selectbox(
            tr("Select Template"),
            options=range(len(template_options)),
            format_func=lambda x: template_options[x],
            index=template_ids.index(st.session_state["niche_template_id"])
            if st.session_state["niche_template_id"] in template_ids else 0,
            key="niche_template_selector",
        )

        selected_template_id = template_ids[selected_idx]
        selected_template = _template_mgr.get_template(selected_template_id)

        if selected_template:
            st.caption(tr("template_%s_desc" % selected_template_id))
            with st.expander(tr("Template Details"), expanded=False):
                col_v, col_m = st.columns(2)
                with col_v:
                    st.markdown(f"**{tr('Visual Style')}**")
                    st.code(selected_template.visual_style.describe())
                with col_m:
                    st.markdown(f"**{tr('Music Info')}**")
                    st.code(selected_template.music_style.describe())
                st.markdown(f"**{tr('Hashtags Example')}**")
                st.code(" ".join(selected_template.hashtags[:6]))

        if st.button(tr("Apply Template to Script"), type="primary", use_container_width=True):
            subject = st.session_state.get("video_subject", "")
            if not subject:
                st.warning("请先在上一步输入视频主题")
            prompt_data = _template_mgr.generate_prompt(selected_template_id, subject or "your topic")
            st.session_state["video_script_prompt"] = prompt_data["script_prompt"]
            st.session_state["niche_template_id"] = selected_template_id
            st.success(f"✅ 已应用赛道: {tr('template_%s_name' % selected_template_id)}")

    nav_cols = st.columns([1, 1])
    with nav_cols[0]:
        if st.button("← 返回选题", use_container_width=True):
            st.session_state["wizard_step"] = 0
            st.rerun()
    with nav_cols[1]:
        if st.button("下一步 → 📝 编辑脚本", type="primary", use_container_width=True):
            st.session_state["wizard_step"] = 2
            st.rerun()

# ============================================================
# Step 3: 📝 脚本
# ============================================================
elif current_step == 2:
    st.subheader(STEPS[2])
    st.caption("AI 自动生成脚本，或手动编辑文案")

    # 显示当前主题，为空时允许输入
    subject = st.session_state.get("video_subject", "")
    if subject:
        st.info(f"🎯 当前主题: **{subject}**")
    else:
        subject = st.text_input("请输入视频主题", key="step3_subject_input").strip()
        if subject:
            st.session_state["video_subject"] = subject
    params.video_subject = subject or st.session_state.get("video_subject", "")
    video_languages = [(tr("Auto Detect"), "")] + [(code, code) for code in support_locales]
    selected_index = st.selectbox(
        tr("Script Language"), index=0,
        options=range(len(video_languages)),
        format_func=lambda x: video_languages[x][0],
    )
    params.video_language = video_languages[selected_index][1]

    with st.expander(tr("Advanced Script Settings"), expanded=False):
        params.paragraph_number = st.slider(
            tr("Script Paragraph Number"),
            min_value=llm.MIN_SCRIPT_PARAGRAPH_NUMBER,
            max_value=llm.MAX_SCRIPT_PARAGRAPH_NUMBER,
            value=st.session_state.get("paragraph_number_input", 1),
            key="paragraph_number_input",
        )
        params.video_script_prompt = st.text_area(
            tr("Custom Script Requirements"), height=100,
            max_chars=llm.MAX_SCRIPT_PROMPT_LENGTH,
            placeholder=tr("Custom Script Requirements Placeholder"),
            key="video_script_prompt",
        ).strip()
        use_custom_system_prompt = st.checkbox(
            tr("Use Custom System Prompt"),
            help=tr("Use Custom System Prompt Help"),
            key="use_custom_system_prompt",
        )
        if use_custom_system_prompt:
            params.custom_system_prompt = st.text_area(
                tr("Custom System Prompt"), height=240,
                max_chars=llm.MAX_SCRIPT_SYSTEM_PROMPT_LENGTH,
                key="custom_system_prompt",
            ).strip()
        else:
            params.custom_system_prompt = ""

    gen_col, kw_col = st.columns([1, 1])
    with gen_col:
        if st.button(tr("Generate Video Script and Keywords"), key="auto_generate_script", type="primary", use_container_width=True):
            with st.spinner(tr("Generating Video Script and Keywords")):
                script = llm.generate_script(
                    video_subject=params.video_subject,
                    language=params.video_language,
                    paragraph_number=params.paragraph_number,
                    video_script_prompt=params.video_script_prompt,
                    custom_system_prompt=params.custom_system_prompt,
                )
                terms = llm.generate_terms(params.video_subject, script)
                if "Error: " in script:
                    st.error(tr(script))
                elif "Error: " in terms:
                    st.error(tr(terms))
                else:
                    st.session_state["video_script"] = script
                    st.session_state["video_terms"] = ", ".join(terms)

    params.video_script = st.text_area(
        tr("Video Script"), value=st.session_state.get("video_script", ""), height=280
    )

    with kw_col:
        if st.button(tr("Generate Video Keywords"), key="auto_generate_terms", use_container_width=True):
            if not params.video_script:
                st.error(tr("Please Enter the Video Subject"))
            else:
                with st.spinner(tr("Generating Video Keywords")):
                    terms = llm.generate_terms(params.video_subject, params.video_script)
                    if "Error: " in terms:
                        st.error(tr(terms))
                    else:
                        st.session_state["video_terms"] = ", ".join(terms)

    params.video_terms = st.text_area(
        tr("Video Keywords"), value=st.session_state.get("video_terms", "")
    )

    nav_cols = st.columns([1, 1])
    with nav_cols[0]:
        if st.button("← 返回赛道", use_container_width=True):
            st.session_state["wizard_step"] = 1
            st.rerun()
    with nav_cols[1]:
        if st.button("下一步 → ⚙️ 视频设置", type="primary", use_container_width=True):
            st.session_state["wizard_step"] = 3
            st.rerun()

# ============================================================
# Step 4: ⚙️ 设置
# ============================================================
elif current_step == 3:
    st.subheader(STEPS[3])
    st.caption("配置视频、音频和字幕参数")

    panel = st.columns(3)
    left_panel = panel[0]
    middle_panel = panel[1]
    right_panel = panel[2]

    # --- 左列：视频设置 ---
    with left_panel:
        with st.container(border=True):
            st.write(tr("Video Settings"))
            video_concat_modes = [
                (tr("Sequential"), "sequential"), (tr("Random"), "random"),
            ]
            video_sources = [
                (tr("Pexels"), "pexels"), (tr("Pixabay"), "pixabay"),
                (tr("Local file"), "local"), (tr("TikTok"), "douyin"),
                (tr("Bilibili"), "bilibili"), (tr("Xiaohongshu"), "xiaohongshu"),
            ]
            saved_video_source_name = config.app.get("video_source", "pexels")
            saved_video_source_index = [v[1] for v in video_sources].index(saved_video_source_name)
            selected_index = st.selectbox(
                tr("Video Source"), options=range(len(video_sources)),
                format_func=lambda x: video_sources[x][0], index=saved_video_source_index,
            )
            params.video_source = video_sources[selected_index][1]
            config.app["video_source"] = params.video_source

            if params.video_source == "local":
                local_file_types = ["mp4", "mov", "avi", "flv", "mkv", "jpg", "jpeg", "png"]
                uploaded_files = st.file_uploader(
                    "Upload Local Files", type=local_file_types + [ft.upper() for ft in local_file_types],
                    accept_multiple_files=True,
                )

            selected_index = st.selectbox(
                tr("Video Concat Mode"), index=1, options=range(len(video_concat_modes)),
                format_func=lambda x: video_concat_modes[x][0],
            )
            params.video_concat_mode = VideoConcatMode(video_concat_modes[selected_index][1])

            video_transition_modes = [
                (tr("None"), VideoTransitionMode.none.value),
                (tr("Shuffle"), VideoTransitionMode.shuffle.value),
                (tr("FadeIn"), VideoTransitionMode.fade_in.value),
                (tr("FadeOut"), VideoTransitionMode.fade_out.value),
                (tr("SlideIn"), VideoTransitionMode.slide_in.value),
                (tr("SlideOut"), VideoTransitionMode.slide_out.value),
            ]
            selected_index = st.selectbox(
                tr("Video Transition Mode"), options=range(len(video_transition_modes)),
                format_func=lambda x: video_transition_modes[x][0], index=0,
            )
            params.video_transition_mode = VideoTransitionMode(video_transition_modes[selected_index][1])

            video_aspect_ratios = [
                (tr("Portrait"), VideoAspect.portrait.value),
                (tr("Landscape"), VideoAspect.landscape.value),
            ]
            selected_index = st.selectbox(
                tr("Video Ratio"), options=range(len(video_aspect_ratios)),
                format_func=lambda x: video_aspect_ratios[x][0],
            )
            params.video_aspect = VideoAspect(video_aspect_ratios[selected_index][1])
            params.video_clip_duration = st.selectbox(tr("Clip Duration"), options=[2, 3, 4, 5, 6, 7, 8, 9, 10], index=1)
            params.video_count = st.selectbox(tr("Number of Videos Generated Simultaneously"), options=[1, 2, 3, 4, 5], index=0)

    # --- 中列：音频设置 ---
    with middle_panel:
        with st.container(border=True):
            st.write(tr("Audio Settings"))
            tts_servers = [
                ("azure-tts-v1", "Azure TTS V1"), ("azure-tts-v2", "Azure TTS V2"),
                ("siliconflow", "SiliconFlow TTS"), ("gemini-tts", "Google Gemini TTS"),
                ("mimo-tts", "Xiaomi MiMo TTS"),
            ]
            saved_tts_server = config.ui.get("tts_server", "azure-tts-v1")
            saved_tts_server_index = 0
            for i, (sv, _) in enumerate(tts_servers):
                if sv == saved_tts_server:
                    saved_tts_server_index = i
                    break
            selected_tts_server_index = st.selectbox(
                tr("TTS Servers"), options=range(len(tts_servers)),
                format_func=lambda x: tts_servers[x][1], index=saved_tts_server_index,
            )
            selected_tts_server = tts_servers[selected_tts_server_index][0]
            config.ui["tts_server"] = selected_tts_server

            filtered_voices = []
            if selected_tts_server == "siliconflow":
                filtered_voices = voice.get_siliconflow_voices()
            elif selected_tts_server == "gemini-tts":
                filtered_voices = voice.get_gemini_voices()
            elif selected_tts_server == "mimo-tts":
                filtered_voices = voice.get_mimo_voices()
            else:
                all_voices = voice.get_all_azure_voices(filter_locals=None)
                for v in all_voices:
                    if selected_tts_server == "azure-tts-v2":
                        if "V2" in v:
                            filtered_voices.append(v)
                    else:
                        if "V2" not in v:
                            filtered_voices.append(v)

            friendly_names = {v: v.replace("Female", tr("Female")).replace("Male", tr("Male")).replace("Neural", "") for v in filtered_voices}
            saved_voice_name = config.ui.get("voice_name", "")
            saved_voice_name_index = 0
            if saved_voice_name in friendly_names:
                saved_voice_name_index = list(friendly_names.keys()).index(saved_voice_name)
            else:
                for i, v in enumerate(filtered_voices):
                    if v.lower().startswith(st.session_state["ui_language"].lower()):
                        saved_voice_name_index = i
                        break
            if saved_voice_name_index >= len(friendly_names) and friendly_names:
                saved_voice_name_index = 0
            if friendly_names:
                selected_friendly_name = st.selectbox(
                    tr("Speech Synthesis"),
                    options=list(friendly_names.values()),
                    index=min(saved_voice_name_index, len(friendly_names) - 1) if friendly_names else 0,
                )
                voice_name = list(friendly_names.keys())[list(friendly_names.values()).index(selected_friendly_name)]
                params.voice_name = voice_name
                config.ui["voice_name"] = voice_name
            else:
                st.warning("No voices available")
                params.voice_name = ""
                config.ui["voice_name"] = ""

            if friendly_names and st.button(tr("Play Voice")):
                play_content = params.video_subject or params.video_script or tr("Voice Example")
                with st.spinner(tr("Synthesizing Voice")):
                    temp_dir = utils.storage_dir("temp", create=True)
                    audio_file = os.path.join(temp_dir, f"tmp-voice-{str(uuid4())}.mp3")
                    sub_maker = voice.tts(text=play_content, voice_name=voice_name, voice_rate=params.voice_rate, voice_file=audio_file, voice_volume=params.voice_volume)
                    if not sub_maker:
                        play_content = "This is a example voice."
                        sub_maker = voice.tts(text=play_content, voice_name=voice_name, voice_rate=params.voice_rate, voice_file=audio_file, voice_volume=params.voice_volume)
                    if sub_maker and os.path.exists(audio_file):
                        st.audio(audio_file, format="audio/mp3")
                        if os.path.exists(audio_file):
                            os.remove(audio_file)

            if selected_tts_server == "azure-tts-v2" or (voice_name and voice.is_azure_v2_voice(voice_name)):
                saved_azure_speech_region = config.azure.get("speech_region", "")
                saved_azure_speech_key = config.azure.get("speech_key", "")
                azure_speech_region = st.text_input(tr("Speech Region"), value=saved_azure_speech_region, key="azure_speech_region_input")
                azure_speech_key = st.text_input(tr("Speech Key"), value=saved_azure_speech_key, type="password", key="azure_speech_key_input")
                config.azure["speech_region"] = azure_speech_region
                config.azure["speech_key"] = azure_speech_key

            if selected_tts_server == "siliconflow" or (voice_name and voice.is_siliconflow_voice(voice_name)):
                saved_api_key = config.siliconflow.get("api_key", "")
                siliconflow_api_key = st.text_input(tr("SiliconFlow API Key"), value=saved_api_key, type="password", key="siliconflow_api_key_input")
                st.info(tr("SiliconFlow TTS Settings") + ":\n- " + tr("Speed: Range [0.25, 4.0], default is 1.0") + "\n- " + tr("Volume: Uses Speech Volume setting, default 1.0 maps to gain 0"))
                config.siliconflow["api_key"] = siliconflow_api_key

            if selected_tts_server == "mimo-tts" or (voice_name and voice.is_mimo_voice(voice_name)):
                saved_mimo_api_key = config.app.get("mimo_api_key", "")
                mimo_api_key = st.text_input(tr("MiMo API Key"), value=saved_mimo_api_key, type="password", key="mimo_tts_api_key_input")
                st.info(tr("MiMo TTS Settings") + ":\n- " + tr("Uses Xiaomi MiMo V2.5 TTS preset voices") + "\n- " + tr("Speed and volume are currently handled by the provider defaults"))
                config.app["mimo_api_key"] = mimo_api_key

            params.voice_volume = st.selectbox(tr("Speech Volume"), options=[0.6, 0.8, 1.0, 1.2, 1.5, 2.0, 3.0, 4.0, 5.0], index=2)
            params.voice_rate = st.selectbox(tr("Speech Rate"), options=[0.8, 0.9, 1.0, 1.1, 1.2, 1.3, 1.5, 1.8, 2.0], index=2)

            custom_audio_file_types = ["mp3", "wav", "m4a", "aac", "flac", "ogg"]
            uploaded_audio_file = st.file_uploader(tr("Custom Audio File"),
                type=custom_audio_file_types + [ft.upper() for ft in custom_audio_file_types],
                accept_multiple_files=False, key="custom_audio_file_uploader")
            if uploaded_audio_file:
                st.audio(uploaded_audio_file, format="audio/mp3")
                st.info("Custom audio will be used directly.")

            bgm_options = [(tr("No Background Music"), ""), (tr("Random Background Music"), "random"), (tr("Custom Background Music"), "custom")]
            selected_index = st.selectbox(tr("Background Music"), index=1, options=range(len(bgm_options)), format_func=lambda x: bgm_options[x][0])
            params.bgm_type = bgm_options[selected_index][1]
            if params.bgm_type == "custom":
                custom_bgm_file = st.text_input(tr("Custom Background Music File"), key="custom_bgm_file_input")
                if custom_bgm_file:
                    params.bgm_file = custom_bgm_file.strip()
            params.bgm_volume = st.selectbox(tr("Background Music Volume"), options=[0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0], index=2)

    # --- 右列：字幕设置 + API 管理 ---
    with right_panel:
        with st.container(border=True):
            st.write(tr("Subtitle Settings"))
            params.subtitle_enabled = st.checkbox(tr("Enable Subtitles"), value=True)
            font_names = get_all_fonts()
            saved_font_name = config.ui.get("font_name", "MicrosoftYaHeiBold.ttc")
            saved_font_name_index = 0
            if saved_font_name in font_names:
                saved_font_name_index = font_names.index(saved_font_name)
            params.font_name = st.selectbox(tr("Font"), font_names, index=saved_font_name_index)
            config.ui["font_name"] = params.font_name

            subtitle_positions = [(tr("Top"), "top"), (tr("Center"), "center"), (tr("Bottom"), "bottom"), (tr("Custom"), "custom")]
            saved_subtitle_position = config.ui.get("subtitle_position", "bottom")
            saved_position_index = 2
            for i, (_, pos_value) in enumerate(subtitle_positions):
                if pos_value == saved_subtitle_position:
                    saved_position_index = i
                    break
            selected_index = st.selectbox(tr("Position"), index=saved_position_index,
                options=range(len(subtitle_positions)), format_func=lambda x: subtitle_positions[x][0])
            params.subtitle_position = subtitle_positions[selected_index][1]
            config.ui["subtitle_position"] = params.subtitle_position

            if params.subtitle_position == "custom":
                saved_custom_position = config.ui.get("custom_position", 70.0)
                custom_position = st.text_input(tr("Custom Position (% from top)"), value=str(saved_custom_position), key="custom_position_input")
                try:
                    params.custom_position = float(custom_position)
                    if params.custom_position < 0 or params.custom_position > 100:
                        st.error(tr("Please enter a value between 0 and 100"))
                    else:
                        config.ui["custom_position"] = params.custom_position
                except ValueError:
                    st.error(tr("Please enter a valid number"))

            font_cols = st.columns([0.3, 0.7])
            with font_cols[0]:
                saved_text_fore_color = config.ui.get("text_fore_color", "#FFFFFF")
                params.text_fore_color = st.color_picker(tr("Font Color"), saved_text_fore_color)
                config.ui["text_fore_color"] = params.text_fore_color
            with font_cols[1]:
                saved_font_size = config.ui.get("font_size", 60)
                params.font_size = st.slider(tr("Font Size"), 30, 100, saved_font_size)
                config.ui["font_size"] = params.font_size

            stroke_cols = st.columns([0.3, 0.7])
            with stroke_cols[0]:
                params.stroke_color = st.color_picker(tr("Stroke Color"), "#000000")
            with stroke_cols[1]:
                params.stroke_width = st.slider(tr("Stroke Width"), 0.0, 10.0, 1.5)

    # API 密钥管理（折叠）
    with st.expander(tr("Click to show API Key management"), expanded=False):
        st.subheader(tr("Manage Pexels and Pixabay API Keys"))
        col1, col2 = st.tabs(["Pexels API Keys", "Pixabay API Keys"])
        with col1:
            st.subheader("Pexels API Keys")
            if config.app["pexels_api_keys"]:
                st.write(tr("Current Keys:"))
                for key in config.app["pexels_api_keys"]:
                    st.code(key)
            else:
                st.info(tr("No Pexels API Keys currently"))
            new_key = st.text_input(tr("Add Pexels API Key"), key="pexels_new_key")
            if st.button(tr("Add Pexels API Key")):
                if new_key and new_key not in config.app["pexels_api_keys"]:
                    config.app["pexels_api_keys"].append(new_key)
                    config.save_config()
                    st.success(tr("Pexels API Key added successfully"))
            if config.app["pexels_api_keys"]:
                delete_key = st.selectbox(tr("Select Pexels API Key to delete"), config.app["pexels_api_keys"], key="pexels_delete_key")
                if st.button(tr("Delete Selected Pexels API Key")):
                    config.app["pexels_api_keys"].remove(delete_key)
                    config.save_config()
                    st.success(tr("Pexels API Key deleted successfully"))
        with col2:
            st.subheader("Pixabay API Keys")
            if config.app["pixabay_api_keys"]:
                st.write(tr("Current Keys:"))
                for key in config.app["pixabay_api_keys"]:
                    st.code(key)
            else:
                st.info(tr("No Pixabay API Keys currently"))
            new_key = st.text_input(tr("Add Pixabay API Key"), key="pixabay_new_key")
            if st.button(tr("Add Pixabay API Key")):
                if new_key and new_key not in config.app["pixabay_api_keys"]:
                    config.app["pixabay_api_keys"].append(new_key)
                    config.save_config()
                    st.success(tr("Pixabay API Key added successfully"))
            if config.app["pixabay_api_keys"]:
                delete_key = st.selectbox(tr("Select Pixabay API Key to delete"), config.app["pixabay_api_keys"], key="pixabay_delete_key")
                if st.button(tr("Delete Selected Pixabay API Key")):
                    config.app["pixabay_api_keys"].remove(delete_key)
                    config.save_config()
                    st.success(tr("Pixabay API Key deleted successfully"))

    nav_cols = st.columns([1, 1])
    with nav_cols[0]:
        if st.button("← 返回脚本", use_container_width=True):
            st.session_state["wizard_step"] = 2
            st.rerun()
    with nav_cols[1]:
        if st.button("下一步 → 🎬 生成视频", type="primary", use_container_width=True):
            st.session_state["wizard_step"] = 4
            st.rerun()

# ============================================================
# Step 5: 🎬 生成
# ============================================================
elif current_step == 4:
    st.subheader(STEPS[4])
    st.caption("确认所有参数无误后，点击生成视频")

    # 参数摘要
    summary_cols = st.columns(3)
    with summary_cols[0]:
        st.markdown("**🎯 主题**")
        st.write(st.session_state.get("video_subject", "(未设置)"))
        tmpl_id = st.session_state.get("niche_template_id", "")
        if tmpl_id:
            st.write(f"**🎨 赛道**: {tr('template_%s_name' % tmpl_id)}")
    with summary_cols[1]:
        st.markdown("**📝 脚本**")
        script = st.session_state.get("video_script", "")
        st.write(f"{len(script)} 字" if script else "(未生成)")
        terms = st.session_state.get("video_terms", "")
        st.write(f"**🔑 关键词**: {terms[:50] + '...' if len(terms) > 50 else terms or '(未生成)'}")
    with summary_cols[2]:
        st.markdown("**⚙️ 设置**")
        st.write(f"视频源: {config.app.get('video_source', 'pexels')}")
        st.write(f"音色: {config.ui.get('voice_name', '默认')[:30]}...")

    if st.button("🎬 " + tr("Generate Video"), use_container_width=True, type="primary"):
        config.save_config()
        task_id = str(uuid4())

        params.video_subject = st.session_state.get("video_subject", "")
        params.video_script = st.session_state.get("video_script", "")
        terms_str = st.session_state.get("video_terms", "")
        params.video_terms = terms_str

        if not params.video_subject and not params.video_script:
            st.error(tr("Video Script and Subject Cannot Both Be Empty"))
            st.stop()

        if uploaded_audio_file:
            task_dir = utils.task_dir(task_id)
            _, audio_ext = os.path.splitext(os.path.basename(uploaded_audio_file.name))
            audio_ext = audio_ext.lower() or ".mp3"
            custom_audio_path = os.path.join(task_dir, f"custom-audio{audio_ext}")
            with open(custom_audio_path, "wb") as f:
                f.write(uploaded_audio_file.getbuffer())
            params.custom_audio_file = custom_audio_path

        if uploaded_files:
            local_videos_dir = utils.storage_dir("local_videos", create=True)
            params.video_materials = []
            for file in uploaded_files:
                file_path = os.path.join(local_videos_dir, f"{file.file_id}_{file.name}")
                with open(file_path, "wb") as f:
                    f.write(file.getbuffer())
                    m = MaterialInfo()
                    m.provider = "local"
                    m.url = file_path
                    params.video_materials.append(m)

        log_container = st.empty()
        log_records = []

        def log_received(msg):
            if config.ui["hide_log"]:
                return
            with log_container:
                log_records.append(msg)
                st.code("\n".join(log_records))

        logger.add(log_received)

        st.toast(tr("Generating Video"))
        logger.info(tr("Start Generating Video"))
        logger.info(utils.to_json(params))

        result = tm.start(task_id=task_id, params=params)
        if not result or "videos" not in result:
            st.error(tr("Video Generation Failed"))
            logger.error(tr("Video Generation Failed"))
            st.stop()

        video_files = result.get("videos", [])
        st.success(tr("Video Generation Completed"))
        try:
            if video_files:
                player_cols = st.columns(len(video_files) * 2 + 1)
                for i, url in enumerate(video_files):
                    player_cols[i * 2 + 1].video(url)
        except Exception:
            pass

        open_task_folder(task_id)
        logger.info(tr("Video Generation Completed"))

    nav_cols = st.columns([1, 1])
    with nav_cols[0]:
        if st.button("← 返回设置", use_container_width=True):
            st.session_state["wizard_step"] = 3
            st.rerun()
    with nav_cols[1]:
        if st.button("🔄 重新开始", use_container_width=True):
            st.session_state["wizard_step"] = 0
            st.rerun()

config.save_config()
