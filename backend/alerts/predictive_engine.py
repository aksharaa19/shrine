from datetime import datetime
from collections import deque

class PredictiveAlertEngine:
    def __init__(self):
        self.alert_history = deque(maxlen=100)
        self.confidence_threshold = 0.6
        
    def predict_escalation(self, sliding_window_analyzer, attack_detection_dict):
        current_toxicity = sliding_window_analyzer.get_window_average(30)
        velocity_30 = sliding_window_analyzer.get_window_velocity(30)
        acceleration = sliding_window_analyzer.get_acceleration()
        
        attack_score = 0
        if attack_detection_dict and isinstance(attack_detection_dict, dict):
            attack_score = attack_detection_dict.get('attack_score', 0)
        
        prediction_score = 0.0
        time_to_escalation = None
        confidence = 0.0
        
        if current_toxicity > 0.3 and acceleration > 0.05:
            prediction_score += 0.4
            time_to_escalation = 90
        elif current_toxicity > 0.2 and acceleration > 0.03:
            prediction_score += 0.2
            time_to_escalation = 120
        
        if velocity_30 > 0.1:
            prediction_score += 0.3
            if time_to_escalation:
                time_to_escalation = max(30, time_to_escalation - 30)
        
        if attack_score > 0.5:
            prediction_score += 0.3
            if time_to_escalation:
                time_to_escalation = max(15, time_to_escalation - 45)
        
        prediction_score = min(1.0, prediction_score)
        
        if prediction_score > 0.3:
            confidence = min(0.9, 0.5 + (prediction_score * 0.4))
        
        is_escalation_predicted = prediction_score > self.confidence_threshold
        
        return {
            'is_escalation_predicted': is_escalation_predicted,
            'prediction_score': round(prediction_score, 3),
            'confidence': round(confidence, 3),
            'time_to_escalation_seconds': time_to_escalation,
            'time_to_escalation_text': self._format_time(time_to_escalation),
            'factors': {
                'current_toxicity': round(current_toxicity, 3),
                'velocity_30': round(velocity_30, 3),
                'acceleration': round(acceleration, 3),
                'attack_score': round(attack_score, 3)
            }
        }
    
    def _format_time(self, seconds):
        if not seconds:
            return 'Unknown'
        if seconds < 60:
            return f'{seconds} seconds'
        minutes = seconds // 60
        remaining = seconds % 60
        if remaining == 0:
            return f'{minutes} minute(s)'
        return f'{minutes} minute(s) {remaining} second(s)'
    
    def generate_alert(self, prediction, attack_detection_dict, toxicity_alert):
        alert_id = datetime.now().strftime('%Y%m%d%H%M%S%f')
        timestamp = datetime.now().isoformat()
        
        severity = 'low'
        if prediction['is_escalation_predicted']:
            severity = 'high'
        elif toxicity_alert.get('alert_triggered', False):
            severity = 'medium'
        
        alert = {
            'id': alert_id,
            'timestamp': timestamp,
            'severity': severity,
            'prediction': prediction,
            'toxicity_alert': toxicity_alert,
            'attack_detected': attack_detection_dict.get('is_attack', False) if attack_detection_dict else False,
            'recommendations': self.get_recommendations(prediction, toxicity_alert, attack_detection_dict)
        }
        
        self.alert_history.append(alert)
        return alert
    
    def get_recommendations(self, prediction, toxicity_alert, attack_detection_dict):
        recommendations = []
        
        if prediction['is_escalation_predicted']:
            recommendations.append({
                'priority': 'critical',
                'action': 'Enable comment moderation filters',
                'description': 'Activate YouTube built-in moderation tools to hold potentially toxic comments.',
                'timeframe': 'immediate'
            })
            recommendations.append({
                'priority': 'critical',
                'action': 'Pin a clarifying comment',
                'description': 'Post a pinned comment addressing the controversy.',
                'timeframe': 'within 1 minute'
            })
        
        if toxicity_alert.get('alert_triggered', False):
            if toxicity_alert.get('alert_level') == 'critical':
                recommendations.append({
                    'priority': 'high',
                    'action': 'Prepare holding statement',
                    'description': 'Draft a response acknowledging viewer concerns.',
                    'timeframe': 'immediate'
                })
            recommendations.append({
                'priority': 'medium',
                'action': 'Increase moderation staff',
                'description': 'Assign additional team members to monitor comments.',
                'timeframe': 'within 5 minutes'
            })
        
        if attack_detection_dict and attack_detection_dict.get('is_attack', False):
            recommendations.append({
                'priority': 'high',
                'action': 'Enable comment hold',
                'description': 'Temporarily hold all comments for review.',
                'timeframe': 'immediate'
            })
            recommendations.append({
                'priority': 'high',
                'action': 'Report coordinated attack to YouTube',
                'description': 'Use YouTube harassment reporting tools.',
                'timeframe': 'within 2 minutes'
            })
        
        if len(recommendations) == 0:
            recommendations.append({
                'priority': 'low',
                'action': 'Continue monitoring',
                'description': 'No immediate action required.',
                'timeframe': 'ongoing'
            })
        
        return recommendations
    
    def get_alert_history(self, limit=20):
        return list(self.alert_history)[-limit:]
    
    def get_alert_summary(self):
        if not self.alert_history:
            return {
                'total_alerts': 0,
                'high_severity_count': 0,
                'medium_severity_count': 0,
                'low_severity_count': 0,
                'last_alert': None
            }
        
        high_count = sum(1 for a in self.alert_history if a.get('severity') == 'high')
        medium_count = sum(1 for a in self.alert_history if a.get('severity') == 'medium')
        low_count = sum(1 for a in self.alert_history if a.get('severity') == 'low')
        
        return {
            'total_alerts': len(self.alert_history),
            'high_severity_count': high_count,
            'medium_severity_count': medium_count,
            'low_severity_count': low_count,
            'last_alert': self.alert_history[-1].get('timestamp') if self.alert_history else None
        }