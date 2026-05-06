FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    MODELSCOPE_CACHE=/modelscope_cache

# 安装 ffmpeg、Python
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    ffmpeg \
    python3.10 \
    python3-pip \
    git \
    wget \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 安装 Python 依赖
RUN pip3 install --break-system-packages --no-cache-dir \
    funasr==1.3.1 \
    modelscope \
    torch \
    torchaudio \
    yt-dlp

# 关键：预下载模型，禁用更新检查
RUN mkdir -p ${MODELSCOPE_CACHE} && \
    MODELSCOPE_CACHE=/modelscope_cache \
    python3 -c "\
import os; \
os.environ['MODELSCOPE_CACHE'] = '/modelscope_cache'; \
os.environ['MODELSCOPE_SKIP_UPDATE'] = '1'; \
from funasr import AutoModel; \
print('>>> ASR...'); \
m1 = AutoModel(model='damo/speech_paraformer-large_asr_nat-zh-cn-16k-common-vocab8404-pytorch', disable_update=True); \
print('>>> VAD...'); \
m2 = AutoModel(model='damo/speech_fsmn_vad_zh-cn-16k-common-pytorch', disable_update=True); \
print('>>> PUNC...'); \
m3 = AutoModel(model='damo/punc_ct-transformer_zh-cn-common-vocab272727-pytorch', disable_update=True); \
print('>>> All models cached.')"

# 验证模型确实在镜像里
RUN du -sh /modelscope_cache && ls -R /modelscope_cache/ | head -30

WORKDIR /workspace