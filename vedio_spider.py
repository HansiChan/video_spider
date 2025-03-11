from flask import Flask, render_template, request, jsonify, send_file
from flask_socketio import SocketIO
import requests
import os
import time
import json
from urllib.parse import urljoin
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")
SAVE_DIR = "downloads"

def send_log(message):
    """向前端发送日志信息"""
    socketio.emit('log', {'message': message})

def send_progress(progress):
    """向前端发送下载进度（只更新当前进度）"""
    socketio.emit('progress', {'progress': progress})

def get_video_url(url):
    """使用多种策略获取视频 URL"""
    send_log(f"🌐 访问网页: {url}")

    chrome_options = Options()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--disable-web-security')
    chrome_options.add_argument('--disable-features=IsolateOrigins,site-per-process')
    chrome_options.add_argument("--remote-debugging-port=9222")
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")

    driver = webdriver.Chrome(options=chrome_options)
    video_url = None
    retry_count = 3

    try:
        for attempt in range(retry_count):
            try:
                driver.get(url)
                time.sleep(5)
                
                # 1. 尝试直接查找video标签
                video_elements = driver.find_elements(By.TAG_NAME, "video")
                if video_elements:
                    for video in video_elements:
                        video_url = video.get_attribute('src')
                        if video_url:
                            send_log(f"✅ 通过video标签找到视频地址: {video_url}")
                            return video_url

                # 2. 尝试查找iframe
                iframes = driver.find_elements(By.TAG_NAME, "iframe")
                for iframe in iframes:
                    try:
                        driver.switch_to.frame(iframe)
                        video_elements = driver.find_elements(By.TAG_NAME, "video")
                        if video_elements:
                            for video in video_elements:
                                video_url = video.get_attribute('src')
                                if video_url:
                                    send_log(f"✅ 通过iframe中的video标签找到视频地址: {video_url}")
                                    return video_url
                        driver.switch_to.default_content()
                    except:
                        driver.switch_to.default_content()
                        continue

                # 3. 尝试查找source标签
                source_elements = driver.find_elements(By.TAG_NAME, "source")
                if source_elements:
                    for source in source_elements:
                        video_url = source.get_attribute('src')
                        if video_url:
                            send_log(f"✅ 通过source标签找到视频地址: {video_url}")
                            return video_url

                # 4. 尝试查找特定的视频播放器
                video_players = [
                    ".video-player video",
                    ".player video",
                    "#player video",
                    "#video-player video",
                    ".video-container video"
                ]
                for selector in video_players:
                    try:
                        element = driver.find_element(By.CSS_SELECTOR, selector)
                        video_url = element.get_attribute('src')
                        if video_url:
                            send_log(f"✅ 通过播放器选择器找到视频地址: {video_url}")
                            return video_url
                    except:
                        continue

                if attempt < retry_count - 1:
                    send_log(f"⚠️ 第{attempt + 1}次尝试未找到视频，将重试...")
                    time.sleep(2)
                else:
                    send_log("❌ 所有尝试均未找到视频地址")

            except Exception as e:
                if attempt < retry_count - 1:
                    send_log(f"⚠️ 第{attempt + 1}次尝试发生错误: {str(e)}，将重试...")
                    time.sleep(2)
                else:
                    send_log(f"❌ 解析过程发生错误: {str(e)}")

    finally:
        driver.quit()

    return video_url

def download_video(video_url):
    """下载视频，并动态更新进度"""
    try:
        if not os.path.exists(SAVE_DIR):
            os.makedirs(SAVE_DIR)

        send_log(f"⬇️ 开始下载: {video_url}")

        headers = {
            'User-Agent': 'Mozilla/5.0',
            'Referer': video_url
        }

        response = requests.get(video_url, headers=headers, stream=True)
        response.raise_for_status()

        # 使用固定文件名
        filename = "video.mp4"
        filepath = os.path.join(SAVE_DIR, filename)

        total_size = int(response.headers.get('content-length', 0))
        downloaded_size = 0
        block_size = 1024

        with open(filepath, 'wb') as f:
            for chunk in response.iter_content(chunk_size=block_size):
                if chunk:
                    f.write(chunk)
                    downloaded_size += len(chunk)
                    if total_size > 0:
                        progress = (downloaded_size / total_size) * 100
                        send_progress(f"{progress:.2f}%")

        send_log(f"✅ 下载完成: {filepath}")
        send_progress("100%")
        return filepath

    except Exception as e:
        send_log(f"❌ 下载失败: {e}")
        return None

@app.route('/')
def index():
    """显示网页"""
    return render_template("index.html")

@app.route('/fetch_video', methods=['POST'])
def fetch_video():
    """解析视频 URL 并自动触发下载"""
    page_url = request.form.get("url")
    if not page_url:
        return jsonify({"status": "error", "message": "请输入有效的 URL"}), 400

    send_log("🔍 开始解析视频...")
    video_url = get_video_url(page_url)

    if video_url:
        send_log("✅ 解析完成！自动下载...")
        filepath = download_video(video_url)

        if filepath:
            return jsonify({"status": "success", "video_url": video_url, "download_url": f"/download_video?path={filepath}"})
        else:
            return jsonify({"status": "error", "message": "下载失败"}), 500
    else:
        send_log("❌ 解析失败！")
        return jsonify({"status": "error", "message": "未找到视频"}), 404

@app.route('/download_video', methods=['GET'])
def download():
    """返回下载的视频文件"""
    filepath = request.args.get("path")
    if not filepath or not os.path.exists(filepath):
        return "❌ 文件不存在", 404

    return send_file(filepath, as_attachment=True)

if __name__ == '__main__':
    socketio.run(app, host="0.0.0.0", port=5030, debug=True, allow_unsafe_werkzeug=True)
