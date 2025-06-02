import requests
import sys
import os

def send_to_webhook(message):
    webhook_url = os.getenv('discord_webhook')
    payload = {"content": message}
    response = requests.post(
        webhook_url,
        json=payload,
        headers={'Content-Type': 'application/json'}
    )

if __name__ == "__main__":
   
    

    
    with open('comic_download_task.txt', 'r', encoding='utf-8') as file:
        comic_mid = file.read()    

    

    content = "666\n"+comic_mid+"\n789"
    if send_to_slack(content):
        print("内容已成功发送到Slack!")

    else:
        print("发送到Slack失败")

