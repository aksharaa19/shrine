import json
import csv
from datetime import datetime
import io

class ReportGenerator:
    def generate_containment_report(self, video_id, video_title, sliding_window, attack_detector, alert_engine, comments_analyzed=None):
        timestamp = datetime.now().isoformat()
        
        # Safely get alert summary
        try:
            alert_summary = alert_engine.get_alert_summary()
        except:
            alert_summary = {'total_alerts': 0, 'high_severity_count': 0, 'medium_severity_count': 0, 'low_severity_count': 0}
        
        # Safely get attack summary
        try:
            attack_summary = attack_detector.get_summary() if attack_detector else {}
        except Exception as e:
            print(f"Error getting attack summary: {e}")
            attack_summary = {'total_messages_analyzed': 0, 'recent_attacks': []}
        
        # Get timeline and stats
        try:
            timeline = sliding_window.get_trend_data()
        except:
            timeline = []
        
        try:
            current = sliding_window.get_window_average(30)
        except:
            current = 0.0
        
        try:
            peak = self._get_peak(sliding_window)
        except:
            peak = 0.0
        
        try:
            comments_with_scores = self._get_comments(sliding_window)
        except:
            comments_with_scores = []
        
        try:
            duration = self._get_duration(sliding_window)
        except:
            duration = 0
        
        try:
            avg_toxicity = self._get_avg(sliding_window)
        except:
            avg_toxicity = 0.0
        
        try:
            peak_attack = self._get_peak_attack(attack_summary)
        except:
            peak_attack = 0.0
        
        return {
            'report_id': datetime.now().strftime('%Y%m%d_%H%M%S'),
            'generated_at': timestamp,
            'video_id': video_id,
            'video_title': video_title,
            'duration_minutes': duration,
            'comments_analyzed': comments_analyzed or len(sliding_window.sentiment_history),
            'toxicity_summary': {
                'current_toxicity': round(current * 100, 1),
                'peak_toxicity': round(peak * 100, 1),
                'average_toxicity': avg_toxicity
            },
            'alert_summary': alert_summary,
            'attack_summary': {
                'attacks_detected': attack_summary.get('total_messages_analyzed', 0) > 0,
                'attack_count': len(attack_summary.get('recent_attacks', [])),
                'peak_attack_score': peak_attack
            },
            'toxicity_timeline': timeline,
            'comments_with_scores': comments_with_scores
        }
    
    def _get_comments(self, sw):
        try:
            history = list(sw.sentiment_history)
            return [{
                'timestamp': h['timestamp'].isoformat(), 
                'toxicity_score': round(h['toxicity_score'] * 100, 1), 
                'comment': h['comment'], 
                'author': h['author']
            } for h in history[-100:]]
        except:
            return []
    
    def _get_peak(self, sw):
        try:
            hist = list(sw.sentiment_history)
            return max((h['toxicity_score'] for h in hist), default=0.0)
        except:
            return 0.0
    
    def _get_avg(self, sw):
        try:
            hist = list(sw.sentiment_history)
            if not hist:
                return 0.0
            return round((sum(h['toxicity_score'] for h in hist) / len(hist)) * 100, 1)
        except:
            return 0.0
    
    def _get_peak_attack(self, summ):
        try:
            attacks = summ.get('recent_attacks', [])
            if not attacks:
                return 0.0
            return round(max(a.get('attack_score', 0) for a in attacks) * 100, 1)
        except:
            return 0.0
    
    def _get_duration(self, sw):
        try:
            hist = list(sw.sentiment_history)
            if len(hist) < 2:
                return 0
            return round((hist[-1]['timestamp'] - hist[0]['timestamp']).total_seconds() / 60, 1)
        except:
            return 0
    
    def export_to_json(self, report, filepath=None):
        if filepath:
            with open(filepath, 'w') as f:
                json.dump(report, f, indent=2, default=str)
            return filepath
        return json.dumps(report, indent=2, default=str)
    
    def export_to_csv(self, report, filepath=None):
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(['Timestamp', 'Author', 'Toxicity Score (%)', 'Comment'])
        for c in report.get('comments_with_scores', []):
            writer.writerow([c['timestamp'], c['author'], c['toxicity_score'], c['comment']])
        if filepath:
            with open(filepath, 'w', newline='') as f:
                f.write(output.getvalue())
            return filepath
        return output.getvalue()