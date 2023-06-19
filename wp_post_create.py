import requests
from requests.auth import HTTPBasicAuth
import time
import random
from flask import Flask, request, jsonify
import os
from dotenv import load_dotenv
import pickle
import re

# 读取根目录下的.env文件
load_dotenv()

# 创建文章
def post_to_wp( post_title, post_content, category_id ):
    # 设置相关参数
    wp_base_url = os.getenv('WP_BASE_URL')  # 用您的 WordPress 网站地址替换
    wp_username = os.getenv('WP_USERNAME')  # 用您的用户名替换
    wp_password = os.getenv('WP_PASSWORD')  # 用您的密码替换
    wp_api_posts_url = f"{wp_base_url}/wp-json/wp/v2/posts"

    # 准备文章数据
    post_data = {
        "title": post_title,
        "content": post_content,
        "categories": [category_id],  # 将文章分配到指定分类
        "status": "publish",  # 设置文章状态为已发布
    }

    # 发送请求，将文章写入 WordPress v6.2 文章表
    response = requests.post(
        wp_api_posts_url, auth=HTTPBasicAuth(wp_username, wp_password), json=post_data
    )

    if response.status_code == 201:
        print("文章已成功发布！")
    else:
        print("发布文章时发生错误。请检查您的设置和输入。")