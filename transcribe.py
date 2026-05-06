#!/usr/bin/env python3
"""
FunASR 音频转录脚本
支持单文件和多文件转录
"""

import os
import sys
import time
import logging
from pathlib import Path
from typing import List, Optional

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('transcription.log', mode='a'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

def setup_model():
    """加载 FunASR 模型"""
    try:
        from funasr import AutoModel
        
        logger.info("正在加载 FunASR 模型...")
        start_time = time.time()
        
        # 根据环境选择模型
        # CPU 环境使用 paraformer-zh，GPU 环境可以尝试 larger 模型
        model = AutoModel(
            model="paraformer-zh",      # 中文模型
            vad_model="fsmn-vad",       # 语音端点检测
            punc_model="ct-punc",       # 标点恢复
            device="cpu",               # 使用 CPU（GitHub Actions 环境）
            disable_update=True,        # 禁用自动更新
            cache_dir="./model_cache"   # 缓存模型文件
        )
        
        load_time = time.time() - start_time
        logger.info(f"模型加载完成，耗时: {load_time:.2f} 秒")
        
        return model
    except ImportError as e:
        logger.error(f"无法导入 funasr: {e}")
        logger.error("请确保已安装: pip install funasr modelscope")
        raise
    except Exception as e:
        logger.error(f"模型加载失败: {e}")
        raise

def transcribe_audio(model, audio_path: str) -> Optional[str]:
    """
    转录单个音频文件
    
    Args:
        model: FunASR 模型实例
        audio_path: 音频文件路径
    
    Returns:
        识别出的文本，失败返回 None
    """
    if not os.path.exists(audio_path):
        logger.error(f"文件不存在: {audio_path}")
        return None
    
    # 检查文件格式
    valid_extensions = ['.wav', '.mp3', '.m4a', '.mp4', '.flac', '.ogg']
    file_ext = Path(audio_path).suffix.lower()
    if file_ext not in valid_extensions:
        logger.warning(f"不支持的文件格式: {file_ext}，跳过: {audio_path}")
        return None
    
    logger.info(f"开始转录: {audio_path}")
    file_size = os.path.getsize(audio_path) / (1024 * 1024)  # MB
    logger.info(f"文件大小: {file_size:.2f} MB")
    
    start_time = time.time()
    
    try:
        # 执行转录
        result = model.generate(
            input=audio_path,
            batch_size_s=300,      # 批量处理大小
            hotwords=''            # 可以添加热词，如: "人工智能 AI 大模型"
        )
        
        elapsed = time.time() - start_time
        
        if result and len(result) > 0:
            text = result[0].get('text', '')
            logger.info(f"转录完成: {audio_path}")
            logger.info(f"识别文本: {text[:100]}..." if len(text) > 100 else f"识别文本: {text}")
            logger.info(f"耗时: {elapsed:.2f} 秒, 实时率: {elapsed/file_size:.2f}" if file_size > 0 else f"耗时: {elapsed:.2f} 秒")
            
            return text
        else:
            logger.warning(f"转录结果为空: {audio_path}")
            return None
            
    except Exception as e:
        logger.error(f"转录失败 {audio_path}: {e}")
        return None

def transcribe_batch(model, audio_paths: List[str]) -> dict:
    """
    批量转录多个音频文件
    
    Args:
        model: FunASR 模型实例
        audio_paths: 音频文件路径列表
    
    Returns:
        包含统计信息的字典
    """
    results = {}
    success_count = 0
    fail_count = 0
    total_duration = 0
    
    logger.info(f"开始批量转录，共 {len(audio_paths)} 个文件")
    
    for i, audio_path in enumerate(audio_paths, 1):
        logger.info(f"\n[{i}/{len(audio_paths)}] 处理: {audio_path}")
        
        start_time = time.time()
        text = transcribe_audio(model, audio_path)
        elapsed = time.time() - start_time
        
        if text:
            results[audio_path] = text
            success_count += 1
            total_duration += elapsed
        else:
            fail_count += 1
    
    # 写入结果文件
    output_file = "recognized_text.txt"
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(f"# 转录结果\n")
        f.write(f"# 生成时间: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"# 成功: {success_count}, 失败: {fail_count}\n")
        f.write(f"# 总耗时: {total_duration:.2f} 秒\n\n")
        
        for audio_path, text in results.items():
            f.write(f"## 文件: {audio_path}\n")
            f.write(f"{text}\n")
            f.write("\n" + "-" * 50 + "\n\n")
    
    logger.info(f"\n批量转录完成")
    logger.info(f"成功: {success_count}, 失败: {fail_count}")
    logger.info(f"总耗时: {total_duration:.2f} 秒")
    logger.info(f"结果已保存到: {output_file}")
    
    return {
        'success_count': success_count,
        'fail_count': fail_count,
        'total_duration': total_duration,
        'results': results
    }

def append_download_log_to_summary():
    """将下载日志添加到转录日志中"""
    download_log_path = "logs/download.log"
    if os.path.exists(download_log_path):
        logger.info("\n" + "="*60)
        logger.info("下载日志摘要:")
        logger.info("="*60)
        
        with open(download_log_path, 'r') as f:
            content = f.read()
            # 只记录重要的统计信息
            for line in content.split('\n'):
                if any(keyword in line for keyword in ['成功:', '失败:', '总耗时:', '下载开始时间', '下载结束时间']):
                    logger.info(line)
        
        logger.info("="*60)

def main():
    """主函数"""
    logger.info("="*60)
    logger.info("FunASR 音频转录服务启动")
    logger.info(f"工作目录: {os.getcwd()}")
    logger.info(f"环境变量: AUDIO_FILE_LIST={os.environ.get('AUDIO_FILE_LIST', '未设置')}")
    logger.info(f"环境变量: DOWNLOAD_LOG_PATH={os.environ.get('DOWNLOAD_LOG_PATH', '未设置')}")
    logger.info("="*60)
    
    # 模型加载
    try:
        model = setup_model()
    except Exception as e:
        logger.error(f"模型加载失败，退出: {e}")
        sys.exit(1)
    
    # 获取音频文件列表
    audio_file_list = os.environ.get('AUDIO_FILE_LIST', '')
    
    if not audio_file_list:
        logger.warning("未指定音频文件，退出")
        sys.exit(0)
    
    # 解析音频文件列表（逗号分隔）
    audio_paths = [p.strip() for p in audio_file_list.split(',') if p.strip()]
    
    # 去重并过滤已存在的文件
    valid_paths = []
    seen = set()
    for path in audio_paths:
        if path not in seen and os.path.exists(path):
            seen.add(path)
            valid_paths.append(path)
        elif path in seen:
            logger.warning(f"重复文件，已跳过: {path}")
        elif not os.path.exists(path):
            logger.warning(f"文件不存在，已跳过: {path}")
    
    if not valid_paths:
        logger.warning("没有有效的音频文件可处理")
        sys.exit(0)
    
    logger.info(f"找到 {len(valid_paths)} 个有效音频文件")
    for i, path in enumerate(valid_paths, 1):
        logger.info(f"  {i}. {path}")
    
    # 执行转录
    try:
        result = transcribe_batch(model, valid_paths)
        
        # 添加下载日志摘要（如果有）
        append_download_log_to_summary()
        
        # 返回退出码
        if result['success_count'] == 0:
            logger.error("没有成功转录任何文件")
            sys.exit(1)
        else:
            logger.info("转录任务完成")
            sys.exit(0)
            
    except KeyboardInterrupt:
        logger.warning("用户中断")
        sys.exit(130)
    except Exception as e:
        logger.error(f"转录过程出错: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
