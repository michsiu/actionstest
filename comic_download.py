import os
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
import time
import threading
import base64
import json

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
        self.results_lock = threading.Lock()
        self.all_results = {}  # 保存所有章节的结果
        self.failed_urls = []  # 保存失败的URL

    def send_to_webhook(self, message):
        """发送消息到webhook，添加错误处理"""
        try:
            payload = {"content": str(message)}
            response = requests.post(
                self.webhook_url,
                json=payload,
                headers={'Content-Type': 'application/json'},
                timeout=10
            )
            response.raise_for_status()
        except Exception as e:
            print(f"Failed to send webhook: {e}")

    def download_image(self, url):
        """下载单张图片，返回结果字典"""
        try:
            full_url = self.img_base_url + url
            response = requests.get(full_url, headers=self.base_headers, stream=True, timeout=30)
            response.raise_for_status()
            
            base64_img = base64.b64encode(response.content).decode('utf-8')
            return {
                'status': 'success',
                'url': url,
                'data': f'<img src="data:image/png;base64,{base64_img}">'
            }
        except Exception as e:
            self.send_to_webhook(f"图片下载失败: {url} - 错误: {str(e)}")
            return {
                'status': 'failed',
                'url': url,
                'error': str(e)
            }

    def process_chapter(self, chapter_info):
        """处理单个章节，返回章节结果"""
        chapter_num = chapter_info['id']
        chapter_results = {
            'chapter_id': chapter_num,
            'images': [],
            'success_count': 0,
            'failed_count': 0
        }
        
        try:
            response = requests.get(
                f"{self.api_base_url}/api/chapter/getinfo?m={self.comic_mid}&c={chapter_num}",
                headers=self.base_headers,
                timeout=30
            )
            data = response.json()
            image_urls = data['data']['info']['images']['images']['urls']
            
            with ThreadPoolExecutor(max_workers=self.max_image_workers) as executor:
                futures = [executor.submit(self.download_image, url) for url in image_urls]
                
                for future in as_completed(futures):
                    result = future.result()
                    chapter_results['images'].append(result)
                    
                    if result['status'] == 'success':
                        chapter_results['success_count'] += 1
                    else:
                        chapter_results['failed_count'] += 1
                        self.failed_urls.append(result['url'])
            
            # 保存章节结果
            with self.results_lock:
                self.all_results[chapter_num] = chapter_results
            
            self.send_to_webhook(
                f"章节 {chapter_num} 完成 - 成功: {chapter_results['success_count']}, "
                f"失败: {chapter_results['failed_count']}"
            )
            
            return chapter_results
        except Exception as e:
            self.send_to_webhook(f"章节 {chapter_num} 处理失败: {str(e)}")
            return None

    def download_comic(self):
        """下载整部漫画，返回所有结果"""
        self.send_to_webhook(f"任务开始: 漫画ID {self.comic_mid}")
        
        try:
            response = requests.get(
                f"{self.api_base_url}/api/manga/get?mid={self.comic_mid}&mode=all",
                headers=self.base_headers,
                timeout=30
            )
            data = response.json()
            chapters = data['data']['chapters']
            
            with ThreadPoolExecutor(max_workers=self.max_chapter_workers) as executor:
                futures = [executor.submit(self.process_chapter, chapter) for chapter in chapters]
                
                for future in as_completed(futures):
                    future.result()  # 只是为了捕获异常
            
            # 生成汇总报告
            total_success = sum(ch['success_count'] for ch in self.all_results.values())
            total_failed = sum(ch['failed_count'] for ch in self.all_results.values())
            
            report = {
                'comic_id': self.comic_mid,
                'total_chapters': len(self.all_results),
                'total_images_success': total_success,
                'total_images_failed': total_failed,
                'failed_urls': self.failed_urls,
                'chapters': self.all_results
            }
            
            self.send_to_webhook(
                f"任务完成! 总章节: {len(self.all_results)}, "
                f"成功图片: {total_success}, 失败图片: {total_failed}"
            )
            
            # 保存结果到文件
            with open(f'comic_{self.comic_mid}_results.json', 'w', encoding='utf-8') as f:
                json.dump(report, f, ensure_ascii=False, indent=2)
            
            return report
        except Exception as e:
            self.send_to_webhook(f"漫画下载失败: {str(e)}")
            return None

if __name__ == "__main__":
    # 应该使用实际的漫画ID，而不是文件名
    comic_mid = 'your_comic_id_here'  # 替换为实际的漫画ID
    
    downloader = ComicDownloader(comic_mid, max_chapter_workers=30, max_image_workers=20)
    results = downloader.download_comic()
    
    if results:
        print(f"下载完成! 结果已保存到 comic_{comic_mid}_results.json")