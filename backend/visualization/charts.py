class ChartDataGenerator:
    def generate_toxicity_timeline(self, sliding_window):
        trend = sliding_window.get_trend_data()
        if not trend:
            return {'labels': [], 'datasets': []}
        labels = [t['timestamp'][11:16] for t in trend[-30:]]
        values = [round(t['toxicity_score']*100,1) for t in trend[-30:]]
        return {
            'labels': labels,
            'datasets': [{
                'label': 'Toxicity (%)',
                'data': values,
                'borderColor': '#e94560',
                'fill': False
            }]
        }

    def generate_attack_timeline(self, attack_detector):
        attacks = list(attack_detector.attack_history)
        if not attacks:
            return {'labels': [], 'datasets': []}
        labels = [a['timestamp'][11:16] for a in attacks[-30:]]
        scores = [round(a['attack_score']*100,1) for a in attacks[-30:]]
        return {
            'labels': labels,
            'datasets': [{
                'label': 'Attack Score (%)',
                'data': scores,
                'borderColor': '#ff9800',
                'fill': False
            }]
        }

    def generate_velocity_chart(self, sliding_window):
        v30 = max(0, sliding_window.get_window_velocity(30)*100)
        v60 = max(0, sliding_window.get_window_velocity(60)*100)
        acc = max(0, sliding_window.get_acceleration()*100)
        return {
            'labels': ['Velocity 30s', 'Velocity 60s', 'Acceleration'],
            'datasets': [{
                'label': 'Rate of Change (%)',
                'data': [v30, v60, acc],
                'backgroundColor': ['#ffd600', '#ff9800', '#e94560']
            }]
        }

    def generate_gauge_data(self, current_toxicity):
        value = round(current_toxicity*100,1)
        return {'value': value, 'remaining': 100-value}