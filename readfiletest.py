
import requests
import os

webhook_url = os.getenv('discord_webhook')

def send_to_webhook(message):

    payload = {"content": message}
    response = requests.post(webhook_url, json=payload, headers={'Content-Type': 'application/json'})

if __name__ == "__main__":
    with open('foldertesst/foldertest.txt', 'r', encoding='utf-8') as file:
        send_to_webhook(file)
    
