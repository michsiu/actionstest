FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1

# 安装 ffmpeg 和 Python
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    ffmpeg \
    python3.10 \
    python3-pip \
    git \
    && rm -rf /var/lib/apt/lists/*

# 安装 Python 依赖
RUN pip3 install --break-system-packages --no-cache-dir \
    funasr==1.3.1 \
    modelscope \
    torch \
    torchaudio

# 预下载所有模型到镜像中
RUN python3 -c "\
from funasr import AutoModel; \
print('>>> Downloading ASR model...'); \
AutoModel(model='damo/speech_paraformer-large_asr_nat-zh-cn-16k-common-vocab8404-pytorch', disable_update=True); \
print('>>> Downloading VAD model...'); \
AutoModel(model='damo/speech_fsmn_vad_zh-cn-16k-common-pytorch', disable_update=True); \
print('>>> Downloading Punctuation model...'); \
AutoModel(model='damo/punc_ct-transformer_zh-cn-common-vocab272727-pytorch', disable_update=True); \
print('>>> All models downloaded successfully.')"

WORKDIR /workspace