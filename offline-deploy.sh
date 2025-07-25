#!/bin/bash

# 视频音频处理网站离线部署脚本

echo "========================================"
echo "      视频音频处理网站离线部署脚本       "
echo "========================================"

# 检查是否有root权限
if [ "$(id -u)" -ne 0 ]; then
    echo "请使用root权限运行此脚本"
    exit 1
fi

# 检查系统类型
if [ -f /etc/redhat-release ]; then
    OS="centos"
elif [ -f /etc/lsb-release ]; then
    OS="ubuntu"
elif [ -f /etc/debian_version ]; then
    OS="debian"
else
    echo "不支持的操作系统"
    exit 1
fi

# 检查离线文件完整性
check_files() {
    echo "正在检查离线部署文件完整性..."
    
    if [ ! -f "media-processor-image.tar" ]; then
        echo "错误：找不到Docker镜像文件 media-processor-image.tar"
        exit 1
    fi
    
    if [ ! -d "templates" ] || [ ! -f "templates/index.html" ]; then
        echo "错误：找不到前端模板文件"
        exit 1
    fi
    
    if [ ! -f "app.py" ]; then
        echo "错误：找不到后端应用文件 app.py"
        exit 1
    fi
    
    echo "文件检查通过"
}

# 安装Docker
install_docker() {
    echo "正在安装Docker..."
    
    if [ "$OS" == "centos" ]; then
        # CentOS安装Docker
        yum install -y yum-utils device-mapper-persistent-data lvm2
        yum-config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo
        yum install -y docker-ce docker-ce-cli containerd.io
    else
        # Ubuntu/Debian安装Docker
        apt-get update
        apt-get install -y apt-transport-https ca-certificates curl software-properties-common
        curl -fsSL https://download.docker.com/linux/ubuntu/gpg | apt-key add -
        add-apt-repository "deb [arch=amd64] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable"
        apt-get update
        apt-get install -y docker-ce docker-ce-cli containerd.io
    fi
    
    # 启动Docker服务
    systemctl start docker
    systemctl enable docker
    
    echo "Docker安装完成"
}

# 加载Docker镜像
load_image() {
    echo "正在加载Docker镜像..."
    docker load -i media-processor-image.tar
    echo "Docker镜像加载完成"
}

# 部署应用
deploy_app() {
    echo "正在部署应用..."
    
    # 创建持久化目录
    mkdir -p /opt/media-processor/uploads
    mkdir -p /opt/media-processor/output
    chmod 777 /opt/media-processor/uploads /opt/media-processor/output
    
    # 停止并删除现有容器（如果存在）
    docker stop media-processor >/dev/null 2>&1
    docker rm media-processor >/dev/null 2>&1
    
    # 启动新容器
    docker run -d -p 5000:5000 \
        --name media-processor \
        -v /opt/media-processor/uploads:/app/uploads \
        -v /opt/media-processor/output:/app/output \
        media-processor
    
    echo "应用部署完成！"
    echo "访问地址: http://$(hostname -I | awk '{print $1}'):5000"
}

# 主函数
main() {
    check_files
    
    # 检查Docker是否已安装
    if ! command -v docker &> /dev/null; then
        install_docker
    else
        echo "Docker已安装"
    fi
    
    # 加载镜像
    load_image
    
    # 部署应用
    deploy_app
}

# 执行主函数
main