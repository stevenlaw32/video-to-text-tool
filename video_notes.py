"""
本地视频转笔记命令行入口。

抽出语音 / 画面文字，再用 models.json 里当前模型和提示词整理。
进度打在终端；结构化结果写入 --json-out，供 skill 收尾落盘。
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional, Tuple

from dotenv import load_dotenv
from openai import OpenAI

PROJECT_ROOT = Path(__file__).resolve().parent
os.chdir(PROJECT_ROOT)
load_dotenv(PROJECT_ROOT / ".env")

from models_config import ModelsConfig
from prompt_presets import get_default_prompt, get_prompt


MODE_CHOICES = ("whisper", "ocr", "hybrid")
WHISPER_CHOICES = ("tiny", "base", "small", "medium", "large")
LANG_CHOICES = ("zh", "en", "ja", "ko")
VIDEO_SUFFIXES = {".mp4", ".avi", ".mov", ".mkv", ".flv", ".wmv", ".m4v", ".webm"}

HYBRID_PREFIX = (
    "你收到的内容来自同一视频的两路提取：\n"
    "- **音频转录**（语音识别）：口述内容，可能因语速过快而有所遗漏\n"
    "- **画面文字**（OCR 识别）：视频画面中的文字，通常更完整准确\n\n"
    "融合规则（严格执行）：\n"
    "1. **两路内容同等重要**，任意一路中出现的信息都必须保留在最终笔记中\n"
    "2. **不得因音频未提及而遗漏 OCR 内容**——音频可能因语速过快或识别误差而有缺漏，OCR 是补充音频的关键依据\n"
    "3. 两路都提到同一内容时，合并为一条，以 OCR 的精确文字（名称、地址、数据）为准\n"
    "4. 音频负责提供叙述语气和上下文逻辑，OCR 负责提供精确的专有名词和数字\n\n"
    "请将两路内容完整融合后，按以下要求整理笔记：\n\n---\n\n"
)


def log(message: str) -> None:
    print(message, flush=True)


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def transcribe_audio(video_path: Path, model_size: str, language: str) -> str:
    from video_transcriber import VideoTranscriber

    transcriber = VideoTranscriber(model_size=model_size)
    result = transcriber.process_video(str(video_path), language=language)
    return (result.get("text") or "").strip()


def extract_ocr(video_path: Path) -> Tuple[str, int, str]:
    from ocr_config import OCRConfig
    from simple_ocr import SimpleOCR

    ocr_config = OCRConfig(str(PROJECT_ROOT / "ocr_apis.json"))
    provider = ocr_config.get_active_provider()
    provider_config = ocr_config.get_provider_config(provider) or {}
    if provider not in ("baidu", "tencent", "aliyun"):
        raise ValueError(
            f"画面识别需要云端 OCR（百度/腾讯云/阿里云），当前是 {provider_config.get('name', provider)}。"
            "请先在网页「OCR 配置」里切换并保存。"
        )
    processor = SimpleOCR()
    result = processor.process_video(
        str(video_path),
        interval=1.0,
        cloud_provider=provider,
        cloud_config=provider_config,
    )
    return (
        (result.get("text") or "").strip(),
        int(result.get("frame_count") or 0),
        provider_config.get("name", provider),
    )


def build_transcript(mode: str, audio_text: str, ocr_text: str) -> str:
    if mode == "whisper":
        return audio_text
    if mode == "ocr":
        return ocr_text
    if audio_text and ocr_text:
        return (
            f"## 音频转录内容（语音识别）\n\n{audio_text}\n\n"
            f"---\n\n"
            f"## 画面文字内容（OCR 识别）\n\n{ocr_text}"
        )
    return audio_text or ocr_text


def get_ai_client(
    model_alias: str = "",
    prompt_preset: str = "restructure",
) -> Tuple[OpenAI, str, str, Optional[int], Optional[float], Optional[str], str]:
    models_config = ModelsConfig(str(PROJECT_ROOT / "models.json"))
    model_config = None
    if model_alias:
        model_config = models_config.get_model_by_alias(model_alias)
    if not model_config:
        model_config = models_config.get_active_model()

    prompt = get_prompt(prompt_preset) if prompt_preset else get_default_prompt()

    if model_config:
        client = OpenAI(api_key=model_config["api_key"], base_url=model_config["base_url"])
        model_name = model_config["model_name"]
        display = model_config.get("alias") or model_name
        return (
            client,
            model_name,
            prompt,
            model_config.get("max_tokens"),
            model_config.get("temperature", 0.7),
            model_config.get("reasoning_effort"),
            display,
        )

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("未找到可用的 AI 模型。请先在网页「多模型」里配置并设为当前模型。")
    client = OpenAI(api_key=api_key, base_url=os.getenv("OPENAI_BASE_URL"))
    model_name = os.getenv("MODEL_NAME", "gpt-4o")
    return client, model_name, prompt, None, 0.7, None, model_name


def summarize(
    transcript: str,
    title: str,
    mode: str,
    model_alias: str = "",
    prompt_preset: str = "restructure",
) -> Tuple[str, str]:
    client, model_name, prompt_tpl, max_tokens, temperature, reasoning_effort, display = get_ai_client(
        model_alias, prompt_preset
    )
    tpl = prompt_tpl
    is_dual_source = (
        mode == "hybrid"
        and "## 音频转录内容" in transcript
        and "## 画面文字内容" in transcript
    )
    if is_dual_source:
        tpl = HYBRID_PREFIX + tpl
    if "{transcript}" in tpl:
        prompt = tpl.replace("{transcript}", transcript)
    else:
        header = f"# 标题：{title}\n\n" if title else ""
        prompt = header + tpl + "\n\n---\n\n转录内容：\n" + transcript

    req_params: Dict = {
        "model": model_name,
        "messages": [
            {"role": "system", "content": "你是一个专业的内容整理助手，擅长将视频转录文本整理成结构化的文档。"},
            {"role": "user", "content": prompt},
        ],
    }
    if temperature is not None:
        req_params["temperature"] = temperature
    if max_tokens:
        req_params["max_tokens"] = max_tokens
    if reasoning_effort:
        req_params["extra_body"] = {"reasoning_effort": reasoning_effort}

    log(f"🤖 调用整理模型：{display} / {model_name}")
    resp = client.chat.completions.create(**req_params)
    text = (resp.choices[0].message.content or "").strip()
    log(f"✓ 整理完成：{len(text)} 字符")
    return text, display


def process_video(
    video_path: Path,
    mode: str,
    whisper_model: str,
    language: str,
    model_alias: str = "",
    prompt_preset: str = "restructure",
) -> dict:
    warnings = []
    audio_text = ""
    ocr_text = ""
    ocr_frames = 0
    ocr_engine = ""

    if mode in ("whisper", "hybrid"):
        try:
            audio_text = transcribe_audio(video_path, whisper_model, language)
            log(f"✓ 语音转录：{len(audio_text)} 字符")
        except Exception as exc:
            msg = f"语音转录失败: {exc}"
            log(f"⚠️  {msg}")
            warnings.append(msg)
            if mode == "whisper":
                raise

    if mode in ("ocr", "hybrid"):
        try:
            ocr_text, ocr_frames, ocr_engine = extract_ocr(video_path)
            log(f"✓ 画面识别：{len(ocr_text)} 字符，{ocr_frames} 帧（{ocr_engine}）")
        except Exception as exc:
            msg = f"画面识别失败: {exc}"
            log(f"⚠️  {msg}")
            warnings.append(msg)
            if mode == "ocr":
                raise

    transcript = build_transcript(mode, audio_text, ocr_text)
    if not transcript.strip():
        raise ValueError("没有提取到任何文本。请换一种处理模式，或检查视频是否有声音/画面文字。")

    title = video_path.stem
    summary, ai_display = summarize(transcript, title, mode, model_alias, prompt_preset)
    if not summary:
        warnings.append("整理模型返回空内容，笔记将仅包含原始提取文本")
        summary = transcript

    return {
        "success": True,
        "source": str(video_path),
        "title": title,
        "mode": mode,
        "whisper_model": whisper_model if mode != "ocr" else None,
        "language": language,
        "ocr_engine": ocr_engine or None,
        "ocr_frames": ocr_frames,
        "ai_model": ai_display,
        "prompt_preset": prompt_preset,
        "audio_chars": len(audio_text),
        "ocr_chars": len(ocr_text),
        "transcript": transcript,
        "ai_summary": summary,
        "warnings": warnings,
        "finished_at": datetime.now().isoformat(timespec="seconds"),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="本地视频转笔记（抽文本 + 按已配置模型整理）")
    parser.add_argument("video", help="本地视频文件路径")
    parser.add_argument("--mode", required=True, choices=MODE_CHOICES, help="whisper=只听声音, ocr=只认画面, hybrid=两路一起")
    parser.add_argument("--whisper-model", default="small", choices=WHISPER_CHOICES)
    parser.add_argument("--language", default="zh", choices=LANG_CHOICES)
    parser.add_argument("--model-alias", default="", help="models.json 里的模型别名；默认用当前激活模型")
    parser.add_argument(
        "--prompt-preset",
        default="restructure",
        choices=("restructure", "faithful"),
        help="整理重排=restructure（默认），尊重原文=faithful",
    )
    parser.add_argument("--json-out", required=True, help="结果 JSON 路径，供 skill 读取后写入下载文件夹")
    args = parser.parse_args()

    video_path = Path(args.video).expanduser().resolve()
    json_out = Path(args.json_out).expanduser().resolve()

    if not video_path.is_file():
        payload = {"success": False, "error": f"找不到视频文件: {video_path}"}
        write_json(json_out, payload)
        log(payload["error"])
        return 1
    if video_path.suffix.lower() not in VIDEO_SUFFIXES:
        log(f"⚠️  扩展名 {video_path.suffix} 不在常见视频列表里，仍继续处理")

    try:
        payload = process_video(
            video_path=video_path,
            mode=args.mode,
            whisper_model=args.whisper_model,
            language=args.language,
            model_alias=args.model_alias,
            prompt_preset=args.prompt_preset,
        )
        write_json(json_out, payload)
        log(f"RESULT_JSON={json_out}")
        return 0
    except Exception as exc:
        payload = {
            "success": False,
            "source": str(video_path),
            "mode": args.mode,
            "error": str(exc),
        }
        write_json(json_out, payload)
        log(f"❌ {exc}")
        log(f"RESULT_JSON={json_out}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
