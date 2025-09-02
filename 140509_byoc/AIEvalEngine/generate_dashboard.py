#!/usr/bin/env python3
"""
Static HTML Dashboard Generator
Creates a self-contained HTML file with real-time leaderboard
"""

import sqlite3
import json
from datetime import datetime
from dashboard_data import get_dashboard_data

def generate_static_dashboard():
    """Generate a static HTML dashboard with embedded data"""
    
    # Get current data
    data = get_dashboard_data()
    
    html_template = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI Jury Evaluation Leaderboard</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: 'SF Pro Display', -apple-system, BlinkMacSystemFont, sans-serif;
            background: linear-gradient(135deg, #0f0f23 0%, #1a1a3a 100%);
            color: #e6e6e6;
            min-height: 100vh;
            padding: 20px;
        }}
        
        .header {{
            text-align: center;
            margin-bottom: 30px;
            padding: 20px;
            background: rgba(255, 255, 255, 0.05);
            border-radius: 15px;
            backdrop-filter: blur(10px);
        }}
        
        .header h1 {{
            font-size: 2.5em;
            background: linear-gradient(45deg, #64ffda, #00bcd4);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 10px;
        }}
        
        .stats {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }}
        
        .stat-card {{
            background: rgba(255, 255, 255, 0.08);
            padding: 20px;
            border-radius: 12px;
            text-align: center;
            border: 1px solid rgba(255, 255, 255, 0.1);
        }}
        
        .stat-number {{
            font-size: 2em;
            font-weight: bold;
            color: #64ffda;
        }}
        
        .stat-label {{
            opacity: 0.8;
            margin-top: 5px;
        }}
        
        .progress-bar {{
            width: 100%;
            height: 20px;
            background: rgba(255, 255, 255, 0.1);
            border-radius: 10px;
            overflow: hidden;
            margin: 10px 0;
        }}
        
        .progress-fill {{
            height: 100%;
            background: linear-gradient(90deg, #64ffda, #00bcd4);
            transition: width 0.5s ease;
        }}
        
        .leaderboard {{
            background: rgba(255, 255, 255, 0.05);
            border-radius: 15px;
            overflow: hidden;
            backdrop-filter: blur(10px);
        }}
        
        .leaderboard-header {{
            background: rgba(100, 255, 218, 0.1);
            padding: 20px;
            font-weight: bold;
            font-size: 1.1em;
            display: grid;
            grid-template-columns: 60px 150px 100px 100px 80px 1fr;
            gap: 15px;
        }}
        
        .project-row {{
            display: grid;
            grid-template-columns: 60px 150px 100px 100px 80px 1fr;
            gap: 15px;
            padding: 15px 20px;
            border-bottom: 1px solid rgba(255, 255, 255, 0.1);
            align-items: center;
            transition: background 0.3s ease;
        }}
        
        .project-row:hover {{
            background: rgba(255, 255, 255, 0.05);
        }}
        
        .rank {{
            font-size: 1.5em;
            font-weight: bold;
            text-align: center;
        }}
        
        .rank.gold {{ color: #ffd700; }}
        .rank.silver {{ color: #c0c0c0; }}
        .rank.bronze {{ color: #cd7f32; }}
        
        .project-name {{
            font-weight: 600;
            color: #64ffda;
        }}
        
        .score {{
            font-weight: bold;
            font-size: 1.1em;
        }}
        
        .percentage {{
            color: #64ffda;
        }}
        
        .grade {{
            padding: 5px 10px;
            border-radius: 20px;
            font-weight: bold;
            text-align: center;
        }}
        
        .grade.A-plus {{ background: #4caf50; }}
        .grade.A {{ background: #66bb6a; }}
        .grade.A-minus {{ background: #8bc34a; }}
        .grade.B-plus {{ background: #ffc107; color: #000; }}
        .grade.B {{ background: #ff9800; color: #000; }}
        .grade.B-minus {{ background: #ff5722; }}
        
        .feedback {{
            font-size: 0.9em;
            opacity: 0.9;
            line-height: 1.4;
        }}
        
        .feedback strong {{
            color: #64ffda;
        }}
        
        .doc-type {{
            font-size: 0.8em;
            color: #00bcd4;
            font-style: italic;
        }}
        
        .evaluating {{
            background: rgba(255, 193, 7, 0.1);
            border-left: 4px solid #ffc107;
        }}
        
        @keyframes pulse {{
            0%, 100% {{ opacity: 0.6; }}
            50% {{ opacity: 1; }}
        }}
        
        .evaluating .project-name {{
            animation: pulse 2s infinite;
        }}
        
        .update-time {{
            text-align: center;
            opacity: 0.6;
            margin-top: 20px;
            font-size: 0.9em;
        }}
        
        .auto-refresh {{
            position: fixed;
            top: 20px;
            right: 20px;
            background: rgba(100, 255, 218, 0.1);
            padding: 10px 15px;
            border-radius: 20px;
            font-size: 0.9em;
            border: 1px solid rgba(100, 255, 218, 0.3);
        }}
    </style>
    <script>
        // Auto-refresh every 30 seconds
        setTimeout(function() {{
            window.location.reload();
        }}, 30000);
        
        // Countdown timer
        let countdown = 30;
        setInterval(function() {{
            countdown--;
            if (countdown <= 0) countdown = 30;
            document.getElementById('refresh-countdown').textContent = countdown;
        }}, 1000);
    </script>
</head>
<body>
    <div class="auto-refresh">
        🔄 Auto-refresh in <span id="refresh-countdown">30</span>s
    </div>
    
    <div class="header">
        <h1>🎯 AI Jury Evaluation Leaderboard</h1>
        <p>Real-time multi-round evaluation results with detailed feedback analysis</p>
        <p><em>Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</em></p>
    </div>
    
    <div class="stats">
        <div class="stat-card">
            <div class="stat-number">{data['completed']}</div>
            <div class="stat-label">Projects Completed</div>
        </div>
        <div class="stat-card">
            <div class="stat-number">{(data['completed'] / data['total'] * 100):.1f}%</div>
            <div class="stat-label">Overall Progress</div>
            <div class="progress-bar">
                <div class="progress-fill" style="width: {(data['completed'] / data['total'] * 100):.1f}%"></div>
            </div>
        </div>
        <div class="stat-card">
            <div class="stat-number">{data['avgScore']:.1f}</div>
            <div class="stat-label">Average Score</div>
        </div>
        <div class="stat-card">
            <div class="stat-number">{data.get('completedRounds', 0)}</div>
            <div class="stat-label">Rounds Completed</div>
        </div>
    </div>
    
    <div class="leaderboard">
        <div class="leaderboard-header">
            <div><strong>Rank</strong></div>
            <div><strong>Project</strong></div>
            <div><strong>Score</strong></div>
            <div><strong>Percentage</strong></div>
            <div><strong>Grade</strong></div>
            <div><strong>Analysis & Feedback</strong></div>
        </div>
"""
    
    # Add project rows
    for i, project in enumerate(data['projects']):
        rank = i + 1
        rank_icon = '🥇' if rank == 1 else '🥈' if rank == 2 else '🥉' if rank == 3 else str(rank)
        rank_class = 'gold' if rank == 1 else 'silver' if rank == 2 else 'bronze' if rank == 3 else ''
        
        is_evaluating = project.get('evaluating', False)
        row_class = 'evaluating' if is_evaluating else ''
        
        score_display = f"{project['score']:.1f}" if project['score'] is not None else '--'
        percentage_display = f"{project['percentage']:.1f}%" if project['percentage'] is not None else '--'
        grade_display = project['grade'] or '⏳'
        grade_class = project['grade'].replace('+', '-plus').replace('-', '-minus') if project['grade'] else 'evaluating'
        
        html_template += f"""
        <div class="project-row {row_class}">
            <div class="rank {rank_class}">{rank_icon}</div>
            <div>
                <div class="project-name">{project['name']}</div>
                <div class="doc-type">{project['docType']}</div>
            </div>
            <div class="score">{score_display}/220</div>
            <div class="percentage">{percentage_display}</div>
            <div class="grade {grade_class}">{grade_display}</div>
            <div class="feedback">{project['feedback']}</div>
        </div>"""
    
    html_template += f"""
    </div>
    
    <div class="update-time">
        Last updated: {datetime.now().strftime('%H:%M:%S')} | Status: {data.get('status', 'unknown').title()} | 
        Evaluating: {', '.join(data.get('evaluating', [])) if data.get('evaluating') else 'None'}
    </div>
</body>
</html>"""
    
    return html_template

if __name__ == "__main__":
    html = generate_static_dashboard()
    with open('leaderboard.html', 'w') as f:
        f.write(html)
    print("📊 Static dashboard generated: leaderboard.html")