from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

class SentimentAnalyzer:
    def __init__(self):
        self.vader = SentimentIntensityAnalyzer()
        print("VADER sentiment analyzer ready")
    
    def analyze(self, text):
        if not text or not text.strip():
            return {'toxic_score': 0.0, 'toxicity_level': 'safe', 'reason': 'Empty comment', 'is_toxic': False}
        scores = self.vader.polarity_scores(text)
        compound = scores['compound']
        neg = scores['neg']
        if compound > -0.1 and neg < 0.2:
            toxicity_level = 'safe'
            reason = 'Positive or neutral sentiment'
        elif compound > -0.5 and neg < 0.5:
            toxicity_level = 'moderate'
            reason = 'Negative sentiment detected' if neg > 0.3 else 'Slightly negative tone'
        else:
            toxicity_level = 'toxic'
            reason = 'Strongly negative or hostile tone'
        return {
            'toxic_score': neg,
            'toxicity_level': toxicity_level,
            'reason': reason,
            'is_toxic': toxicity_level in ['moderate', 'toxic']
        }
    
    def analyze_batch(self, comments):
        analyzed = []
        for i, c in enumerate(comments):
            text = c.get('text', '')
            tox = self.analyze(text)
            analyzed.append({**c, 'toxicity': tox})
            if i < 3:
                print(f"Comment {i}: {text[:50]}... score {tox['toxic_score']}")
        return analyzed
    
    def get_summary_stats(self, analyzed):
        if not analyzed:
            return {'total_comments':0, 'toxic_count':0, 'moderate_count':0, 'safe_count':0, 'avg_toxicity':0, 'toxic_percentage':0}
        toxic = sum(1 for c in analyzed if c['toxicity']['toxicity_level'] == 'toxic')
        moderate = sum(1 for c in analyzed if c['toxicity']['toxicity_level'] == 'moderate')
        safe = sum(1 for c in analyzed if c['toxicity']['toxicity_level'] == 'safe')
        avg = sum(c['toxicity']['toxic_score'] for c in analyzed) / len(analyzed)
        return {
            'total_comments': len(analyzed),
            'toxic_count': toxic,
            'moderate_count': moderate,
            'safe_count': safe,
            'avg_toxicity': round(avg, 3),
            'toxic_percentage': round((toxic / len(analyzed)) * 100, 1)
        }