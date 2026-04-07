const API_URL = '';
const token = localStorage.getItem('shrine_token');
const username = localStorage.getItem('shrine_username');
if (!token) window.location.href = 'index.html';
document.getElementById('userDisplay').textContent = username || 'User';

let currentVideoId = null;
let currentComments = null;
let liveInterval = null;
let currentLiveVideoId = null;
let currentReportData = null;
let toxicityChart, attackChart, velocityChart, gaugeChart, chartInterval, historyData;

function escapeHtml(text) { 
    if (!text) return '';
    const div = document.createElement('div'); 
    div.textContent = text; 
    return div.innerHTML; 
}

async function logout() { 
    try { 
        await fetch(`${API_URL}/api/auth/logout`, {
            method: 'POST', 
            headers: {'Content-Type': 'application/json'}, 
            body: JSON.stringify({token})
        }); 
    } catch(e){} 
    localStorage.clear(); 
    window.location.href='index.html'; 
}

function switchTab(tab) {
    document.querySelectorAll('.tab-content').forEach(t=>t.classList.remove('active'));
    document.querySelectorAll('.tab-btn').forEach(b=>b.classList.remove('active'));
    document.getElementById(`${tab}Tab`).classList.add('active');
    event.target.classList.add('active');
    if(tab==='history') loadHistory();
}

async function analyzeVideo() {
    const url = document.getElementById('videoUrl').value;
    const resDiv = document.getElementById('results');
    if(!url){ resDiv.innerHTML='<div class="error">Enter URL</div>'; return; }
    resDiv.innerHTML='<div class="loading">Fetching...</div>';
    document.getElementById('videoInfo').style.display='none';
    document.getElementById('statsSection').style.display='none';
    document.getElementById('commentsList').innerHTML='';
    document.getElementById('fetchBtn').disabled=true;
    document.getElementById('sentimentBtn').disabled=true;
    try{
        const resp = await fetch(`${API_URL}/api/video`, {
            method:'POST',
            headers:{'Content-Type':'application/json'},
            body:JSON.stringify({url})
        });
        const data = await resp.json();
        if(resp.ok){
            currentVideoId = data.video_id;
            document.getElementById('videoInfo').innerHTML = `<h3>${escapeHtml(data.title)}</h3><p>${escapeHtml(data.channel)}</p><p>${new Date(data.published_at).toLocaleDateString()}</p>`;
            document.getElementById('videoInfo').style.display='block';
            resDiv.innerHTML='<div class="success">Video found. Fetch Comments.</div>';
            document.getElementById('fetchBtn').disabled=false;
        } else { 
            resDiv.innerHTML=`<div class="error">${data.error || 'Video not found'}</div>`; 
        }
    } catch(e){ 
        resDiv.innerHTML='<div class="error">Backend error: ' + e.message + '</div>'; 
    }
}

async function fetchComments() {
    const url = document.getElementById('videoUrl').value;
    const resDiv = document.getElementById('results');
    resDiv.innerHTML='<div class="loading">Fetching comments...</div>';
    document.getElementById('commentsList').innerHTML='';
    document.getElementById('statsSection').style.display='none';
    document.getElementById('fetchBtn').disabled=true;
    document.getElementById('sentimentBtn').disabled=true;
    try{
        const resp = await fetch(`${API_URL}/api/comments`, {
            method:'POST',
            headers:{'Content-Type':'application/json'},
            body:JSON.stringify({url, limit:50})
        });
        const data = await resp.json();
        if(resp.ok){
            currentComments = data.comments;
            resDiv.innerHTML=`<div class="success">Fetched ${data.total_comments_fetched} comments. Analyze Sentiment.</div>`;
            displayRawComments(currentComments);
            document.getElementById('fetchBtn').disabled=false;
            document.getElementById('sentimentBtn').disabled=false;
        } else { 
            resDiv.innerHTML=`<div class="error">${data.error || 'Failed to fetch'}</div>`; 
            document.getElementById('fetchBtn').disabled=false; 
        }
    } catch(e){ 
        resDiv.innerHTML=`<div class="error">${e.message}</div>`; 
        document.getElementById('fetchBtn').disabled=false; 
    }
}

function displayRawComments(comments) {
    const container = document.getElementById('commentsList');
    if(!comments || !comments.length){ container.innerHTML='<p>No comments</p>'; return; }
    let html=`<h3>Comments (${comments.length}) - Analysis Pending</h3>`;
    comments.forEach(c=>{ 
        html+=`<div class="comment-card"><div class="comment-author">${escapeHtml(c.author)}</div><div class="comment-text">${escapeHtml(c.text)}</div><div class="comment-meta">Likes: ${c.likes} • ${new Date(c.timestamp).toLocaleString()}</div></div>`; 
    });
    container.innerHTML=html;
}

async function analyzeSentiment() {
    if(!currentComments){ 
        document.getElementById('results').innerHTML='<div class="error">Fetch comments first</div>'; 
        return; 
    }
    const resDiv = document.getElementById('results');
    resDiv.innerHTML='<div class="loading">Analyzing...</div>';
    document.getElementById('sentimentBtn').disabled=true;
    try{
        const resp = await fetch(`${API_URL}/api/analyze`, {
            method:'POST',
            headers:{'Content-Type':'application/json'},
            body:JSON.stringify({comments:currentComments})
        });
        const data = await resp.json();
        if(resp.ok){
            displayStats(data.stats);
            displayAnalyzedComments(data.analyzed_comments);
            resDiv.innerHTML=`<div class="success">Complete. ${data.stats.toxic_count} toxic (${data.stats.toxic_percentage}%)</div>`;
        } else { 
            resDiv.innerHTML=`<div class="error">${data.error || 'Analysis failed'}</div>`; 
        }
    } catch(e){ 
        resDiv.innerHTML=`<div class="error">${e.message}</div>`; 
    }
    document.getElementById('sentimentBtn').disabled=false;
}

function displayStats(stats){
    const grid = document.getElementById('statsGrid');
    const prog = document.getElementById('toxicityProgress');
    grid.innerHTML=`<div class="stat-card"><div class="stat-value">${stats.total_comments}</div><div class="stat-label">Total</div></div><div class="stat-card"><div class="stat-value" style="color:#e94560">${stats.toxic_count}</div><div class="stat-label">Toxic</div></div><div class="stat-card"><div class="stat-value" style="color:#ffd600">${stats.moderate_count}</div><div class="stat-label">Moderate</div></div><div class="stat-card"><div class="stat-value" style="color:#00c853">${stats.safe_count}</div><div class="stat-label">Safe</div></div>`;
    prog.style.width=`${stats.toxic_percentage}%`;
    document.getElementById('statsSection').style.display='block';
}

function displayAnalyzedComments(comments){
    const container = document.getElementById('commentsList');
    if(!comments || !comments.length){ container.innerHTML='<p>No comments</p>'; return; }
    let html=`<h3>Analyzed Comments (${comments.length})</h3>`;
    comments.forEach(c=>{
        const level = c.toxicity.toxicity_level;
        const badge = level==='toxic'?'Toxic':(level==='moderate'?'Moderate':'Safe');
        const badgeClass = level==='toxic'?'badge-toxic':(level==='moderate'?'badge-moderate':'badge-safe');
        const reason = level!=='safe'?`<div style="font-size:0.7rem; color:#ffd600">Reason: ${escapeHtml(c.toxicity.reason)}</div>`:'';
        html+=`<div class="comment-card ${level}"><div class="comment-author">${escapeHtml(c.author)} <span class="toxicity-badge ${badgeClass}">${badge}</span></div><div class="comment-text">${escapeHtml(c.text)}</div>${reason}<div class="comment-meta">Likes: ${c.likes} • Score: ${(c.toxicity.toxic_score*100).toFixed(1)}%</div></div>`;
    });
    container.innerHTML=html;
}

async function startLive() {
    const url = document.getElementById('liveVideoUrl').value;
    const statusDiv = document.getElementById('liveStatus');
    if(!url){ statusDiv.innerHTML='<div class="error">Enter URL</div>'; return; }
    statusDiv.innerHTML='<div class="loading">Starting...</div>';
    const btn = event.target;
    btn.disabled=true;
    try{
        const resp = await fetch(`${API_URL}/api/live/start`, {
            method:'POST',
            headers:{'Content-Type':'application/json'},
            body:JSON.stringify({url})
        });
        const data = await resp.json();
        if(resp.ok){
            currentLiveVideoId = data.video_id;
            statusDiv.innerHTML=`<div class="success">Monitoring ${data.video_id}</div>`;
            document.getElementById('stopLiveBtn').disabled=false;
            document.getElementById('reportSection').style.display='block';
            if(liveInterval) clearInterval(liveInterval);
            liveInterval = setInterval(pollLive, 3000);
            startCharts();
        } else { 
            statusDiv.innerHTML=`<div class="error">${data.error || 'Failed to start'}</div>`; 
        }
    } catch(e){ 
        statusDiv.innerHTML=`<div class="error">${e.message}</div>`; 
    }
    btn.disabled=false;
}

async function pollLive() {
    if(!currentLiveVideoId) return;
    try{
        const resp = await fetch(`${API_URL}/api/live/status`, {
            method:'POST',
            headers:{'Content-Type':'application/json'},
            body:JSON.stringify({video_id:currentLiveVideoId})
        });
        const data = await resp.json();
        if(resp.ok && data.active) {
            updateLiveDisplay(data);
        } else if(resp.ok && !data.active) {
            stopLive();
        }
    } catch(e){ console.error(e); }
}

function updateLiveDisplay(data){
    const toxPct = (data.current_toxicity*100).toFixed(1);
    const velPct = (data.velocity_30*100).toFixed(1);
    const accPct = (data.acceleration*100).toFixed(1);
    document.getElementById('liveStats').innerHTML=`<div class="live-stat-card"><div class="live-stat-value">${data.comment_count}</div><div class="live-stat-label">Comments</div></div><div class="live-stat-card"><div class="live-stat-value">${toxPct}%</div><div class="live-stat-label">Toxicity</div></div><div class="live-stat-card"><div class="live-stat-value">${velPct}%</div><div class="live-stat-label">Velocity</div></div><div class="live-stat-card"><div class="live-stat-value">${accPct}%</div><div class="live-stat-label">Acceleration</div></div>`;
    document.getElementById('liveStatus').innerHTML=`<div class="success">Active • ${data.comment_count} comments</div>`;
    const alertDiv = document.getElementById('liveAlert');
    if(data.alert && data.alert.alert_triggered){
        alertDiv.style.display='block';
        alertDiv.className=`live-alert ${data.alert.alert_level}`;
        alertDiv.innerHTML=`<strong>Alert:</strong> ${data.alert.alert_message}<br><small>Toxicity: ${toxPct}% | Acceleration: ${accPct}%</small>`;
    } else {
        alertDiv.style.display='none';
    }
    if(data.attack_detection){
        const a = data.attack_detection;
        document.getElementById('attackSection').style.display='block';
        document.getElementById('attackSection').innerHTML=`<h4>Attack Detection</h4><div style="display:flex; gap:15px; flex-wrap:wrap"><div style="background:rgba(255,152,0,0.2); padding:8px 15px; border-radius:8px">Attack Score: <strong style="color:#ff9800">${(a.attack_score*100).toFixed(0)}%</strong></div><div style="background:rgba(255,152,0,0.2); padding:8px 15px; border-radius:8px">Type: ${a.attack_type || 'None'}</div></div><div style="margin-top:10px">Frequency: ${a.metrics.frequency_30s} msg/sec | Duplicate: ${(a.metrics.duplicate_ratio*100).toFixed(0)}%</div>${a.is_attack?`<div style="background:#e94560; padding:10px; margin-top:10px; border-radius:8px"><strong>Attack Detected!</strong> ${a.alert_message}</div>`:''}`;
    }
    fetchRecommendations();
    fetchPrediction();
}

async function fetchRecommendations(){
    if(!currentLiveVideoId) return;
    try{
        const resp = await fetch(`${API_URL}/api/recommendations`, {
            method:'POST',
            headers:{'Content-Type':'application/json'},
            body:JSON.stringify({video_id:currentLiveVideoId})
        });
        const data = await resp.json();
        if(resp.ok && data.recommendations && data.recommendations.length){
            document.getElementById('recommendationsSection').style.display='block';
            document.getElementById('recommendationsSection').innerHTML=`<h4>Recommendations</h4>${data.recommendations.map(r=>`<div style="border-left:3px solid ${r.priority==='critical'?'#e94560':(r.priority==='high'?'#ff9800':'#ffd600')}; padding:10px; margin-bottom:10px; background:rgba(255,255,255,0.03); border-radius:8px"><strong>${r.action}</strong><br>${r.description}<br><small style="color:#ffd600">${r.timeframe}</small></div>`).join('')}`;
        }
    } catch(e){ console.error(e); }
}

async function fetchPrediction(){
    if(!currentLiveVideoId) return;
    try{
        const resp = await fetch(`${API_URL}/api/live/alert`, {
            method:'POST',
            headers:{'Content-Type':'application/json'},
            body:JSON.stringify({video_id:currentLiveVideoId})
        });
        const data = await resp.json();
        if(resp.ok && data.prediction){
            const p = data.prediction;
            const predDiv = document.getElementById('alertPrediction');
            if(p.is_escalation_predicted){
                predDiv.innerHTML = `<div style="background:rgba(233,69,96,0.2); padding:10px; margin-top:15px; border-radius:8px; text-align:center"><strong style="color:#e94560">Escalation predicted in ${p.time_to_escalation_text}</strong><br>Confidence: ${(p.confidence*100).toFixed(0)}% | Score: ${(p.prediction_score*100).toFixed(0)}%</div>`;
            } else {
                predDiv.innerHTML = `<div style="background:rgba(0,200,83,0.2); padding:10px; margin-top:15px; border-radius:8px; text-align:center"><strong style="color:#00c853">No immediate escalation predicted</strong></div>`;
            }
        }
    } catch(e){ console.error(e); }
}

async function stopLive(){
    if(liveInterval) clearInterval(liveInterval);
    if(chartInterval) clearInterval(chartInterval);
    if(currentLiveVideoId){
        try{ 
            await fetch(`${API_URL}/api/live/stop`, {
                method:'POST',
                headers:{'Content-Type':'application/json'},
                body:JSON.stringify({video_id:currentLiveVideoId})
            }); 
        } catch(e){}
    }
    document.getElementById('liveStatus').innerHTML='<div class="success">Monitoring stopped</div>';
    document.getElementById('stopLiveBtn').disabled=true;
    document.getElementById('liveStats').innerHTML='';
    document.getElementById('liveAlert').style.display='none';
    document.getElementById('attackSection').style.display='none';
    document.getElementById('recommendationsSection').style.display='none';
    if(toxicityChart) toxicityChart.destroy();
    if(attackChart) attackChart.destroy();
    if(velocityChart) velocityChart.destroy();
    if(gaugeChart) gaugeChart.destroy();
    currentLiveVideoId=null;
}

async function updateCharts(){
    if(!currentLiveVideoId) return;
    try{
        const toxResp = await fetch(`${API_URL}/api/charts/toxicity`, {
            method:'POST',
            headers:{'Content-Type':'application/json'},
            body:JSON.stringify({video_id:currentLiveVideoId})
        });
        if(toxResp.ok){
            const toxData = await toxResp.json();
            if(toxicityChart) toxicityChart.destroy();
            const toxCtx = document.getElementById('toxicityChart').getContext('2d');
            toxicityChart = new Chart(toxCtx, {type:'line', data:toxData, options:{responsive:true, maintainAspectRatio:true, plugins:{legend:{labels:{color:'white'}}}}});
        }
        
        const attResp = await fetch(`${API_URL}/api/charts/attack`, {
            method:'POST',
            headers:{'Content-Type':'application/json'},
            body:JSON.stringify({video_id:currentLiveVideoId})
        });
        if(attResp.ok){
            const attData = await attResp.json();
            if(attackChart) attackChart.destroy();
            const attCtx = document.getElementById('attackChart').getContext('2d');
            attackChart = new Chart(attCtx, {type:'line', data:attData, options:{responsive:true, maintainAspectRatio:true, plugins:{legend:{labels:{color:'white'}}}}});
        }
        
        const velResp = await fetch(`${API_URL}/api/charts/velocity`, {
            method:'POST',
            headers:{'Content-Type':'application/json'},
            body:JSON.stringify({video_id:currentLiveVideoId})
        });
        if(velResp.ok){
            const velData = await velResp.json();
            if(velocityChart) velocityChart.destroy();
            const velCtx = document.getElementById('velocityChart').getContext('2d');
            velocityChart = new Chart(velCtx, {type:'bar', data:velData, options:{responsive:true, maintainAspectRatio:true, plugins:{legend:{labels:{color:'white'}}}}});
        }
        
        const gaugeResp = await fetch(`${API_URL}/api/charts/gauge`, {
            method:'POST',
            headers:{'Content-Type':'application/json'},
            body:JSON.stringify({video_id:currentLiveVideoId})
        });
        if(gaugeResp.ok){
            const gaugeData = await gaugeResp.json();
            if(gaugeChart) gaugeChart.destroy();
            const gaugeCtx = document.getElementById('gaugeChart').getContext('2d');
            gaugeChart = new Chart(gaugeCtx, {type:'doughnut', data:{labels:['Toxicity','Remaining'], datasets:[{data:[gaugeData.value, gaugeData.remaining], backgroundColor:['#e94560','#2a2a4a'], borderWidth:0}]}, options:{cutout:'70%', responsive:true, maintainAspectRatio:true, plugins:{legend:{labels:{color:'white'}}}}});
        }
    } catch(e){ console.error('Chart error:', e); }
}

function startCharts(){ 
    if(chartInterval) clearInterval(chartInterval); 
    chartInterval = setInterval(updateCharts, 5000); 
    updateCharts(); 
}

async function generateReport(){
    if(!currentLiveVideoId){ alert('Start monitoring first'); return; }
    const btn = document.getElementById('generateReportBtn');
    const cont = document.getElementById('reportContent');
    btn.disabled=true; 
    btn.textContent='Generating...';
    cont.innerHTML='<div class="loading">Generating report...</div>';
    try{
        const resp = await fetch(`${API_URL}/api/report/generate`, {
            method:'POST',
            headers:{'Content-Type':'application/json'},
            body:JSON.stringify({video_id:currentLiveVideoId})
        });
        const data = await resp.json();
        if(resp.ok){
            currentReportData = data;
            displayReport(data);
            document.getElementById('exportJSONBtn').disabled=false;
            document.getElementById('exportCSVBtn').disabled=false;
            document.getElementById('saveHistoryBtn').disabled=false;
        } else { 
            cont.innerHTML=`<div class="error">${data.error || 'Failed to generate'}</div>`; 
        }
    } catch(e){ 
        cont.innerHTML=`<div class="error">${e.message}</div>`; 
    }
    btn.disabled=false; 
    btn.textContent='Generate Report';
}

function displayReport(r){
    const cont = document.getElementById('reportContent');
    cont.innerHTML=`<div class="stats-grid"><div class="stat-card"><div class="stat-value">${r.toxicity_summary.current_toxicity}%</div><div class="stat-label">Current</div></div><div class="stat-card"><div class="stat-value">${r.toxicity_summary.peak_toxicity}%</div><div class="stat-label">Peak</div></div><div class="stat-card"><div class="stat-value">${r.toxicity_summary.average_toxicity}%</div><div class="stat-label">Avg</div></div><div class="stat-card"><div class="stat-value">${r.comments_analyzed}</div><div class="stat-label">Comments</div></div><div class="stat-card"><div class="stat-value">${r.duration_minutes}</div><div class="stat-label">Minutes</div></div><div class="stat-card"><div class="stat-value">${r.alert_summary.total_alerts||0}</div><div class="stat-label">Alerts</div></div></div><div class="stats-grid"><div class="stat-card"><div class="stat-value">${r.attack_summary.attack_count||0}</div><div class="stat-label">Attacks</div></div><div class="stat-card"><div class="stat-value">${r.attack_summary.peak_attack_score||0}%</div><div class="stat-label">Peak Attack</div></div><div class="stat-card"><div class="stat-value">${r.alert_summary.high_severity_count||0}</div><div class="stat-label">Critical Alerts</div></div></div><p><strong>Report ID:</strong> ${r.report_id}<br><strong>Generated:</strong> ${new Date(r.generated_at).toLocaleString()}</p>`;
}

async function exportReportJSON(){
    if(!currentReportData){ alert('Generate report first'); return; }
    const btn = document.getElementById('exportJSONBtn');
    btn.disabled = true;
    btn.textContent = 'Exporting...';
    try{
        const resp = await fetch(`${API_URL}/api/report/export/json`, {
            method:'POST',
            headers:{'Content-Type':'application/json'},
            body:JSON.stringify({video_id:currentLiveVideoId})
        });
        const data = await resp.json();
        if(resp.ok && data.success){
            const blob = new Blob([data.report_json], {type:'application/json'});
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `shrine_report_${currentLiveVideoId}_${Date.now()}.json`;
            a.click();
            URL.revokeObjectURL(url);
            alert('JSON exported successfully');
        } else {
            alert('Export failed: ' + (data.error || 'Unknown error'));
        }
    } catch(e){ 
        alert('Error: ' + e.message); 
    }
    btn.disabled = false;
    btn.textContent = 'Export JSON';
}

async function exportReportCSV(){
    if(!currentReportData){ alert('Generate report first'); return; }
    const btn = document.getElementById('exportCSVBtn');
    btn.disabled = true;
    btn.textContent = 'Exporting...';
    try{
        const resp = await fetch(`${API_URL}/api/report/export/csv`, {
            method:'POST',
            headers:{'Content-Type':'application/json'},
            body:JSON.stringify({video_id:currentLiveVideoId})
        });
        const data = await resp.json();
        if(resp.ok && data.success){
            const blob = new Blob([data.csv], {type:'text/csv'});
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `shrine_comments_${currentLiveVideoId}_${Date.now()}.csv`;
            a.click();
            URL.revokeObjectURL(url);
            alert('CSV exported successfully');
        } else {
            alert('Export failed: ' + (data.error || 'Unknown error'));
        }
    } catch(e){ 
        alert('Error: ' + e.message); 
    }
    btn.disabled = false;
    btn.textContent = 'Export CSV';
}

async function saveToHistory(){
    if(!currentReportData){ alert('Generate report first'); return; }
    const btn = document.getElementById('saveHistoryBtn');
    btn.disabled=true; 
    btn.textContent='Saving...';
    try{
        const resp = await fetch(`${API_URL}/api/history/save`, {
            method:'POST',
            headers:{'Content-Type':'application/json'},
            body:JSON.stringify({
                token: token, 
                video_id: currentLiveVideoId, 
                video_title: currentReportData.video_title || 'Unknown', 
                report: currentReportData
            })
        });
        const data = await resp.json();
        if(resp.ok) {
            alert('Saved to history!');
        } else {
            alert('Save failed: ' + (data.error || 'Unknown error'));
        }
    } catch(e){ 
        alert('Error: ' + e.message); 
    }
    btn.disabled=false; 
    btn.textContent='Save to History';
}

async function loadHistory(){
    const container = document.getElementById('historyList');
    container.innerHTML='<div class="loading">Loading...</div>';
    try{
        const resp = await fetch(`${API_URL}/api/history/get`, {
            method:'POST',
            headers:{'Content-Type':'application/json'},
            body:JSON.stringify({token})
        });
        const data = await resp.json();
        if(resp.ok && data.history && data.history.length){
            historyData = data.history;
            container.innerHTML = data.history.slice().reverse().map((item,idx)=>`
                <div class="history-card">
                    <div class="history-header">
                        <span class="history-title">${escapeHtml(item.video_title)}</span>
                        <span class="history-date">${new Date(item.timestamp).toLocaleString()}</span>
                    </div>
                    <div class="history-stats">
                        <span>Toxicity: ${item.report.toxicity_summary?.current_toxicity||0}%</span>
                        <span>Comments: ${item.report.comments_analyzed||0}</span>
                        <span>Alerts: ${item.report.alert_summary?.total_alerts||0}</span>
                    </div>
                    <button class="history-btn" onclick="viewHistoryReport(${data.history.length-1-idx})">View Report</button>
                </div>
            `).join('');
        } else {
            container.innerHTML='<p>No history yet. Start monitoring and save reports.</p>';
        }
    } catch(e){ 
        container.innerHTML='<div class="error">Failed to load history</div>'; 
    }
}

function viewHistoryReport(index){
    if(!historyData || !historyData[index]) return;
    const item = historyData[index];
    const r = item.report;
    const modal = document.createElement('div');
    modal.className='modal';
    modal.innerHTML=`
        <div class="modal-content">
            <div class="modal-header">
                <h3 style="color:#e94560">Report Details</h3>
                <button class="close-modal" onclick="this.closest('.modal').remove()">X</button>
            </div>
            <div><strong>Video:</strong> ${escapeHtml(item.video_title)}</div>
            <div><strong>Date:</strong> ${new Date(item.timestamp).toLocaleString()}</div>
            <div><strong>Video ID:</strong> ${item.video_id}</div>
            <hr style="margin:15px 0; border-color:rgba(255,255,255,0.1)">
            <h4>Toxicity Summary</h4>
            <div class="stats-grid" style="margin-top:10px">
                <div class="stat-card"><div class="stat-value">${r.toxicity_summary.current_toxicity}%</div><div class="stat-label">Current</div></div>
                <div class="stat-card"><div class="stat-value">${r.toxicity_summary.peak_toxicity}%</div><div class="stat-label">Peak</div></div>
                <div class="stat-card"><div class="stat-value">${r.toxicity_summary.average_toxicity}%</div><div class="stat-label">Average</div></div>
            </div>
            <h4>Alert Summary</h4>
            <div class="stats-grid" style="margin-top:10px">
                <div class="stat-card"><div class="stat-value">${r.alert_summary.total_alerts||0}</div><div class="stat-label">Total Alerts</div></div>
                <div class="stat-card"><div class="stat-value">${r.alert_summary.high_severity_count||0}</div><div class="stat-label">Critical</div></div>
            </div>
            <hr>
            <p><strong>Report ID:</strong> ${r.report_id}</p>
        </div>
    `;
    document.body.appendChild(modal);
}

function initButtons(){
    const gen = document.getElementById('generateReportBtn');
    if(gen) gen.onclick = generateReport;
    const jbtn = document.getElementById('exportJSONBtn');
    if(jbtn) jbtn.onclick = exportReportJSON;
    const cbtn = document.getElementById('exportCSVBtn');
    if(cbtn) cbtn.onclick = exportReportCSV;
    const sbtn = document.getElementById('saveHistoryBtn');
    if(sbtn) sbtn.onclick = saveToHistory;
}
document.addEventListener('DOMContentLoaded', initButtons);