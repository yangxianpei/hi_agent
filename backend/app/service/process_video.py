from typing import Any

import json
from app.utils.logger import get_logger
logger = get_logger(__name__)
from app.utils.video_utils.com_helper import results_to_md,results_ai_to_md
from app.utils.video_utils.generate_heading import generate_heading
from app.utils.video_utils.ASR_VAD import asr_vad
from pathlib import Path
from app.utils.video_utils.video_cut import video_cut
from app.utils.video_task_events import emit


def process_video(file_path: str, wav_file_path: str, output_dir: str):
    output_dir = Path(output_dir)
    tk = output_dir.name

    def _stage(stage: str, message: str = "", data: dict | None = None):
        emit(tk, stage, message, data or {})

    try:
        _stage("started", "开始处理", {"file_path": file_path})

        # 第一步 ASR 语音识别
        logger.info(f" ASR 语音识别 {file_path}")
        _stage("asr_started", "语音识别中")
        before_merge = asr_vad.run_pipeline(file_path, wav_file_path)
        logger.info(f" 存入before_merge.json")
        with open(output_dir / "before_merge.json", "w", encoding="utf-8") as f:
            json.dump(before_merge, f, ensure_ascii=False, indent=2)
        merge_res = asr_vad.merge_to_paragraphs(before_merge)
        logger.info(f" 存入merge.json")
        with open(output_dir / "merge.json", "w", encoding="utf-8") as f:
            json.dump(merge_res, f, ensure_ascii=False, indent=2)
        _stage("asr_done", "ASR 与段落合并完成", {"segments": len(merge_res)})

        cxt = []
        for i, chunk in enumerate[Any](merge_res):
            heading = generate_heading.generate_heading(chunk["text"])
            logger.info(f"生成标题: {heading}")
            cxt.append(
                {
                    "speaker": chunk["speaker"],
                    "heading": heading,
                    "text": chunk["text"],
                    "start": chunk["start"],
                    "end": chunk["end"],
                }
            )
        mdstr = results_to_md(cxt)
        with open(output_dir / "origin_result.md", "w", encoding="utf-8") as f:
            f.write(mdstr)
        logger.info(f" 存入origin_result.md")
        _stage("origin_md_done", "已生成 origin_result.md")

        try:
            video_cut_path = output_dir / "video_cut"
            video_cut(
                merge_res,
                str(video_cut_path),
                file_path,
                run_similarity=False,
                similarity_threshold=0.2,
                similarity_top_k=3,
                cxt=cxt,
                real_output_dir=str(output_dir),
            )
            logger.info("抽帧与 OCR 相似度任务已提交到 video_cut 子线程池")
            _stage("video_cut_submitted", "抽帧任务已提交后台线程")
        except Exception as e:
            logger.error(f"切割视频失败: {e}")
            _stage("video_cut_error", str(e), {"error": str(e)})

        _stage("ai_started", "开始生成 AI 解读")
        Ai_cxt = []
        for i, chunk in enumerate[Any](cxt):
            ai_text = generate_heading.generate_Ai_think(chunk["heading"], chunk["text"])
            logger.info(f"AI生成对应标题的思考: {ai_text}")
            Ai_cxt.append(
                {
                    "speaker": chunk["speaker"],
                    "heading": chunk["heading"],
                    "text": chunk["text"],
                    "Ai_text": ai_text,
                    "start": chunk["start"],
                    "end": chunk["end"],
                }
            )

        Ai_mdstr = results_ai_to_md(Ai_cxt)
        with open(output_dir / "Ai_result.md", "w", encoding="utf-8") as f:
            f.write(Ai_mdstr)
        logger.info(f" 存入Ai_result.md")
        _stage("ai_done", "已生成 Ai_result.md")

        _stage("finished", "主流程处理完成（抽帧若后台进行会另发 video_cut_done）")
    except Exception as e:
        logger.exception("process_video 失败")
        emit(tk, "error", str(e), {"error": str(e)})







