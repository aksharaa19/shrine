import sys
import os
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
from dotenv import load_dotenv
from youtube_client import YouTubeClient
from mining.sliding_window import SlidingWindowAnalyzer
from live_stream_monitor import LiveStreamMonitor
from reports.report_generator import ReportGenerator
from auth import UserAuth
from sentiment.analyzer import SentimentAnalyzer
from monitoring import monitor_metrics, ACTIVE_MONITORS, TOXICITY_SCORE, ATTACK_SCORE
from logging_config import logger

load_dotenv()

app = Flask(__name__)
CORS(app)

# Get absolute paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FRONTEND_DIR = os.path.join(BASE_DIR, '../frontend')

print(f"Frontend directory: {FRONTEND_DIR}")
print(f"Files in frontend: {os.listdir(FRONTEND_DIR) if os.path.exists(FRONTEND_DIR) else 'NOT FOUND'}")

youtube = YouTubeClient()

print("Initializing Sentiment Analyzer...")
sentiment_analyzer = SentimentAnalyzer()
print("Sentiment Analyzer ready")

active_monitors = {}
report_generator = ReportGenerator()
user_auth = UserAuth()

@app.before_request
def log_request():
    logger.info("Request received", 
                method=request.method, 
                path=request.path,
                ip=request.remote_addr)

@app.after_request
def update_metrics(response):
    ACTIVE_MONITORS.set(len(active_monitors))
    return response

# Static file routes
@app.route('/')
def serve_index():
    return send_from_directory(FRONTEND_DIR, 'index.html')

@app.route('/dashboard')
def serve_dashboard():
    return send_from_directory(FRONTEND_DIR, 'dashboard.html')

@app.route('/dashboard.js')
def serve_dashboard_js():
    return send_from_directory(FRONTEND_DIR, 'dashboard.js')

@app.route('/style.css')
def serve_style_css():
    return send_from_directory(FRONTEND_DIR, 'style.css')

@app.route('/<path:path>')
def serve_static(path):
    return send_from_directory(FRONTEND_DIR, path)

# API routes
@app.route('/api/health')
def health_check():
    return jsonify({
        'status': 'healthy',
        'active_monitors': len(active_monitors),
        'environment': os.environ.get('RENDER', 'development'),
        'timestamp': datetime.now().isoformat()
    })

@app.route('/api/video', methods=['POST'])
@monitor_metrics
def get_video_details():
    data = request.json
    url = data.get('url')
    if not url:
        return jsonify({'error': 'No URL provided'}), 400
    video_id = youtube.extract_video_id(url)
    details = youtube.get_video_details(video_id)
    if not details:
        return jsonify({'error': 'Video not found'}), 404
    return jsonify({
        'video_id': video_id,
        'title': details['title'],
        'channel': details['channel'],
        'published_at': details['published_at']
    })

@app.route('/api/comments', methods=['POST'])
@monitor_metrics
def get_comments():
    data = request.json
    url = data.get('url')
    limit = data.get('limit', 100)
    if not url:
        return jsonify({'error': 'No URL provided'}), 400
    video_id = youtube.extract_video_id(url)
    details = youtube.get_video_details(video_id)
    comments = youtube.get_comments(video_id, limit)
    return jsonify({
        'video_id': video_id,
        'video_title': details['title'] if details else 'Unknown',
        'channel': details['channel'] if details else 'Unknown',
        'total_comments_fetched': len(comments),
        'comments': comments
    })

@app.route('/api/analyze', methods=['POST'])
@monitor_metrics
def analyze_comments():
    data = request.json
    comments = data.get('comments', [])
    if not comments:
        return jsonify({'error': 'No comments provided'}), 400
    analyzed_comments = sentiment_analyzer.analyze_batch(comments)
    stats = sentiment_analyzer.get_summary_stats(analyzed_comments)
    return jsonify({'stats': stats, 'analyzed_comments': analyzed_comments})

@app.route('/api/live/start', methods=['POST'])
@monitor_metrics
def start_live_monitoring():
    data = request.json
    url = data.get('url')
    if not url:
        return jsonify({'error': 'No URL provided'}), 400
    video_id = youtube.extract_video_id(url)
    is_live = youtube.is_live_stream(video_id)
    if not is_live:
        return jsonify({'error': 'This video is not currently live streaming'}), 400
    live_chat_id = youtube.get_live_chat_id(video_id)
    if not live_chat_id:
        return jsonify({'error': 'Could not retrieve live chat'}), 400
    if video_id in active_monitors:
        return jsonify({'error': 'Already monitoring this stream'}), 400
    sliding_window = SlidingWindowAnalyzer()
    monitor = LiveStreamMonitor(video_id, live_chat_id, youtube, sentiment_analyzer, sliding_window)
    monitor.start()
    active_monitors[video_id] = monitor
    logger.info(f"Live monitoring started", video_id=video_id)
    return jsonify({'status': 'monitoring', 'video_id': video_id})

@app.route('/api/live/status', methods=['POST'])
@monitor_metrics
def get_live_status():
    data = request.json
    video_id = data.get('video_id')
    if video_id not in active_monitors:
        return jsonify({'error': 'Not monitoring this stream'}), 400
    monitor = active_monitors[video_id]
    status = monitor.get_status()
    attack_status = monitor.sliding_window.detect_coordinated_attack()
    status['attack_detection'] = attack_status
    return jsonify(status)

@app.route('/api/live/stop', methods=['POST'])
@monitor_metrics
def stop_live_monitoring():
    data = request.json
    video_id = data.get('video_id')
    if video_id in active_monitors:
        monitor = active_monitors[video_id]
        monitor.stop()
        del active_monitors[video_id]
        logger.info(f"Live monitoring stopped", video_id=video_id)
        return jsonify({'status': 'stopped', 'video_id': video_id})
    return jsonify({'error': 'Not monitoring this stream'}), 400

@app.route('/api/live/alert', methods=['POST'])
@monitor_metrics
def get_live_alert():
    data = request.json
    video_id = data.get('video_id')
    if video_id not in active_monitors:
        return jsonify({'error': 'Not monitoring this stream'}), 400
    monitor = active_monitors[video_id]
    alert = monitor.sliding_window.generate_full_alert()
    return jsonify(alert)

@app.route('/api/recommendations', methods=['POST'])
@monitor_metrics
def get_recommendations():
    data = request.json
    video_id = data.get('video_id')
    if video_id not in active_monitors:
        return jsonify({'error': 'Not monitoring this stream'}), 400
    monitor = active_monitors[video_id]
    alert = monitor.sliding_window.generate_full_alert()
    return jsonify({'video_id': video_id, 'recommendations': alert['recommendations']})

@app.route('/api/report/generate', methods=['POST'])
@monitor_metrics
def generate_report():
    data = request.json
    video_id = data.get('video_id')
    if video_id not in active_monitors:
        return jsonify({'error': 'Not monitoring this stream'}), 400
    monitor = active_monitors[video_id]
    video_details = youtube.get_video_details(video_id)
    video_title = video_details['title'] if video_details else 'Unknown'
    report = report_generator.generate_containment_report(
        video_id=video_id, video_title=video_title,
        sliding_window=monitor.sliding_window,
        attack_detector=monitor.sliding_window.attack_detector,
        alert_engine=monitor.sliding_window.alert_engine,
        comments_analyzed=monitor.comment_count
    )
    return jsonify(report)

@app.route('/api/report/export/json', methods=['POST'])
@monitor_metrics
def export_report_json():
    data = request.json
    video_id = data.get('video_id')
    if video_id not in active_monitors:
        return jsonify({'error': 'Not monitoring this stream'}), 400
    monitor = active_monitors[video_id]
    video_details = youtube.get_video_details(video_id)
    video_title = video_details['title'] if video_details else 'Unknown'
    report = report_generator.generate_containment_report(
        video_id=video_id, video_title=video_title,
        sliding_window=monitor.sliding_window,
        attack_detector=monitor.sliding_window.attack_detector,
        alert_engine=monitor.sliding_window.alert_engine,
        comments_analyzed=monitor.comment_count
    )
    json_output = report_generator.export_to_json(report)
    return jsonify({'success': True, 'report_json': json_output})

@app.route('/api/report/export/csv', methods=['POST'])
@monitor_metrics
def export_report_csv():
    data = request.json
    video_id = data.get('video_id')
    if video_id not in active_monitors:
        return jsonify({'error': 'Not monitoring this stream'}), 400
    monitor = active_monitors[video_id]
    video_details = youtube.get_video_details(video_id)
    video_title = video_details['title'] if video_details else 'Unknown'
    report = report_generator.generate_containment_report(
        video_id=video_id, video_title=video_title,
        sliding_window=monitor.sliding_window,
        attack_detector=monitor.sliding_window.attack_detector,
        alert_engine=monitor.sliding_window.alert_engine,
        comments_analyzed=monitor.comment_count
    )
    csv_output = report_generator.export_to_csv(report)
    return jsonify({'success': True, 'csv': csv_output})

@app.route('/api/auth/register', methods=['POST'])
@monitor_metrics
def register():
    data = request.json
    result = user_auth.register(data.get('username'), data.get('password'), data.get('email'))
    if result['success']:
        logger.info(f"User registered", username=data.get('username'))
        return jsonify(result)
    return jsonify({'error': result['error']}), 400

@app.route('/api/auth/login', methods=['POST'])
@monitor_metrics
def login():
    data = request.json
    result = user_auth.login(data.get('username'), data.get('password'))
    if result['success']:
        logger.info(f"User logged in", username=data.get('username'))
        return jsonify(result)
    return jsonify({'error': result['error']}), 401

@app.route('/api/auth/logout', methods=['POST'])
@monitor_metrics
def logout():
    data = request.json
    result = user_auth.logout(data.get('token'))
    return jsonify(result)

@app.route('/api/history/save', methods=['POST'])
@monitor_metrics
def save_history():
    data = request.json
    session = user_auth.verify_session(data.get('token'))
    if not session['success']:
        return jsonify({'error': 'Invalid session'}), 401
    user_auth.save_monitoring_session(session['username'], data.get('video_id'), data.get('video_title'), data.get('report'))
    return jsonify({'success': True})

@app.route('/api/history/get', methods=['POST'])
@monitor_metrics
def get_history():
    data = request.json
    session = user_auth.verify_session(data.get('token'))
    if not session['success']:
        return jsonify({'error': 'Invalid session'}), 401
    history = user_auth.get_user_monitoring_history(session['username'])
    return jsonify({'history': history})

@app.route('/metrics')
def metrics():
    from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
    from flask import Response
    return Response(generate_latest(), mimetype=CONTENT_TYPE_LATEST)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)), debug=False)