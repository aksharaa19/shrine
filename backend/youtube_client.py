import requests
import os
from dotenv import load_dotenv

load_dotenv()

class YouTubeClient:
    def __init__(self):
        self.api_key = os.getenv('YOUTUBE_API_KEY')
        self.base_url = "https://www.googleapis.com/youtube/v3"
    
    def extract_video_id(self, url):
        if "youtu.be" in url:
            return url.split("/")[-1].split("?")[0]
        if "v=" in url:
            return url.split("v=")[1].split("&")[0]
        if "/live/" in url:
            return url.split("/live/")[1].split("?")[0]
        return url
    
    def get_video_details(self, video_id):
        url = f"{self.base_url}/videos"
        params = {'part': 'snippet', 'id': video_id, 'key': self.api_key}
        try:
            resp = requests.get(url, params=params, timeout=30)
            data = resp.json()
            if data.get('items'):
                s = data['items'][0]['snippet']
                return {'title': s.get('title', 'Unknown'), 'channel': s.get('channelTitle', 'Unknown'), 'published_at': s.get('publishedAt', 'Unknown')}
            return None
        except Exception as e:
            print(f"Video error: {e}")
            return None
    
    def get_comments(self, video_id, max_results=100):
        comments = []
        url = f"{self.base_url}/commentThreads"
        params = {'part': 'snippet', 'videoId': video_id, 'maxResults': min(max_results,100), 'key': self.api_key, 'order': 'relevance'}
        try:
            resp = requests.get(url, params=params, timeout=30)
            data = resp.json()
            if 'error' in data:
                return []
            for item in data.get('items', []):
                s = item['snippet']['topLevelComment']['snippet']
                comments.append({
                    'id': item['id'],
                    'text': s['textDisplay'],
                    'author': s['authorDisplayName'],
                    'likes': s['likeCount'],
                    'timestamp': s['publishedAt']
                })
            return comments
        except Exception as e:
            print(f"Comments error: {e}")
            return []
    
    def get_live_chat_id(self, video_id):
        url = f"{self.base_url}/videos"
        params = {'part': 'liveStreamingDetails', 'id': video_id, 'key': self.api_key}
        try:
            resp = requests.get(url, params=params, timeout=30)
            data = resp.json()
            if data.get('items'):
                details = data['items'][0].get('liveStreamingDetails', {})
                return details.get('activeLiveChatId')
            return None
        except Exception as e:
            print(f"Live chat ID error: {e}")
            return None

    def get_live_chat_messages(self, live_chat_id, page_token=None):
        url = f"{self.base_url}/liveChat/messages"
        params = {'part': 'snippet,authorDetails', 'liveChatId': live_chat_id, 'key': self.api_key}
        if page_token:
            params['pageToken'] = page_token
        try:
            resp = requests.get(url, params=params, timeout=30)
            data = resp.json()
            if 'error' in data:
                return [], None
            messages = []
            for item in data.get('items', []):
                messages.append({
                    'id': item['id'],
                    'text': item['snippet'].get('displayMessage', ''),
                    'author': item['authorDetails'].get('displayName', 'unknown'),
                    'author_id': item['authorDetails'].get('channelId', ''),
                    'timestamp': item['snippet'].get('publishedAt', '')
                })
            return messages, data.get('nextPageToken')
        except Exception as e:
            print(f"Live chat messages error: {e}")
            return [], None

    def is_live_stream(self, video_id):
        url = f"{self.base_url}/videos"
        params = {'part': 'liveStreamingDetails', 'id': video_id, 'key': self.api_key}
        try:
            resp = requests.get(url, params=params, timeout=30)
            data = resp.json()
            if data.get('items'):
                details = data['items'][0].get('liveStreamingDetails', {})
                return details.get('actualStartTime') is not None
            return False
        except Exception as e:
            print(f"Live check error: {e}")
            return False