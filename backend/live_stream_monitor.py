import threading
import time
from datetime import datetime
from collections import deque

class LiveStreamMonitor:
    def __init__(self, video_id, live_chat_id, youtube_client, sentiment_analyzer, sliding_window):
        self.video_id = video_id
        self.live_chat_id = live_chat_id
        self.youtube_client = youtube_client
        self.sentiment_analyzer = sentiment_analyzer
        self.sliding_window = sliding_window
        self.active = True
        self.page_token = None
        self.comment_count = 0
        self.last_poll_time = None
        self.poll_interval = 5
        self.thread = None
        self.alerts = deque(maxlen=100)
        
    def start(self):
        self.active = True
        self.thread = threading.Thread(target=self._poll_loop)
        self.thread.daemon = True
        self.thread.start()
        return True
    
    def stop(self):
        self.active = False
        if self.thread:
            self.thread.join(timeout=2)
        return True
    
    def _poll_loop(self):
        while self.active:
            try:
                self._poll_messages()
                time.sleep(self.poll_interval)
            except Exception as e:
                print(f"Polling error: {e}")
                time.sleep(self.poll_interval)
    
    def _poll_messages(self):
        messages, next_token = self.youtube_client.get_live_chat_messages(
            self.live_chat_id, self.page_token
        )
        
        if messages:
            for message in messages:
                self._process_message(message)
            self.comment_count += len(messages)
            self.last_poll_time = datetime.now()
        
        if next_token:
            self.page_token = next_token
    
    def _process_message(self, message):
        text = message.get('text', '')
        if not text or len(text.strip()) == 0:
            return
        
        toxicity = self.sentiment_analyzer.analyze(text)
        comment_data = {
            'id': message['id'],
            'text': text,
            'author': message['author'],
            'likes': 0,
            'timestamp': message['timestamp']
        }
        
        self.sliding_window.add_comment(comment_data, toxicity['toxic_score'])
        alert = self.sliding_window.detect_acceleration_alert()
        if alert['alert_triggered']:
            self.alerts.append({
                'timestamp': datetime.now().isoformat(),
                'alert': alert,
                'comment': text[:100]
            })
    
    def get_status(self):
        return {
            'video_id': self.video_id,
            'active': self.active,
            'comment_count': self.comment_count,
            'last_poll': self.last_poll_time.isoformat() if self.last_poll_time else None,
            'current_toxicity': self.sliding_window.get_window_average(30),
            'velocity_30': self.sliding_window.get_window_velocity(30),
            'velocity_60': self.sliding_window.get_window_velocity(60),
            'acceleration': self.sliding_window.get_acceleration(),
            'alert': self.sliding_window.detect_acceleration_alert(),
            'recent_alerts': list(self.alerts)[-5:],
            'trend_data': self.sliding_window.get_trend_data()
        }