#!/usr/bin/env python3
"""
WebSocket 转录服务 - 修复保持连接版
- 循环接收消息，不会因一条消息就断开
- 支持多轮请求（一次连接可处理多个文件/URL）
- 空闲超时基于无活动连接
"""

import asyncio
import websockets
import json
import os
import re
import time
import subprocess
import logging
from pathlib import Path
from urllib.parse import urlparse
import requests
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad
import base64

# ---------- 配置 ----------
UPLOAD_DIR = Path("tmp_uploads")
LOG_DIR = Path("logs")
UPLOAD_DIR.mkdir(exist_ok=True)
LOG_DIR.mkdir(exist_ok=True)

IDLE_TIMEOUT = 300  # 无任何客户端连接时，5分钟后关闭服务

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_DIR / 'transcription.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ---------- 全局状态 ----------
active_connections = set()
last_activity_time = time.time()
stop_event = asyncio.Event()
# 模型全局加载一次
_model = None

def get_model():
    global _model
    if _model is None:
        from funasr import AutoModel
        _model = AutoModel(
            model="damo/speech_paraformer-large_asr_nat-zh-cn-16k-common-vocab8404-pytorch",
            vad_model="damo/speech_fsmn_vad_zh-cn-16k-common-pytorch",
            punc_model="damo/punc_ct-transformer_zh-cn-common-vocab272727-pytorch",
            disable_update=True
        )
    return _model

# ---------- 抖音解析 ----------
def parse_douyin_url(share_url):
    try:
        resp1 = requests.get("http://i.rcuts.com/update/247", timeout=10)
        if resp1.status_code != 200:
            return None
        data = resp1.json()
        api_url = data.get("api")
        if not api_url:
            return None
        resp2 = requests.post(api_url, data={"url": share_url}, timeout=15)
        if resp2.status_code != 200:
            return None
        result = resp2.json()
        video_url = result.get("video_url") or (result.get("video_urls") and result["video_urls"][0])
        return video_url
    except Exception as e:
        logger.error(f"抖音解析失败: {e}")
        return None

# ---------- 哇能下载 ----------
KEY = b"aaDJL2d9DfhLZO0z"
IV = b"412ADDSSFA342442"

def aes_encrypt(data):
    cipher = AES.new(KEY, AES.MODE_CBC, IV)
    padded = pad(json.dumps(data).encode('utf-8'), AES.block_size)
    encrypted = cipher.encrypt(padded)
    return base64.b64encode(encrypted).decode('utf-8')

def aes_decrypt(encrypted_b64):
    cipher = AES.new(KEY, AES.MODE_CBC, IV)
    decrypted = cipher.decrypt(base64.b64decode(encrypted_b64))
    return unpad(decrypted, AES.block_size).decode('utf-8')

def get_via_transcriptgenerate(url):
    try:
        payload = {"appType": "transcript", "workUrl": url, "type": "text"}
        encrypted = aes_encrypt(payload)
        create_resp = requests.post(
            "https://www.transcriptgenerate.com/prod-api/transcript/createTask",
            data=encrypted,
            headers={"Content-Type": "application/octet-stream"},
            timeout=15
        )
        if create_resp.status_code != 200:
            return None
        decrypted = aes_decrypt(create_resp.text)
        task_data = json.loads(decrypted)
        if task_data.get("code") != 200:
            return None
        task_id = task_data["data"]["taskId"]

        for _ in range(30):
            time.sleep(2)
            query_resp = requests.get(
                f"https://www.transcriptgenerate.com/prod-api/transcript/queryTask?taskId={task_id}",
                timeout=10
            )
            if query_resp.status_code != 200:
                continue
            decrypted = aes_decrypt(query_resp.text)
            result = json.loads(decrypted)
            if result.get("code") == 200:
                data = result.get("data", {})
                status = data.get("taskStatus")
                if status == "SUCCESS":
                    video_urls = data.get("videoUrlList")
                    if video_urls and isinstance(video_urls, list) and len(video_urls) > 0:
                        return video_urls[0]
                elif status == "FAILURE":
                    return None
        return None
    except Exception as e:
        logger.error(f"transcriptgenerate 解析失败: {e}")
        return None

def extract_video_direct_url(input_text):
    urls = re.findall(r'(https?://[^\s]+)', input_text)
    if not urls:
        return None
    target_url = urls[0]
    path = urlparse(target_url).path
    ext = Path(path).suffix.lower()
    if ext in ['.mp4', '.avi', '.mov', '.mkv', '.mp3', '.wav', '.m4a']:
        return target_url

    domain = urlparse(target_url).netloc.lower()
    if 'douyin.com' in domain or 'iyangshipin.com' in domain or 'douyinvod' in domain:
        direct = parse_douyin_url(target_url)
        if direct:
            return direct
        direct = get_via_transcriptgenerate(target_url)
        if direct:
            return direct
    else:
        direct = get_via_transcriptgenerate(target_url)
        if direct:
            return direct
    return None

# ---------- 下载与音频提取 ----------
async def download_file(url, output_path, websocket):
    await websocket.send(json.dumps({"type": "log", "content": f"📥 开始下载: {url}"}))
    try:
        response = requests.get(url, stream=True, timeout=30)
        response.raise_for_status()
        total = int(response.headers.get('content-length', 0))
        downloaded = 0
        with open(output_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
                    downloaded += len(chunk)
                    if total:
                        percent = (downloaded / total) * 100
                        await websocket.send(json.dumps({
                            "type": "log",
                            "content": f"下载进度: {percent:.1f}% ({downloaded}/{total} bytes)"
                        }))
        await websocket.send(json.dumps({"type": "log", "content": f"✅ 下载完成: {output_path.name}"}))
        return True
    except Exception as e:
        await websocket.send(json.dumps({"type": "log", "content": f"❌ 下载失败: {str(e)}"}))
        return False

async def extract_audio(video_path, audio_path, websocket):
    await websocket.send(json.dumps({"type": "log", "content": "🎵 提取音频中..."}))
    cmd = [
        'ffmpeg', '-i', str(video_path),
        '-vn', '-acodec', 'mp3', '-q:a', '2', '-y', str(audio_path)
    ]
    try:
        proc = await asyncio.create_subprocess_exec(*cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
        await proc.communicate()
        if audio_path.exists() and audio_path.stat().st_size > 0:
            await websocket.send(json.dumps({"type": "log", "content": f"✅ 音频提取成功: {audio_path.name}"}))
            return True
        else:
            await websocket.send(json.dumps({"type": "log", "content": "❌ 音频提取失败"}))
            return False
    except Exception as e:
        await websocket.send(json.dumps({"type": "log", "content": f"❌ ffmpeg 错误: {str(e)}"}))
        return False

async def transcribe_audio(audio_path, websocket):
    await websocket.send(json.dumps({"type": "log", "content": "📝 开始转录，请稍候..."}))
    try:
        model = get_model()
        res = model.generate(input=str(audio_path), batch_size_s=300, hotwords='')
        if res and len(res) > 0:
            text = res[0].get('text', '').strip()
            if text:
                await websocket.send(json.dumps({"type": "result", "content": text}))
                with open("recognized_text.txt", "a", encoding='utf-8') as f:
                    f.write(f"## {audio_path.name}\n{text}\n\n")
                return True
            else:
                await websocket.send(json.dumps({"type": "log", "content": "⚠️ 识别结果为空"}))
                return False
        else:
            await websocket.send(json.dumps({"type": "log", "content": "⚠️ 无转录结果"}))
            return False
    except Exception as e:
        await websocket.send(json.dumps({"type": "log", "content": f"❌ 转录失败: {str(e)}"}))
        return False

async def process_file(file_bytes, websocket):
    """处理二进制文件上传"""
    await websocket.send(json.dumps({"type": "log", "content": "📁 接收到文件，保存中..."}))
    timestamp = int(time.time() * 1000)
    input_path = UPLOAD_DIR / f"upload_{timestamp}.mp4"
    with open(input_path, 'wb') as f:
        f.write(file_bytes)
    file_size = input_path.stat().st_size
    await websocket.send(json.dumps({"type": "log", "content": f"✅ 文件已保存: {input_path.name} ({file_size} bytes)"}))
    audio_path = input_path.with_suffix('.mp3')
    if await extract_audio(input_path, audio_path, websocket):
        await transcribe_audio(audio_path, websocket)
    else:
        await websocket.send(json.dumps({"type": "log", "content": "无法提取音频，可能文件格式不支持"}))
    input_path.unlink(missing_ok=True)
    audio_path.unlink(missing_ok=True)

async def process_url(text, websocket):
    """处理文本URL"""
    await websocket.send(json.dumps({"type": "log", "content": f"🔍 解析输入: {text}"}))
    video_url = extract_video_direct_url(text)
    if not video_url:
        await websocket.send(json.dumps({"type": "error", "content": "无法获取视频直链，请检查链接或尝试其他平台。"}))
        return

    await websocket.send(json.dumps({"type": "log", "content": f"✅ 获取到直链: {video_url}"}))
    timestamp = int(time.time() * 1000)
    video_path = UPLOAD_DIR / f"download_{timestamp}.mp4"
    if await download_file(video_url, video_path, websocket):
        audio_path = video_path.with_suffix('.mp3')
        if await extract_audio(video_path, audio_path, websocket):
            await transcribe_audio(audio_path, websocket)
        else:
            await websocket.send(json.dumps({"type": "log", "content": "无法提取音频"}))
        video_path.unlink(missing_ok=True)
        audio_path.unlink(missing_ok=True)
    else:
        await websocket.send(json.dumps({"type": "error", "content": "下载失败，任务终止。"}))

# ---------- WebSocket 处理器（保持长连接）----------
async def handle_client(websocket):
    global last_activity_time
    remote = websocket.remote_address
    logger.info(f"客户端连接: {remote}")
    active_connections.add(websocket)
    last_activity_time = time.time()

    try:
        await websocket.send(json.dumps({"type": "log", "content": "✅ 已连接到转录服务，请上传视频/音频文件或发送视频链接。"}))

        # 循环接收消息
        async for message in websocket:
            last_activity_time = time.time()
            if isinstance(message, bytes):
                await process_file(message, websocket)
            else:
                await process_url(message, websocket)
            # 处理完毕后继续等待下一条消息，连接保持
        logger.info(f"客户端断开: {remote}")
    except websockets.exceptions.ConnectionClosed:
        logger.info(f"客户端连接关闭: {remote}")
    finally:
        active_connections.discard(websocket)
        last_activity_time = time.time()

# ---------- 空闲超时监控 ----------
async def idle_monitor():
    global last_activity_time
    while not stop_event.is_set():
        await asyncio.sleep(10)
        if not active_connections and (time.time() - last_activity_time) > IDLE_TIMEOUT:
            logger.info("空闲超时，关闭服务")
            with open("/tmp/stop", "w") as f:
                f.write("timeout")
            stop_event.set()
            asyncio.get_event_loop().stop()
            break

# ---------- 启动服务 ----------
async def main():
    # 预加载模型
    logger.info("预加载 FunASR 模型...")
    get_model()
    logger.info("模型加载完成")

    asyncio.create_task(idle_monitor())

    async with websockets.serve(handle_client, "0.0.0.0", 8765, ping_interval=20, ping_timeout=60):
        logger.info("WebSocket 服务启动在 0.0.0.0:8765")
        await stop_event.wait()

if __name__ == "__main__":
    asyncio.run(main())