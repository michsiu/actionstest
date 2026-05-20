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
LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_DIR / 'transcription.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ---------- 全局变量 ----------
UPLOAD_DIR = Path("tmp_uploads")
UPLOAD_DIR.mkdir(exist_ok=True)
IDLE_TIMEOUT = 300  # 5分钟无活动则关闭服务
last_activity = time.time()

# ---------- 抖音解析（i.rcuts.com API）----------
def parse_douyin_url(share_url):
    """使用 i.rcuts.com 解析抖音视频直链"""
    try:
        # 步骤1: 获取 api 地址
        resp1 = requests.get("http://i.rcuts.com/update/247", timeout=10)
        if resp1.status_code != 200:
            logger.error(f"获取API地址失败: {resp1.status_code}")
            return None
        data = resp1.json()
        api_url = data.get("api")
        if not api_url:
            logger.error("API地址为空")
            return None

        # 步骤2: POST 请求获取视频直链
        resp2 = requests.post(api_url, data={"url": share_url}, timeout=15)
        if resp2.status_code != 200:
            logger.error(f"解析失败: {resp2.status_code}")
            return None
        result = resp2.json()
        
        # 尝试多种可能的返回字段
        video_url = result.get("video_url")
        if not video_url:
            video_url = result.get("video_urls")
            if video_url and isinstance(video_url, list) and len(video_url) > 0:
                video_url = video_url[0]
        if not video_url:
            video_url = result.get("url")
        if not video_url:
            video_url = result.get("data", {}).get("video_url")
            
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
    json_str = json.dumps(data, ensure_ascii=False)
    padded = pad(json_str.encode('utf-8'), AES.block_size)
    encrypted = cipher.encrypt(padded)
    return base64.b64encode(encrypted).decode('utf-8')

def aes_decrypt(encrypted_b64):
    """解密"""
    try:
        cipher = AES.new(KEY, AES.MODE_CBC, IV)
        decrypted = cipher.decrypt(base64.b64decode(encrypted_b64))
        unpadded = unpad(decrypted, AES.block_size)
        return unpadded.decode('utf-8')
    except Exception as e:
        logger.error(f"解密失败: {e}")
        return None

def get_via_transcriptgenerate(url):
    """使用 transcriptgenerate.com 获取视频直链（videoUrlList）"""
    try:
        # 创建任务
        payload = {"appType": "transcript", "workUrl": url, "type": "text"}
        encrypted = aes_encrypt(payload)
        
        create_resp = requests.post(
            "https://www.transcriptgenerate.com/prod-api/transcript/createTask",
            data=encrypted,
            headers={"Content-Type": "application/json"},
            timeout=15
        )
        if create_resp.status_code != 200:
            logger.error(f"创建任务失败: {create_resp.status_code}")
            return None
            
        decrypted = aes_decrypt(create_resp.text)
        if not decrypted:
            return None
        task_data = json.loads(decrypted)
        if task_data.get("code") != 200:
            logger.error(f"任务创建返回错误: {task_data.get('code')}")
            return None
        task_id = task_data.get("data", {}).get("taskId")
        if not task_id:
            logger.error("未获取到 taskId")
            return None

        # 轮询查询任务
        for i in range(30):
            time.sleep(2)
            query_resp = requests.get(
                f"https://www.transcriptgenerate.com/prod-api/transcript/queryTask?taskId={task_id}",
                timeout=10
            )
            if query_resp.status_code != 200:
                continue
                
            decrypted = aes_decrypt(query_resp.text)
            if not decrypted:
                continue
            result = json.loads(decrypted)
            if result.get("code") == 200:
                data = result.get("data", {})
                status = data.get("taskStatus")
                if status == "SUCCESS":
                    video_urls = data.get("videoUrlList")
                    if video_urls and isinstance(video_urls, list) and len(video_urls) > 0:
                        return video_urls[0]
                elif status == "FAILURE":
                    logger.error("任务失败")
                    return None
        return None
    except Exception as e:
        logger.error(f"transcriptgenerate 解析失败: {e}")
        return None

def extract_video_direct_url(input_text):
    """从文本中提取URL，并尝试获取视频直链"""
    # 提取所有URL
    urls = re.findall(r'(https?://[^\s<>"\']+)', input_text)
    if not urls:
        # 尝试匹配抖音口令中的链接
        match = re.search(r'https?://v\.douyin\.com/[^\s]+', input_text)
        if match:
            urls = [match.group()]
        else:
            return None
    target_url = urls[0]

    # 判断是否为直链（媒体文件扩展名）
    path = urlparse(target_url).path
    ext = Path(path).suffix.lower()
    if ext in ['.mp4', '.avi', '.mov', '.mkv', '.mp3', '.wav', '.m4a', '.flv', '.webm']:
        return target_url

    # 域名判断
    domain = urlparse(target_url).netloc.lower()
    # 抖音相关域名
    douyin_domains = ['douyin.com', 'iyangshipin.com', 'douyinvod.com', 'iesdouyin.com']
    if any(d in domain for d in douyin_domains):
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
        await websocket.send(json.dumps({"type": "log", "content": f"📥 开始下载..."}))
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        response = requests.get(url, headers=headers, stream=True, timeout=60)
        response.raise_for_status()
        
        total = int(response.headers.get('content-length', 0))
        downloaded = 0
        last_percent = 0
        
        with open(output_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
                    downloaded += len(chunk)
                    if total:
                        percent = int((downloaded / total) * 100)
                        if percent >= last_percent + 10:
                            last_percent = percent
                            await websocket.send(json.dumps({
                                "type": "log",
                                "content": f"📥 下载进度: {percent}% ({downloaded//1024//1024}MB / {total//1024//1024}MB)"
                            }))
        
        file_size_mb = output_path.stat().st_size / (1024 * 1024)
        await websocket.send(json.dumps({"type": "log", "content": f"✅ 下载完成: {file_size_mb:.1f} MB"}))
        return True
    except Exception as e:
        await websocket.send(json.dumps({"type": "log", "content": f"❌ 下载失败: {str(e)}"}))
        return False

async def extract_audio(video_path, audio_path, websocket):
    """使用 ffmpeg 提取音频"""
    await websocket.send(json.dumps({"type": "log", "content": "🎵 正在提取音频..."}))
    cmd = [
        'ffmpeg', '-i', str(video_path),
        '-vn', '-acodec', 'mp3', '-q:a', '2', 
        '-y', str(audio_path)
    ]
    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd, 
            stdout=asyncio.subprocess.PIPE, 
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await proc.communicate()
        
        if audio_path.exists() and audio_path.stat().st_size > 0:
            size_mb = audio_path.stat().st_size / (1024 * 1024)
            await websocket.send(json.dumps({"type": "log", "content": f"✅ 音频提取成功: {size_mb:.1f} MB"}))
            return True
        else:
            await websocket.send(json.dumps({"type": "log", "content": "❌ 音频提取失败"}))
            return False
    except Exception as e:
        await websocket.send(json.dumps({"type": "log", "content": f"❌ ffmpeg 错误: {str(e)}"}))
        return False

# ---------- FunASR 转录 ----------
_model = None

def get_model():
    """懒加载模型"""
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

async def transcribe_audio(audio_path, websocket):
    """执行转录并推送结果"""
    await websocket.send(json.dumps({"type": "log", "content": "📝 开始语音识别，请稍候..."}))
    
    # 保存转录结果的文件
    results_file = Path("recognized_text.txt")
    
    try:
        model = get_model()
        res = model.generate(input=str(audio_path), batch_size_s=300, hotwords='')
        
        if res and len(res) > 0:
            text = res[0].get('text', '').strip()
            if text:
                # 发送结果
                await websocket.send(json.dumps({"type": "result", "content": text}))
                # 保存到文件
                with open(results_file, 'a', encoding='utf-8') as f:
                    timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
                    f.write(f"[{timestamp}] 文件: {audio_path.name}\n{text}\n\n")
                
                # 统计字数
                char_count = len(text)
                await websocket.send(json.dumps({"type": "log", "content": f"✅ 识别完成，共 {char_count} 字"}))
                return True
            else:
                await websocket.send(json.dumps({"type": "log", "content": "⚠️ 识别结果为空"}))
                return False
        else:
            await websocket.send(json.dumps({"type": "log", "content": "⚠️ 无转录结果"}))
            return False
    except Exception as e:
        await websocket.send(json.dumps({"type": "log", "content": f"❌ 转录失败: {str(e)}"}))
        logger.error(f"转录失败: {e}")
        return False

# ---------- 处理 URL 输入 ----------
async def process_url(websocket, text):
    """处理 URL 输入"""
    await websocket.send(json.dumps({"type": "log", "content": f"🔍 解析: {text}"}))
    
    video_url = extract_video_direct_url(text)
    if not video_url:
        await websocket.send(json.dumps({"type": "error", "content": "无法获取视频直链，请检查链接或尝试其他平台"}))
        return False
    
    await websocket.send(json.dumps({"type": "log", "content": f"✅ 获取到直链: {video_url[:80]}..."}))
    
    timestamp = int(time.time() * 1000)
    video_path = UPLOAD_DIR / f"download_{timestamp}.mp4"
    
    if await download_file(video_url, video_path, websocket):
        audio_path = video_path.with_suffix('.mp3')
        if await extract_audio(video_path, audio_path, websocket):
            success = await transcribe_audio(audio_path, websocket)
            # 清理临时文件
            video_path.unlink(missing_ok=True)
            audio_path.unlink(missing_ok=True)
            return success
        else:
            video_path.unlink(missing_ok=True)
            return False
    return False

# ---------- 处理文件上传 ----------
async def process_file(websocket, file_data):
    """处理上传的二进制文件"""
    timestamp = int(time.time() * 1000)
    
    # 尝试识别文件类型
    input_path = UPLOAD_DIR / f"upload_{timestamp}.mp4"
    with open(input_path, 'wb') as f:
        f.write(file_data)
    
    file_size_mb = input_path.stat().st_size / (1024 * 1024)
    await websocket.send(json.dumps({"type": "log", "content": f"✅ 文件已保存: {file_size_mb:.1f} MB"}))
    
    audio_path = input_path.with_suffix('.mp3')
    
    if await extract_audio(input_path, audio_path, websocket):
        success = await transcribe_audio(audio_path, websocket)
        # 清理
        input_path.unlink(missing_ok=True)
        audio_path.unlink(missing_ok=True)
        return success
    else:
        input_path.unlink(missing_ok=True)
        await websocket.send(json.dumps({"type": "log", "content": "无法提取音频，可能文件格式不支持"}))
        return False

# ---------- WebSocket 主处理 ----------
async def handle_client(websocket, path):
    global last_activity
    logger.info(f"客户端连接: {websocket.remote_address}")
    last_activity = time.time()
    
    # 发送欢迎消息
    await websocket.send(json.dumps({
        "type": "log", 
        "content": "🎙️ 音频转录服务已连接\n支持: 发送视频链接(抖音/其他) 或 上传音视频文件"
    }))
    
    try:
        # 接收消息
        message = await websocket.recv()
        last_activity = time.time()
        
        if isinstance(message, bytes):
            # 二进制文件
            await process_file(websocket, message)
        else:
            # 文本消息
            text = message.strip()
            if not text:
                await websocket.send(json.dumps({"type": "error", "content": "请输入内容"}))
            else:
                await process_url(websocket, text)
                
    except websockets.exceptions.ConnectionClosed:
        logger.info("客户端断开")
    except Exception as e:
        logger.error(f"处理错误: {e}")
        try:
            await websocket.send(json.dumps({"type": "error", "content": f"服务错误: {str(e)}"}))
        except:
            pass

# ---------- 空闲超时监控 ----------
async def idle_monitor():
    """监控空闲超时，超时则关闭服务"""
    global last_activity
    while True:
        await asyncio.sleep(10)
        if time.time() - last_activity > IDLE_TIMEOUT:
            logger.info("空闲超时，关闭服务")
            with open("/tmp/stop", "w") as f:
                f.write("timeout")
            # 停止事件循环
            asyncio.get_event_loop().stop()
            break

# ---------- 启动服务 ----------
async def main():
    # 预加载模型
    logger.info("🚀 正在加载 FunASR 模型...")
    start_time = time.time()
    get_model()
    load_time = time.time() - start_time
    logger.info(f"✅ 模型加载完成，耗时 {load_time:.1f} 秒")
    
    # 启动空闲监控
    asyncio.create_task(idle_monitor())
    
    # 启动 WebSocket 服务
    async with websockets.serve(handle_client, "0.0.0.0", 8765):
        logger.info("🌐 WebSocket 服务启动在 0.0.0.0:8765")
        await asyncio.Future()  # 运行直到被停止

if __name__ == "__main__":
    asyncio.run(main())