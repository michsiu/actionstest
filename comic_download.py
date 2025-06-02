
import requests
import os

# 全局变量

webhook_url = os.getenv('discord_webhook')

def send_to_webhook(message):

    payload = {"content": message}
    response = requests.post(webhook_url, json=payload, headers={'Content-Type': 'application/json'})



if __name__ == "__main__":
    with open('comic_download_task.txt', 'r', encoding='utf-8') as file:
        comic_mid = file.read()
    
    send_to_webhook(comic_mid)