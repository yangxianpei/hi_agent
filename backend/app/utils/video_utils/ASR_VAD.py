import numpy as np
import soundfile as sf
from sklearn.cluster import AgglomerativeClustering
from modelscope.pipelines import pipeline
from modelscope.utils.constant import Tasks
from app.utils.logger import get_logger
import os

logger = get_logger(__name__)

class ASR_VAD:
    def __init__(self):
        self.asr_pipeline =None
        self.vad_pipeline = None
    
    def pipeline(self):
        if self.asr_pipeline is None:
            self.asr_pipeline = pipeline(
                task=Tasks.auto_speech_recognition,
                model= os.getenv("ASR_MODEL",""),
                device="cpu",
                local_files_only=True,
                disable_update=True,
            )
        if self.vad_pipeline is None:
            self.vad_pipeline = pipeline(
                task=Tasks.voice_activity_detection,
                model= os.getenv("VAD_MODEL",""),
                device="cpu",
                local_files_only=True,
            )


    def video_to_audio(self,video_path, audio_path="temp_audio.wav"):
        import ffmpeg
        (
            ffmpeg.input(video_path)
            .output(audio_path, ar=16000, ac=1, format="wav")
            .overwrite_output()
            .run(quiet=True)
        )
        return audio_path


    def segment_feature(self,x):
        x = np.asarray(x, dtype=np.float32).reshape(-1)
        if x.size == 0:
            return None
        x = x - float(np.mean(x))
        x = x / (float(np.std(x)) + 1e-8)
        zcr = float(np.mean(np.abs(np.diff(np.sign(x))) > 0))
        energy = float(np.mean(x ** 2))
        n_fft = min(2048, int(2 ** np.floor(np.log2(max(256, x.size)))))
        spec = np.abs(np.fft.rfft(x[:n_fft]))
        spec = spec / (np.sum(spec) + 1e-8)
        bands = np.array_split(spec, 12)
        feat = np.asarray([zcr, energy] + [float(np.mean(b)) for b in bands], dtype=np.float32)
        return feat / (np.linalg.norm(feat) + 1e-8)


    def diarize(self,embeddings, expected_speakers=2):
        if len(embeddings) == 0:
            return []
        if len(embeddings) == 1:
            return [0]
        if len(embeddings) < expected_speakers:
            return list(range(len(embeddings)))
        x = np.asarray(embeddings, dtype=np.float32)
        try:
            model = AgglomerativeClustering(n_clusters=expected_speakers, metric="cosine", linkage="average")
        except TypeError:
            model = AgglomerativeClustering(n_clusters=expected_speakers, affinity="cosine", linkage="average")
        return model.fit_predict(x).tolist()


    def run_pipeline(self, video_path, wav_file_path, expected_speakers=2):
        logger.info(f"开启初始化ASR_VAD 模型")
        self.pipeline()
        logger.info(f"初始化ASR_VAD 模型完成")
        logger.info(f"开始转换视频为音频")
        audio_path = self.video_to_audio(video_path, wav_file_path)
        logger.info(f"转换视频为音频完成")
        logger.info(f"开始读取音频")
        audio_data, sr = sf.read(audio_path)
        segments = self.vad_pipeline(audio_path)[0]["value"]
        logger.info(f"读取音频完成")
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
            asr_res = self.asr_pipeline(part)
            text = asr_res[0].get("text", "") if isinstance(asr_res, list) else asr_res.get("text", "")
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


    def merge_to_paragraphs(self,results, max_gap=1.5, min_chars_to_next=20):
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

        # 第二轮：短句（< min_chars_to_next）并到下一条，避免出现“另外就是”这类孤立行
        def _effective_len(text: str) -> int:
            # 去掉空白与常见中英文标点，只按有效字符判断“短句”
            remove_chars = " \t\r\n.,!?;:，。！？；：、\"'()[]{}<>《》“”‘’"
            return len("".join(ch for ch in (text or "") if ch not in remove_chars))

        compact = []
        i = 0
        while i < len(merged):
            cur = merged[i].copy()
            j = i
            # 连续向后并，直到达到阈值或没有下一条
            while _effective_len(cur.get("text", "")) < min_chars_to_next and j + 1 < len(merged):
                nxt = merged[j + 1]
                cur["text"] = (cur.get("text", "").strip() + " " + nxt.get("text", "").strip()).strip()
                cur["end"] = max(cur.get("end", nxt["end"]), nxt.get("end"))
                j += 1
            compact.append(cur)
            i = j + 1

        return compact


asr_vad = ASR_VAD()
# if __name__ == "__main__":
#     video_file = r"D:\test\hi_agent\backend\uploads\2.mp4"
#     results = run_pipeline(video_file, expected_speakers=2)
#     print("\n===== 原始结果 =====")
#     for r in results:
#         print(r)
#     print("\n===== 合并段落 =====")
#     for m in merge_to_paragraphs(results):
#         print(m)