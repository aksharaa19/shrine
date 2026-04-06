import os
import requests
from typing import Dict, Any

class InferenceAPIClient:
    def __init__(self):
        self.api_token = os.getenv('HUGGINGFACE_API_KEY')
        self.api_url = "https://api-inference.huggingface.co/models/unitary/toxic-bert"
        self.headers = {"Authorization": f"Bearer {self.api_token}"}
    
    def analyze(self, text: str) -> Dict[str, Any]:
        """Send text to Hugging Face Inference API for toxicity analysis"""
        if not text or len(text.strip()) == 0:
            return self._get_empty_result()
        
        # Truncate long texts (API has limits)
        if len(text) > 500:
            text = text[:500]
        
        payload = {"inputs": text}
        
        try:
            response = requests.post(self.api_url, headers=self.headers, json=payload, timeout=30)
            
            if response.status_code == 200:
                return self._parse_response(response.json())
            elif response.status_code == 503:
                # Model is loading on Hugging Face servers
                return self._get_loading_result()
            else:
                print(f"API Error: {response.status_code}")
                return self._get_fallback_result(text)
                
        except Exception as e:
            print(f"API request failed: {e}")
            return self._get_fallback_result(text)
    
    def _parse_response(self, result):
        """Parse the API response into Shrine's expected format"""
        if isinstance(result, list) and len(result) > 0:
            scores = result[0]
        else:
            scores = result
        
        toxic_score = scores.get('toxic', 0.0)
        
        # Determine toxicity level
        if toxic_score < 0.2:
            toxicity_level = 'safe'
            reason = 'No significant toxic content detected'
        elif toxic_score < 0.4:
            toxicity_level = 'moderate'
            reason = 'Potentially toxic content detected'
        else:
            toxicity_level = 'toxic'
            reason = 'Toxic content detected'
        
        return {
            'toxic_score': toxic_score,
            'toxicity_level': toxicity_level,
            'reason': reason,
            'is_toxic': toxic_score >= 0.2,
            'severe_toxic': scores.get('severe_toxic', 0),
            'obscene': scores.get('obscene', 0),
            'threat': scores.get('threat', 0),
            'insult': scores.get('insult', 0),
            'identity_hate': scores.get('identity_hate', 0)
        }
    
    def _get_empty_result(self):
        return {
            'toxic_score': 0.0,
            'toxicity_level': 'safe',
            'reason': 'Empty comment',
            'is_toxic': False
        }
    
    def _get_loading_result(self):
        return {
            'toxic_score': 0.0,
            'toxicity_level': 'safe',
            'reason': 'Model is loading on Hugging Face servers. Try again.',
            'is_toxic': False
        }
    
    def _get_fallback_result(self, text):
        """Simple keyword-based fallback when API fails"""
        toxic_keywords = ['hate', 'stupid', 'idiot', 'terrible', 'awful', 'useless', 'trash']
        text_lower = text.lower()
        toxic_score = sum(1 for word in toxic_keywords if word in text_lower) / len(toxic_keywords)
        toxic_score = min(toxic_score, 0.8)
        
        if toxic_score < 0.1:
            toxicity_level = 'safe'
            reason = 'Fallback: No toxic keywords detected'
        elif toxic_score < 0.3:
            toxicity_level = 'moderate'
            reason = 'Fallback: Potential toxic keywords detected'
        else:
            toxicity_level = 'toxic'
            reason = 'Fallback: Toxic keywords detected'
        
        return {
            'toxic_score': toxic_score,
            'toxicity_level': toxicity_level,
            'reason': reason,
            'is_toxic': toxic_score >= 0.2
        }
    
    def analyze_batch(self, comments):
        """Analyze multiple comments"""
        analyzed_comments = []
        for comment in comments:
            text = comment.get('text', '')
            toxicity = self.analyze(text)
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