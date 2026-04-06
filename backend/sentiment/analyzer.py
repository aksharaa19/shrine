import os
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

class SentimentAnalyzer:
    def __init__(self):
        self.vader = SentimentIntensityAnalyzer()
        print("Using VADER sentiment analyzer (local, no API required, no rate limits)")
    
    def analyze(self, text):
        if not text or len(text.strip()) == 0:
            return self._get_empty_result()
        
        scores = self.vader.polarity_scores(text)
        compound = scores['compound']
        neg = scores['neg']
        
        if compound > -0.1 and neg < 0.2:
            toxicity_level = 'safe'
            reason = 'Positive or neutral sentiment detected'
        elif compound > -0.5 and neg < 0.5:
            toxicity_level = 'moderate'
            reason = 'Negative sentiment detected' if neg > 0.3 else 'Slightly negative tone'
        else:
            toxicity_level = 'toxic'
            reason = 'Strongly negative or hostile tone detected'
        
        return {
            'toxic_score': neg,
            'toxicity_level': toxicity_level,
            'reason': reason,
            'is_toxic': toxicity_level in ['moderate', 'toxic']
        }
    
    def _get_empty_result(self):
        return {
            'toxic_score': 0.0,
            'toxicity_level': 'safe',
            'reason': 'Empty comment',
            'is_toxic': False
        }
    
    def analyze_batch(self, comments):
        analyzed_comments = []
        for i, comment in enumerate(comments):
            text = comment.get('text', '')
            toxicity = self.analyze(text)
            if i < 5:
                print(f"Comment {i+1}: {text[:50]}... Score: {toxicity['toxic_score']:.3f}")
            analyzed_comments.append({**comment, 'toxicity': toxicity})
        return analyzed_comments
    
    def get_summary_stats(self, analyzed_comments):
        if not analyzed_comments:
            return {
                'total_comments': 0,
                'toxic_count': 0,
                'moderate_count': 0,
                'safe_count': 0,
                'avg_toxicity': 0.0,
                'toxic_percentage': 0.0
            }
        
        toxic_count = sum(1 for c in analyzed_comments if c['toxicity']['toxicity_level'] == 'toxic')
        moderate_count = sum(1 for c in analyzed_comments if c['toxicity']['toxicity_level'] == 'moderate')
        safe_count = sum(1 for c in analyzed_comments if c['toxicity']['toxicity_level'] == 'safe')
        avg_toxicity = sum(c['toxicity']['toxic_score'] for c in analyzed_comments) / len(analyzed_comments)
        
        return {
            'total_comments': len(analyzed_comments),
            'toxic_count': toxic_count,
            'moderate_count': moderate_count,
            'safe_count': safe_count,
            'avg_toxicity': round(avg_toxicity, 3),
            'toxic_percentage': round((toxic_count / len(analyzed_comments)) * 100, 1)
        }