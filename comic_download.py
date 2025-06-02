import os
import requests
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urlparse
import time
import threading
import base64

class ComicDownloader:
    def __init__(self, comic_mid, max_chapter_workers=5, max_image_workers=10):
        self.base_url = "https://m.g-mh.org"
        self.api_base_url = "https://api-get-v2.mgsearcher.com"
        self.img_base_url = "https://f40-1-4.g-mh.online" 

        self.comic_mid = comic_mid

        self.webhook_url = os.getenv('discord_webhook')

        self.base_headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Referer': 'https://m.g-mh.org/'
        }
              
        self.max_chapter_workers = max_chapter_workers
        self.max_image_workers = max_image_workers

    def send_to_webhook(self, message):
        try:
            payload = {
                "content": message
            }
            response = requests.post(
                self.webhook_url,
                json=payload,
                headers={'Content-Type': 'application/json'}
            )
            response.raise_for_status()
        except Exception as e:
            print(f"Failed to send to webhook: {str(e)}")

    def download_image(self, url):
        """
        下载单张图片
        """
        try:
            response = requests.get(self.img_base_url+url, headers=self.base_headers, stream=True, timeout=30)
            response.raise_for_status()
            
            base64_img = base64.b64encode(response.content).decode('utf-8')
            base64_img_html = f'<img src="data:image/png;base64,{base64_img}">'
            
            return base64_img_html
        except Exception as e:
            error_msg = f"Image download failed for {url}: {str(e)}"
            self.send_to_webhook(error_msg)
            return False

    def process_chapter(self, chapter_info):
        """
        处理单个章节
        """
        try:
            chapter_num = chapter_info['id']
            try:
                response = requests.get(self.api_base_url+'/api/chapter/getinfo?m='+self.comic_mid+'&c='+chapter_num, 
                                       headers=self.base_headers, timeout=30)
                response.raise_for_status()
                data = response.json()
            except Exception as e:
                error_msg = f"Failed to get chapter info for chapter {chapter_num}: {str(e)}"
                self.send_to_webhook(error_msg)
                return
            
            image_urls = data['data']['info']['images']['images']['urls']
            
            # 使用线程池下载本章节的所有图片
            with ThreadPoolExecutor(max_workers=self.max_image_workers) as executor:
                results = list(executor.map(self.download_image, image_urls))
            
        except Exception as e:
            error_msg = f"Error processing chapter {chapter_info.get('id', 'unknown')}: {str(e)}"
            self.send_to_webhook(error_msg)

    def download_comic(self):
        """
        下载整部漫画
        """
        try:
            self.send_to_webhook(f"Mission Start")

            try:
                response = requests.get(self.api_base_url+'/api/manga/get?mid='+self.comic_mid+'&mode=all', 
                                     headers=self.base_headers, timeout=30)
                response.raise_for_status()
                data = response.json()
            except Exception as e:
                error_msg = f"Failed to get comic data: {str(e)}"
                self.send_to_webhook(error_msg)
                return
            
            chapters = data['data']['chapters']
           
            # 使用线程池处理所有章节
            with ThreadPoolExecutor(max_workers=self.max_chapter_workers) as executor:
                executor.map(self.process_chapter, chapters)
            
        except Exception as e:
            error_msg = f"Error in download_comic: {str(e)}"
            self.send_to_webhook(error_msg)

# 示例用法
if __name__ == "__main__":
    comic_mid = 'comic_download_task.txt'

    # 创建下载器并开始下载
    downloader = ComicDownloader(comic_mid, max_chapter_workers=30, max_image_workers=20)
    downloader.download_comic()
