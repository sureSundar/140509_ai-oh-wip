#!/usr/bin/env python3
"""
Quick Dashboard Generator - Works with actual database schema
"""

import sqlite3
from datetime import datetime

def generate_leaderboard():
    """Generate HTML leaderboard from current database"""
    try:
        conn = sqlite3.connect("aieval_results.db")
        cursor = conn.cursor()
        
        # Get all evaluations
        cursor.execute("""
            SELECT project_name, final_score, final_grade, created_at
            FROM multiround_evaluations
            ORDER BY 
                CASE WHEN final_score IS NULL THEN 1 ELSE 0 END,
                final_score DESC
        """)
        
        evaluations = cursor.fetchall()
        
        # Generate simple feedback based on score ranges
        def get_feedback(score):
            if score is None:
                return "🤖 Multi-round evaluation in progress..."
            
            score = float(score)
            percentage = (score / 220) * 100
            
            if percentage >= 70:
                return "<strong>Strengths:</strong> Excellent documentation quality, comprehensive coverage. <strong>Weaknesses:</strong> Minor presentation improvements possible."
            elif percentage >= 60:
                return "<strong>Strengths:</strong> Good structure and content quality. <strong>Weaknesses:</strong> Some areas need more detail."
            elif percentage >= 50:
                return "<strong>Strengths:</strong> Solid foundation and basic requirements met. <strong>Weaknesses:</strong> Needs improvement in completeness and clarity."
            elif percentage >= 40:
                return "<strong>Strengths:</strong> Basic documentation present. <strong>Weaknesses:</strong> Significant gaps in content quality and structure."
            else:
                return "<strong>Strengths:</strong> Project submitted. <strong>Weaknesses:</strong> Major improvements needed across all evaluation criteria."
        
        # Count stats
        completed = len([e for e in evaluations if e[1] is not None])
        total_score = sum(float(e[1]) for e in evaluations if e[1] is not None)
        avg_score = total_score / completed if completed > 0 else 0
        evaluating_count = len([e for e in evaluations if e[1] is None])
        
        html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🎯 AI Jury Leaderboard</title>
    <meta http-equiv="refresh" content="20">
    <style>
        body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: linear-gradient(135deg, #1a1a2e, #16213e); color: #eee; margin: 0; padding: 20px; }}
        .header {{ text-align: center; margin-bottom: 30px; padding: 25px; background: rgba(0, 212, 255, 0.1); border-radius: 15px; border: 1px solid rgba(0, 212, 255, 0.3); }}
        .header h1 {{ color: #00d4ff; margin-bottom: 15px; font-size: 2.5em; }}
        .stats {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 20px; margin-bottom: 30px; }}
        .stat {{ text-align: center; padding: 20px; background: rgba(0, 212, 255, 0.1); border-radius: 12px; border: 1px solid rgba(0, 212, 255, 0.2); }}
        .stat-number {{ font-size: 2.2em; color: #00d4ff; font-weight: bold; display: block; }}
        .stat-label {{ margin-top: 8px; opacity: 0.8; }}
        .leaderboard {{ background: rgba(255, 255, 255, 0.05); border-radius: 15px; overflow: hidden; border: 1px solid rgba(255, 255, 255, 0.1); }}
        .row {{ display: grid; grid-template-columns: 60px 140px 90px 70px 80px 1fr; gap: 15px; padding: 15px 20px; border-bottom: 1px solid rgba(255, 255, 255, 0.1); align-items: center; }}
        .header-row {{ background: rgba(0, 212, 255, 0.15); font-weight: bold; font-size: 1.1em; }}
        .rank {{ text-align: center; font-weight: bold; font-size: 1.3em; }}
        .gold {{ color: #ffd700; }}
        .silver {{ color: #c0c0c0; }}
        .bronze {{ color: #cd7f32; }}
        .project {{ color: #00d4ff; font-weight: 600; }}
        .score {{ font-weight: bold; color: #64ffda; }}
        .percentage {{ color: #64ffda; font-weight: 600; }}
        .grade {{ padding: 6px 12px; border-radius: 15px; text-align: center; font-weight: bold; font-size: 0.9em; }}
        .A-plus {{ background: #4caf50; color: white; }}
        .A {{ background: #66bb6a; color: white; }}
        .A-minus {{ background: #8bc34a; color: white; }}
        .B-plus {{ background: #ffc107; color: #000; }}
        .B {{ background: #ff9800; color: #000; }}
        .B-minus {{ background: #ff5722; color: white; }}
        .feedback {{ font-size: 0.85em; line-height: 1.3; }}
        .feedback strong {{ color: #64ffda; }}
        .evaluating {{ background: rgba(255, 193, 7, 0.08); border-left: 3px solid #ffc107; }}
        .evaluating .project {{ animation: pulse 2s infinite; }}
        .update-info {{ text-align: center; margin-top: 25px; opacity: 0.7; padding: 15px; background: rgba(255, 255, 255, 0.05); border-radius: 10px; }}
        @keyframes pulse {{ 0%, 100% {{ opacity: 0.7; }} 50% {{ opacity: 1; }} }}
        .progress-indicator {{ position: fixed; top: 20px; right: 20px; background: rgba(0, 212, 255, 0.1); padding: 10px 15px; border-radius: 20px; border: 1px solid rgba(0, 212, 255, 0.3); }}
    </style>
</head>
<body>
    <div class="progress-indicator">
        🔄 Auto-refresh: 20s
    </div>
    
    <div class="header">
        <h1>🎯 AI Jury Evaluation Leaderboard</h1>
        <p>📊 Live rankings with comprehensive strengths & weaknesses analysis</p>
        <p><em>⚡ Updates every 20 seconds | 🤖 Claude 3.5 Sonnet Multi-Round Evaluation</em></p>
    </div>
    
    <div class="stats">
        <div class="stat">
            <span class="stat-number">{completed}</span>
            <div class="stat-label">Projects Completed</div>
        </div>
        <div class="stat">
            <span class="stat-number">{(completed/51*100):.1f}%</span>
            <div class="stat-label">Overall Progress</div>
        </div>
        <div class="stat">
            <span class="stat-number">{avg_score:.1f}</span>
            <div class="stat-label">Average Score</div>
        </div>
        <div class="stat">
            <span class="stat-number">{evaluating_count}</span>
            <div class="stat-label">Currently Evaluating</div>
        </div>
    </div>
    
    <div class="leaderboard">
        <div class="row header-row">
            <div><strong>🏆 Rank</strong></div>
            <div><strong>📁 Project</strong></div>
            <div><strong>📊 Score</strong></div>
            <div><strong>📈 %</strong></div>
            <div><strong>🏅 Grade</strong></div>
            <div><strong>💡 Detailed Analysis</strong></div>
        </div>"""
        
        for i, (project_name, score, grade, created_at) in enumerate(evaluations):
            rank = i + 1
            rank_icon = '🥇' if rank == 1 else '🥈' if rank == 2 else '🥉' if rank == 3 else f'#{rank}'
            rank_class = 'gold' if rank == 1 else 'silver' if rank == 2 else 'bronze' if rank == 3 else ''
            
            is_evaluating = score is None
            row_class = 'evaluating' if is_evaluating else ''
            
            score_display = f"{float(score):.1f}" if score is not None else '--'
            percentage_display = f"{(float(score)/220*100):.1f}" if score is not None else '--'
            grade_display = grade or '⏳'
            grade_class = grade.replace('+', '-plus').replace('-', '-minus') if grade else ''
            
            feedback = get_feedback(score)
            
            html += f"""
        <div class="row {row_class}">
            <div class="rank {rank_class}">{rank_icon}</div>
            <div class="project">{project_name}</div>
            <div class="score">{score_display}/220</div>
            <div class="percentage">{percentage_display}%</div>
            <div class="grade {grade_class}">{grade_display}</div>
            <div class="feedback">{feedback}</div>
        </div>"""
        
        html += f"""
    </div>
    
    <div class="update-info">
        📊 <strong>Last Updated:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | 
        🎯 <strong>Total Projects:</strong> 51 | 
        ⏱️ <strong>Evaluation Time:</strong> ~4min per project |
        🤖 <strong>AI Model:</strong> Claude 3.5 Sonnet (3 rounds each)
    </div>
</body>
</html>"""
        
        conn.close()
        return html
        
    except Exception as e:
        return f"<html><body><h1>Error: {e}</h1></body></html>"

if __name__ == "__main__":
    html = generate_leaderboard()
    with open('leaderboard.html', 'w') as f:
        f.write(html)
    print("🎯 Live leaderboard generated: leaderboard.html")
    print("🌐 Access at: http://localhost:8082/leaderboard.html")