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
from visualization.charts import ChartDataGenerator

load_dotenv()

app = Flask(__name__)
CORS(app)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FRONTEND_DIR = os.path.join(BASE_DIR, '../frontend')

print(f"Frontend directory: {FRONTEND_DIR}")

youtube = YouTubeClient()
sentiment_analyzer = SentimentAnalyzer()
active_monitors = {}
report_generator = ReportGenerator()
user_auth = UserAuth()
chart_gen = ChartDataGenerator()

# -------------------- Static Routes --------------------
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

# -------------------- API Routes --------------------
@app.route('/api/health')
def health():
    return jsonify({'status': 'healthy', 'active_monitors': len(active_monitors)})

@app.route('/api/video', methods=['POST'])
def get_video():
    data = request.json
    url = data.get('url')
    if not url:
        return jsonify({'error': 'No URL'}), 400
    vid = youtube.extract_video_id(url)
    details = youtube.get_video_details(vid)
    if not details:
        return jsonify({'error': 'Video not found'}), 404
    return jsonify({'video_id': vid, 'title': details['title'], 'channel': details['channel'], 'published_at': details['published_at']})

@app.route('/api/comments', methods=['POST'])
def get_comments():
    data = request.json
    url = data.get('url')
    if not url:
        return jsonify({'error': 'No URL'}), 400
    vid = youtube.extract_video_id(url)
    details = youtube.get_video_details(vid)
    comments = youtube.get_comments(vid, data.get('limit', 100))
    return jsonify({
        'video_id': vid,
        'video_title': details['title'] if details else 'Unknown',
        'total_comments_fetched': len(comments),
        'comments': comments
    })

@app.route('/api/analyze', methods=['POST'])
def analyze():
    data = request.json
    comments = data.get('comments', [])
    if not comments:
        return jsonify({'error': 'No comments'}), 400
    analyzed = sentiment_analyzer.analyze_batch(comments)
    stats = sentiment_analyzer.get_summary_stats(analyzed)
    return jsonify({'stats': stats, 'analyzed_comments': analyzed})

@app.route('/api/live/start', methods=['POST'])
def start_live():
    data = request.json
    url = data.get('url')
    if not url:
        return jsonify({'error': 'No URL'}), 400
    vid = youtube.extract_video_id(url)
    if not youtube.is_live_stream(vid):
        return jsonify({'error': 'Not a live stream'}), 400
    chat_id = youtube.get_live_chat_id(vid)
    if not chat_id:
        return jsonify({'error': 'Live chat not available'}), 400
    if vid in active_monitors:
        return jsonify({'error': 'Already monitoring'}), 400
    sw = SlidingWindowAnalyzer()
    monitor = LiveStreamMonitor(vid, chat_id, youtube, sentiment_analyzer, sw)
    monitor.start()
    active_monitors[vid] = monitor
    return jsonify({'status': 'monitoring', 'video_id': vid})

@app.route('/api/live/status', methods=['POST'])
def live_status():
    data = request.json
    vid = data.get('video_id')
    if vid not in active_monitors:
        return jsonify({'error': 'Not monitoring'}), 400
    status = active_monitors[vid].get_status()
    attack = active_monitors[vid].sliding_window.detect_coordinated_attack()
    status['attack_detection'] = attack
    return jsonify(status)

@app.route('/api/live/stop', methods=['POST'])
def stop_live():
    data = request.json
    vid = data.get('video_id')
    if vid in active_monitors:
        active_monitors[vid].stop()
        del active_monitors[vid]
        return jsonify({'status': 'stopped'})
    return jsonify({'error': 'Not monitoring'}), 400

@app.route('/api/live/alert', methods=['POST'])
def live_alert():
    data = request.json
    vid = data.get('video_id')
    if vid not in active_monitors:
        return jsonify({'error': 'Not monitoring'}), 400
    alert = active_monitors[vid].sliding_window.generate_full_alert()
    return jsonify(alert)

@app.route('/api/recommendations', methods=['POST'])
def recommendations():
    data = request.json
    vid = data.get('video_id')
    if vid not in active_monitors:
        return jsonify({'error': 'Not monitoring'}), 400
    alert = active_monitors[vid].sliding_window.generate_full_alert()
    return jsonify({'recommendations': alert['recommendations']})

@app.route('/api/report/generate', methods=['POST'])
def generate_report():
    data = request.json
    vid = data.get('video_id')
    if vid not in active_monitors:
        return jsonify({'error': 'Not monitoring'}), 400
    monitor = active_monitors[vid]
    details = youtube.get_video_details(vid)
    title = details['title'] if details else 'Unknown'
    report = report_generator.generate_containment_report(
        vid, title, monitor.sliding_window,
        monitor.sliding_window.attack_detector,
        monitor.sliding_window.alert_engine,
        monitor.comment_count
    )
    return jsonify(report)

@app.route('/api/report/export/json', methods=['POST'])
def export_json():
    try:
        data = request.json
        vid = data.get('video_id')
        if vid not in active_monitors:
            return jsonify({'success': False, 'error': 'Not monitoring this stream'}), 400
        
        monitor = active_monitors[vid]
        details = youtube.get_video_details(vid)
        title = details['title'] if details else 'Unknown'
        report = report_generator.generate_containment_report(
            vid, title, monitor.sliding_window,
            monitor.sliding_window.attack_detector,
            monitor.sliding_window.alert_engine,
            monitor.comment_count
        )
        json_output = report_generator.export_to_json(report)
        return jsonify({'success': True, 'report_json': json_output})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/report/export/csv', methods=['POST'])
def export_csv():
    try:
        data = request.json
        vid = data.get('video_id')
        if vid not in active_monitors:
            return jsonify({'success': False, 'error': 'Not monitoring this stream'}), 400
        
        monitor = active_monitors[vid]
        details = youtube.get_video_details(vid)
        title = details['title'] if details else 'Unknown'
        report = report_generator.generate_containment_report(
            vid, title, monitor.sliding_window,
            monitor.sliding_window.attack_detector,
            monitor.sliding_window.alert_engine,
            monitor.comment_count
        )
        csv_output = report_generator.export_to_csv(report)
        return jsonify({'success': True, 'csv': csv_output})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/auth/register', methods=['POST'])
def register():
    data = request.json
    result = user_auth.register(data.get('username'), data.get('password'), data.get('email'))
    return jsonify(result) if result['success'] else (jsonify({'error': result['error']}), 400)

@app.route('/api/auth/login', methods=['POST'])
def login():
    data = request.json
    result = user_auth.login(data.get('username'), data.get('password'))
    return jsonify(result) if result['success'] else (jsonify({'error': result['error']}), 401)

@app.route('/api/auth/logout', methods=['POST'])
def logout():
    data = request.json
    result = user_auth.logout(data.get('token'))
    return jsonify(result)

@app.route('/api/history/save', methods=['POST'])
def save_history():
    data = request.json
    session = user_auth.verify_session(data.get('token'))
    if not session['success']:
        return jsonify({'error': 'Invalid session'}), 401
    user_auth.save_monitoring_session(session['username'], data.get('video_id'), data.get('video_title'), data.get('report'))
    return jsonify({'success': True})

@app.route('/api/history/get', methods=['POST'])
def get_history():
    data = request.json
    session = user_auth.verify_session(data.get('token'))
    if not session['success']:
        return jsonify({'error': 'Invalid session'}), 401
    history = user_auth.get_user_monitoring_history(session['username'])
    return jsonify({'history': history})

# -------------------- Chart Endpoints --------------------
@app.route('/api/charts/toxicity', methods=['POST'])
def chart_toxicity():
    data = request.json
    vid = data.get('video_id')
    if vid not in active_monitors:
        return jsonify({'error': 'Not monitoring'}), 400
    chart_data = chart_gen.generate_toxicity_timeline(active_monitors[vid].sliding_window)
    return jsonify(chart_data)

@app.route('/api/charts/attack', methods=['POST'])
def chart_attack():
    data = request.json
    vid = data.get('video_id')
    if vid not in active_monitors:
        return jsonify({'error': 'Not monitoring'}), 400
    chart_data = chart_gen.generate_attack_timeline(active_monitors[vid].sliding_window.attack_detector)
    return jsonify(chart_data)

@app.route('/api/charts/velocity', methods=['POST'])
def chart_velocity():
    data = request.json
    vid = data.get('video_id')
    if vid not in active_monitors:
        return jsonify({'error': 'Not monitoring'}), 400
    chart_data = chart_gen.generate_velocity_chart(active_monitors[vid].sliding_window)
    return jsonify(chart_data)

@app.route('/api/charts/gauge', methods=['POST'])
def chart_gauge():
    data = request.json
    vid = data.get('video_id')
    if vid not in active_monitors:
        return jsonify({'error': 'Not monitoring'}), 400
    current_toxicity = active_monitors[vid].sliding_window.get_window_average(30)
    gauge_data = chart_gen.generate_gauge_data(current_toxicity)
    return jsonify(gauge_data)

# -------------------- Run --------------------
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port, debug=False)