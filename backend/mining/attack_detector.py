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
    
    def add_message(self, text, author, timestamp=None):
        if timestamp is None:
            timestamp = datetime.now()
        h = self._get_hash(text)
        self.message_history.append({'text': text, 'author': author, 'timestamp': timestamp, 'hash': h})
        self._update_duplicate_cache(h, timestamp)
    
    def _normalize(self, text):
        return re.sub(r'[^\w\s]', '', text.lower()).strip()
    
    def _get_hash(self, text):
        return hashlib.md5(self._normalize(text).encode()).hexdigest()[:16]
    
    def _update_duplicate_cache(self, h, ts):
        cutoff = ts - timedelta(seconds=self.window_size)
        self.duplicate_cache[h] = [t for t in self.duplicate_cache.get(h, []) if t > cutoff]
        self.duplicate_cache[h].append(ts)
    
    def get_recent(self, seconds=60):
        cutoff = datetime.now() - timedelta(seconds=seconds)
        return [m for m in self.message_history if m['timestamp'] > cutoff]
    
    def get_frequency(self, seconds=60):
        recent = self.get_recent(seconds)
        return len(recent)/seconds if recent else 0.0
    
    def get_duplicate_ratio(self, seconds=60):
        recent = self.get_recent(seconds)
        if len(recent) < 5:
            return 0.0
        counts = Counter(m['hash'] for m in recent)
        dup = sum(c-1 for c in counts.values() if c>1)
        return dup/len(recent)
    
    def get_top_duplicates(self, seconds=60, top=3):
        recent = self.get_recent(seconds)
        if not recent:
            return []
        counts = Counter(m['hash'] for m in recent)
        dup_hashes = [h for h,c in counts.items() if c>1]
        results = []
        for h in dup_hashes[:top]:
            sample = next((m for m in recent if m['hash']==h), None)
            if sample:
                results.append({'text': sample['text'], 'count': counts[h], 'hash': h})
        return sorted(results, key=lambda x: x['count'], reverse=True)
    
    def get_author_concentration(self, seconds=60):
        recent = self.get_recent(seconds)
        if len(recent) < 10:
            return 0.0
        authors = Counter(m['author'] for m in recent)
        return max(authors.values())/len(recent)
    
    def get_attack_score(self):
        freq = self.get_frequency(30)
        dup = self.get_duplicate_ratio(30)
        conc = self.get_author_concentration(30)
        score = 0.0
        if freq > self.frequency_threshold:
            score += min(0.4, (freq - self.frequency_threshold)/100)
        if dup > self.duplicate_threshold:
            score += min(0.4, (dup - self.duplicate_threshold)*2)
        if conc > 0.5:
            score += min(0.3, (conc - 0.5)*1.5)
        return min(1.0, score)
    
    def detect_attack(self):
        score = self.get_attack_score()
        freq = self.get_frequency(30)
        dup = self.get_duplicate_ratio(30)
        top = self.get_top_duplicates(30,3)
        is_attack = False
        attack_type = None
        if score > 0.6:
            is_attack = True
            if dup > 0.4:
                attack_type = 'duplicate_flooding'
            elif freq > self.frequency_threshold*2:
                attack_type = 'message_storm'
            else:
                attack_type = 'coordinated_attack'
        elif score > 0.3:
            is_attack = True
            if dup > 0.25:
                attack_type = 'suspected_duplicate_flooding'
            elif freq > self.frequency_threshold:
                attack_type = 'high_activity'
            else:
                attack_type = 'suspicious_activity'
        if is_attack:
            self.attack_history.append({'timestamp': datetime.now().isoformat(), 'attack_score': score, 'attack_type': attack_type})
        return {
            'is_attack': is_attack,
            'attack_score': round(score,3),
            'attack_type': attack_type,
            'alert_message': f'Attack detected: {attack_type}' if attack_type else 'No attack',
            'metrics': {'frequency_30s': round(freq,1), 'duplicate_ratio': round(dup,3), 'author_concentration': round(self.get_author_concentration(30),3)},
            'top_duplicates': top
        }