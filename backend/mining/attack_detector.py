from collections import deque, Counter
from datetime import datetime, timedelta
import re
import hashlib

class CoordinatedAttackDetector:
    def __init__(self, window_size=60, duplicate_threshold=0.3, frequency_threshold=50):
        self.window_size = window_size
        self.duplicate_threshold = duplicate_threshold
        self.frequency_threshold = frequency_threshold
        self.message_history = deque(maxlen=500)
        self.attack_history = deque(maxlen=10)
        self.duplicate_cache = {}
        
    def add_message(self, message_text, author, timestamp=None):
        if timestamp is None:
            timestamp = datetime.now()
        
        message_hash = self._get_message_hash(message_text)
        message_data = {
            'text': message_text,
            'author': author,
            'timestamp': timestamp,
            'hash': message_hash,
            'normalized': self._normalize_text(message_text)
        }
        
        self.message_history.append(message_data)
        self._update_duplicate_cache(message_hash, timestamp)
        
    def _normalize_text(self, text):
        text = text.lower()
        text = re.sub(r'[^\w\s]', '', text)
        text = re.sub(r'\s+', ' ', text).strip()
        return text
    
    def _get_message_hash(self, text):
        normalized = self._normalize_text(text)
        return hashlib.md5(normalized.encode()).hexdigest()[:16]
    
    def _update_duplicate_cache(self, message_hash, timestamp):
        cutoff = timestamp - timedelta(seconds=self.window_size)
        self.duplicate_cache[message_hash] = [ts for ts in self.duplicate_cache.get(message_hash, []) if ts > cutoff]
        self.duplicate_cache[message_hash].append(timestamp)
    
    def get_recent_messages(self, seconds=60):
        cutoff = datetime.now() - timedelta(seconds=seconds)
        return [m for m in self.message_history if m['timestamp'] > cutoff]
    
    def get_message_frequency(self, seconds=60):
        recent = self.get_recent_messages(seconds)
        if not recent:
            return 0.0
        return len(recent) / seconds
    
    def get_duplicate_ratio(self, seconds=60):
        recent = self.get_recent_messages(seconds)
        if len(recent) < 5:
            return 0.0
        hash_counts = Counter([m['hash'] for m in recent])
        duplicate_count = sum(count - 1 for count in hash_counts.values() if count > 1)
        return duplicate_count / len(recent)
    
    def get_top_duplicates(self, seconds=60, top_n=5):
        recent = self.get_recent_messages(seconds)
        if not recent:
            return []
        hash_counts = Counter([m['hash'] for m in recent])
        duplicate_hashes = [h for h, count in hash_counts.items() if count > 1]
        
        results = []
        for h in duplicate_hashes[:top_n]:
            sample = next((m for m in recent if m['hash'] == h), None)
            if sample:
                results.append({'text': sample['text'], 'count': hash_counts[h], 'hash': h})
        return sorted(results, key=lambda x: x['count'], reverse=True)
    
    def get_author_concentration(self, seconds=60):
        recent = self.get_recent_messages(seconds)
        if len(recent) < 10:
            return 0.0
        author_counts = Counter([m['author'] for m in recent])
        top_author_count = max(author_counts.values()) if author_counts else 0
        return top_author_count / len(recent)
    
    def get_attack_score(self):
        frequency = self.get_message_frequency(30)
        duplicate_ratio = self.get_duplicate_ratio(30)
        author_concentration = self.get_author_concentration(30)
        
        score = 0.0
        if frequency > self.frequency_threshold:
            score += min(0.4, (frequency - self.frequency_threshold) / 100)
        if duplicate_ratio > self.duplicate_threshold:
            score += min(0.4, (duplicate_ratio - self.duplicate_threshold) * 2)
        if author_concentration > 0.5:
            score += min(0.3, (author_concentration - 0.5) * 1.5)
        return min(1.0, score)
    
    def detect_attack(self):
        attack_score = self.get_attack_score()
        frequency = self.get_message_frequency(30)
        duplicate_ratio = self.get_duplicate_ratio(30)
        top_duplicates = self.get_top_duplicates(30, 3)
        
        is_attack = False
        attack_type = None
        attack_severity = 'none'
        
        if attack_score > 0.6:
            is_attack = True
            attack_severity = 'critical'
            if duplicate_ratio > 0.4:
                attack_type = 'duplicate_flooding'
            elif frequency > self.frequency_threshold * 2:
                attack_type = 'message_storm'
            else:
                attack_type = 'coordinated_attack'
        elif attack_score > 0.3:
            is_attack = True
            attack_severity = 'warning'
            if duplicate_ratio > 0.25:
                attack_type = 'suspected_duplicate_flooding'
            elif frequency > self.frequency_threshold:
                attack_type = 'high_activity'
            else:
                attack_type = 'suspicious_activity'
        
        alert_message = self._generate_alert_message(attack_type, attack_score)
        
        if is_attack:
            self.attack_history.append({
                'timestamp': datetime.now().isoformat(),
                'attack_score': attack_score,
                'attack_type': attack_type,
                'severity': attack_severity,
                'top_duplicates': top_duplicates[:2]
            })
        
        return {
            'is_attack': is_attack,
            'attack_score': round(attack_score, 3),
            'attack_type': attack_type,
            'attack_severity': attack_severity,
            'alert_message': alert_message,
            'metrics': {
                'frequency_30s': round(frequency, 1),
                'duplicate_ratio': round(duplicate_ratio, 3),
                'author_concentration': round(self.get_author_concentration(30), 3)
            },
            'top_duplicates': top_duplicates
        }
    
    def _generate_alert_message(self, attack_type, attack_score):
        if attack_type == 'duplicate_flooding':
            return f'Duplicate message flooding detected. Attack score: {attack_score:.0%}'
        elif attack_type == 'message_storm':
            return f'Message storm detected. Potential hate raid. Attack score: {attack_score:.0%}'
        elif attack_type == 'coordinated_attack':
            return f'Coordinated attack detected. Attack score: {attack_score:.0%}'
        elif attack_type == 'suspected_duplicate_flooding':
            return 'Suspected duplicate flooding. Monitor closely.'
        elif attack_type == 'high_activity':
            return 'High message activity detected. Possible coordinated effort.'
        elif attack_type == 'suspicious_activity':
            return 'Suspicious chat activity detected.'
        else:
            return 'No coordinated attack detected.'
    
    def get_summary(self):
        return {
            'total_messages_analyzed': len(self.message_history),
            'recent_attacks': list(self.attack_history)[-5:],
            'current_attack_score': self.get_attack_score(),
            'is_attacked': self.detect_attack()['is_attack']
        }
    
    def reset(self):
        self.message_history.clear()
        self.attack_history.clear()
        self.duplicate_cache.clear()