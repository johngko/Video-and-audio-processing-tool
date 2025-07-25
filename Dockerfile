FROM python:3.9-slim

# 设置工作目录
WORKDIR /app

# 复制依赖文件
COPY requirements.txt .

# 安装Python依赖
RUN pip install --no-cache-dir -r requirements.txt

# 复制应用代码
COPY app.py .
COPY templates/ ./templates/

# 复制FFmpeg静态二进制文件
COPY bin/ffmpeg /usr/bin/
COPY bin/ffprobe /usr/bin/
RUN chmod +x /usr/bin/ffmpeg /usr/bin/ffprobe

# 创建上传和输出目录
RUN mkdir -p /app/uploads /app/output
RUN chmod 777 /app/uploads /app/output

# 暴露端口
EXPOSE 5000

# 启动命令
CMD ["python", "app.py"]