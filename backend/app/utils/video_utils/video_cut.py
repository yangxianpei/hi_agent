from app.utils.logger import get_logger
logger = get_logger(__name__)
import ffmpeg
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from typing import Callable
from app.utils.video_utils.ocr_similarity import select_similar_frames
from app.utils.video_utils.com_helper import results_ai_video_cut_to_md
executor = ThreadPoolExecutor(max_workers=10)


def _run_cut_task(video_path: str, start_time: float, end_time: float, frame_dir: Path, frame_interval_sec: float):
    # 按时间间隔抽帧（避免逐帧导致大量重复图），不保存中间 mp4 切片
    frame_dir.mkdir(parents=True, exist_ok=True)
    frame_pattern = frame_dir / "frame_%06d.jpg"
    fps = 1.0 / max(frame_interval_sec, 0.1)
    (
        ffmpeg
        .input(video_path, ss=start_time, to=end_time)
        .output(str(frame_pattern), format="image2", start_number=1, vf=f"fps={fps}")
        .overwrite_output()
        .run(quiet=True)
    )
    logger.info(f"时间段逐帧图片已生成: {frame_dir}")



def _run_on_cut_done_after_cut(futures, cxt, frame_dir, real_output_dir):
    for f in futures:
        f.result()
    try:
        mdstr = results_ai_video_cut_to_md(cxt, frame_dir)
        with open(real_output_dir / "Ai_video_cut_result.md", "w", encoding="utf-8") as f:
            f.write(mdstr)
        from app.utils.video_task_events import emit

        emit(
            Path(real_output_dir).name,
            "video_cut_done",
            "抽帧与 Ai_video_cut_result.md 已完成",
            {"path": "Ai_video_cut_result.md"},
        )
    except Exception as e:
        logger.error(f"视频切割完成回调执行失败: {e}")


def video_cut(
    list_data,
    output_path: str,
    video_path: str,
    frame_interval_sec: float = 1.0,
    run_similarity: bool = True,
    similarity_threshold: float = 0.2,
    similarity_top_k: int = 3,
    on_cut_done: Callable[[dict], None] | None = None,
    cxt: list[dict] | None = None,
    real_output_dir: str = "",
):
    output_dir = Path(output_path)
    output_dir.mkdir(parents=True, exist_ok=True)
    real_output_path = Path(real_output_dir) if real_output_dir else output_dir.parent
    futures = []
    for i, data in enumerate(list_data, start=1):
        start_time = float(data["start"])
        end_time = float(data["end"])
        end_time = float(data["end"])
        frame_dir = output_dir / f"{i}_frames"
        logger.info(f"开始抽帧: {frame_dir} ({start_time}-{end_time}s, interval={frame_interval_sec}s)")
        future = executor.submit(_run_cut_task, video_path, start_time, end_time, frame_dir, frame_interval_sec)
        futures.append(future)

    if cxt:
        executor.submit(_run_on_cut_done_after_cut, futures, cxt, output_dir, real_output_path)

    if run_similarity:
        executor.submit(
            select_similar_frames,
            list_data,
            output_dir,
            real_output_path / "ocr_similarity.json",
            similarity_threshold,
            similarity_top_k,
        )




