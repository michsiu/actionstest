
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

    
send_to_webhook("666")