import os
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
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
        self.all_results = {'chapters': []}  # 存储所有章节的图片数据

    def send_to_webhook(self, message):
        payload = {"content": message}
        response = requests.post(
            self.webhook_url,
            json=payload,
            headers={'Content-Type': 'application/json'}
        )

    def download_image(self, url):
        """下载单张图片并返回 base64 编码"""
        try:
            response = requests.get(self.img_base_url + url, headers=self.base_headers, stream=True, timeout=30)
            response.raise_for_status()
            
            base64_img = base64.b64encode(response.content).decode('utf-8')
            base64_img_html = f'<img src="data:image/png;base64,{base64_img}">'
            return base64_img_html
        except Exception as e:
            self.send_to_webhook(f"下载图片失败: {e}")
            return None

    def process_chapter(self, chapter_info):
        """处理单个章节，返回该章节的所有图片"""
        chapter_num = chapter_info['id']
        response = requests.get(
            self.api_base_url + f'/api/chapter/getinfo?m={self.comic_mid}&c={chapter_num}',
            headers=self.base_headers
        )
        data = response.json()
        image_urls = data['data']['info']['images']['images']['urls']

        chapter_results = {'images': []}

        with ThreadPoolExecutor(max_workers=self.max_image_workers) as executor:
            futures = [executor.submit(self.download_image, url) for url in image_urls]
            
            for future in as_completed(futures):
                result = future.result()
                if result:
                    chapter_results['images'].append(result)
        
        self.send_to_webhook(f"章节 {chapter_num} 完成")
        return chapter_results

    def save_to_html(self, filename="comic_output.html"):
        """将所有章节的图片保存到一个 HTML 文件"""
        html_content = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>漫画下载结果</title>
            <meta charset="UTF-8">
            <style>
                body { font-family: Arial, sans-serif; margin: 20px; }
                h1 { color: #333; }
                .chapter { margin-bottom: 40px; border-bottom: 2px solid #ccc; padding-bottom: 20px; }
                .chapter-title { font-size: 1.5em; color: #555; margin-bottom: 10px; }
                img { max-width: 100%; margin-bottom: 5px; display: block; }
            </style>
        </head>
        <body>
            <h1>漫画下载结果</h1>
        """

        for chapter_num, chapter_data in self.all_results.items():
            html_content += f'<div class="chapter">\n'
            html_content += f'    <div class="chapter-title">章节 {chapter_num}</div>\n'
            
            for img_html in chapter_data['images']:
                html_content += f'    {img_html}\n'
            
            html_content += '</div>\n'

        html_content += """
        </body>
        </html>
        """

        with open(filename, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        self.send_to_webhook(f"结果已保存到 {filename}")

    def download_comic(self):
        """下载整部漫画，并合并结果"""
        self.send_to_webhook("任务开始")

        response = requests.get(
            self.api_base_url + f'/api/manga/get?mid={self.comic_mid}&mode=all',
            headers=self.base_headers
        )
        data = response.json()
        chapters = data['data']['chapters']

       

        # 合并并保存结果
        self.send_to_webhook("任务完成")

if __name__ == "__main__":
    with open('comic_download_task.txt', 'r', encoding='utf-8') as file:
            comic_mid = file.read()

    downloader = ComicDownloader(comic_mid, max_chapter_workers=30, max_image_workers=20)
    downloader.download_comic()