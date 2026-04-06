import json
import csv
from datetime import datetime
import io

class ReportGenerator:
    def __init__(self):
        pass
    
    def generate_containment_report(self, video_id, video_title, sliding_window, attack_detector, alert_engine, comments_analyzed=None):
        timestamp = datetime.now().isoformat()
        
        alert_summary_raw = alert_engine.get_alert_summary()
        alert_summary = {
            'total_alerts': alert_summary_raw.get('total_alerts', 0),
            'high_severity_count': alert_summary_raw.get('high_severity_count', 0),
            'medium_severity_count': alert_summary_raw.get('medium_severity_count', 0),
            'low_severity_count': alert_summary_raw.get('low_severity_count', 0),
            'last_alert': alert_summary_raw.get('last_alert')
        }
        
        attack_summary = attack_detector.get_summary() if attack_detector else {}
        toxicity_timeline = sliding_window.get_trend_data()
        current_toxicity = sliding_window.get_window_average(30)
        peak_toxicity = self._get_peak_toxicity(sliding_window)
        comments_with_scores = self._get_comments_with_scores(sliding_window)
        
        report = {
            'report_id': datetime.now().strftime('%Y%m%d_%H%M%S'),
            'generated_at': timestamp,
            'video_id': video_id,
            'video_title': video_title,
            'duration_minutes': self._get_duration_minutes(sliding_window),
            'comments_analyzed': comments_analyzed or len(sliding_window.sentiment_history),
            'toxicity_summary': {
                'current_toxicity': round(current_toxicity * 100, 1),
                'peak_toxicity': round(peak_toxicity * 100, 1),
                'average_toxicity': self._get_average_toxicity(sliding_window)
            },
            'alert_summary': alert_summary,
            'attack_summary': {
                'attacks_detected': attack_summary.get('total_messages_analyzed', 0) > 0,
                'attack_count': len(attack_summary.get('recent_attacks', [])),
                'peak_attack_score': self._get_peak_attack_score(attack_summary)
            },
            'toxicity_timeline': toxicity_timeline,
            'comments_with_scores': comments_with_scores
        }
        
        return report
    
    def _get_comments_with_scores(self, sliding_window):
        history = list(sliding_window.sentiment_history)
        comments = []
        for item in history[-100:]:
            comments.append({
                'timestamp': item['timestamp'].isoformat() if hasattr(item['timestamp'], 'isoformat') else str(item['timestamp']),
                'toxicity_score': round(item['toxicity_score'] * 100, 1),
                'comment': item['comment'],
                'author': item['author']
            })
        return comments
    
    def _get_peak_toxicity(self, sliding_window):
        history = list(sliding_window.sentiment_history)
        if not history:
            return 0.0
        return max(item['toxicity_score'] for item in history)
    
    def _get_average_toxicity(self, sliding_window):
        history = list(sliding_window.sentiment_history)
        if not history:
            return 0.0
        avg = sum(item['toxicity_score'] for item in history) / len(history)
        return round(avg * 100, 1)
    
    def _get_peak_attack_score(self, attack_summary):
        attacks = attack_summary.get('recent_attacks', [])
        if not attacks:
            return 0.0
        peak = max(a.get('attack_score', 0) for a in attacks)
        return round(peak * 100, 1)
    
    def _get_duration_minutes(self, sliding_window):
        history = list(sliding_window.sentiment_history)
        if len(history) < 2:
            return 0
        start = history[0]['timestamp']
        end = history[-1]['timestamp']
        return round((end - start).total_seconds() / 60, 1)
    
    def export_to_json(self, report, filepath=None):
        if filepath:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(report, f, indent=2, default=str, ensure_ascii=False)
            return filepath
        return json.dumps(report, indent=2, default=str, ensure_ascii=False)
    
    def export_to_csv(self, report, filepath=None):
        comments = report.get('comments_with_scores', [])
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(['Timestamp', 'Author', 'Toxicity Score (%)', 'Comment'])
        for comment in comments:
            writer.writerow([comment['timestamp'], comment['author'], comment['toxicity_score'], comment['comment']])
        
        if filepath:
            with open(filepath, 'w', newline='', encoding='utf-8') as f:
                f.write(output.getvalue())
            return filepath
        return output.getvalue()