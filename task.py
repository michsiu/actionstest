import requests
import sys
import os

def read_txt_file(file_path):
    """读取txt文件内容"""
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            content = file.read()
        return content
    except FileNotFoundError:
        print(f"错误：文件 {file_path} 未找到")
        sys.exit(1)
    except Exception as e:
        print(f"读取文件时出错: {e}")
        sys.exit(1)

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
   
    
    file_path = 'task.txt'
    webhook_url = os.getenv('discord_webhook')
    
    # 读取文件内容
    file_content = read_txt_file(file_path)
    os_content = os.getenv('send_content')
    

    content = file_content+"\n"+os_content

    # 发送到Slack
    if send_to_slack(webhook_url, content):
        print("内容已成功发送到Slack!")

    else:
        print("发送到Slack失败")

