#!/usr/bin/env python3
import sys
import os
import logging
import subprocess
from datetime import datetime
from funasr import AutoModel

# 日志文件写在当前工作目录
LOG_FILE = os.path.join(os.getcwd(), 'transcription.log')
RESULT_FILE = os.path.join(os.getcwd(), 'recognized_text.txt')

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler(sys.stdout)
    ]
)

audio_file = os.environ.get('AUDIO_FILE', 'audio.mp3')

# 如果传入的是纯文件名，确保在工作目录下找
if not os.path.isabs(audio_file):
    audio_file = os.path.join(os.getcwd(), audio_file)

if not os.path.exists(audio_file):
    logging.error(f"Audio file not found: {audio_file}")
    logging.info(f"Current directory: {os.getcwd()}")
    logging.info(f"Contents: {os.listdir('.')}")
    sys.exit(1)

# MP4/M4A 转 WAV
file_ext = os.path.splitext(audio_file)[1].lower()
if file_ext in ['.mp4', '.m4a']:
    logging.info(f"Converting {audio_file} to 16kHz mono WAV...")
    wav_file = audio_file.rsplit('.', 1)[0] + '_converted.wav'
    cmd = [
        'ffmpeg', '-i', audio_file,
        '-vn', '-acodec', 'pcm_s16le',
        '-ar', '16000', '-ac', '1',
        '-y', wav_file
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        logging.error(f"FFmpeg conversion failed: {result.stderr}")
        sys.exit(1)
    logging.info(f"Converted to: {wav_file}")
    audio_file = wav_file

logging.info(f"Starting transcription for: {audio_file}")

try:
    logging.info("Loading models...")
    model = AutoModel(
        model="damo/speech_paraformer-large_asr_nat-zh-cn-16k-common-vocab8404-pytorch",
        vad_model="damo/speech_fsmn_vad_zh-cn-16k-common-pytorch",
        punc_model="damo/punc_ct-transformer_zh-cn-common-vocab272727-pytorch",
        disable_update=True
    )
    logging.info("Models loaded.")

    logging.info(f"Processing: {audio_file}")
    result = model.generate(input=audio_file, batch_size_s=300)

    if result and len(result) > 0:
        transcribed_text = result[0].get('text', 'No text output')
        logging.info(f"Result: {transcribed_text}")
    else:
        transcribed_text = "No result returned from model"
        logging.warning("Empty result from model")

    with open(RESULT_FILE, 'w', encoding='utf-8') as f:
        f.write(f"Audio file: {audio_file}\n")
        f.write(f"Transcription time: {datetime.now().isoformat()}\n")
        f.write(f"\nRecognized Text:\n{transcribed_text}\n")

    logging.info(f"Saved to {RESULT_FILE}")

except Exception as e:
    logging.error(f"Transcription failed: {e}")
    import traceback
    logging.error(traceback.format_exc())
    sys.exit(1)

print("\n=== Transcription Completed ===")