import requests
import os

def send_to_webhook(message):
    """发送消息到Discord webhook"""
    webhook_url = os.getenv('discord_webhook')
    
    # 检查webhook URL是否设置
    if not webhook_url:
        print("错误: 未设置 discord_webhook 环境变量")
        return False
    
    # 确保消息是字符串且不为空
    if not message or not isinstance(message, str):
        message = "空消息或非字符串内容"
    
    payload = {"content": message}
    
    try:
        response = requests.post(
            webhook_url, 
            json=payload, 
            headers={'Content-Type': 'application/json'},
            timeout=10  # 添加超时
        )
        
        # 检查响应状态
        if response.status_code == 204:
            print("消息发送成功")
            return True
        else:
            print(f"发送失败，状态码: {response.status_code}")
            print(f"响应内容: {response.text}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"网络请求错误: {e}")
        return False
    except Exception as e:
        print(f"未知错误: {e}")
        return False

def read_and_send_file():
    """读取文件并发送内容"""
    file_path = 'foldertesst/foldertest.txt'
    
    # 检查文件是否存在
    if not os.path.exists(file_path):
        error_msg = f"错误: 文件不存在 - {file_path}"
        print(error_msg)
        send_to_webhook(error_msg)
        return
    
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            content = file.read().strip()  # ✅ 读取内容并去除首尾空白
            
        # 检查文件是否为空
        if not content:
            send_to_webhook("文件内容为空")
            return
            
        # 限制消息长度（Discord限制2000字符）
        if len(content) > 1900:
            content = content[:1900] + "...（内容过长已截断）"
            
        send_to_webhook(content)
        
    except UnicodeDecodeError:
        error_msg = "错误: 文件编码问题，无法读取为UTF-8"
        print(error_msg)
        send_to_webhook(error_msg)
    except Exception as e:
        error_msg = f"读取文件时出错: {e}"
        print(error_msg)
        send_to_webhook(error_msg)

if __name__ == "__main__":
    # 先发送开始通知
    send_to_webhook('🚀 Task Start')
    
    # 读取并发送文件内容
    read_and_send_file()
    
    # 可选：发送完成通知
    send_to_webhook('✅ Task Complete')