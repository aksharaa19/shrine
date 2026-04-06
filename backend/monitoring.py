from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST
from flask import Response, request
import time
from functools import wraps

REQUEST_COUNT = Counter('http_requests_total', 'Total HTTP requests', ['method', 'endpoint', 'status'])
REQUEST_DURATION = Histogram('http_request_duration_seconds', 'HTTP request duration', ['method', 'endpoint'])
ACTIVE_MONITORS = Gauge('active_live_monitors', 'Number of active live stream monitors')
TOXICITY_SCORE = Gauge('current_toxicity_score', 'Current toxicity score for active monitor', ['video_id'])
ATTACK_SCORE = Gauge('attack_detection_score', 'Current attack detection score', ['video_id'])
COMMENT_COUNT = Counter('comments_processed_total', 'Total comments processed', ['video_id'])

def monitor_metrics(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        start_time = time.time()
        response = f(*args, **kwargs)
        duration = time.time() - start_time
        
        REQUEST_COUNT.labels(
            method=request.method,
            endpoint=request.endpoint or 'unknown',
            status=response.status_code
        ).inc()
        
        REQUEST_DURATION.labels(
            method=request.method,
            endpoint=request.endpoint or 'unknown'
        ).observe(duration)
        
        return response
    return decorated_function