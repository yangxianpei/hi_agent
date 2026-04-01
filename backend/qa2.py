import numpy as np
import soundfile as sf
from sklearn.cluster import AgglomerativeClustering
from modelscope.pipelines import pipeline
from modelscope.utils.constant import Tasks

ASR_MODEL = r"D:\test\model\speech_paraformer-large-vad-punc_asr_nat-zh-cn-16k-common-vocab8404-pytorch"
VAD_MODEL = r"D:\test\model\speech_fsmn_vad_zh-cn-16k-common-pytorch"




asr_pipeline = pipeline(
                task=Tasks.auto_speech_recognition,
                model=ASR_MODEL,
                device="cpu",
                local_files_only=True,
                disable_update=True,
            )
vad_pipeline = pipeline(
    task=Tasks.voice_activity_detection,
    model=VAD_MODEL,
    device="cpu",
    local_files_only=True,
)


def video_to_audio(video_path, audio_path="temp_audio.wav"):
    import ffmpeg
    (
        ffmpeg.input(video_path)
        .output(audio_path, ar=16000, ac=1, format="wav")
        .overwrite_output()
        .run(quiet=True)
    )
    return audio_path


def segment_feature(x):
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


def diarize(embeddings, expected_speakers=2):
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


def run_pipeline(video_path, expected_speakers=2):
    audio_path = video_to_audio(video_path)
    audio_data, sr = sf.read(audio_path)
    segments = vad_pipeline(audio_path)[0]["value"]

    chunks, embs = [], []
    for start, end in segments:
        s = int(start * sr / 1000)
        e = int(end * sr / 1000)
        part = audio_data[s:e]
        if len(part) < int(sr * 0.5):
            continue
        feat = segment_feature(part)
        if feat is None:
            continue
        chunks.append((start, end, part))
        embs.append(feat)

    labels = diarize(embs, expected_speakers=expected_speakers)
    results = []
    for i, (start, end, part) in enumerate(chunks):
        asr_res = asr_pipeline(part)
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


def merge_to_paragraphs(results, max_gap=1.5):
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
    return merged


if __name__ == "__main__":
    video_file = r"D:\test\hi_agent\backend\uploads\2.mp4"
    results = run_pipeline(video_file, expected_speakers=2)
    print("\n===== 原始结果 =====")
    for r in results:
        print(r)
    print("\n===== 合并段落 =====")
    for m in merge_to_paragraphs(results):
        print(m)