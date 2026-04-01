from datetime import datetime
from pathlib import Path
from app.utils.logger import get_logger
logger = get_logger(__name__)
from dotenv import load_dotenv
import os
load_dotenv()

def _cn_index(num: int) -> str:
    digits = "零一二三四五六七八九"
    if num <= 10:
        return "十" if num == 10 else digits[num]
    if num < 20:
        return "十" + digits[num % 10]
    if num < 100:
        tens, ones = divmod(num, 10)
        return digits[tens] + "十" + (digits[ones] if ones else "")
    return str(num)


def results_to_md(results: list[dict], title: str = "识别结果") -> str:
    logger.info(f"开始将识别结果转换为markdown格式")
    try:

        lines = [f"# {title}", "", f"- 生成时间：{datetime.now().isoformat(timespec='seconds')}"]
        for idx, r in enumerate(results, start=1):
            # lines.append(f"  -({r['start']:.0f}s–{r['end']:.0f}s)")
            lines.append(f"   ## {_cn_index(idx)}、{r.get('heading','').strip()}")
            lines.append(f"   {r.get('text','').strip()}")
            lines.append("")
        return "\n".join(lines)
    except Exception as e:
        logger.error(f"将识别结果转换为markdown格式失败: {e}")
        return ""


def results_ai_to_md(results: list[dict], title: str = "识别结果") -> str:
    logger.info(f"开始将识别结果转换为markdown格式")
    try:
        lines = [f"# {title}", "", f"- 生成时间：{datetime.now().isoformat(timespec='seconds')}"]
        lines.append("")
        lines.append("## 原文（含时间）")
        lines.append("")
        for idx, r in enumerate(results, start=1):
            lines.append(f"### {_cn_index(idx)}、{r.get('heading', '').strip()}")
            lines.append(f"> 时间：{r.get('start', 0):.3f}s - {r.get('end', 0):.3f}s")
            lines.append(f"> 原文：{r.get('text','').strip()}")
            lines.append("")

            lines.append("## AI生成")
            lines.append("")
            lines.append(f"### {_cn_index(idx)}、{r.get('heading', '').strip()}")
            lines.append(f"{r.get('Ai_text','').strip()}")
            lines.append("")
  
        return "\n".join(lines)
    except Exception as e:
        logger.error(f"将识别结果转换为markdown格式失败: {e}")
        return ""

def results_ai_video_cut_to_md(results: list[dict], frame_dir: Path, title: str = "识别结果") -> str:
    logger.info(f"开始将识别结果转换为markdown格式")
    try:

        lines = [f"# {title}", "", f"- 生成时间：{datetime.now().isoformat(timespec='seconds')}"]
        task_id = frame_dir.parent.name
        url = os.getenv("URL","").rstrip("/")
        base_url = f"{url}/output/{task_id}/video_cut"
        for idx, r in enumerate(results, start=1):
        
            seg_frame_dir = frame_dir / f"{idx}_frames"
            frame_files = sorted(seg_frame_dir.glob("*.jpg"))
            lines.append(f"   ## {_cn_index(idx)}、{r.get('heading','').strip()}")
            lines.append(f"   {r.get('text','').strip()}")
            lines.append("")
            for img in frame_files:
                img_url = f"{base_url}/{idx}_frames/{img.name}"
                lines.append(f'<img src="{img_url}" alt="{img.name}" width="420" />')
            lines.append("")
        return "\n".join(lines)
    except Exception as e:
        logger.error(f"将识别结果转换为markdown格式失败: {e}")
        return ""



