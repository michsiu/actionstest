import requests
import os

webhook_url = os.getenv('discord_webhook')

def send_to_webhook(message):
    if webhook_url is None:
        print("Webhook URL 未设置！")
        return False
    payload = {"content": message}
    response = requests.post(webhook_url, json=payload, headers={'Content-Type': 'application/json'})
    return response.status_code == 200  # 返回是否发送成功

if __name__ == "__main__":
    with open('comic_download_task.txt', 'r', encoding='utf-8') as file:
        comic_mid = file.read()
    
    content = "666\n" + comic_mid + "\n789"
    if send_to_webhook(content):  # 修复函数名
        print("内容已成功发送到Webhook!")
    else:
        print("发送到Webhook失败")
