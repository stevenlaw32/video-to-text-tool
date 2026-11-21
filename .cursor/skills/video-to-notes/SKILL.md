---
name: video-to-notes
description: >
  把本地视频提炼成按主题重组的 Markdown 深度笔记，保存到下载文件夹。
  用户说「提炼这个视频」「提炼视频」「把这个视频整理成笔记」时必须使用本 skill。
  默认用「整理重排」提示词，不是尊重原文。三种模式：只听声音、只认画面字、声音和画面一起抽。
  用 video-to-text-tool 已配置的模型做整理，聊天模型只负责提问、调度和落盘。
  用户说「帮我转存成文档」时不要用本 skill，改用 experimental-media-to-md。
  不要用本 skill 处理图片或在线链接。
---

# 本地视频转笔记

把用户给的**本地视频**抽成文字，用「整理重排」做成深度笔记，最后由你把结果写成 `.md` 存到下载文件夹。

惯用触发话术是：**提炼这个视频**。听到「提炼」就走本 skill，默认整理重排。

用户说 **帮我转存成文档** 时停下来，改用 `experimental-media-to-md`（尊重原文，不重排）。

不要开网页，不要启动 Flask。

## 分工

| 谁 | 做什么 |
|----|--------|
| 你 | 问模式和 Whisper、调用脚本、把整理结果写成 md 放到 `~/Downloads/` |
| `video_notes.py` | 语音/OCR 提取，并用 `models.json` 当前模型 + **整理重排** 提示词整理 |

不要自己根据转录稿重写笔记。工具返回的 `ai_summary` 就是正文。

## 1. 先问清楚再跑

用户一句话里已经说了的，不要再问。缺什么问什么，问完再调用脚本。

**处理模式**（必选，没有「自动」）：

1. 只听声音（`whisper`）
2. 只认画面字（`ocr`）
3. 声音和画面一起抽（`hybrid`）

**Whisper 模型**：选了 1 或 3 时必问。选项：`tiny` / `base` / `small` / `medium` / `large`。默认 **small**。不确定就选 small。选了「只认画面」则不问。

语言默认中文，不每次都问。用户说了英文/日文/韩文再改：`--language en|ja|ko`。

提炼默认用 `--prompt-preset restructure`（整理重排），不必再问用哪套提示词。

## 2. 调用工具

项目根目录：`/Users/steven_law/开发/video-to-text-tool`  
Python：`venv311/bin/python`（也可用环境变量 `VIDEO_TO_TEXT_TOOL` 覆盖根目录）

```bash
TOOL_ROOT="${VIDEO_TO_TEXT_TOOL:-$HOME/开发/video-to-text-tool}"
JSON_OUT="/tmp/video-notes-result.json"

"$TOOL_ROOT/venv311/bin/python" "$TOOL_ROOT/video_notes.py" "/绝对路径/视频.mp4" \
  --mode whisper \
  --whisper-model small \
  --language zh \
  --prompt-preset restructure \
  --json-out "$JSON_OUT"
```

`--mode` 只能是 `whisper` / `ocr` / `hybrid`。`ocr` 可省略 `--whisper-model`。

这是慢活。短视频也预留几分钟；超过 15 分钟把等待时间提到够用（例如 30–60 分钟）。看到终端出现 `RESULT_JSON=` 或 JSON 文件写好再往下。

失败时读 JSON 里的 `error`，原样告诉用户。不要改去自己转写。

## 3. 收尾：写成 md 放到下载文件夹

读 `--json-out` 指向的 JSON。

- `success` 为 false：报告 `error`，不要编一篇笔记。
- `ai_summary` 就是笔记正文。**原样写入**，不要重排、不要删「核心萃取」、不要再调一次大模型。
- 若 `ai_summary` 为空，再用 `transcript`，并说明整理模型没返回正文。

保存到 `~/Downloads/{短标题}-笔记.md`。

- 短标题优先用 JSON 的 `title`（视频文件名去掉后缀）。不要空格堆砌。
- 同名已存在就在文件名后加 `YYYYMMDD-HHMM`。
- 用户指定了别的路径，用指定路径。

文件结构：

```markdown
# {短标题}

> 来源：`{原文件名}` · 模式：{只听声音|只认画面|声音+画面} · 整理：{ai_model}

{ai_summary}
```

如果 `ai_summary` 已经以 `# ` 开头，就不要再套一层标题；只在文首保留引用行。

`warnings` 里有内容时，用一两句话告诉用户。

写完只回报下载路径和用了哪种模式，不要把全文贴进聊天。
