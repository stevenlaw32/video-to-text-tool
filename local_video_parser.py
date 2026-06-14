"""
视频链接下载器

抖音沿用 lark-video2note 的 iesdouyin share API 路径；小红书、
B站、快手等其它平台统一使用 yt-dlp。旧的站点专用解析器不再参与
运行链路，避免维护多套容易失效的下载逻辑。
"""

import asyncio
import importlib.util
import json
import logging
import os
import re
import requests
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class LocalVideoParser:
    """视频链接下载器：抖音专用路径 + yt-dlp 通用路径。"""

    UA_IOS = "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15"

    def __init__(self, download_dir: str = "temp_videos/link_downloads"):
        self.download_dir = Path(download_dir)
        self.download_dir.mkdir(parents=True, exist_ok=True)
        self.ytdlp_cmd = self._resolve_ytdlp()

    def _resolve_ytdlp(self) -> List[str]:
        """找到可用的 yt-dlp 命令。"""
        binary = shutil.which("yt-dlp")
        if binary:
            return [binary]

        fallback = Path("/tmp/yt-dlp-nightly")
        if fallback.exists() and os.access(fallback, os.X_OK):
            return [str(fallback)]

        if importlib.util.find_spec("yt_dlp"):
            return [sys.executable, "-m", "yt_dlp"]

        raise RuntimeError(
            "未找到 yt-dlp。请先安装：pip install yt-dlp，"
            "或把可执行文件放到 /tmp/yt-dlp-nightly"
        )

    def _extract_url(self, raw: str) -> str:
        match = re.search(r"https?://[^\s]+", raw or "")
        if not match:
            raise ValueError("未找到有效的视频链接")
        return match.group(0).strip()

    def _detect_platform(self, url: str, extractor: str = "") -> str:
        text = f"{url} {extractor}".lower()
        if "xiaohongshu.com" in text or "xhslink" in text or "xiaohongshu" in text:
            return "xiaohongshu"
        if "douyin.com" in text or "iesdouyin" in text or "douyin" in text:
            return "douyin"
        if "kuaishou.com" in text or "kuaishou" in text:
            return "kuaishou"
        if "bilibili.com" in text or "b23.tv" in text or "bilibili" in text:
            return "bilibili"
        if "youtube.com" in text or "youtu.be" in text or "youtube" in text:
            return "youtube"
        return (extractor or "video").lower()

    def _is_douyin_url(self, url: str) -> bool:
        lowered = url.lower()
        return "douyin.com" in lowered or "iesdouyin" in lowered

    def _cookie_args(self, url: str) -> List[str]:
        """短视频平台优先读取 Chrome 登录态。"""
        lowered = url.lower()
        needs_cookie = any(
            key in lowered
            for key in (
                "xiaohongshu.com",
                "xhslink",
                "kuaishou.com",
            )
        )
        return ["--cookies-from-browser", "chrome"] if needs_cookie else []

    def _safe_filename(self, value: str, max_length: int = 80) -> str:
        cleaned = re.sub(r'[/\\:*?"<>|\r\n\t]+', "", value or "").strip()
        return (cleaned[:max_length] or "untitled").strip()

    def _decode_json_text(self, value: str, fallback: str) -> str:
        if not value:
            return fallback
        try:
            return json.loads(f'"{value}"')
        except json.JSONDecodeError:
            return value or fallback

    def _unescape_url(self, value: str) -> str:
        return (
            value.replace("\\u002F", "/")
            .replace("\\u0026", "&")
            .replace("\\/", "/")
        )

    def _run_ytdlp(self, args: List[str], timeout: int) -> subprocess.CompletedProcess:
        cmd = self.ytdlp_cmd + args
        logger.info("运行 yt-dlp: %s", " ".join(cmd[:2] + ["..."]))
        return subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
        )

    def _resolve_douyin_video_id(self, url: str) -> str:
        response = requests.get(
            url,
            headers={"User-Agent": self.UA_IOS},
            allow_redirects=True,
            timeout=30,
        )
        final_url = response.url
        match = re.search(r"video/(\d+)", final_url) or re.search(r"aweme_id=(\d+)", final_url)
        if not match:
            raise ValueError(f"无法从抖音链接解析 video_id: {final_url}")
        return match.group(1)

    def _get_douyin_info(self, raw_url: str) -> Dict:
        url = self._extract_url(raw_url)
        video_id = self._resolve_douyin_video_id(url)
        share_url = f"https://www.iesdouyin.com/share/video/{video_id}/"

        response = requests.get(
            share_url,
            headers={"User-Agent": self.UA_IOS},
            timeout=30,
        )
        response.raise_for_status()
        html = response.text

        play_block = re.search(r'"play_addr":\{[^}]*"url_list":\[[^\]]*\]', html)
        if not play_block:
            raise ValueError("NOT_A_VIDEO: 这条抖音链接看起来不是视频，可能是图文内容或页面结构已变化")

        candidates = [
            self._unescape_url(item)
            for item in re.findall(r'https:[^"]+', play_block.group(0))
        ]
        play_url = next((item for item in candidates if "playwm" in item), None) or (candidates[0] if candidates else "")
        if not play_url:
            raise ValueError("未能从抖音 share 页面解析视频播放地址")

        title_match = re.search(r'"desc":"((?:\\.|[^"])*)"', html)
        author_match = re.search(r'"nickname":"((?:\\.|[^"])*)"', html)
        duration_match = re.search(r'"duration":(\d+)', html)

        title = self._decode_json_text(title_match.group(1) if title_match else "", f"douyin-{video_id}")
        author = self._decode_json_text(author_match.group(1) if author_match else "", "unknown")
        duration = int(duration_match.group(1)) / 1000 if duration_match else 0

        return {
            "success": True,
            "platform": "douyin",
            "title": title,
            "author": author,
            "duration": duration,
            "video_id": video_id,
            "thumbnail": "",
            "source_url": url,
            "video_url": play_url,
        }

    def _download_douyin(self, raw_url: str, output_dir: Optional[str] = None) -> Dict:
        target_dir = Path(output_dir) if output_dir else self.download_dir
        target_dir.mkdir(parents=True, exist_ok=True)

        info = self._get_douyin_info(raw_url)
        safe_title = self._safe_filename(info["title"])
        output_file = target_dir / f"douyin-{safe_title}.mp4"

        with requests.get(
            info["video_url"],
            headers={"User-Agent": self.UA_IOS},
            stream=True,
            timeout=120,
        ) as response:
            response.raise_for_status()
            with open(output_file, "wb") as f:
                for chunk in response.iter_content(chunk_size=1024 * 256):
                    if chunk:
                        f.write(chunk)

        if not output_file.exists() or output_file.stat().st_size < 10000:
            raise ValueError("抖音视频下载失败，输出文件为空或过小")

        info["file_path"] = str(output_file)
        info["video_file"] = str(output_file)
        info["file_size"] = output_file.stat().st_size
        return info

    def _parse_info_from_stdout(self, stdout: str) -> Dict:
        """yt-dlp 可能输出多行 JSON，取最后一个对象。"""
        for line in reversed(stdout.splitlines()):
            line = line.strip()
            if not line.startswith("{"):
                continue
            try:
                return json.loads(line)
            except json.JSONDecodeError:
                continue
        return {}

    def _find_downloaded_file(self, output_dir: Path, before: set[Path]) -> Optional[Path]:
        candidates = [
            p
            for p in output_dir.iterdir()
            if p.is_file() and p not in before and p.suffix.lower() in {".mp4", ".m4v", ".mov", ".webm", ".mkv"}
        ]
        if not candidates:
            candidates = [p for p in output_dir.iterdir() if p.is_file() and p not in before]
        if not candidates:
            return None
        return max(candidates, key=lambda p: p.stat().st_mtime)

    def _normalize_info(self, info: Dict, url: str, file_path: Optional[Path] = None) -> Dict:
        platform = self._detect_platform(url, info.get("extractor_key") or info.get("extractor") or "")
        return {
            "success": True,
            "platform": platform,
            "title": info.get("title") or "未命名视频",
            "author": info.get("uploader") or info.get("channel") or info.get("creator") or "unknown",
            "duration": info.get("duration") or 0,
            "video_id": info.get("id") or "",
            "thumbnail": info.get("thumbnail") or "",
            "source_url": url,
            "video_file": str(file_path) if file_path else "",
            "file_size": file_path.stat().st_size if file_path and file_path.exists() else 0,
        }

    async def parse(self, raw_url: str) -> Dict:
        """只读取视频元信息，不下载。"""
        return await asyncio.to_thread(self.parse_sync, raw_url)

    def parse_sync(self, raw_url: str) -> Dict:
        try:
            url = self._extract_url(raw_url)
            if self._is_douyin_url(url):
                return self._get_douyin_info(url)

            args = [
                "--dump-single-json",
                "--skip-download",
                "--no-playlist",
                *self._cookie_args(url),
                url,
            ]
            result = self._run_ytdlp(args, timeout=60)
            if result.returncode != 0:
                return {
                    "success": False,
                    "error": self._format_error(result.stderr),
                }

            info = self._parse_info_from_stdout(result.stdout)
            if not info:
                return {"success": False, "error": "yt-dlp 未返回可解析的视频信息"}

            data = self._normalize_info(info, url)
            data["video_url"] = info.get("url", "")
            return data
        except Exception as e:
            logger.exception("解析视频链接失败")
            return {"success": False, "error": str(e)}

    async def download(self, raw_url: str, output_dir: Optional[str] = None) -> Dict:
        """下载视频到本地，返回文件路径和元信息。"""
        return await asyncio.to_thread(self.download_sync, raw_url, output_dir)

    def download_sync(self, raw_url: str, output_dir: Optional[str] = None) -> Dict:
        try:
            url = self._extract_url(raw_url)
            if self._is_douyin_url(url):
                return self._download_douyin(url, output_dir)

            target_dir = Path(output_dir) if output_dir else self.download_dir
            target_dir.mkdir(parents=True, exist_ok=True)
            before = set(target_dir.iterdir())

            output_template = str(target_dir / "%(extractor_key)s-%(title).80s.%(ext)s")
            args = [
                "--no-playlist",
                "-f",
                "bv*+ba/b",
                "--merge-output-format",
                "mp4",
                "--print-json",
                "-o",
                output_template,
                *self._cookie_args(url),
                url,
            ]

            result = self._run_ytdlp(args, timeout=600)
            if result.returncode != 0:
                return {
                    "success": False,
                    "error": self._format_error(result.stderr),
                }

            info = self._parse_info_from_stdout(result.stdout)
            downloaded = self._find_downloaded_file(target_dir, before)
            if not downloaded:
                maybe_path = info.get("filepath") or info.get("_filename")
                if maybe_path and Path(maybe_path).exists():
                    downloaded = Path(maybe_path)

            if not downloaded or not downloaded.exists():
                return {"success": False, "error": "下载完成但未找到输出文件"}

            data = self._normalize_info(info, url, downloaded)
            data["file_path"] = str(downloaded)
            return data
        except subprocess.TimeoutExpired:
            return {"success": False, "error": "yt-dlp 下载超时"}
        except Exception as e:
            logger.exception("下载视频失败")
            return {"success": False, "error": str(e)}

    async def download_video(self, video_url: str, save_path: str) -> Dict:
        """兼容旧调用：现在 video_url 可以直接传原始页面链接。"""
        result = await self.download(video_url, str(Path(save_path).parent))
        if not result.get("success"):
            return result

        downloaded = Path(result["file_path"])
        save_path_obj = Path(save_path)
        if downloaded.resolve() != save_path_obj.resolve():
            save_path_obj.parent.mkdir(parents=True, exist_ok=True)
            if save_path_obj.exists():
                save_path_obj.unlink()
            downloaded.replace(save_path_obj)
            result["file_path"] = str(save_path_obj)
            result["video_file"] = str(save_path_obj)
            result["file_size"] = save_path_obj.stat().st_size
        return result

    def _format_error(self, stderr: str) -> str:
        text = (stderr or "").strip()
        if not text:
            return "yt-dlp 执行失败"
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        tail = "\n".join(lines[-6:])
        if "cookies" in tail.lower() or "login" in tail.lower():
            return f"{tail}\n请确认已在 Chrome 登录对应平台，并允许 yt-dlp 读取浏览器 Cookie。"
        return tail


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    parser = LocalVideoParser()
    test = sys.argv[1] if len(sys.argv) > 1 else ""
    if not test:
        print("用法: python local_video_parser.py <视频链接>")
        raise SystemExit(1)
    print(json.dumps(parser.download_sync(test), ensure_ascii=False, indent=2))
