#!/usr/bin/env python3
"""
WebSocket 转录服务
- 接收二进制文件或 URL
- 解析抖音/其他平台视频直链
- 下载 -> 音频提取 -> FunASR 转录
- 实时推送日志和结果
"""

import asyncio
import websockets
import json
import os
import re
import time
import subprocess
import logging
import tempfile
import shutil
from pathlib import Path
from urllib.parse import urlparse
import requests
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad
import base64

# ---------- 日志配置 ----------
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/transcription.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ---------- 全局变量 ----------
UPLOAD_DIR = Path("tmp_uploads")
UPLOAD_DIR.mkdir(exist_ok=True)
LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)
IDLE_TIMEOUT = 300  # 5分钟无活动则关闭服务

# ---------- 抖音解析（第三方API）----------
def parse_douyin_url(share_url):
    """使用 i.rcuts.com 解析抖音视频直链"""
    try:
        # 步骤1: 获取 api 地址
        resp1 = requests.get("http://i.rcuts.com/update/247", timeout=10)
        if resp1.status_code != 200:
            return None
        data = resp1.json()
        api_url = data.get("api")
        if not api_url:
            return None

        # 步骤2: POST 请求获取视频直链
        resp2 = requests.post(api_url, data={"url": share_url}, timeout=15)
        if resp2.status_code != 200:
            return None
        result = resp2.json()
        # 常见返回字段: video_url, video_urls 等
        video_url = result.get("video_url") or (result.get("video_urls") and result["video_urls"][0])
        return video_url
    except Exception as e:
        logger.error(f"抖音解析失败: {e}")
        return None

# ---------- 哇能下载（transcriptgenerate 加密API）----------
KEY = b"aaDJL2d9DfhLZO0z"
IV = b"412ADDSSFA342442"

def aes_encrypt(data):
    """AES-CBC 加密并返回 Base64"""
    cipher = AES.new(KEY, AES.MODE_CBC, IV)
    padded = pad(json.dumps(data).encode('utf-8'), AES.block_size)
    encrypted = cipher.encrypt(padded)
    return base64.b64encode(encrypted).decode('utf-8')

def aes_decrypt(encrypted_b64):
    """解密"""
    cipher = AES.new(KEY, AES.MODE_CBC, IV)
    decrypted = cipher.decrypt(base64.b64decode(encrypted_b64))
    return unpad(decrypted, AES.block_size).decode('utf-8')

def get_via_transcriptgenerate(url):
    """使用 transcriptgenerate.com 获取视频直链（videoUrlList）"""
    try:
        # 创建任务
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

        # 轮询查询任务
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
    """从文本中提取URL，并尝试获取视频直链"""
    # 提取所有URL
    urls = re.findall(r'(https?://[^\s]+)', input_text)
    if not urls:
        return None
    target_url = urls[0]

    # 判断是否为直链（媒体文件扩展名）
    path = urlparse(target_url).path
    ext = Path(path).suffix.lower()
    if ext in ['.mp4', '.avi', '.mov', '.mkv', '.mp3', '.wav', '.m4a']:
        return target_url

    # 域名判断
    domain = urlparse(target_url).netloc.lower()
    # 抖音
    if 'douyin.com' in domain or 'iyangshipin.com' in domain or 'douyinvod' in domain:
        direct = parse_douyin_url(target_url)
        if direct:
            return direct
        # 失败则降级使用 transcriptgenerate
        direct = get_via_transcriptgenerate(target_url)
        if direct:
            return direct
    else:
        # 其他平台直接用 transcriptgenerate
        direct = get_via_transcriptgenerate(target_url)
        if direct:
            return direct
    return None

# ---------- 下载与音频提取 ----------
async def download_file(url, output_path, websocket):
    """下载文件并推送进度"""
    try:
        await websocket.send(json.dumps({"type": "log", "content": f"📥 开始下载: {url}"}))
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
    """使用 ffmpeg 提取音频"""
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

# ---------- FunASR 转录 ----------
def load_funasr_model():
    """加载模型（首次会下载）"""
    from funasr import AutoModel
    model = AutoModel(
        model="damo/speech_paraformer-large_asr_nat-zh-cn-16k-common-vocab8404-pytorch",
        vad_model="damo/speech_fsmn_vad_zh-cn-16k-common-pytorch",
        punc_model="damo/punc_ct-transformer_zh-cn-common-vocab272727-pytorch",
        disable_update=True
    )
    return model

async def transcribe_audio(audio_path, websocket, model):
    """执行转录并推送结果"""
    await websocket.send(json.dumps({"type": "log", "content": "📝 开始转录，请稍候..."}))
    try:
        res = model.generate(input=str(audio_path), batch_size_s=300, hotwords='')
        if res and len(res) > 0:
            text = res[0].get('text', '').strip()
            if text:
                await websocket.send(json.dumps({"type": "result", "content": text}))
                # 同时保存到文件
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

# ---------- WebSocket 主处理 ----------
async def handle_client(websocket, path):
    logger.info(f"客户端连接: {websocket.remote_address}")
    await websocket.send(json.dumps({"type": "log", "content": "✅ 已连接到转录服务，请上传视频/音频文件或发送视频链接。"}))

    # 重置空闲计时器
    global last_activity
    last_activity = time.time()

    try:
        # 接收第一条消息（文件或URL）
        message = await websocket.recv()
        last_activity = time.time()

        # 判断消息类型
        if isinstance(message, bytes):
            # 二进制文件上传
            await websocket.send(json.dumps({"type": "log", "content": "📁 接收到文件，保存中..."}))
            timestamp = int(time.time() * 1000)
            input_path = UPLOAD_DIR / f"upload_{timestamp}.mp4"  # 默认扩展名，后续根据实际修改
            with open(input_path, 'wb') as f:
                f.write(message)
            file_size = input_path.stat().st_size
            await websocket.send(json.dumps({"type": "log", "content": f"✅ 文件已保存: {input_path.name} ({file_size} bytes)"}))
            audio_path = input_path.with_suffix('.mp3')
            model = load_funasr_model()
            # 直接提取音频（如果是视频文件）
            if await extract_audio(input_path, audio_path, websocket):
                await transcribe_audio(audio_path, websocket, model)
            else:
                await websocket.send(json.dumps({"type": "log", "content": "无法提取音频，可能文件格式不支持"}))
            # 清理临时文件
            input_path.unlink(missing_ok=True)
            audio_path.unlink(missing_ok=True)
        else:
            # 文本消息：可能是 URL
            text = message
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
                model = load_funasr_model()
                if await extract_audio(video_path, audio_path, websocket):
                    await transcribe_audio(audio_path, websocket, model)
                else:
                    await websocket.send(json.dumps({"type": "log", "content": "无法提取音频"}))
                # 清理
                video_path.unlink(missing_ok=True)
                audio_path.unlink(missing_ok=True)
            else:
                await websocket.send(json.dumps({"type": "error", "content": "下载失败，任务终止。"}))

    except websockets.exceptions.ConnectionClosed:
        logger.info("客户端断开")
    finally:
        # 空闲超时检测
        while True:
            await asyncio.sleep(IDLE_TIMEOUT)
            if time.time() - last_activity > IDLE_TIMEOUT:
                logger.info("空闲超时，关闭服务")
                with open("/tmp/stop", "w") as f:
                    f.write("timeout")
                asyncio.get_event_loop().stop()
                break

# ---------- 启动服务 ----------
async def main():
    # 预加载模型（避免首次连接时下载）
    logger.info("预加载 FunASR 模型...")
    model = load_funasr_model()
    logger.info("模型加载完成")

    async with websockets.serve(handle_client, "0.0.0.0", 8765):
        logger.info("WebSocket 服务启动在 0.0.0.0:8765")
        await asyncio.Future()  # 运行直到被停止

if __name__ == "__main__":
    asyncio.run(main())