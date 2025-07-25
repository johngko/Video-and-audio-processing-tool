#!/bin/bash

# 视频音频处理网站镜像构建脚本

echo "========================================"
echo "      视频音频处理网站镜像构建脚本       "
echo "========================================"

# 检查系统架构
ARCH=$(uname -m)
echo "检测到系统架构: $ARCH"

# 创建bin目录
mkdir -p bin
cd bin

# 根据架构下载对应的FFmpeg版本
if [ "$ARCH" = "aarch64" ]; then
    echo "下载ARM64版本的FFmpeg..."
    wget https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-arm64-static.tar.xz
else
    echo "下载x86_64版本的FFmpeg..."
    wget https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-amd64-static.tar.xz
fi

# 解压并安装FFmpeg
tar xf ffmpeg-*-static.tar.xz
cp ffmpeg-*-static/ffmpeg .
cp ffmpeg-*-static/ffprobe .
chmod +x ffmpeg ffprobe
rm -rf ffmpeg-*-static*
cd ..

# 构建Docker镜像
docker build -t media-processor .

# 保存镜像为tar文件（用于离线部署）
docker save -o media-processor-image.tar media-processor

echo "镜像构建完成，生成的离线镜像文件：media-processor-image.tar"