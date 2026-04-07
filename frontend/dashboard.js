const API_URL = window.location.hostname === 'localhost' ? 'http://localhost:8080' : '';
const token = localStorage.getItem('shrine_token');
const username = localStorage.getItem('shrine_username');

if (!token) { window.location.href = 'index.html'; }

document.getElementById('userDisplay').textContent = username || 'User';

let currentVideoId = null;
let currentComments = null;
let liveInterval = null;
let currentLiveVideoId = null;
let currentReportData = null;
let toxicityChart = null;
let attackChart = null;
let velocityChart = null;
let gaugeChart = null;
let chartUpdateInterval = null;
let historyData = null;

function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

async function logout() {
    try { await fetch(`${API_URL}/api/auth/logout`, { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({token: token}) }); } catch(e) {}
    localStorage.clear();
    window.location.href = 'index.html';
}

function switchTab(tabName) {
    document.querySelectorAll('.tab-content').forEach(tab => tab.classList.remove('active'));
    document.querySelectorAll('.tab-btn').forEach(btn => btn.classList.remove('active'));
    document.getElementById(`${tabName}Tab`).classList.add('active');
    event.target.classList.add('active');
    if (tabName === 'history') loadHistory();
}

async function analyzeVideo() {
    const url = document.getElementById('videoUrl').value;
    const resultsDiv = document.getElementById('results');
    if (!url) { resultsDiv.innerHTML = '<div class="error">Please enter a YouTube URL</div>'; return; }
    resultsDiv.innerHTML = '<div class="loading">Fetching video details...</div>';
    document.getElementById('videoInfo').style.display = 'none';
    document.getElementById('statsSection').style.display = 'none';
    document.getElementById('commentsList').innerHTML = '';
    document.getElementById('fetchBtn').disabled = true;
    document.getElementById('sentimentBtn').disabled = true;
    try {
        const response = await fetch(`${API_URL}/api/video`, { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({url: url}) });
        const data = await response.json();
        if (response.ok) {
            currentVideoId = data.video_id;
            document.getElementById('videoInfo').innerHTML = `<h3>${escapeHtml(data.title)}</h3><p>Channel: ${escapeHtml(data.channel)}</p><p>Published: ${new Date(data.published_at).toLocaleDateString()}</p>`;
            document.getElementById('videoInfo').style.display = 'block';
            resultsDiv.innerHTML = '<div class="success">Video found. Click Fetch Comments.</div>';
            document.getElementById('fetchBtn').disabled = false;
        } else { resultsDiv.innerHTML = `<div class="error">${data.error}</div>`; }
    } catch(error) { resultsDiv.innerHTML = '<div class="error">Cannot connect to backend.</div>'; }
}

async function fetchVideoComments() {
    const url = document.getElementById('videoUrl').value;
    const resultsDiv = document.getElementById('results');
    resultsDiv.innerHTML = '<div class="loading">Fetching comments...</div>';
    document.getElementById('commentsList').innerHTML = '';
    document.getElementById('statsSection').style.display = 'none';
    document.getElementById('fetchBtn').disabled = true;
    document.getElementById('sentimentBtn').disabled = true;
    try {
        const response = await fetch(`${API_URL}/api/comments`, { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({url: url, limit: 50}) });
        const data = await response.json();
        if (response.ok) {
            currentComments = data.comments;
            resultsDiv.innerHTML = `<div class="success">Fetched ${data.total_comments_fetched} comments. Click Analyze Sentiment.</div>`;
            displayRawComments(currentComments);
            document.getElementById('fetchBtn').disabled = false;
            document.getElementById('sentimentBtn').disabled = false;
        } else { resultsDiv.innerHTML = `<div class="error">${data.error}</div>`; document.getElementById('fetchBtn').disabled = false; }
    } catch(error) { resultsDiv.innerHTML = `<div class="error">Error: ${error.message}</div>`; document.getElementById('fetchBtn').disabled = false; }
}

function displayRawComments(comments) {
    const container = document.getElementById('commentsList');
    if (!comments || comments.length === 0) { container.innerHTML = '<p>No comments found.</p>'; return; }
    let html = `<h3 style="margin-bottom:16px">Comments (${comments.length}) - Analysis Pending</h3>`;
    comments.forEach(c => { html += `<div class="comment-card"><div class="comment-author">${escapeHtml(c.author)}</div><div class="comment-text">${escapeHtml(c.text)}</div><div class="comment-meta">Likes: ${c.likes} • ${new Date(c.timestamp).toLocaleString()}</div></div>`; });
    container.innerHTML = html;
}

async function analyzeSentiment() {
    if (!currentComments) { document.getElementById('results').innerHTML = '<div class="error">Please fetch comments first</div>'; return; }
    const resultsDiv = document.getElementById('results');
    resultsDiv.innerHTML = '<div class="loading">Analyzing sentiment...</div>';
    document.getElementById('sentimentBtn').disabled = true;
    try {
        const response = await fetch(`${API_URL}/api/analyze`, { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({comments: currentComments}) });
        const data = await response.json();
        if (response.ok) {
            displayStats(data.stats);
            displayAnalyzedComments(data.analyzed_comments);
            resultsDiv.innerHTML = `<div class="success">Analysis complete. ${data.stats.toxic_count} toxic comments (${data.stats.toxic_percentage}%)</div>`;
        } else { resultsDiv.innerHTML = `<div class="error">${data.error}</div>`; }
    } catch(error) { resultsDiv.innerHTML = `<div class="error">Error: ${error.message}</div>`; }
    document.getElementById('sentimentBtn').disabled = false;
}

function displayStats(stats) {
    const grid = document.getElementById('statsGrid');
    const progress = document.getElementById('toxicityProgress');
    grid.innerHTML = `<div class="stat-card"><div class="stat-value">${stats.total_comments}</div><div class="stat-label">Total Comments</div></div><div class="stat-card"><div class="stat-value" style="color:#e94560">${stats.toxic_count}</div><div class="stat-label">Toxic</div></div><div class="stat-card"><div class="stat-value" style="color:#ffd600">${stats.moderate_count}</div><div class="stat-label">Moderate</div></div><div class="stat-card"><div class="stat-value" style="color:#00c853">${stats.safe_count}</div><div class="stat-label">Safe</div></div>`;
    progress.style.width = `${stats.toxic_percentage}%`;
    document.getElementById('statsSection').style.display = 'block';
}

function displayAnalyzedComments(comments) {
    const container = document.getElementById('commentsList');
    if (!comments || comments.length === 0) { container.innerHTML = '<p>No comments to display.</p>'; return; }
    let html = `<h3 style="margin-bottom:16px">Analyzed Comments (${comments.length})</h3>`;
    comments.forEach(c => {
        const level = c.toxicity.toxicity_level;
        const badgeText = level === 'toxic' ? 'Toxic' : (level === 'moderate' ? 'Moderate' : 'Safe');
        const badgeClass = level === 'toxic' ? 'badge-toxic' : (level === 'moderate' ? 'badge-moderate' : 'badge-safe');
        const reasonHtml = level !== 'safe' ? `<div style="font-size:0.7rem; color:#ffd600; margin-top:5px;">Reason: ${escapeHtml(c.toxicity.reason)}</div>` : '';
        html += `<div class="comment-card ${level}"><div class="comment-author">${escapeHtml(c.author)} <span class="toxicity-badge ${badgeClass}">${badgeText}</span></div><div class="comment-text">${escapeHtml(c.text)}</div>${reasonHtml}<div class="comment-meta">Likes: ${c.likes} • ${new Date(c.timestamp).toLocaleString()} • Score: ${(c.toxicity.toxic_score * 100).toFixed(1)}%</div></div>`;
    });
    container.innerHTML = html;
}

async function startLiveMonitoring() {
    const url = document.getElementById('liveVideoUrl').value;
    const liveStatus = document.getElementById('liveStatus');
    if (!url) { liveStatus.innerHTML = '<div class="error">Please enter a YouTube URL</div>'; return; }
    liveStatus.innerHTML = '<div class="loading">Starting live monitoring...</div>';
    const startBtn = event.target;
    startBtn.disabled = true;
    try {
        const response = await fetch(`${API_URL}/api/live/start`, { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({url: url}) });
        const data = await response.json();
        if (response.ok) {
            currentLiveVideoId = data.video_id;
            liveStatus.innerHTML = `<div class="success">Monitoring: ${data.video_id}</div>`;
            document.getElementById('stopLiveBtn').disabled = false;
            document.getElementById('reportSection').style.display = 'block';
            initReportButtons();
            if (liveInterval) clearInterval(liveInterval);
            liveInterval = setInterval(pollLiveStatus, 3000);
            startChartUpdates();
        } else { liveStatus.innerHTML = `<div class="error">${data.error}</div>`; }
    } catch(error) { liveStatus.innerHTML = `<div class="error">Error: ${error.message}</div>`; }
    startBtn.disabled = false;
}

function initReportButtons() {
    const genBtn = document.getElementById('generateReportBtn');
    const jsonBtn = document.getElementById('exportJSONBtn');
    const csvBtn = document.getElementById('exportCSVBtn');
    const saveBtn = document.getElementById('saveHistoryBtn');
    if (genBtn) genBtn.onclick = generateReport;
    if (jsonBtn) jsonBtn.onclick = exportReportJSON;
    if (csvBtn) csvBtn.onclick = exportReportCSV;
    if (saveBtn) saveBtn.onclick = saveToHistory;
}

async function pollLiveStatus() {
    if (!currentLiveVideoId) return;
    try {
        const response = await fetch(`${API_URL}/api/live/status`, { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({video_id: currentLiveVideoId}) });
        const data = await response.json();
        if (response.ok && data.active) updateLiveDisplay(data);
        else if (response.ok && !data.active) stopLiveMonitoring();
    } catch(error) { console.error('Poll error:', error); }
}

function updateLiveDisplay(data) {
    const toxicityPercent = (data.current_toxicity * 100).toFixed(1);
    const velocityPercent = (data.velocity_30 * 100).toFixed(1);
    const accPercent = (data.acceleration * 100).toFixed(1);
    document.getElementById('liveStats').innerHTML = `<div class="live-stat-card"><div class="live-stat-value">${data.comment_count}</div><div class="live-stat-label">Comments</div></div><div class="live-stat-card"><div class="live-stat-value">${toxicityPercent}%</div><div class="live-stat-label">Toxicity</div></div><div class="live-stat-card"><div class="live-stat-value">${velocityPercent}%</div><div class="live-stat-label">Velocity (30s)</div></div><div class="live-stat-card"><div class="live-stat-value">${accPercent}%</div><div class="live-stat-label">Acceleration</div></div>`;
    document.getElementById('liveStatus').innerHTML = `<div class="success">Active • ${data.comment_count} comments • Last poll: ${data.last_poll ? new Date(data.last_poll).toLocaleTimeString() : '...'}</div>`;
    const alertDiv = document.getElementById('liveAlert');
    if (data.alert.alert_triggered) {
        alertDiv.className = `live-alert ${data.alert.alert_level}`;
        alertDiv.innerHTML = `<strong>Alert:</strong> ${data.alert.alert_message}<br><small>Toxicity: ${toxicityPercent}% | Acceleration: ${accPercent}%</small>`;
    } else { alertDiv.style.display = 'none'; }
    if (data.recent_alerts && data.recent_alerts.length > 0) {
        document.getElementById('recentAlerts').innerHTML = `<h4 style="margin-bottom:10px">Recent Alerts</h4>${data.recent_alerts.slice().reverse().map(a => `<div style="padding:5px 0; border-bottom:1px solid rgba(255,255,255,0.1); font-size:0.8rem"><span style="color:#888">${new Date(a.timestamp).toLocaleTimeString()}</span> • ${a.alert.alert_message}</div>`).join('')}`;
    }
    if (data.attack_detection) {
        const attack = data.attack_detection;
        document.getElementById('attackSection').style.display = 'block';
        document.getElementById('attackSection').innerHTML = `<h4>Coordinated Attack Detection</h4><div style="display:flex; gap:15px; flex-wrap:wrap; margin-bottom:10px"><div style="background:rgba(255,152,0,0.2); padding:8px 15px; border-radius:8px">Attack Score: <strong style="color:#ff9800">${(attack.attack_score * 100).toFixed(0)}%</strong></div><div style="background:rgba(255,152,0,0.2); padding:8px 15px; border-radius:8px">Type: ${attack.attack_type ? attack.attack_type.replace(/_/g, ' ').toUpperCase() : 'None'}</div></div><div style="display:flex; gap:10px; flex-wrap:wrap; margin-bottom:10px"><span style="background:rgba(255,255,255,0.1); padding:5px 10px; border-radius:5px">Frequency: ${attack.metrics.frequency_30s} msg/sec</span><span style="background:rgba(255,255,255,0.1); padding:5px 10px; border-radius:5px">Duplicate: ${(attack.metrics.duplicate_ratio * 100).toFixed(0)}%</span></div>${attack.is_attack ? `<div style="background:#e94560; padding:10px; border-radius:8px; margin-top:10px"><strong>Attack Detected!</strong> ${attack.alert_message}</div>` : ''}${attack.top_duplicates && attack.top_duplicates.length > 0 ? `<div style="margin-top:10px"><strong>Top duplicates:</strong> ${attack.top_duplicates.map(d => `<div>${d.count}x: ${escapeHtml(d.text.substring(0, 60))}</div>`).join('')}</div>` : ''}`;
    }
    fetchRecommendations();
    fetchPrediction();
}

async function fetchRecommendations() {
    if (!currentLiveVideoId) return;
    try {
        const response = await fetch(`${API_URL}/api/recommendations`, { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({video_id: currentLiveVideoId}) });
        const data = await response.json();
        if (response.ok && data.recommendations && data.recommendations.length > 0) {
            document.getElementById('recommendationsSection').style.display = 'block';
            document.getElementById('recommendationsSection').innerHTML = `<h4>Intervention Recommendations</h4>${data.recommendations.map(rec => `<div style="background:rgba(255,255,255,0.05); padding:12px; border-radius:8px; margin-bottom:10px; border-left:3px solid ${rec.priority === 'critical' ? '#e94560' : (rec.priority === 'high' ? '#ff9800' : '#ffd600')}"><div style="font-weight:bold">${escapeHtml(rec.action)}</div><div style="font-size:0.8rem; opacity:0.8">${escapeHtml(rec.description)}</div><div style="font-size:0.7rem; color:#ffd600; margin-top:5px">Timeframe: ${escapeHtml(rec.timeframe)}</div></div>`).join('')}</div>`;
        }
    } catch(e) { console.error(e); }
}

async function fetchPrediction() {
    if (!currentLiveVideoId) return;
    try {
        const response = await fetch(`${API_URL}/api/live/alert`, { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({video_id: currentLiveVideoId}) });
        const data = await response.json();
        if (response.ok && data.prediction) {
            const pred = data.prediction;
            document.getElementById('alertPrediction').innerHTML = pred.is_escalation_predicted ? `<div style="margin-top:15px; padding:10px; background:rgba(233,69,96,0.2); border-radius:8px; text-align:center"><div style="font-size:1.2rem; font-weight:bold; color:#e94560">Escalation predicted in ${pred.time_to_escalation_text}</div><div style="font-size:0.8rem">Confidence: ${(pred.confidence * 100).toFixed(0)}% | Score: ${(pred.prediction_score * 100).toFixed(0)}%</div></div>` : `<div style="margin-top:15px; padding:10px; background:rgba(0,200,83,0.2); border-radius:8px; text-align:center"><div style="font-size:1.2rem; font-weight:bold; color:#00c853">No immediate escalation predicted</div></div>`;
        }
    } catch(e) { console.error(e); }
}

async function stopLiveMonitoring() {
    if (liveInterval) clearInterval(liveInterval);
    if (chartUpdateInterval) clearInterval(chartUpdateInterval);
    if (currentLiveVideoId) {
        try { await fetch(`${API_URL}/api/live/stop`, { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({video_id: currentLiveVideoId}) }); } catch(e) {}
    }
    document.getElementById('liveStatus').innerHTML = '<div class="success">Monitoring stopped.</div>';
    document.getElementById('stopLiveBtn').disabled = true;
    document.getElementById('liveStats').innerHTML = '';
    document.getElementById('liveAlert').style.display = 'none';
    document.getElementById('attackSection').style.display = 'none';
    document.getElementById('recommendationsSection').style.display = 'none';
    if (toxicityChart) toxicityChart.destroy();
    if (attackChart) attackChart.destroy();
    if (velocityChart) velocityChart.destroy();
    if (gaugeChart) gaugeChart.destroy();
    toxicityChart = attackChart = velocityChart = gaugeChart = null;
    currentLiveVideoId = null;
}

async function updateCharts() {
    if (!currentLiveVideoId) return;
    try {
        const toxRes = await fetch(`${API_URL}/api/charts/toxicity`, { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({video_id: currentLiveVideoId}) });
        const toxData = await toxRes.json();
        if (toxicityChart) toxicityChart.destroy();
        toxicityChart = new Chart(document.getElementById('toxicityChart'), { type: 'line', data: toxData, options: { responsive: true, maintainAspectRatio: true, plugins: { legend: { labels: { color: 'white' } } } } });
        const attackRes = await fetch(`${API_URL}/api/charts/attack`, { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({video_id: currentLiveVideoId}) });
        const attackData = await attackRes.json();
        if (attackChart) attackChart.destroy();
        attackChart = new Chart(document.getElementById('attackChart'), { type: 'line', data: attackData, options: { responsive: true, maintainAspectRatio: true, plugins: { legend: { labels: { color: 'white' } } } } });
        const velRes = await fetch(`${API_URL}/api/charts/velocity`, { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({video_id: currentLiveVideoId}) });
        const velData = await velRes.json();
        if (velocityChart) velocityChart.destroy();
        velocityChart = new Chart(document.getElementById('velocityChart'), { type: 'bar', data: velData, options: { responsive: true, maintainAspectRatio: true, plugins: { legend: { labels: { color: 'white' } } } } });
        const gaugeRes = await fetch(`${API_URL}/api/charts/gauge`, { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({video_id: currentLiveVideoId}) });
        const gaugeData = await gaugeRes.json();
        if (gaugeChart) gaugeChart.destroy();
        gaugeChart = new Chart(document.getElementById('gaugeChart'), { type: 'doughnut', data: { labels: ['Toxicity', 'Remaining'], datasets: [{ data: [gaugeData.value, gaugeData.remaining], backgroundColor: ['#e94560', '#2a2a4a'], borderWidth: 0 }] }, options: { responsive: true, maintainAspectRatio: true, cutout: '70%', plugins: { legend: { labels: { color: 'white' } } } } });
    } catch(e) { console.error('Chart error:', e); }
}

function startChartUpdates() {
    if (chartUpdateInterval) clearInterval(chartUpdateInterval);
    chartUpdateInterval = setInterval(updateCharts, 5000);
    updateCharts();
}

async function generateReport() {
    if (!currentLiveVideoId) { alert('Please start live monitoring first'); return; }
    const genBtn = document.getElementById('generateReportBtn');
    const content = document.getElementById('reportContent');
    genBtn.disabled = true;
    genBtn.textContent = 'Generating...';
    content.innerHTML = '<div class="loading">Generating report...</div>';
    try {
        const response = await fetch(`${API_URL}/api/report/generate`, { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({video_id: currentLiveVideoId}) });
        const data = await response.json();
        if (response.ok) {
            currentReportData = data;
            displayReport(data);
            document.getElementById('exportJSONBtn').disabled = false;
            document.getElementById('exportCSVBtn').disabled = false;
            document.getElementById('saveHistoryBtn').disabled = false;
        } else { content.innerHTML = `<div class="error">${data.error || 'Failed to generate report'}</div>`; }
    } catch(error) { content.innerHTML = `<div class="error">Error: ${error.message}</div>`; }
    genBtn.disabled = false;
    genBtn.textContent = 'Generate Report';
}

function displayReport(report) {
    const content = document.getElementById('reportContent');
    content.innerHTML = `<div class="stats-grid"><div class="stat-card"><div class="stat-value">${report.toxicity_summary.current_toxicity}%</div><div class="stat-label">Current Toxicity</div></div><div class="stat-card"><div class="stat-value">${report.toxicity_summary.peak_toxicity}%</div><div class="stat-label">Peak Toxicity</div></div><div class="stat-card"><div class="stat-value">${report.toxicity_summary.average_toxicity}%</div><div class="stat-label">Average Toxicity</div></div><div class="stat-card"><div class="stat-value">${report.comments_analyzed}</div><div class="stat-label">Comments Analyzed</div></div><div class="stat-card"><div class="stat-value">${report.duration_minutes}</div><div class="stat-label">Duration (min)</div></div><div class="stat-card"><div class="stat-value">${report.alert_summary.total_alerts || 0}</div><div class="stat-label">Total Alerts</div></div></div><div class="stats-grid"><div class="stat-card"><div class="stat-value">${report.attack_summary.attack_count || 0}</div><div class="stat-label">Attacks Detected</div></div><div class="stat-card"><div class="stat-value">${report.attack_summary.peak_attack_score || 0}%</div><div class="stat-label">Peak Attack Score</div></div><div class="stat-card"><div class="stat-value">${report.alert_summary.high_severity_count || 0}</div><div class="stat-label">Critical Alerts</div></div></div><div style="margin-top:15px; padding-top:15px; border-top:1px solid rgba(255,255,255,0.1)"><p><strong>Report ID:</strong> ${report.report_id}</p><p><strong>Generated:</strong> ${new Date(report.generated_at).toLocaleString()}</p><p><strong>Video ID:</strong> ${report.video_id}</p></div>${report.comments_with_scores && report.comments_with_scores.length ? `<div style="margin-top:15px"><strong>Recent Comments with Toxicity Scores:</strong><div style="max-height:200px; overflow-y:auto; margin-top:10px">${report.comments_with_scores.slice(-15).reverse().map(c => `<div style="border-bottom:1px solid rgba(255,255,255,0.1); padding:8px 0"><span style="color:${c.toxicity_score > 50 ? '#e94560' : (c.toxicity_score > 20 ? '#ffd600' : '#00c853')}; font-weight:bold">${c.toxicity_score}%</span> <span style="color:#888">| ${escapeHtml(c.author)}</span><div style="font-size:0.75rem; margin-top:3px">${escapeHtml(c.comment.substring(0, 100))}${c.comment.length > 100 ? '...' : ''}</div></div>`).join('')}</div></div>` : ''}`;
}

async function exportReportJSON() {
    if (!currentReportData) { alert('Please generate a report first'); return; }
    try {
        const response = await fetch(`${API_URL}/api/report/export/json`, { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({video_id: currentLiveVideoId}) });
        const data = await response.json();
        if (response.ok && data.success) {
            const blob = new Blob([data.report_json], {type: 'application/json'});
            const a = document.createElement('a');
            a.href = URL.createObjectURL(blob);
            a.download = `shrine_report_${currentLiveVideoId}_${Date.now()}.json`;
            a.click();
            URL.revokeObjectURL(a.href);
        } else { alert('Export failed'); }
    } catch(error) { alert('Error: ' + error.message); }
}

async function exportReportCSV() {
    if (!currentReportData) { alert('Please generate a report first'); return; }
    try {
        const response = await fetch(`${API_URL}/api/report/export/csv`, { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({video_id: currentLiveVideoId}) });
        const data = await response.json();
        if (response.ok && data.success) {
            const blob = new Blob([data.csv], {type: 'text/csv'});
            const a = document.createElement('a');
            a.href = URL.createObjectURL(blob);
            a.download = `shrine_comments_${currentLiveVideoId}_${Date.now()}.csv`;
            a.click();
            URL.revokeObjectURL(a.href);
        } else { alert('Export failed'); }
    } catch(error) { alert('Error: ' + error.message); }
}

async function saveToHistory() {
    if (!currentReportData) { alert('Please generate a report first'); return; }
    const saveBtn = document.getElementById('saveHistoryBtn');
    saveBtn.disabled = true;
    saveBtn.textContent = 'Saving...';
    try {
        const response = await fetch(`${API_URL}/api/history/save`, { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({ token: token, video_id: currentLiveVideoId, video_title: currentReportData.video_title || 'Unknown', report: currentReportData }) });
        const data = await response.json();
        if (response.ok) { alert('Saved to history!'); } else { alert('Save failed: ' + data.error); }
    } catch(error) { alert('Error: ' + error.message); }
    saveBtn.disabled = false;
    saveBtn.textContent = 'Save to History';
}

async function loadHistory() {
    const container = document.getElementById('historyList');
    container.innerHTML = '<div class="loading">Loading history...</div>';
    try {
        const response = await fetch(`${API_URL}/api/history/get`, { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({token: token}) });
        const data = await response.json();
        if (response.ok && data.history && data.history.length) {
            historyData = data.history;
            container.innerHTML = data.history.slice().reverse().map((item, idx) => `<div class="history-card"><div class="history-header"><span class="history-title">${escapeHtml(item.video_title)}</span><span class="history-date">${new Date(item.timestamp).toLocaleString()}</span></div><div class="history-stats"><span>Toxicity: ${item.report.toxicity_summary?.current_toxicity || 0}%</span><span>Comments: ${item.report.comments_analyzed || 0}</span><span>Alerts: ${item.report.alert_summary?.total_alerts || 0}</span></div><button class="history-btn" onclick="viewHistoryReport(${data.history.length - 1 - idx})">View Full Report</button></div>`).join('');
        } else { container.innerHTML = '<p>No history yet. Start monitoring and save reports.</p>'; }
    } catch(error) { container.innerHTML = '<div class="error">Failed to load history</div>'; }
}

function viewHistoryReport(index) {
    if (!historyData || !historyData[index]) return;
    const item = historyData[index];
    const report = item.report;
    const modalHtml = `<div id="reportModal" class="modal"><div class="modal-content"><div class="modal-header"><h3 style="color:#e94560">Report Details</h3><button class="close-modal" onclick="closeModal()">X</button></div><div><strong>Video:</strong> ${escapeHtml(item.video_title)}</div><div><strong>Date:</strong> ${new Date(item.timestamp).toLocaleString()}</div><div><strong>Video ID:</strong> ${item.video_id}</div><hr style="margin:15px 0; border-color:rgba(255,255,255,0.1)"><h4>Toxicity Summary</h4><div class="stats-grid" style="margin-top:10px"><div class="stat-card"><div class="stat-value">${report.toxicity_summary.current_toxicity}%</div><div class="stat-label">Current</div></div><div class="stat-card"><div class="stat-value">${report.toxicity_summary.peak_toxicity}%</div><div class="stat-label">Peak</div></div><div class="stat-card"><div class="stat-value">${report.toxicity_summary.average_toxicity}%</div><div class="stat-label">Average</div></div></div><h4>Alert Summary</h4><div class="stats-grid" style="margin-top:10px"><div class="stat-card"><div class="stat-value">${report.alert_summary.total_alerts || 0}</div><div class="stat-label">Total Alerts</div></div><div class="stat-card"><div class="stat-value">${report.alert_summary.high_severity_count || 0}</div><div class="stat-label">Critical</div></div></div><h4>Attack Summary</h4><div class="stats-grid" style="margin-top:10px"><div class="stat-card"><div class="stat-value">${report.attack_summary.attack_count || 0}</div><div class="stat-label">Attacks</div></div><div class="stat-card"><div class="stat-value">${report.attack_summary.peak_attack_score || 0}%</div><div class="stat-label">Peak Attack Score</div></div></div><hr style="margin:15px 0"><p><strong>Report ID:</strong> ${report.report_id}</p><p><strong>Generated:</strong> ${new Date(report.generated_at).toLocaleString()}</p></div></div>`;
    document.body.insertAdjacentHTML('beforeend', modalHtml);
}

function closeModal() {
    const modal = document.getElementById('reportModal');
    if (modal) modal.remove();
}

document.addEventListener('DOMContentLoaded', initReportButtons);