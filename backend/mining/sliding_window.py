from collections import deque
from datetime import datetime
from mining.attack_detector import CoordinatedAttackDetector
from alerts.predictive_engine import PredictiveAlertEngine

class SlidingWindowAnalyzer:
    def __init__(self, window_sizes=[30, 60, 120]):
        self.window_sizes = window_sizes
        self.windows = {}
        self.sentiment_history = deque(maxlen=1000)
        self.attack_detector = CoordinatedAttackDetector()
        self.alert_engine = PredictiveAlertEngine()
        for size in window_sizes:
            self.windows[size] = deque(maxlen=size * 10)
    
    def add_comment(self, comment, toxicity_score, timestamp=None):
        if timestamp is None:
            timestamp = datetime.now()
        point = {'timestamp': timestamp, 'toxicity_score': toxicity_score, 'comment': comment.get('text','')[:100], 'author': comment.get('author','unknown')}
        self.sentiment_history.append(point)
        for size, win in self.windows.items():
            win.append(point)
        self.attack_detector.add_message(comment.get('text',''), comment.get('author','unknown'), timestamp)
    
    def get_window_average(self, window_size):
        if window_size not in self.windows:
            return 0.0
        win = self.windows[window_size]
        if not win:
            return 0.0
        return sum(p['toxicity_score'] for p in win) / len(win)
    
    def get_window_velocity(self, window_size):
        avg = self.get_window_average(window_size)
        if len(self.sentiment_history) < 20:
            return 0.0
        older = list(self.sentiment_history)[-20:]
        older_avg = sum(p['toxicity_score'] for p in older) / len(older)
        return avg - older_avg
    
    def get_acceleration(self):
        return self.get_window_velocity(30) - self.get_window_velocity(60)
    
    def detect_acceleration_alert(self):
        acc = self.get_acceleration()
        vel30 = self.get_window_velocity(30)
        cur = self.get_window_average(30)
        if cur > 0.4 and acc > 0.1:
            return {'alert_triggered': True, 'alert_level': 'critical', 'alert_message': 'Toxicity acceleration detected. Escalation within 1-2 minutes.', 'acceleration': round(acc,3), 'velocity_30': round(vel30,3), 'velocity_60': round(self.get_window_velocity(60),3), 'current_toxicity': round(cur,3)}
        elif cur > 0.3 and acc > 0.05:
            return {'alert_triggered': True, 'alert_level': 'warning', 'alert_message': 'Negative sentiment increasing rapidly. Monitor closely.', 'acceleration': round(acc,3), 'velocity_30': round(vel30,3), 'velocity_60': round(self.get_window_velocity(60),3), 'current_toxicity': round(cur,3)}
        elif vel30 > 0.05 and acc > 0.02:
            return {'alert_triggered': True, 'alert_level': 'advisory', 'alert_message': 'Slight uptick in negative language.', 'acceleration': round(acc,3), 'velocity_30': round(vel30,3), 'velocity_60': round(self.get_window_velocity(60),3), 'current_toxicity': round(cur,3)}
        return {'alert_triggered': False, 'alert_level': 'none', 'alert_message': '', 'acceleration': round(acc,3), 'velocity_30': round(vel30,3), 'velocity_60': round(self.get_window_velocity(60),3), 'current_toxicity': round(cur,3)}
    
    def detect_coordinated_attack(self):
        return self.attack_detector.detect_attack()
    
    def generate_full_alert(self):
        attack = self.detect_coordinated_attack()
        tox_alert = self.detect_acceleration_alert()
        pred = self.alert_engine.predict_escalation(self, attack)
        return self.alert_engine.generate_alert(pred, attack, tox_alert)
    
    def get_trend_data(self):
        if len(self.sentiment_history) < 10:
            return []
        trend = []
        step = max(1, len(self.sentiment_history)//20)
        for i in range(0, len(self.sentiment_history), step):
            batch = list(self.sentiment_history)[i:i+step]
            avg = sum(p['toxicity_score'] for p in batch)/len(batch)
            trend.append({'timestamp': batch[-1]['timestamp'].isoformat(), 'toxicity_score': round(avg,3)})
        return trend