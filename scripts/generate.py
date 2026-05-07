#!/usr/bin/env python3
"""
FunASR 音频转录脚本
支持 URL 下载（yt-dlp + requests）和本地文件转录
"""

import os
import sys
import time
import json
import logging
import subprocess
from pathlib import Path
from typing import List, Optional, Tuple, Dict
from urllib.parse import urlparse

import requests

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('transcription.log', mode='a', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


class VideoDownloader:
    """视频下载器，支持 yt-dlp 和直接下载"""
    
    def __init__(self, download_dir: str = "downloaded_audios", log_dir: str = "logs"):
        self.download_dir = Path(download_dir)
        self.log_dir = Path(log_dir)
        self.download_dir.mkdir(exist_ok=True)
        self.log_dir.mkdir(exist_ok=True)
        
        self.download_log = self.log_dir / "download.log"
        self._init_log()
    
    def _init_log(self):
        """初始化下载日志"""
        with open(self.download_log, 'a', encoding='utf-8') as f:
            f.write(f"\n{'='*60}\n")
            f.write(f"下载会话开始: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"{'='*60}\n")
    
    def _log(self, message: str, level: str = "INFO"):
        """写入日志"""
        timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
        log_msg = f"[{timestamp}] [{level}] {message}"
        logger.info(message)
        with open(self.download_log, 'a', encoding='utf-8') as f:
            f.write(log_msg + '\n')
    
    def _is_direct_link(self, url: str) -> bool:
        """判断是否为直接媒体链接"""
        # 检查文件扩展名
        video_extensions = ['.mp4', '.avi', '.mkv', '.mov', '.webm', '.flv']
        audio_extensions = ['.mp3', '.wav', '.m4a', '.flac', '.ogg', '.aac']
        
        path = urlparse(url).path
        ext = Path(path).suffix.lower()
        
        if ext in video_extensions or ext in audio_extensions:
            return True
        
        # 检查常见 CDN 特征
        cdn_patterns = [
            'video/tos/',      # 抖音/头条
            '.douyinvod.com',
            '.ixigua.com/video',
            'mime_type=video_mp4',
            'content-type=video'
        ]
        
        for pattern in cdn_patterns:
            if pattern in url:
                return True
        
        return False
    
    def _download_with_requests(self, url: str, output_path: Path) -> Tuple[bool, str]:
        """使用 requests 直接下载"""
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': '*/*',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Range': 'bytes=0-'
        }
        
        try:
            self._log(f"开始下载 (requests): {url}")
            
            response = requests.get(url, headers=headers, stream=True, timeout=30)
            response.raise_for_status()
            
            total_size = int(response.headers.get('content-length', 0))
            downloaded = 0
            
            with open(output_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        if total_size > 0:
                            percent = (downloaded / total_size) * 100
                            print(f"\r下载进度: {percent:.1f}% ({downloaded}/{total_size} bytes)", end='')
            
            print()
            
            if output_path.exists() and output_path.stat().st_size > 0:
                file_size = output_path.stat().st_size
                self._log(f"下载成功: {output_path.name} ({file_size} bytes)")
                return True, f"成功下载 {file_size} bytes"
            else:
                return False, "下载文件为空"
                
        except requests.exceptions.RequestException as e:
            return False, f"请求错误: {str(e)}"
        except Exception as e:
            return False, f"未知错误: {str(e)}"
    
    def _download_with_ytdlp(self, url: str, output_path: Path) -> Tuple[bool, str]:
        """使用 yt-dlp 下载"""
        # 检查 yt-dlp 是否可用
        try:
            subprocess.run(['yt-dlp', '--version'], capture_output=True, check=True)
        except (subprocess.CalledProcessError, FileNotFoundError):
            self._log("yt-dlp 未安装，正在安装...")
            try:
                subprocess.run([sys.executable, '-m', 'pip', 'install', 'yt-dlp'], check=True)
                self._log("yt-dlp 安装成功")
            except Exception as e:
                return False, f"yt-dlp 安装失败: {str(e)}"
        
        # 准备输出路径（yt-dlp 会自动添加扩展名）
        output_template = str(output_path.with_suffix(''))
        
        cmd = [
            'yt-dlp',
            '--no-playlist',
            '-x',
            '--audio-format', 'mp3',
            '--audio-quality', '0',
            '-o', f'{output_template}.%(ext)s',
            '--no-overwrites',
            '--quiet',
            '--no-warnings'
        ]
        
        cmd.extend([
            '--add-header', 'User-Agent:Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        ])
        
        cmd.append(url)
        
        try:
            self._log(f"开始下载 (yt-dlp): {url}")
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            
            if result.returncode == 0:
                downloaded_files = list(self.download_dir.glob(f"{output_path.stem}.*"))
                if downloaded_files:
                    actual_file = downloaded_files[0]
                    if actual_file != output_path:
                        actual_file.rename(output_path)
                    
                    file_size = output_path.stat().st_size
                    self._log(f"下载成功: {output_path.name} ({file_size} bytes)")
                    return True, f"成功下载 {file_size} bytes"
                else:
                    return False, "未找到下载的文件"
            else:
                return False, f"yt-dlp 错误: {result.stderr[:200]}"
                
        except subprocess.TimeoutExpired:
            return False, "下载超时 (300秒)"
        except Exception as e:
            return False, f"yt-dlp 异常: {str(e)}"
    
    def download_url(self, url: str) -> Tuple[bool, str, Optional[Path]]:
        """
        下载单个 URL
        
        Returns:
            (success, message, file_path)
        """
        self._log(f"处理 URL: {url}")
        
        timestamp = int(time.time() * 1000)
        filename = f"audio_{timestamp}"
        
        is_direct = self._is_direct_link(url)
        self._log(f"URL 类型: {'直接链接' if is_direct else '页面链接'}")
        
        if is_direct:
            temp_file = self.download_dir / f"{filename}.mp4"
            success, message = self._download_with_requests(url, temp_file)
            
            if success:
                audio_file = self.download_dir / f"{filename}.mp3"
                if self._extract_audio(temp_file, audio_file):
                    temp_file.unlink()
                    return True, message, audio_file
                else:
                    return True, f"{message} (音频提取失败, 保留视频)", temp_file
            else:
                self._log(f"requests 下载失败，尝试 yt-dlp...")
                success, message = self._download_with_ytdlp(url, temp_file)
                if success:
                    audio_file = self.download_dir / f"{filename}.mp3"
                    if self._extract_audio(temp_file, audio_file):
                        temp_file.unlink()
                        return True, message, audio_file
                    else:
                        return True, message, temp_file
                return False, message, None
        else:
            audio_file = self.download_dir / f"{filename}.mp3"
            success, message = self._download_with_ytdlp(url, audio_file)
            if success:
                return True, message, audio_file
            else:
                self._log(f"yt-dlp 失败，尝试作为直接链接下载...")
                temp_file = self.download_dir / f"{filename}.mp4"
                success, message = self._download_with_requests(url, temp_file)
                if success:
                    if self._extract_audio(temp_file, audio_file):
                        temp_file.unlink()
                        return True, message, audio_file
                    else:
                        return True, message, temp_file
                return False, message, None
    
    def _extract_audio(self, video_path: Path, audio_path: Path) -> bool:
        """使用 ffmpeg 提取音频"""
        try:
            subprocess.run(['ffmpeg', '-version'], capture_output=True, check=True)
        except (subprocess.CalledProcessError, FileNotFoundError):
            self._log("ffmpeg 未安装，尝试安装...")
            try:
                subprocess.run(['sudo', 'apt-get', 'update'], capture_output=True)
                subprocess.run(['sudo', 'apt-get', 'install', '-y', 'ffmpeg'], capture_output=True)
                self._log("ffmpeg 安装成功")
            except Exception as e:
                self._log(f"ffmpeg 安装失败: {e}", "ERROR")
                return False
        
        cmd = [
            'ffmpeg',
            '-i', str(video_path),
            '-vn',
            '-acodec', 'mp3',
            '-q:a', '2',
            '-y',
            str(audio_path)
        ]
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            if result.returncode == 0 and audio_path.exists() and audio_path.stat().st_size > 0:
                self._log(f"音频提取成功: {audio_path.name}")
                return True
            else:
                error_msg = result.stderr[:200] if result.stderr else "未知错误"
                self._log(f"音频提取失败: {error_msg}", "ERROR")
                return False
        except Exception as e:
            self._log(f"音频提取异常: {str(e)}", "ERROR")
            return False
    
    def download_urls(self, urls: List[str]) -> Tuple[List[Path], Dict]:
        """
        批量下载 URLs
        
        Returns:
            (成功下载的文件列表, 统计信息)
        """
        downloaded_files = []
        stats = {
            'total': len(urls),
            'success': 0,
            'failed': 0,
            'total_time': 0
        }
        
        for i, url in enumerate(urls, 1):
            self._log(f"\n[{i}/{len(urls)}] 处理 URL")
            
            start_time = time.time()
            success, message, file_path = self.download_url(url)
            elapsed = time.time() - start_time
            stats['total_time'] += elapsed
            
            if success and file_path:
                stats['success'] += 1
                downloaded_files.append(file_path)
                self._log(f"✅ 成功 [{i}/{len(urls)}]: {message} (耗时: {elapsed:.2f}秒)")
            else:
                stats['failed'] += 1
                self._log(f"❌ 失败 [{i}/{len(urls)}]: {message} (耗时: {elapsed:.2f}秒)")
        
        with open(self.download_log, 'a', encoding='utf-8') as f:
            f.write(f"\n{'='*60}\n")
            f.write(f"下载统计: 总计={stats['total']}, 成功={stats['success']}, 失败={stats['failed']}\n")
            f.write(f"总耗时: {stats['total_time']:.2f}秒\n")
            f.write(f"结束时间: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"{'='*60}\n")
        
        return downloaded_files, stats


def setup_model():
    """加载 FunASR 模型"""
    try:
        from funasr import AutoModel
        
        logger.info("正在加载 FunASR 模型...")
        start_time = time.time()
        
        model = AutoModel(
            model="damo/speech_paraformer-large_asr_nat-zh-cn-16k-common-vocab8404-pytorch",
            vad_model="damo/speech_fsmn_vad_zh-cn-16k-common-pytorch",
            punc_model="damo/punc_ct-transformer_zh-cn-common-vocab272727-pytorch",
            disable_update=True
        )
        
        load_time = time.time() - start_time
        logger.info(f"模型加载完成，耗时: {load_time:.2f} 秒")
        return model
        
    except ImportError as e:
        logger.error(f"无法导入 funasr: {e}")
        raise
    except Exception as e:
        logger.error(f"模型加载失败: {e}")
        raise



def transcribe_audio(model, audio_path: Path) -> Optional[str]:
    """转录单个音频文件"""
    if not audio_path.exists():
        logger.error(f"文件不存在: {audio_path}")
        return None
    
    file_size = audio_path.stat().st_size / (1024 * 1024)
    logger.info(f"开始转录: {audio_path.name} ({file_size:.2f} MB)")
    
    start_time = time.time()
    
    try:
        result = model.generate(
            input=str(audio_path),
            batch_size_s=300,
            hotwords=''
        )
        
        elapsed = time.time() - start_time
        
        if result and len(result) > 0:
            text = result[0].get('text', '')
            logger.info(f"转录完成: {audio_path.name} (耗时: {elapsed:.2f}秒)")
            if text:
                preview = text[:100] + "..." if len(text) > 100 else text
                logger.info(f"识别文本: {preview}")
            return text
        else:
            logger.warning(f"转录结果为空: {audio_path.name}")
            return None
            
    except Exception as e:
        logger.error(f"转录失败 {audio_path.name}: {e}")
        return None


def transcribe_batch(model, audio_paths: List[Path]) -> Dict:
    """批量转录"""
    results = {}
    success_count = 0
    fail_count = 0
    
    logger.info(f"开始批量转录，共 {len(audio_paths)} 个文件")
    
    for i, audio_path in enumerate(audio_paths, 1):
        logger.info(f"\n[{i}/{len(audio_paths)}] 处理: {audio_path.name}")
        text = transcribe_audio(model, audio_path)
        
        if text:
            results[str(audio_path)] = text
            success_count += 1
        else:
            fail_count += 1
    
    output_file = Path("recognized_text.txt")
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(f"# 转录结果\n")
        f.write(f"# 生成时间: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"# 成功: {success_count}, 失败: {fail_count}\n\n")
        
        for audio_path, text in results.items():
            filename = Path(audio_path).name
            f.write(f"## 文件: {filename}\n")
            f.write(f"{text}\n")
            f.write("\n" + "-" * 50 + "\n\n")
    
    logger.info(f"\n批量转录完成: 成功={success_count}, 失败={fail_count}")
    return {'success': success_count, 'fail': fail_count, 'results': results}


def main():
    """主函数"""
    logger.info("="*60)
    logger.info("FunASR 音频转录服务启动")
    logger.info(f"工作目录: {os.getcwd()}")
    logger.info("="*60)
    
    url_file = Path("VideoUrlTask.txt")
    has_urls = url_file.exists()
    
    audio_files = []
    download_stats = None
    
    if has_urls:
        logger.info("检测到 VideoUrlTask.txt，开始处理 URL 下载...")
        
        with open(url_file, 'r', encoding='utf-8') as f:
            urls = [line.strip() for line in f if line.strip() and not line.startswith('#')]
        
        if not urls:
            logger.warning("VideoUrlTask.txt 中没有有效的 URL")
        else:
            downloader = VideoDownloader()
            audio_files, download_stats = downloader.download_urls(urls)
            
            if not audio_files:
                logger.error("所有 URL 下载失败，没有音频文件可转录")
                with open("no_results.txt", 'w', encoding='utf-8') as f:
                    f.write("任务失败：所有 URL 下载失败\n")
                    f.write(f"检查时间: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
                    f.write("请查看 logs/download.log 获取详细信息\n")
                sys.exit(1)
    
    audio_file_list = os.environ.get('AUDIO_FILE_LIST', '')
    if audio_file_list:
        for path_str in audio_file_list.split(','):
            path = Path(path_str.strip())
            if path.exists() and path not in audio_files:
                audio_files.append(path)
    
    if not audio_files:
        logger.warning("没有找到音频文件")
        with open("no_results.txt", 'w', encoding='utf-8') as f:
            f.write("无转录任务：没有音频文件需要处理\n")
            f.write(f"检查时间: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        sys.exit(0)
    
    try:
        model = setup_model()
        result = transcribe_batch(model, audio_files)
        
        with open("transcription_summary.txt", 'w', encoding='utf-8') as f:
            f.write(f"转录完成时间: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"成功转录: {result['success']} 个文件\n")
            f.write(f"失败: {result['fail']} 个文件\n")
            if download_stats:
                f.write(f"\n下载统计:\n")
                f.write(f"  总计: {download_stats['total']}\n")
                f.write(f"  成功: {download_stats['success']}\n")
                f.write(f"  失败: {download_stats['failed']}\n")
                f.write(f"  总耗时: {download_stats['total_time']:.2f}秒\n")
        
        sys.exit(0 if result['success'] > 0 else 1)
        
    except Exception as e:
        logger.error(f"转录过程出错: {e}")
        with open("no_results.txt", 'w', encoding='utf-8') as f:
            f.write(f"任务失败: {str(e)}\n")
            f.write(f"时间: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        sys.exit(1)


if __name__ == "__main__":
    main()