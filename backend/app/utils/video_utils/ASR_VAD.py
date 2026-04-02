import os

import numpy as np
import soundfile as sf
from funasr import AutoModel
from modelscope.pipelines import pipeline
from modelscope.utils.constant import Tasks
from sklearn.cluster import AgglomerativeClustering

from app.utils.logger import get_logger

logger = get_logger(__name__)


def _text_from_asr_result(asr_res) -> str:
    if asr_res is None:
        return ""
    if isinstance(asr_res, dict):
        return str(asr_res.get("text", "") or "")
    if isinstance(asr_res, list) and asr_res:
        return _text_from_asr_result(asr_res[0])
    return ""


class ASR_VAD:
    def __init__(self):
        self.asr_model = None
        self.vad_pipeline = None

    def pipeline(self):
        if self.asr_model is None:
            asr_path = (os.getenv("ASR_MODEL") or "").strip()
            if not asr_path:
                raise ValueError("环境变量 ASR_MODEL 未设置")
            punc_path = (os.getenv("PUNC_MODEL") or "").strip()
            if not punc_path:
                raise ValueError("环境变量 PUNC_MODEL 未设置")
            vad_model = (os.getenv("VAD_MODEL") or "").strip()
            if not vad_model:
                raise ValueError("环境变量 VAD_MODEL 未设置")
            logger.info("正在初始化 FunASR AutoModel…")
            self.asr_model = AutoModel(
                model=asr_path,
                vad_model=vad_model,
                punc_model=punc_path,
                disable_update=True,
            )
            logger.info("FunASR AutoModel（ASR）初始化完成")
        if self.vad_pipeline is None:
            vad_path = (os.getenv("VAD_MODEL") or "").strip()
            if not vad_path:
                raise ValueError("环境变量 VAD_MODEL 未设置")
            logger.info("正在初始化独立 VAD pipeline（用于分段）…")
            self.vad_pipeline = pipeline(
                task=Tasks.voice_activity_detection,
                model=vad_path,
                device="cpu",
                local_files_only=True,
            )
            logger.info("独立 VAD pipeline 初始化完成")

    def video_to_audio(self, video_path, audio_path="temp_audio.wav"):
        import ffmpeg

        (
            ffmpeg.input(video_path)
            .output(audio_path, ar=16000, ac=1, format="wav")
            .overwrite_output()
            .run(quiet=True)
        )
        return audio_path

    def segment_feature(self, x):
        x = np.asarray(x, dtype=np.float32).reshape(-1)
        if x.size == 0:
            return None
        x = x - float(np.mean(x))
        x = x / (float(np.std(x)) + 1e-8)
        zcr = float(np.mean((np.abs(np.diff(np.sign(x))) > 0)))
        energy = float(np.mean(x**2))
        n_fft = min(2048, int(2 ** np.floor(np.log2(max(256, x.size)))))
        spec = np.abs(np.fft.rfft(x[:n_fft]))
        spec = spec / (np.sum(spec) + 1e-8)
        bands = np.array_split(spec, 12)
        feat = np.asarray([zcr, energy] + [float(np.mean(b)) for b in bands], dtype=np.float32)
        return feat / (np.linalg.norm(feat) + 1e-8)

    def diarize(self, embeddings, expected_speakers=2):
        if len(embeddings) == 0:
            return []
        if len(embeddings) == 1:
            return [0]
        if len(embeddings) < expected_speakers:
            return list(range(len(embeddings)))
        x = np.asarray(embeddings, dtype=np.float32)
        try:
            model = AgglomerativeClustering(
                n_clusters=expected_speakers, metric="cosine", linkage="average"
            )
        except TypeError:
            model = AgglomerativeClustering(
                n_clusters=expected_speakers, affinity="cosine", linkage="average"
            )
        return model.fit_predict(x).tolist()

    def run_pipeline(self, video_path, wav_file_path, expected_speakers=2):
        logger.info("开启初始化ASR_VAD 模型")
        self.pipeline()
        logger.info("初始化ASR_VAD 模型完成")
        logger.info("开始转换视频为音频")
        audio_path = self.video_to_audio(video_path, wav_file_path)
        logger.info("转换视频为音频完成")
        logger.info("开始读取音频")
        audio_data, sr = sf.read(audio_path, dtype="float32")
        if audio_data.ndim > 1:
            audio_data = np.mean(audio_data, axis=1)
        segments = self.vad_pipeline(audio_path)[0]["value"]
        logger.info("读取音频完成")
        chunks, embs = [], []
        for start, end in segments:
            s = int(start * sr / 1000)
            e = int(end * sr / 1000)
            part = audio_data[s:e]
            if len(part) < int(sr * 0.5):
                continue
            feat = self.segment_feature(part)
            if feat is None:
                continue
            chunks.append((start, end, part))
            embs.append(feat)

        labels = self.diarize(embs, expected_speakers=expected_speakers)
        results = []
        for i, (start, end, part) in enumerate(chunks):
            asr_res = self.asr_model.generate(part)
            text = _text_from_asr_result(asr_res)
            sid = int(labels[i]) if i < len(labels) else 0
            item = {
                "speaker": f"spk{sid}",
                "start": round(start / 1000, 3),
                "end": round(end / 1000, 3),
                "text": text,
            }
            results.append(item)
            print(f"[spk{sid}] {item['text']}")
        return results

    def merge_to_paragraphs(self, results, max_gap=1.5, min_chars_to_next=20):
        if not results:
            return []
        merged = [results[0].copy()]
        for cur in results[1:]:
            prev = merged[-1]
            if cur["speaker"] == prev["speaker"] and cur["start"] - prev["end"] < max_gap:
                prev["text"] += " " + cur["text"]
                prev["end"] = cur["end"]
            else:
                merged.append(cur.copy())

        def _effective_len(text: str) -> int:
            remove_chars = " \t\r\n.,!?;:，。！？；：、\"'()[]{}<>《》“”‘’"
            return len("".join(ch for ch in (text or "") if ch not in remove_chars))

        compact = []
        i = 0
        while i < len(merged):
            cur = merged[i].copy()
            j = i
            while _effective_len(cur.get("text", "")) < min_chars_to_next and j + 1 < len(merged):
                nxt = merged[j + 1]
                cur["text"] = (cur.get("text", "").strip() + " " + nxt.get("text", "").strip()).strip()
                cur["end"] = max(cur.get("end", nxt["end"]), nxt.get("end"))
                j += 1
            compact.append(cur)
            i = j + 1

        return compact


asr_vad = ASR_VAD()
