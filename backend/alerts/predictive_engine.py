from datetime import datetime
from collections import deque

class PredictiveAlertEngine:
    def __init__(self):
        self.alert_history = deque(maxlen=100)
        self.confidence_threshold = 0.6
    
    def predict_escalation(self, sliding_window, attack_dict):
        cur = sliding_window.get_window_average(30)
        vel = sliding_window.get_window_velocity(30)
        acc = sliding_window.get_acceleration()
        attack_score = attack_dict.get('attack_score', 0) if attack_dict else 0
        score = 0.0
        time_to = None
        if cur > 0.3 and acc > 0.05:
            score += 0.4
            time_to = 90
        elif cur > 0.2 and acc > 0.03:
            score += 0.2
            time_to = 120
        if vel > 0.1:
            score += 0.3
            if time_to:
                time_to = max(30, time_to-30)
        if attack_score > 0.5:
            score += 0.3
            if time_to:
                time_to = max(15, time_to-45)
        score = min(1.0, score)
        confidence = min(0.9, 0.5 + score*0.4) if score > 0.3 else 0.0
        return {
            'is_escalation_predicted': score > self.confidence_threshold,
            'prediction_score': round(score,3),
            'confidence': round(confidence,3),
            'time_to_escalation_seconds': time_to,
            'time_to_escalation_text': self._format_time(time_to),
            'factors': {'current_toxicity': round(cur,3), 'velocity_30': round(vel,3), 'acceleration': round(acc,3), 'attack_score': round(attack_score,3)}
        }
    
    def _format_time(self, sec):
        if not sec:
            return 'Unknown'
        if sec < 60:
            return f'{sec} seconds'
        m = sec // 60
        s = sec % 60
        return f'{m} minute(s) {s} second(s)' if s else f'{m} minute(s)'
    
    def generate_alert(self, prediction, attack_dict, tox_alert):
        alert_id = datetime.now().strftime('%Y%m%d%H%M%S%f')
        severity = 'high' if prediction['is_escalation_predicted'] else ('medium' if tox_alert.get('alert_triggered', False) else 'low')
        alert = {
            'id': alert_id,
            'timestamp': datetime.now().isoformat(),
            'severity': severity,
            'prediction': prediction,
            'toxicity_alert': tox_alert,
            'attack_detected': attack_dict.get('is_attack', False) if attack_dict else False,
            'recommendations': self.get_recommendations(prediction, tox_alert, attack_dict)
        }
        self.alert_history.append(alert)
        return alert
    
    def get_recommendations(self, prediction, tox_alert, attack_dict):
        recs = []
        if prediction['is_escalation_predicted']:
            recs.append({'priority':'critical','action':'Enable comment moderation filters','description':'Activate YouTube moderation tools','timeframe':'immediate'})
            recs.append({'priority':'critical','action':'Pin a clarifying comment','description':'Post a pinned comment addressing the controversy','timeframe':'within 1 minute'})
        if tox_alert.get('alert_triggered', False):
            if tox_alert.get('alert_level') == 'critical':
                recs.append({'priority':'high','action':'Prepare holding statement','description':'Draft a response acknowledging concerns','timeframe':'immediate'})
            recs.append({'priority':'medium','action':'Increase moderation staff','description':'Assign more team members to monitor','timeframe':'within 5 minutes'})
        if attack_dict and attack_dict.get('is_attack', False):
            recs.append({'priority':'high','action':'Enable comment hold','description':'Temporarily hold all comments for review','timeframe':'immediate'})
            recs.append({'priority':'high','action':'Report coordinated attack to YouTube','description':'Use YouTube harassment reporting tools','timeframe':'within 2 minutes'})
        if not recs:
            recs.append({'priority':'low','action':'Continue monitoring','description':'No immediate action required','timeframe':'ongoing'})
        return recs
    
    def get_alert_history(self, limit=20):
        return list(self.alert_history)[-limit:]
    
    def get_alert_summary(self):
        if not self.alert_history:
            return {'total_alerts':0, 'high_severity_count':0, 'medium_severity_count':0, 'low_severity_count':0, 'last_alert':None}
        high = sum(1 for a in self.alert_history if a.get('severity')=='high')
        med = sum(1 for a in self.alert_history if a.get('severity')=='medium')
        low = sum(1 for a in self.alert_history if a.get('severity')=='low')
        return {'total_alerts':len(self.alert_history), 'high_severity_count':high, 'medium_severity_count':med, 'low_severity_count':low, 'last_alert':self.alert_history[-1].get('timestamp')}