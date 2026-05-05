#!/usr/bin/env python3
import sys
import os

os.environ['MODELSCOPE_CACHE'] = '/modelscope_cache'

import logging
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from urllib.parse import urlparse, unquote
from funasr import AutoModel

LOG_FILE = os.path.join(os.getcwd(), 'transcription.log')
RESULT_FILE = os.path.join(os.getcwd(), 'recognized_text.txt')
URL_TASK_FILE = os.path.join(os.getcwd(), 'VideoUrlTask.txt')
DOWNLOAD_DIR = os.path.join(os.getcwd(), 'downloads')
CONVERTED_DIR = os.path.join(os.getcwd(), 'converted')

# 并行数：可根据需要调整
MAX_WORKERS = 7

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler(sys.stdout)
    ]
)


def download_file(url):
    """下载单个文件，返回 (url, local_path 或 None)"""
    os.makedirs(DOWNLOAD_DIR, exist_ok=True)
    parsed = urlparse(url)
    filename = unquote(os.path.basename(parsed.path))
    if not os.path.splitext(filename)[1]:
        filename = f"download_{abs(hash(url)) % 100000}"

    output_path = os.path.join(DOWNLOAD_DIR, filename)
    logging.info(f"  ⬇ Downloading: {filename}")

    result = subprocess.run(['wget', '-q', '--show-progress', '-O', output_path, url],
                            capture_output=True, text=True)
    if result.returncode != 0:
        result = subprocess.run(['curl', '-L', '--progress-bar', '-o', output_path, url],
                                capture_output=True, text=True)
    if result.returncode != 0:
        logging.error(f"  ❌ Download failed: {url}")
        return (url, None)

    size_mb = os.path.getsize(output_path) / 1024 / 1024
    logging.info(f"  ✅ Downloaded: {filename} ({size_mb:.1f} MB)")
    return (url, output_path)


def parallel_download(urls):
    """多线程并行下载所有 URL"""
    logging.info(f"\n📥 Parallel downloading {len(urls)} file(s) (workers={min(MAX_WORKERS, len(urls))})...")
    results = {}
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {executor.submit(download_file, url): url for url in urls}
        for future in as_completed(futures):
            url, path = future.result()
            results[url] = path
    return results


def convert_to_audio(input_path):
    """转换单个文件为 16kHz WAV"""
    os.makedirs(CONVERTED_DIR, exist_ok=True)
    wav_file = os.path.join(CONVERTED_DIR,
                            os.path.splitext(os.path.basename(input_path))[0] + '_converted.wav')

    logging.info(f"  🔄 Converting: {os.path.basename(input_path)}")
    cmd = ['ffmpeg', '-i', input_path, '-vn', '-acodec', 'pcm_s16le',
           '-ar', '16000', '-ac', '1', '-y', '-loglevel', 'error', wav_file]
    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        logging.error(f"  ❌ Conversion failed: {os.path.basename(input_path)}")
        return None
    logging.info(f"  ✅ Converted: {os.path.basename(wav_file)}")
    return wav_file


def transcribe_one(model, label, audio_path):
    """转录单个文件"""
    try:
        result = model.generate(input=audio_path, batch_size_s=300)
        text = result[0].get('text', '') if result and len(result) > 0 else ''
        if text:
            logging.info(f"  ✅ {label}: {text[:80]}{'...' if len(text) > 80 else ''}")
        else:
            logging.warning(f"  ⚠️ {label}: empty result")
        return (label, text if text else "[EMPTY RESULT]")
    except Exception as e:
        logging.error(f"  ❌ {label}: {e}")
        return (label, f"[ERROR: {e}]")


def find_local_files():
    env_file = os.environ.get('AUDIO_FILE', '')
    if env_file:
        path = os.path.join(os.getcwd(), env_file) if not os.path.isabs(env_file) else env_file
        if os.path.exists(path):
            return [path]

    patterns = ('.wav', '.mp3', '.m4a', '.mp4', '.flac', '.ogg', '.aac', '.webm', '.mkv')
    return [os.path.join(os.getcwd(), f) for f in sorted(os.listdir(os.getcwd()))
            if os.path.splitext(f)[1].lower() in patterns and '_converted' not in f]


def main():
    sources = []   # [(label, audio_path or None)]
    url_count = 0

    # ====== Step 1: 读取 URL ======
    if os.path.exists(URL_TASK_FILE):
        with open(URL_TASK_FILE, 'r') as f:
            urls = [line.strip() for line in f
                    if line.strip() and not line.strip().startswith('#')]

        if urls:
            logging.info(f"📋 {len(urls)} URL(s) in VideoUrlTask.txt\n")

            # ====== Step 2: 并行下载 ======
            download_results = parallel_download(urls)

            # ====== Step 3: 转换音频 ======
            logging.info(f"\n🔄 Converting downloaded files to 16kHz WAV...")
            for url in urls:
                path = download_results.get(url)
                if path is None:
                    sources.append((f"[FAILED DOWNLOAD] {url}", None))
                    continue

                wav = convert_to_audio(path)
                if wav:
                    sources.append((url, wav))
                    url_count += 1
                else:
                    sources.append((f"[FAILED CONVERT] {url}", None))

            os.remove(URL_TASK_FILE)
            logging.info(f"\n🗑 Removed VideoUrlTask.txt")

    # ====== Step 4: 本地文件 ======
    if not sources:
        local_files = find_local_files()
        if local_files:
            for f in local_files:
                if os.path.splitext(f)[1].lower() != '.wav':
                    wav = convert_to_audio(f)
                    if wav:
                        sources.append((os.path.basename(f), wav))
                else:
                    sources.append((os.path.basename(f), f))
        else:
            logging.error("No audio/video files found!")
            sys.exit(1)

    if not sources:
        logging.error("No valid files to transcribe!")
        sys.exit(1)

    # ====== Step 5: 加载模型 ======
    logging.info(f"\n🧠 Loading models...")
    model = AutoModel(
        model="damo/speech_paraformer-large_asr_nat-zh-cn-16k-common-vocab8404-pytorch",
        vad_model="damo/speech_fsmn_vad_zh-cn-16k-common-pytorch",
        punc_model="damo/punc_ct-transformer_zh-cn-common-vocab272727-pytorch",
        disable_update=True
    )
    logging.info("Models loaded.\n")

    # ====== Step 6: 逐个转录（模型已加载，多文件共享） ======
    results = []
    success = 0
    for i, (label, audio_path) in enumerate(sources):
        logging.info(f"[{i+1}/{len(sources)}] Transcribing: {label[:80]}")
        if audio_path is None:
            results.append((label, "DOWNLOAD OR CONVERSION FAILED"))
            continue

        lbl, text = transcribe_one(model, label, audio_path)
        results.append((lbl, text))
        if text and not text.startswith("[ERROR") and text != "[EMPTY RESULT]":
            success += 1

    # ====== Step 7: 一次性写入结果 ======
    with open(RESULT_FILE, 'w', encoding='utf-8') as f:
        f.write(f"FunASR Transcription Results\n")
        f.write(f"{'='*60}\n")
        f.write(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Total tasks: {len(results)} | Success: {success}\n")
        f.write(f"{'='*60}\n\n")

        for i, (label, text) in enumerate(results):
            f.write(f"[{i+1}] {label}\n{text}\n\n")

    logging.info(f"\n{'='*60}")
    logging.info(f"✅ Done! {success}/{len(results)} succeeded.")
    logging.info(f"📄 Results saved to {RESULT_FILE}")
    print("\n=== Transcription Completed ===")


if __name__ == '__main__':
    main()