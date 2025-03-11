# 选择 Python 3.9 作为基础镜像
FROM python:3.9

# 设置工作目录
WORKDIR /app

# 安装系统依赖，包括 Chrome 和 ChromeDriver
RUN apt-get update && apt-get install -y \
    wget \
    unzip \
    curl \
    chromium \
    chromium-driver

# 复制项目文件
COPY . .

# 安装 Python 依赖
RUN pip install --no-cache-dir -r requirements.txt

# 设置 ChromeDriver 路径
ENV PATH="/usr/lib/chromium/:${PATH}"

# 启动 Flask 应用
CMD ["python", "app.py"]
