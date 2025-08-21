
import requests
import os

# 全局变量
base_url = "https://m.g-mh.org"
api_base_url = "https://api-get-v2.mgsearcher.com"
img_base_url = "https://f40-1-4.g-mh.online"
webhook_url = os.getenv('discord_webhook')
base_headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Referer': 'https://m.g-mh.org/',
    'Accept': 'application/json, text/javascript, */*; q=0.01',
    'Accept-Language': 'en-US,en;q=0.9',
    'Origin': 'https://m.g-mh.org',
    'Connection': 'keep-alive',
}

def send_to_webhook(message):

    payload = {"content": message}
    response = requests.post(webhook_url, json=payload, headers={'Content-Type': 'application/json'})

def download_comic(comic_mid):
    """下载整部漫画，并合并结果"""
    send_to_webhook("任务开始")
    try:
        session = requests.Session()
        session.headers.update(base_headers)
        response = session.get('https://api-get-v2.mgsearcher.com/api/manga/get?mid=28197&mode=all')
       
        response.raise_for_status()
        data = response.json()
        chapters = data['data']['chapters']

        # 合并并保存结果
        send_to_webhook(f"任务成功！")

    except requests.exceptions.RequestException as e:
        send_to_webhook(f"发生错误：{e}")
    send_to_webhook("任务结束")


if __name__ == "__main__":
    with open('comic_download_task.txt', 'r', encoding='utf-8') as file:
        comic_mid = file.read()
    
