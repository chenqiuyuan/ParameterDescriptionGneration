import os
import json
from typing import Dict
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions
from selenium.webdriver.remote.webdriver import WebDriver

from selenium.webdriver.firefox import remote_connection

def visualize_code_json(json_string):

    options = Options()
    # 在WSL（windows subsystem linux）环境使用linux的driver和firefox
    options.binary_location = '/usr/bin/firefox'
    service = Service(executable_path="code_parser/geckodriver")

    # Windows 环境
    # options.binary_location = '/mnt/c/Program Files/Mozilla Firefox/Firefox.exe'
    # service = Service(executable_path="code_parser/geckodriver.exe")

    # options.add_argument('--no-sandbox')#解决DevToolsActivePort文件不存在的报错
    # options.add_argument('window-size=1920x3000') #指定浏览器分辨率
    # options.add_argument('--disable-gpu') #谷歌文档提到需要加上这个属性来规避bug
    # options.add_argument('--hide-scrollbars') #隐藏滚动条, 应对一些特殊页面
    # options.add_argument('blink-settings=imagesEnabled=false') #不加载图片, 提升速度
    # # options.add_argument('--headless') #浏览器不提供可视化页面




    # 该程序为WSL编写，需要确保启动了X server
    # 可以在环境变量中设置，最好写入~/.bashrc
    # export DISPLAY=$(cat /etc/resolv.conf | grep nameserver | awk '{print $2; exit;}'):0.0
    # os.system("export DISPLAY=$(cat /etc/resolv.conf | grep nameserver | awk '{print $2; exit;}'):0.0")
        
    driver = webdriver.Firefox(service=service, options=options)

    url = driver.command_executor._url
    session_id = driver.session_id 

    content = {
        "url": str(url),
        "session_id": str(session_id)
    }

    with open("session", "w") as f:
        json.dump(content, f)


    # Get page
    # Online
    driver.get("https://vanya.jp.net/vtree/")
    # 本地
    # driver.get("/mnt/c/Users/38013/OneDrive/Code/vtree-master/index.html")

    # text_area = driver.find_element(By.XPATH, '//*[@id="from-text"]')

    # 找到文本框
    text_area = WebDriverWait(driver, 5, 0.5).until(
                        expected_conditions.presence_of_element_located((By.XPATH, '//*[@id="from-text"]'))
                        )


    text_area.clear()
    text_area.send_keys(json_string)

    button = driver.find_element(By.XPATH, '//*[@id="go-button"]')
    button.click()


def visualize_code_ast(ast: Dict):
    ast_json = json.dumps(ast, indent=4)
    visualize_code_json(ast_json)


if __name__ == "__main__":
    """
    python -m code_parser.visualize_ast
    """
    visualize_code_json("test")
