from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import shutil

def get_video_url(url):
    """使用 Selenium 获取视频 URL"""
    
    send_log(f"🌐 访问网页: {url}")

    chrome_options = Options()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--disable-popup-blocking')

    # 在 Railway 服务器上查找 ChromeDriver 的正确路径
    chromedriver_path = shutil.which("chromedriver")

    if not chromedriver_path:
        send_log("❌ 未找到 ChromeDriver，请检查是否正确安装！")
        return None

    send_log(f"✅ ChromeDriver 路径: {chromedriver_path}")

    # 使用指定路径的 ChromeDriver
    driver = webdriver.Chrome(executable_path=chromedriver_path, options=chrome_options)

    try:
        driver.get(url)
        time.sleep(5)
        video_elements = driver.find_elements_by_tag_name("video")
        if video_elements:
            video_url = video_elements[0].get_attribute("src")
            send_log(f"✅ 找到视频地址: {video_url}")
            return video_url
    except Exception as e:
        send_log(f"❌ 解析视频失败: {e}")
    finally:
        driver.quit()
    return None
