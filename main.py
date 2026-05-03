import argparse
import os
from pathlib import Path
from video_transcriber import VideoTranscriber
from ai_summarizer import AISummarizer


def process_single_video(video_path: str, output_dir: str, model_size: str, style: str, skip_ai: bool):
    video_name = Path(video_path).stem
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"\n{'='*60}")
    print(f"处理视频: {video_path}")
    print(f"{'='*60}\n")
    
    transcriber = VideoTranscriber(model_size=model_size)
    result = transcriber.process_video(video_path)
    
    transcript_path = output_dir / f"{video_name}_transcript.txt"
    transcriber.save_transcript(result, str(transcript_path), format="txt")
    
    srt_path = output_dir / f"{video_name}_subtitles.srt"
    transcriber.save_transcript(result, str(srt_path), format="srt")
    
    segments_path = output_dir / f"{video_name}_segments.txt"
    transcriber.save_transcript(result, str(segments_path), format="segments")
    
    if not skip_ai:
        print("\n开始AI整理...")
        summarizer = AISummarizer()
        summary = summarizer.summarize(result['text'], style=style)
        
        summary_path = output_dir / f"{video_name}_{style}.md"
        summarizer.save_summary(summary, str(summary_path))
    
    print(f"\n{'='*60}")
    print("处理完成！输出文件：")
    print(f"  - 转录文本: {transcript_path}")
    print(f"  - 字幕文件: {srt_path}")
    print(f"  - 分段文本: {segments_path}")
    if not skip_ai:
        print(f"  - AI整理: {summary_path}")
    print(f"{'='*60}\n")


def process_directory(input_dir: str, output_dir: str, model_size: str, style: str, skip_ai: bool):
    video_extensions = {'.mp4', '.avi', '.mov', '.mkv', '.flv', '.wmv', '.m4v'}
    input_path = Path(input_dir)
    
    video_files = [
        f for f in input_path.rglob('*')
        if f.is_file() and f.suffix.lower() in video_extensions
    ]
    
    if not video_files:
        print(f"在 {input_dir} 中没有找到视频文件")
        return
    
    print(f"找到 {len(video_files)} 个视频文件\n")
    
    for i, video_file in enumerate(video_files, 1):
        print(f"\n处理进度: {i}/{len(video_files)}")
        try:
            process_single_video(
                str(video_file),
                output_dir,
                model_size,
                style,
                skip_ai
            )
        except Exception as e:
            print(f"处理 {video_file} 时出错: {str(e)}")
            continue


def main():
    parser = argparse.ArgumentParser(
        description='视频转文字工具 - 自动提取视频内容并生成文字教程',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例用法:
  处理单个视频:
    python main.py -i video.mp4 -o output
  
  处理整个文件夹:
    python main.py -i videos/ -o output --batch
  
  只转录不使用AI:
    python main.py -i video.mp4 -o output --skip-ai
  
  生成学习笔记格式:
    python main.py -i video.mp4 -o output --style notes
        """
    )
    
    parser.add_argument('-i', '--input', required=True, help='输入视频文件或文件夹路径')
    parser.add_argument('-o', '--output', default='output', help='输出文件夹路径 (默认: output)')
    parser.add_argument('-m', '--model', default='base', 
                       choices=['tiny', 'base', 'small', 'medium', 'large'],
                       help='Whisper模型大小 (默认: base, 推荐base或small)')
    parser.add_argument('-s', '--style', default='tutorial',
                       choices=['tutorial', 'summary', 'notes'],
                       help='AI整理风格 (默认: tutorial)')
    parser.add_argument('--batch', action='store_true', help='批量处理文件夹中的所有视频')
    parser.add_argument('--skip-ai', action='store_true', help='跳过AI整理，只进行转录')
    
    args = parser.parse_args()
    
    if not os.path.exists(args.input):
        print(f"错误: 输入路径不存在: {args.input}")
        return
    
    if args.batch or os.path.isdir(args.input):
        process_directory(args.input, args.output, args.model, args.style, args.skip_ai)
    else:
        process_single_video(args.input, args.output, args.model, args.style, args.skip_ai)


if __name__ == '__main__':
    main()
