class ChartDataGenerator:
    def __init__(self):
        pass
    
    def generate_toxicity_timeline(self, sliding_window):
        trend_data = sliding_window.get_trend_data()
        
        if not trend_data or len(trend_data) == 0:
            return {
                'labels': ['No Data'],
                'datasets': [{
                    'label': 'Toxicity Score (%)',
                    'data': [0],
                    'borderColor': '#e94560',
                    'backgroundColor': 'rgba(233, 69, 96, 0.1)',
                    'fill': True,
                    'tension': 0.4
                }]
            }
        
        labels = []
        values = []
        for point in trend_data[-30:]:
            try:
                if 'timestamp' in point:
                    time_str = point['timestamp']
                    if 'T' in time_str:
                        time_str = time_str.split('T')[1][:5]
                    labels.append(time_str)
                else:
                    labels.append('Unknown')
                values.append(round(point['toxicity_score'] * 100, 1))
            except Exception:
                labels.append('Unknown')
                values.append(0)
        
        if len(labels) == 0:
            labels = ['No Data']
            values = [0]
        
        return {
            'labels': labels,
            'datasets': [{
                'label': 'Toxicity Score (%)',
                'data': values,
                'borderColor': '#e94560',
                'backgroundColor': 'rgba(233, 69, 96, 0.1)',
                'fill': True,
                'tension': 0.4
            }]
        }
    
    def generate_attack_timeline(self, attack_detector):
        attacks = list(attack_detector.attack_history)
        
        if not attacks or len(attacks) == 0:
            return {
                'labels': ['No Attacks'],
                'datasets': [{
                    'label': 'Attack Score (%)',
                    'data': [0],
                    'borderColor': '#ff9800',
                    'backgroundColor': 'rgba(255, 152, 0, 0.1)',
                    'fill': True,
                    'tension': 0.3
                }]
            }
        
        labels = []
        scores = []
        
        for a in attacks[-30:]:
            try:
                if 'timestamp' in a:
                    time_str = a['timestamp']
                    if 'T' in time_str:
                        time_str = time_str.split('T')[1][:5]
                    labels.append(time_str)
                else:
                    labels.append('Unknown')
                scores.append(round(a.get('attack_score', 0) * 100, 1))
            except Exception:
                labels.append('Unknown')
                scores.append(0)
        
        if len(labels) == 0:
            labels = ['No Data']
            scores = [0]
        
        return {
            'labels': labels,
            'datasets': [{
                'label': 'Attack Score (%)',
                'data': scores,
                'borderColor': '#ff9800',
                'backgroundColor': 'rgba(255, 152, 0, 0.1)',
                'fill': True,
                'tension': 0.3
            }]
        }
    
    def generate_velocity_chart(self, sliding_window):
        velocity_30 = sliding_window.get_window_velocity(30) * 100
        velocity_60 = sliding_window.get_window_velocity(60) * 100
        acceleration = sliding_window.get_acceleration() * 100
        
        v30 = max(0, round(velocity_30, 1))
        v60 = max(0, round(velocity_60, 1))
        acc = max(0, round(acceleration, 1))
        
        if v30 == 0 and v60 == 0 and acc == 0:
            v30 = 0.1
        
        return {
            'labels': ['Velocity (30s)', 'Velocity (60s)', 'Acceleration'],
            'datasets': [{
                'label': 'Rate of Change (%)',
                'data': [v30, v60, acc],
                'backgroundColor': ['#ffd600', '#ff9800', '#e94560'],
                'borderRadius': 8
            }]
        }
    
    def generate_gauge_data(self, current_toxicity):
        value = round(current_toxicity * 100, 1)
        return {
            'value': value,
            'remaining': 100 - value,
            'color': '#e94560'
        }