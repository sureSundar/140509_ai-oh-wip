#!/usr/bin/env python3
"""
Real-time Dashboard with Server-Sent Events (SSE)
Pushes live updates to browser without refresh
"""

import sqlite3
import json
import threading
import time
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
import os

class SSEHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/':
            self.serve_dashboard()
        elif self.path == '/events':
            self.serve_events()
        else:
            self.send_error(404)
    
    def serve_dashboard(self):
        """Serve the main dashboard HTML with SSE integration"""
        html = """<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>🎯 Live AI Jury Leaderboard</title>
    <style>
        body { font-family: 'Segoe UI', sans-serif; background: linear-gradient(135deg, #1a1a2e, #16213e); color: #eee; margin: 0; padding: 20px; }
        .header { text-align: center; margin-bottom: 30px; padding: 25px; background: rgba(0, 212, 255, 0.1); border-radius: 15px; }
        .header h1 { color: #00d4ff; margin-bottom: 15px; font-size: 2.5em; }
        .stats { display: grid; grid-template-columns: repeat(4, 1fr); gap: 20px; margin-bottom: 30px; }
        .stat { text-align: center; padding: 20px; background: rgba(0, 212, 255, 0.1); border-radius: 12px; }
        .stat-number { font-size: 2.2em; color: #00d4ff; font-weight: bold; }
        .leaderboard { background: rgba(255, 255, 255, 0.05); border-radius: 15px; overflow: hidden; }
        .row { display: grid; grid-template-columns: 60px 130px 90px 70px 80px 1fr; gap: 10px; padding: 12px 15px; border-bottom: 1px solid rgba(255, 255, 255, 0.1); align-items: center; }
        .header-row { background: rgba(0, 212, 255, 0.15); font-weight: bold; }
        .rank { text-align: center; font-weight: bold; font-size: 1.2em; }
        .gold { color: #ffd700; }
        .silver { color: #c0c0c0; }
        .bronze { color: #cd7f32; }
        .project { color: #00d4ff; font-weight: 600; }
        .score { font-weight: bold; color: #64ffda; }
        .grade { padding: 4px 8px; border-radius: 12px; text-align: center; font-weight: bold; font-size: 0.85em; }
        .A-plus { background: #4caf50; }
        .A-minus { background: #8bc34a; }
        .B-plus { background: #ffc107; color: #000; }
        .B { background: #ff9800; color: #000; }
        .B-minus { background: #ff5722; }
        .F { background: #f44336; }
        .feedback { font-size: 0.8em; line-height: 1.2; }
        .feedback strong { color: #64ffda; }
        .evaluating { background: rgba(255, 193, 7, 0.08); animation: pulse 2s infinite; }
        @keyframes pulse { 0%, 100% { opacity: 0.8; } 50% { opacity: 1; } }
        .status { position: fixed; top: 20px; right: 20px; background: #00d4aa; color: #000; padding: 8px 15px; border-radius: 20px; font-weight: bold; }
        .update-info { text-align: center; margin-top: 20px; opacity: 0.7; }
    </style>
</head>
<body>
    <div class="status" id="status">🔄 LIVE</div>
    
    <div class="header">
        <h1>🎯 AI Jury Evaluation Leaderboard</h1>
        <p>📊 Real-time server-pushed updates with detailed analysis</p>
    </div>
    
    <div class="stats">
        <div class="stat">
            <div class="stat-number" id="completed">--</div>
            <div>Completed</div>
        </div>
        <div class="stat">
            <div class="stat-number" id="progress">--%</div>
            <div>Progress</div>
        </div>
        <div class="stat">
            <div class="stat-number" id="avgScore">--</div>
            <div>Avg Score</div>
        </div>
        <div class="stat">
            <div class="stat-number" id="evaluating">--</div>
            <div>Evaluating</div>
        </div>
    </div>
    
    <div class="leaderboard">
        <div class="row header-row">
            <div><strong>🏆</strong></div>
            <div><strong>Project</strong></div>
            <div><strong>Score</strong></div>
            <div><strong>%</strong></div>
            <div><strong>Grade</strong></div>
            <div><strong>Analysis</strong></div>
        </div>
        <div id="leaderboard-content">
            <div style="text-align: center; padding: 40px;">🤖 Loading live data...</div>
        </div>
    </div>
    
    <div class="update-info" id="updateInfo">
        📡 Connecting to live updates...
    </div>

    <script>
        let lastUpdate = 0;
        
        function connectSSE() {
            const eventSource = new EventSource('/events');
            
            eventSource.onmessage = function(event) {
                try {
                    const data = JSON.parse(event.data);
                    updateDashboard(data);
                    document.getElementById('status').textContent = '🟢 LIVE';
                    document.getElementById('status').style.background = '#00d4aa';
                } catch (e) {
                    console.error('Error parsing SSE data:', e);
                }
            };
            
            eventSource.onerror = function(event) {
                document.getElementById('status').textContent = '🔴 DISCONNECTED';
                document.getElementById('status').style.background = '#f44336';
                console.error('SSE connection error');
                
                // Reconnect after 5 seconds
                setTimeout(() => {
                    eventSource.close();
                    connectSSE();
                }, 5000);
            };
            
            return eventSource;
        }
        
        function updateDashboard(data) {
            // Update stats
            document.getElementById('completed').textContent = data.completed || 0;
            document.getElementById('progress').textContent = `${((data.completed / data.total) * 100).toFixed(1)}%`;
            document.getElementById('avgScore').textContent = data.avgScore ? data.avgScore.toFixed(1) : '0.0';
            document.getElementById('evaluating').textContent = data.evaluating ? data.evaluating.length : 0;
            
            // Update leaderboard
            const content = document.getElementById('leaderboard-content');
            
            if (!data.projects || data.projects.length === 0) {
                content.innerHTML = '<div style="text-align: center; padding: 40px;">🤖 No results yet...</div>';
                return;
            }
            
            content.innerHTML = data.projects.map((project, index) => {
                const rank = index + 1;
                const rankIcon = rank === 1 ? '🥇' : rank === 2 ? '🥈' : rank === 3 ? '🥉' : `#${rank}`;
                const rankClass = rank === 1 ? 'gold' : rank === 2 ? 'silver' : rank === 3 ? 'bronze' : '';
                
                const isEvaluating = project.score === null;
                const rowClass = isEvaluating ? 'evaluating' : '';
                
                const score = project.score ? project.score.toFixed(1) : '--';
                const percentage = project.percentage ? project.percentage.toFixed(1) : '--';
                const grade = project.grade || '⏳';
                const gradeClass = project.grade ? project.grade.replace('+', '-plus').replace('-', '-minus') : '';
                
                return `
                    <div class="row ${rowClass}">
                        <div class="rank ${rankClass}">${rankIcon}</div>
                        <div class="project">${project.name}</div>
                        <div class="score">${score}/220</div>
                        <div>${percentage}%</div>
                        <div class="grade ${gradeClass}">${grade}</div>
                        <div class="feedback">${project.feedback || ''}</div>
                    </div>
                `;
            }).join('');
            
            // Update info
            document.getElementById('updateInfo').textContent = 
                `📡 Last push: ${new Date().toLocaleTimeString()} | 🎯 ${data.completed}/${data.total} projects`;
        }
        
        // Connect to SSE stream
        connectSSE();
    </script>
</body>
</html>"""
        
        self.send_response(200)
        self.send_header('Content-Type', 'text/html')
        self.end_headers()
        self.wfile.write(html.encode())
    
    def serve_events(self):
        """Serve Server-Sent Events stream"""
        self.send_response(200)
        self.send_header('Content-Type', 'text/event-stream')
        self.send_header('Cache-Control', 'no-cache')
        self.send_header('Connection', 'keep-alive')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        
        # Keep connection alive and send updates
        last_data = None
        
        try:
            while True:
                data = get_evaluation_data()
                
                # Only send if data changed
                if data != last_data:
                    event_data = f"data: {json.dumps(data)}\n\n"
                    self.wfile.write(event_data.encode())
                    self.wfile.flush()
                    last_data = data
                
                time.sleep(5)  # Check for updates every 5 seconds
                
        except (BrokenPipeError, ConnectionResetError):
            # Client disconnected
            pass

def get_evaluation_data():
    """Get current evaluation data from database"""
    try:
        conn = sqlite3.connect("aieval_results.db")
        cursor = conn.cursor()
        
        # Get completed evaluations
        cursor.execute("""
            SELECT project_name, final_score, final_grade, created_at
            FROM multiround_evaluations
            WHERE final_score IS NOT NULL
            ORDER BY final_score DESC
        """)
        
        completed = cursor.fetchall()
        
        # Get evaluating projects
        cursor.execute("""
            SELECT project_name, created_at
            FROM multiround_evaluations
            WHERE final_score IS NULL
            ORDER BY created_at ASC
        """)
        
        evaluating = cursor.fetchall()
        
        # Build project list
        projects = []
        total_score = 0
        
        # Add completed projects
        for project_name, score, grade, created_at in completed:
            score_val = float(score)
            percentage = (score_val / 220) * 100
            
            # Generate feedback based on score
            if percentage >= 70:
                feedback = "<strong>Strengths:</strong> Excellent documentation, comprehensive coverage. <strong>Weaknesses:</strong> Minor improvements possible."
            elif percentage >= 60:
                feedback = "<strong>Strengths:</strong> Good structure and content. <strong>Weaknesses:</strong> Some areas need more detail."
            elif percentage >= 40:
                feedback = "<strong>Strengths:</strong> Basic requirements met. <strong>Weaknesses:</strong> Significant improvements needed."
            else:
                feedback = "<strong>Strengths:</strong> Project submitted. <strong>Weaknesses:</strong> Major overhaul required across all criteria."
            
            projects.append({
                'name': project_name,
                'score': score_val,
                'percentage': percentage,
                'grade': grade,
                'feedback': feedback
            })
            total_score += score_val
        
        # Add evaluating projects
        for project_name, created_at in evaluating:
            eval_start = datetime.fromisoformat(created_at)
            duration = datetime.now() - eval_start
            duration_str = f"{duration.seconds // 60}m {duration.seconds % 60}s"
            
            projects.append({
                'name': project_name,
                'score': None,
                'percentage': None,
                'grade': None,
                'feedback': f'🤖 Evaluating for {duration_str}...'
            })
        
        avg_score = total_score / len(completed) if completed else 0
        
        conn.close()
        
        return {
            'completed': len(completed),
            'total': 51,
            'avgScore': avg_score,
            'projects': projects,
            'evaluating': [p[0] for p in evaluating],
            'timestamp': datetime.now().isoformat()
        }
        
    except Exception as e:
        return {'error': str(e), 'completed': 0, 'total': 51, 'projects': []}

def start_realtime_server(port=8083):
    """Start real-time SSE dashboard server"""
    server_address = ('', port)
    httpd = HTTPServer(server_address, SSEHandler)
    
    print(f"🚀 Real-time Dashboard Server started!")
    print(f"🌐 Access at: http://localhost:{port}")
    print("📡 Server-Sent Events for real-time updates")
    print("Press Ctrl+C to stop")
    
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n🛑 Real-time server stopped")
        httpd.shutdown()

if __name__ == "__main__":
    start_realtime_server()