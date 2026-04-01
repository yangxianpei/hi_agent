from pathlib import Path
from typing import Any
import json
import shutil

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from app.utils.logger import get_logger

logger = get_logger(__name__)


def _build_ocr_engine():
    try:
        from rapidocr_onnxruntime import RapidOCR

        return RapidOCR()
    except Exception as e:
        logger.error(f"OCR 引擎初始化失败，请安装 rapidocr-onnxruntime: {e}")
        return None


def _ocr_text(engine: Any, image_path: Path) -> str:
    try:
        result, _ = engine(str(image_path))
    except Exception:
        return ""
    if not result:
        return ""
    texts = [item[1] for item in result if len(item) > 1 and isinstance(item[1], str)]
    return " ".join(texts).strip()


def _text_similarity(a: str, b: str) -> float:
    if not a or not b:
        return 0.0
    vec = TfidfVectorizer(analyzer="char", ngram_range=(1, 2))
    x = vec.fit_transform([a, b])
    return float(cosine_similarity(x[0:1], x[1:2])[0][0])


def select_similar_frames(
    merge_res: list[dict],
    video_cut_dir: str | Path,
    output_json_path: str | Path,
    threshold: float = 0.2,
    top_k: int = 3,
) -> dict:
    """
    对每段文本对应帧目录做 OCR，并按文本相似度筛选最相似的帧。
    """
    engine = _build_ocr_engine()
    if engine is None:
        return {"items": [], "error": "ocr_engine_unavailable"}

    base_dir = Path(video_cut_dir)
    out_path = Path(output_json_path)
    similar_root_dir = out_path.parent / "similar_frames"
    similar_root_dir.mkdir(parents=True, exist_ok=True)
    out_items: list[dict] = []

    for idx, seg in enumerate(merge_res, start=1):
        seg_text = (seg.get("text") or "").strip()
        frame_dir = base_dir / f"{idx}_frames"
        frame_files = sorted(frame_dir.glob("*.jpg"))
        scored = []
        for fp in frame_files:
            ocr_txt = _ocr_text(engine, fp)
            score = _text_similarity(seg_text, ocr_txt)
            if score >= threshold:
                scored.append(
                    {
                        "frame": str(fp),
                        "score": round(score, 4),
                        "ocr_text": ocr_txt,
                    }
                )
        scored.sort(key=lambda x: x["score"], reverse=True)
        top_matches = scored[:top_k]
        similar_seg_dir = similar_root_dir / str(idx)
        similar_seg_dir.mkdir(parents=True, exist_ok=True)

        for rank, item in enumerate(top_matches, start=1):
            src = Path(item["frame"])
            dst_name = f"{rank}_{src.name}"
            dst = similar_seg_dir / dst_name
            shutil.copy2(src, dst)
            item["saved_frame"] = str(dst)
            item["saved_frame_rel"] = str(dst.relative_to(out_path.parent))

        out_items.append(
            {
                "index": idx,
                "speaker": seg.get("speaker"),
                "start": seg.get("start"),
                "end": seg.get("end"),
                "text": seg_text,
                "matches": top_matches,
            }
        )

    payload = {
        "threshold": threshold,
        "top_k": top_k,
        "items": out_items,
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    logger.info(f"OCR 相似帧结果已保存: {out_path}")
    return payload

