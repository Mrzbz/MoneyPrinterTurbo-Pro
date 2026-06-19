#!/usr/bin/env python3
"""
MoneyPrinterTurbo-Pro 自动生成视频 CLI
========================================
全自动化视频生成流水线：主题 → 赛道模板 → AI 脚本 → 关键词 → 视频 → 下载

用法:
  # 从主题开始，全自动生成（AI 自动写脚本、生成关键词、合成视频）
  python auto_generate.py --topic "如何理财" --template finance

  # 指定现成的脚本（跳过 AI 生成步骤，直接合成视频）
  python auto_generate.py --script "我的理财心得..." --template finance

  # 只生成脚本（不生成视频，方便手动编辑后再合成）
  python auto_generate.py --topic "如何理财" --template finance --script-only

  # 指定视频参数
  python auto_generate.py --topic "如何理财" --template finance --count 2 --aspect 9:16

可用赛道: finance, health, tech, education, food, motivation, story, travel
"""

import argparse
import json
import os
import sys
import time
import urllib.request
import urllib.error
from pathlib import Path

API_BASE = os.environ.get("MPT_API_BASE", "http://127.0.0.1:8080/api/v1")
DOWNLOAD_DIR = os.environ.get("MPT_DOWNLOAD_DIR", os.path.join(os.path.dirname(__file__), "storage", "tasks"))

TEMPLATE_NAMES = {
    "finance": "财经理财",
    "health": "健康养生",
    "tech": "科技数码",
    "education": "知识教育",
    "food": "美食教程",
    "motivation": "励志鸡汤",
    "story": "悬疑故事",
    "travel": "旅行攻略",
}

TEMPLATE_CHINESE_TO_ID = {v: k for k, v in TEMPLATE_NAMES.items()}


def api_post(path: str, data: dict) -> dict:
    url = f"{API_BASE}{path}"
    req = urllib.request.Request(
        url,
        data=json.dumps(data).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=300) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        print(f"  [错误] HTTP {e.code}: {body}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"  [错误] 请求失败: {e}", file=sys.stderr)
        sys.exit(1)


def api_get(path: str) -> dict:
    url = f"{API_BASE}{path}"
    try:
        with urllib.request.urlopen(url, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        print(f"  [错误] HTTP {e.code}: {body}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"  [错误] 请求失败: {e}", file=sys.stderr)
        sys.exit(1)


def generate_script(
    topic: str,
    language: str = "",
    paragraph_number: int = 1,
    script_prompt: str = "",
    system_prompt: str = "",
) -> str:
    print(f"  🤖 AI 正在生成脚本...")
    resp = api_post("/scripts", {
        "video_subject": topic,
        "video_language": language,
        "paragraph_number": paragraph_number,
        "video_script_prompt": script_prompt,
        "custom_system_prompt": system_prompt,
    })
    script = resp.get("data", {}).get("video_script", "")
    if not script:
        print("  [错误] AI 生成脚本失败，返回为空", file=sys.stderr)
        sys.exit(1)
    preview = script[:80].replace("\n", " ")
    print(f"  ✅ 脚本生成成功 ({len(script)} 字符)")
    print(f"     预览: {preview}...")
    return script


def generate_terms(topic: str, script: str, amount: int = 5) -> list:
    print(f"  🔍 AI 正在生成搜索关键词...")
    resp = api_post("/terms", {
        "video_subject": topic,
        "video_script": script,
        "amount": amount,
    })
    terms = resp.get("data", {}).get("video_terms", [])
    if isinstance(terms, str):
        terms = [t.strip() for t in terms.split(",") if t.strip()]
    print(f"  ✅ 关键词生成成功: {', '.join(terms[:5])}")
    return terms


def create_video(params: dict) -> str:
    print(f"  🎬 正在提交视频生成任务...")
    resp = api_post("/videos", params)
    data = resp.get("data", {})
    task_id = data.get("task_id", "")
    if not task_id:
        print(f"  [错误] 创建任务失败: {resp}", file=sys.stderr)
        sys.exit(1)
    print(f"  ✅ 任务已提交: {task_id}")
    return task_id


def wait_for_task(task_id: str, poll_interval: int = 5, timeout: int = 600) -> dict:
    print(f"  ⏳ 等待任务完成 (每 {poll_interval}s 轮询, 超时 {timeout}s)...")
    start = time.time()
    last_progress = ""
    while True:
        elapsed = int(time.time() - start)
        if elapsed > timeout:
            print(f"\n  [错误] 任务超时 ({timeout}s)", file=sys.stderr)
            sys.exit(1)

        resp = api_get(f"/tasks/{task_id}")
        task = resp.get("data", {})
        state = task.get("state", "unknown")
        progress = task.get("progress", "")

        if progress and progress != last_progress:
            print(f"     [{elapsed}s] {progress}")
            last_progress = progress

        if state == "completed":
            print(f"  ✅ 视频生成完成! (耗时 {elapsed}s)")
            return task
        elif state == "failed":
            error = task.get("error", "未知错误")
            print(f"\n  [错误] 任务失败: {error}", file=sys.stderr)
            sys.exit(1)

        time.sleep(poll_interval)


def download_video(task: dict, task_id: str, output_dir: str = None) -> list:
    videos = task.get("videos", [])
    if not videos:
        # Try combined_videos
        videos = task.get("combined_videos", [])

    if not videos:
        print("  [警告] 没有找到视频文件")
        return []

    if output_dir is None:
        output_dir = os.path.join(DOWNLOAD_DIR, task_id)
    os.makedirs(output_dir, exist_ok=True)

    downloaded = []
    for i, video_url in enumerate(videos):
        if video_url.startswith("/"):
            video_url = f"http://127.0.0.1:8080{video_url}"

        filename = f"final-{i+1}.mp4"
        filepath = os.path.join(output_dir, filename)

        print(f"  📥 下载视频 {i+1}/{len(videos)}...")
        try:
            urllib.request.urlretrieve(video_url, filepath)
            size_mb = os.path.getsize(filepath) / (1024 * 1024)
            print(f"     → {filepath} ({size_mb:.1f} MB)")
            downloaded.append(filepath)
        except Exception as e:
            print(f"     [错误] 下载失败: {e}", file=sys.stderr)

    return downloaded


def resolve_template(template_arg: str) -> str | None:
    if not template_arg:
        return None
    template_id = template_arg.lower()
    if template_id in TEMPLATE_NAMES:
        return template_id
    if template_id in TEMPLATE_CHINESE_TO_ID:
        return TEMPLATE_CHINESE_TO_ID[template_id]
    valid = list(TEMPLATE_NAMES.keys())
    print(f"[错误] 未知赛道: '{template_arg}'. 可用: {', '.join(valid)}", file=sys.stderr)
    sys.exit(1)


def get_template_prompt(template_id: str, topic: str) -> str:
    """从模板系统生成脚本提示词（调用本地 Python 模块）"""
    sys.path.insert(0, os.path.dirname(__file__))
    try:
        from app.templates import get_template_manager
        mgr = get_template_manager()
        if template_id not in mgr:
            print(f"[错误] 模板 '{template_id}' 不存在", file=sys.stderr)
            return ""
        data = mgr.generate_prompt(template_id, topic or "your topic")
        return data.get("script_prompt", "")
    except ImportError:
        print("  [警告] 无法加载模板系统，跳过模板提示词", file=sys.stderr)
        return ""


def print_summary(result: dict):
    videos = result.get("videos", []) or result.get("combined_videos", [])
    print()
    print("=" * 50)
    print("  🎉 自动化视频生成完成!")
    print(f"  任务 ID: {result.get('task_id', 'N/A')}")
    if videos:
        print(f"  视频数量: {len(videos)}")
        for i, v in enumerate(videos):
            print(f"    视频 {i+1}: {v}")
    print("=" * 50)


def main():
    parser = argparse.ArgumentParser(
        description="MoneyPrinterTurbo-Pro 自动生成视频",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    # 必选参数（主题或脚本至少一个）
    content_group = parser.add_mutually_exclusive_group(required=True)
    content_group.add_argument("--topic", "-t", help="视频主题（AI 自动生成脚本）")
    content_group.add_argument("--script", "-s", help="直接提供视频文案（跳过 AI 生成脚本）")

    # 可选参数
    parser.add_argument("--template", "-T", help=f"赛道模板: {', '.join(TEMPLATE_NAMES.keys())}")
    parser.add_argument("--script-only", action="store_true", help="只生成脚本，不生成视频")
    parser.add_argument("--terms-only", action="store_true", help="只生成关键词，不生成视频")
    parser.add_argument("--language", "-l", default="", help="脚本语言（留空自动检测）")
    parser.add_argument("--paragraphs", "-p", type=int, default=1, help="脚本段落数 (1-10)")
    parser.add_argument("--count", "-n", type=int, default=1, help="同时生成视频数量 (1-5)")
    parser.add_argument("--aspect", "-a", default="9:16", choices=["9:16", "16:9", "1:1"], help="视频比例")
    parser.add_argument("--output", "-o", help="视频下载目录")
    parser.add_argument("--prompt", help="自定义文案要求（追加到赛道模板之后）")
    parser.add_argument("--system-prompt", help="自定义系统提示词（覆盖默认）")
    parser.add_argument("--poll-interval", type=int, default=5, help="轮询间隔(秒)")
    parser.add_argument("--timeout", type=int, default=600, help="超时时间(秒)")

    args = parser.parse_args()

    topic = args.topic or ""

    # --- 步骤 0: 解析赛道模板 ---
    template_id = resolve_template(args.template) if args.template else None
    print(f"\n{'='*50}")
    if template_id:
        print(f"  赛道: {TEMPLATE_NAMES[template_id]} ({template_id})")
    else:
        print(f"  赛道: 无 (通用模式)")
    print(f"  主题: {topic or '(直接提供脚本)'}")
    print(f"{'='*50}\n")

    # --- 步骤 1: 获取脚本 ---
    script = args.script
    if not script:
        # 从模板生成提示词
        script_prompt = ""
        if template_id:
            script_prompt = get_template_prompt(template_id, topic)
        # 追加自定义 prompt
        if args.prompt:
            if script_prompt:
                script_prompt += f"\n{args.prompt}"
            else:
                script_prompt = args.prompt

        script = generate_script(
            topic=topic,
            language=args.language,
            paragraph_number=args.paragraphs,
            script_prompt=script_prompt,
            system_prompt=args.system_prompt or "",
        )
        print()
    else:
        print(f"  📝 使用直接提供的脚本 ({len(script)} 字符)\n")

    if args.script_only:
        print(f"\n{'='*50}")
        print("  脚本 (已保存至脚本文件)")
        print(f"{'='*50}\n")
        print(script)
        # Save to file
        out_path = args.output or os.path.join(os.path.dirname(__file__), "auto_generated_script.txt")
        if os.path.isdir(out_path):
            out_path = os.path.join(out_path, "script.txt")
        Path(out_path).write_text(script, encoding="utf-8")
        print(f"\n脚本已保存: {out_path}")
        return

    # --- 步骤 2: 生成关键词 ---
    if template_id:
        # Use template hashtags if available
        try:
            sys.path.insert(0, os.path.dirname(__file__))
            from app.templates import get_template_manager
            mgr = get_template_manager()
            tmpl = mgr.get_template(template_id)
            if tmpl:
                terms = tmpl.hashtags[:5]
                terms_str = ", ".join(terms)
                print(f"  🏷️  使用赛道预设标签: {terms_str}")
            else:
                terms = generate_terms(topic, script)
                terms_str = ", ".join(terms)
        except ImportError:
            terms = generate_terms(topic, script)
            terms_str = ", ".join(terms)
    else:
        terms = generate_terms(topic, script)
        terms_str = ", ".join(terms)

    print()

    if args.terms_only:
        print(f"关键词: {terms_str}")
        return

    # --- 步骤 3: 提交视频生成 ---
    voice_name = "zh-CN-YunxiNeural-Male"  # 中文男声（云希）
    video_params = {
        "video_subject": topic or "视频",
        "video_script": script,
        "video_terms": terms_str,
        "video_aspect": args.aspect,
        "video_count": args.count,
        "video_source": "pexels",
        "voice_name": voice_name,
        "voice_volume": 1.0,
        "voice_rate": 1.0,
        "bgm_type": "random",
        "bgm_volume": 0.2,
        "subtitle_enabled": True,
        "font_name": "MicrosoftYaHeiBold.ttc",
        "text_fore_color": "#FFFFFF",
        "font_size": 60,
        "stroke_color": "#000000",
        "stroke_width": 1.5,
    }

    task_id = create_video(video_params)

    # --- 步骤 4: 轮询等待 ---
    result = wait_for_task(task_id, poll_interval=args.poll_interval, timeout=args.timeout)

    # --- 步骤 5: 下载成品 ---
    downloads = download_video(result, task_id, args.output)

    print_summary(result)

    if downloads:
        print(f"\n  视频文件:")
        for f in downloads:
            print(f"    {f}")


if __name__ == "__main__":
    main()
