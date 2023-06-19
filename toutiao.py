from selenium import webdriver
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import cv2
import numpy as np
from PIL import Image
from io import BytesIO
import requests
import random
import jieba.analyse
import http.client
import json
import os
from dotenv import load_dotenv
import pickle
import re
from datetime import datetime
import schedule
import mysql.connector

# 读取根目录下的.env文件
load_dotenv()

# 替换为你的用户名和密码
TT_USERNAME = os.getenv('TT_USERNAME')
TT_PASSWORD = os.getenv('TT_PASSWORD')
cache_file = "post_id_cache.pickle"
API_KEY = os.getenv('API_KEY')  

def remove_html_tags(content):
    html_tag_pattern = re.compile('<.*?>')
    clean_text = re.sub(html_tag_pattern, '', content)
    return clean_text

def get_mysql_data( cate = 'AI', last_id = 0 ):
    # 连接到MySQL数据库
    conn = mysql.connector.connect(
        host= os.getenv('MYSQL_HOST_IP'),        # 数据库主机地址
        user=os.getenv('MYSQL_USERNAME'),     # 数据库用户名
        password=os.getenv('MYSQL_PASSWORD'), # 数据库密码
        database=os.getenv('MYSQL_DATABASE')  # 数据库名称
    )
    # 创建游标对象
    cursor = conn.cursor( dictionary=True )
    # 查询数据的SQL语句
    sql = "SELECT * FROM oc_article WHERE id>%s and cate=%s LIMIT 1"
    params = (last_id, cate)
    # 执行查询操作
    cursor.execute( sql, params )
    # 获取查询结果（一条数据）
    row = cursor.fetchone()
    # 关闭游标和连接
    cursor.close()
    conn.close()
    return row

#获取分类下是否有标题需要生成文章
def post_get_wp():
    # 检查缓存文件是否存在
    if os.path.exists(cache_file):
        # 如果文件存在，从文件中读取缓存的文章 ID
        with open(cache_file, "rb") as f:
            cached_post_id = pickle.load(f)
            print(f"从缓存文件 {cache_file} 中读取到的文章 ID：{cached_post_id}")
    else:
        cached_post_id = 0
        print(f"缓存文件 {cache_file} 不存在。")
    category = 'AI'  # 分类str
    posts = get_mysql_data( category, cached_post_id )
    print(posts)
    if posts:
        print("找到的文章：" + posts["title"])
        toutiao_article(posts["title"],  posts["content"] )   
        post_id = posts["id"]
        with open( cache_file, "wb" ) as f:
            pickle.dump(post_id, f)
            print(f"文章 ID {post_id} 已缓存到文件 {cache_file}")        
    else:
        print("没有找到符合条件的文章。")

# post_get_wp()
# exit

def extract_keywords( title, topK = 5, withWeight = False):
  # 使用jieba提取关键字
    keywords = jieba.analyse.extract_tags( title, topK, withWeight)
    return keywords

def human_like_drag(actions, slider, x_offset, y_offset):
    total_dragged = 0
    while total_dragged < x_offset:
        x_drag = random.uniform(0.1, 0.5) * x_offset
        y_drag = random.uniform(-0.5, 0.5) * y_offset
        actions.move_by_offset(x_drag, y_drag)
        total_dragged += x_drag
        print(f"拖动进度: {total_dragged}/{x_offset}")
        time.sleep(random.uniform(0.05, 0.15))

    # 如果还没有拖动到目标位置，进行最后的调整
    if total_dragged < x_offset:
        actions.move_by_offset(x_offset - total_dragged, 0)

def download_image(image_url):
    response = requests.get(image_url)
    return Image.open(BytesIO(response.content))

def find_best_match(template, source):
    result = cv2.matchTemplate(source, template, cv2.TM_CCOEFF_NORMED)
    min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
    return max_loc

def slide_verification(driver):
    # 等待验证图片加载完成
    WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, ".captcha_verify_img--wrapper img"))
    )
    
    # 获取原始图片和滑块图片的 URL
    original_img_url = driver.find_element(By.CSS_SELECTOR, ".captcha_verify_img--wrapper img").get_attribute("src")
    slider_img_url = driver.find_element(By.CSS_SELECTOR, ".captcha_verify_img_slide.react-draggable").get_attribute("src")
    print("original_img_url")
    print(original_img_url)
    print("slider_img_url")
    print(slider_img_url)

    # 下载并保存图片
    original_img = np.array(download_image(original_img_url))
    print("original_img")
    print(original_img)
    slider_img = np.array(download_image(slider_img_url))
    print("slider_img")
    print(slider_img)

    # 灰度化图片
    original_img_gray = cv2.cvtColor(original_img, cv2.COLOR_BGR2GRAY)
    slider_img_gray = cv2.cvtColor(slider_img, cv2.COLOR_BGR2GRAY)

    # 查找最佳匹配位置
    x, y = find_best_match(slider_img_gray, original_img_gray)
    print("x, y")
    print(x, y)

    # 获取滑块
    slider = driver.find_element(By.CSS_SELECTOR, ".captcha_verify_slide--slidebar")
    # 创建一个动作链
    actions = ActionChains(driver)
    # 点击并按住滑动条
    actions.click_and_hold(slider).perform()
    # 将滑动条模拟人类拖动到目标位置
    human_like_drag(actions, slider, x, 0)
    # 释放滑动条
    actions.release().perform()
    print('验证成功！')

def toutiao_article( title, content ):
    # 提取标题关键字
    keyword = extract_keywords( title, 1 )
    title_keyword = keyword[0]
    # 打开今日头条文章发布页
    driver.get('https://mp.toutiao.com/profile_v4/graphic/publish')

    # 暂停几秒钟，以便页面完全加载
    time.sleep( 10 )

    # 查找标题输入框并输入标题
    #title_input = driver.find_element(By.CSS_SELECTOR, "div.editor-title textarea[placeholder='请输入文章标题（2～30个字）']")
    title_input = driver.find_element_by_xpath("//textarea[@placeholder='请输入文章标题（2～30个字）']")
    title_input.send_keys( title )

    content_input = driver.find_element(By.CSS_SELECTOR, "div.ProseMirror[contenteditable='true']")
    # 使用 ActionChains 模拟点击操作
    actions = ActionChains(driver)
    actions.move_to_element(content_input).click().perform()
    content_input.send_keys( content )

    # 点击上传封面按钮
    upload_button = driver.find_element(By.CSS_SELECTOR, "div.article-cover-add")
    driver.execute_script("arguments[0].click();", upload_button)

    # 切换到免费正版图片
    free_images_tab = driver.find_element(By.XPATH, "//div[@class='byte-tabs-header-title' and text()='免费正版图片']")
    driver.execute_script("arguments[0].click();", free_images_tab)

    # 1. 定位搜索框并输入关键词
    #search_box = driver.find_element_by_xpath("//div[@class='inp-search']/input")
    search_box = driver.find_element(By.XPATH, "//div[@class='inp-search']/input")
    search_box.clear()
    search_box.send_keys( title_keyword )

    time.sleep(5)

    # 2. 点击搜索按钮
    search_button = driver.find_element(By.XPATH, "//span[@class='btn-search']")
    search_button.click()

    time.sleep(20)

    # 通过CSS选择器定位第一张图
    first_image = driver.find_element(By.CSS_SELECTOR, "ul.list li.item:first-child")
    first_image.click()

    # 通过CSS选择器定位确定按钮
    confirm_button = driver.find_element(By.CSS_SELECTOR, "button.byte-btn.byte-btn-primary.byte-btn-size-default.byte-btn-shape-square.btn[type='button']")
    # 点击确定按钮
    confirm_button.click()

    time.sleep(16)
    #勾选原创声明
    button = driver.find_element_by_xpath("//span[@class='byte-checkbox-wrapper']")
    driver.execute_script("arguments[0].click();", button)

    time.sleep(18)

    # 通过CSS选择器定位发布按钮
    publish_button = driver.find_element(By.CSS_SELECTOR, "button.byte-btn.byte-btn-primary.byte-btn-size-large.byte-btn-shape-square.publish-btn.publish-btn-last")
    # 点击发布按钮
    publish_button.click()

    time.sleep(19)

    # 通过CSS选择器定位确认发布按钮
    confirm_publish_button = driver.find_element(By.CSS_SELECTOR, "button.byte-btn.byte-btn-primary.byte-btn-size-large.byte-btn-shape-square.publish-btn.publish-btn-last")
    # 点击确认发布按钮
    confirm_publish_button.click()

    # 暂停几秒钟，以便提交完成
    time.sleep(5)

# 初始化Selenium Webdriver
driver = webdriver.Chrome("D:\workspace_python\chat_py\chromedriver_win32\chromedriver.exe")

# 打开今日头条登录页
driver.get('https://mp.toutiao.com/auth/page/login')

# 等待元素加载
wait = WebDriverWait(driver, 10)
password_login_element = wait.until(
    EC.element_to_be_clickable((By.XPATH, '//li[@aria-label="账密登录"]'))
)

# 点击密码登录按钮
password_login_element.click()

# 输入手机号/邮箱
phone_email_input = wait.until(
    EC.element_to_be_clickable((By.XPATH, '//input[@placeholder="手机号/邮箱"]'))
)
phone_email_input.send_keys( USERNAME )

# 输入密码
password_input = wait.until(
    EC.element_to_be_clickable((By.XPATH, '//input[@placeholder="密码"]'))
)
password_input.send_keys( PASSWORD )

# 勾选同意多选框
agree_checkbox = wait.until(
    EC.element_to_be_clickable((By.XPATH, '//span[@class="web-login-confirm-info__checkbox"]'))
)
agree_checkbox.click()

# 点击登录按钮
login_button = wait.until(
    EC.element_to_be_clickable((By.XPATH, '//button[@type="submit"]'))
)
login_button.click()

# 等待元素加载
time.sleep( 30 )

# post_get_wp()
# exit()

# 定时任务
schedule.every().day.at("05:00").do(post_get_wp)
schedule.every().day.at("14:55").do(post_get_wp)
schedule.every().day.at("15:00").do(post_get_wp)
schedule.every().day.at("16:22").do(post_get_wp)
schedule.every().day.at("17:00").do(post_get_wp)
schedule.every().day.at("18:30").do(post_get_wp)

# 主循环，定期检查是否有任务需要执行
while True:
    schedule.run_pending()
    time.sleep(60)