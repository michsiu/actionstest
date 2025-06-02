
import requests

# 全局变量
base_url = "https://m.g-mh.org"
api_base_url = "https://api-get-v2.mgsearcher.com"
img_base_url = "https://f40-1-4.g-mh.online"
webhook_url = os.getenv('discord_webhook')
base_headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Referer': 'https://m.g-mh.org/'
}

def send_to_webhook(message):
    payload = {"content": message}
    response = requests.post(
        webhook_url,
        json=payload,
        headers={'Content-Type': 'application/json'}
    )

def download_comic(comic_mid):
    """下载整部漫画，并合并结果"""
    send_to_webhook("任务开始")

    response = requests.get(
        api_base_url + f'/api/manga/get?mid={comic_mid}&mode=all',
        headers=base_headers
    )
    data = response.json()
    chapters = data['data']['chapters']

    # 合并并保存结果
    send_to_webhook("任务完成")

if __name__ == "__main__":
    with open('comic_download_task.txt', 'r', encoding='utf-8') as file:
        comic_mid = file.read()
    
    send_to_webhook(comic_mid)