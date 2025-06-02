import requests
import sys
import os

def send_to_slack(webhook_url, message):
    """发送消息到Slack webhook"""
    payload = {
        "content": message
    }
    
    try:
        response = requests.post(
            webhook_url,
            json=payload,
            headers={'Content-Type': 'application/json'}
        )
        
        if response.status_code != 200:
            print(f"发送到Slack失败，状态码: {response.status_code}, 响应: {response.text}")
            return False
        return True
    except Exception as e:
        print(f"发送到Slack时出错: {e}")
        return False

if __name__ == "__main__":
   
    

    webhook_url = os.getenv('discord_webhook')
    with open('comic_download_task.txt', 'r', encoding='utf-8') as file:
        comic_mid = file.read()    

    

    content = "666\n"+comic_mid+"\n789"
    if send_to_slack(webhook_url, content):
        print("内容已成功发送到Slack!")

    else:
        print("发送到Slack失败")

