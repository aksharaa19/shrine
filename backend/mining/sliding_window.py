from collections import deque
from datetime import datetime
from mining.attack_detector import CoordinatedAttackDetector
from alerts.predictive_engine import PredictiveAlertEngine

class SlidingWindowAnalyzer:
    def __init__(self, window_sizes=[30, 60, 120]):
        self.window_sizes = window_sizes
        self.windows = {}
        self.sentiment_history = deque(maxlen=1000)
        self.acceleration_threshold = 0.15
        self.attack_detector = CoordinatedAttackDetector()
        self.alert_engine = PredictiveAlertEngine()
        
        for size in window_sizes:
            self.windows[size] = deque(maxlen=size * 10)
    
    def add_comment(self, comment, toxicity_score, timestamp=None):
        if timestamp is None:
            timestamp = datetime.now()
        
        data_point = {
            'timestamp': timestamp,
            'toxicity_score': toxicity_score,
            'comment': comment.get('text', '')[:100],
            'author': comment.get('author', 'unknown')
        }
        
        self.sentiment_history.append(data_point)
        for size, window in self.windows.items():
            window.append(data_point)
        
        self.attack_detector.add_message(
            comment.get('text', ''),
            comment.get('author', 'unknown'),
            timestamp
        )
    
    def get_window_average(self, window_size):
        if window_size not in self.windows:
            return 0.0
        window = self.windows[window_size]
        if len(window) == 0:
            return 0.0
        total_score = sum(item['toxicity_score'] for item in window)
        return total_score / len(window)
    
    def get_window_velocity(self, window_size):
        avg = self.get_window_average(window_size)
        if len(self.sentiment_history) < 20:
            return 0.0
        older_window = list(self.sentiment_history)[-20:]
        older_avg = sum(item['toxicity_score'] for item in older_window) / len(older_window)
        return avg - older_avg
    
    def get_acceleration(self):
        velocity_30 = self.get_window_velocity(30)
        velocity_60 = self.get_window_velocity(60)
        return velocity_30 - velocity_60
    
    def detect_acceleration_alert(self):
        acceleration = self.get_acceleration()
        velocity_30 = self.get_window_velocity(30)
        current_avg = self.get_window_average(30)
        
        alert_triggered = False
        alert_level = 'none'
        alert_message = ''
        
        if current_avg > 0.4 and acceleration > 0.1:
            alert_triggered = True
            alert_level = 'critical'
            alert_message = 'Toxicity acceleration detected. Comment section may escalate within 1-2 minutes.'
        elif current_avg > 0.3 and acceleration > 0.05:
            alert_triggered = True
            alert_level = 'warning'
            alert_message = 'Negative sentiment increasing rapidly. Monitor closely.'
        elif velocity_30 > 0.05 and acceleration > 0.02:
            alert_triggered = True
            alert_level = 'advisory'
            alert_message = 'Slight uptick in negative language detected.'
        
        return {
            'alert_triggered': alert_triggered,
            'alert_level': alert_level,
            'alert_message': alert_message,
            'acceleration': round(acceleration, 3),
            'velocity_30': round(velocity_30, 3),
            'velocity_60': round(self.get_window_velocity(60), 3),
            'current_toxicity': round(current_avg, 3)
        }
    
    def detect_coordinated_attack(self):
        return self.attack_detector.detect_attack()
    
    def get_prediction(self):
        attack_status = self.detect_coordinated_attack()
        return self.alert_engine.predict_escalation(self, attack_status)
    
    def generate_full_alert(self):
        attack_status = self.detect_coordinated_attack()
        toxicity_alert = self.detect_acceleration_alert()
        prediction = self.alert_engine.predict_escalation(self, attack_status)
        return self.alert_engine.generate_alert(prediction, attack_status, toxicity_alert)
    
    def get_alert_history(self):
        return self.alert_engine.get_alert_history()
    
    def get_alert_summary(self):
        return self.alert_engine.get_alert_summary()
    
    def get_trend_data(self):
        if len(self.sentiment_history) < 10:
            return []
        
        trend_data = []
        interval = max(1, len(self.sentiment_history) // 20)
        history_list = list(self.sentiment_history)
        
        for i in range(0, len(history_list), interval):
            batch = history_list[i:i+interval]
            avg_score = sum(item['toxicity_score'] for item in batch) / len(batch)
            trend_data.append({
                'timestamp': batch[-1]['timestamp'].isoformat(),
                'toxicity_score': round(avg_score, 3)
            })
        
        return trend_data
    
    def reset(self):
        self.sentiment_history.clear()
        for size in self.window_sizes:
            self.windows[size].clear()
        self.attack_detector.reset()