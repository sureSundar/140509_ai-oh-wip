#!/usr/bin/env python3
"""
Simple Auto-Updating HTML Dashboard Generator
Creates leaderboard with real evaluation data from database
"""

import sqlite3
import json
from datetime import datetime

def get_simple_data():
    """Get evaluation data with simplified queries"""
    db_path = "aieval_results.db"
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Get all evaluations (completed and in progress)
        cursor.execute("""
            SELECT 
                project_name,
                final_score,
                final_grade,
                created_at
            FROM multiround_evaluations
            ORDER BY 
                CASE WHEN final_score IS NULL THEN 1 ELSE 0 END,
                final_score DESC
        """)
        
        all_evaluations = cursor.fetchall()
        
        # Get category scores for feedback analysis
        projects = []
        total_score = 0
        completed_count = 0
        
        for project_name, final_score, final_grade, created_at in all_evaluations:
            is_completed = final_score is not None
            
            if is_completed:
                # Get category performance for feedback
                cursor.execute("""
                    SELECT 
                        cs.category,
                        cs.subcategory,
                        AVG(cs.score) as avg_score,
                        cs.weight
                    FROM category_scores cs
                    JOIN evaluation_rounds er ON cs.round_id = er.id
                    JOIN multiround_evaluations me ON er.evaluation_id = me.id
                    WHERE me.project_name = ?
                    GROUP BY cs.category, cs.subcategory, cs.weight
                    ORDER BY avg_score DESC
                """, (project_name,))
                
                categories = cursor.fetchall()
                
                # Analyze performance
                strengths = []
                weaknesses = []
                
                for cat, subcat, score, weight in categories:
                    if weight > 0:
                        score_pct = (score / weight) * 100
                        cat_name = cat.replace('_', ' ').title()
                        if subcat:
                            cat_name = f"{cat_name}/{subcat.replace('_', ' ').title()}"
                        
                        if score_pct >= 85:
                            strengths.append(f"Excellent {cat_name}")
                        elif score_pct >= 75:
                            strengths.append(f"Strong {cat_name}")
                        elif score_pct <= 40:
                            weaknesses.append(f"Weak {cat_name}")
                        elif score_pct <= 60:
                            weaknesses.append(f"Needs improvement in {cat_name}")
                
                # Build feedback
                feedback_parts = []
                if strengths:
                    feedback_parts.append(f"<strong>Strengths:</strong> {', '.join(strengths[:3])}")
                if weaknesses:
                    feedback_parts.append(f"<strong>Weaknesses:</strong> {', '.join(weaknesses[:3])}")
                
                feedback = ". ".join(feedback_parts) if feedback_parts else "Balanced performance across categories"
                
                projects.append({
                    'name': project_name,
                    'score': float(final_score),
                    'percentage': (float(final_score) / 220 * 100),
                    'grade': final_grade,
                    'feedback': feedback,
                    'completed': True
                })
                
                total_score += float(final_score)
                completed_count += 1
            else:
                # In progress
                projects.append({
                    'name': project_name,
                    'score': None,
                    'percentage': None,
                    'grade': None,
                    'feedback': '🤖 Multi-round evaluation in progress...',
                    'completed': False
                })
        
        conn.close()
        
        avg_score = total_score / completed_count if completed_count > 0 else 0
        
        return {
            'completed': completed_count,
            'total': 51,
            'avgScore': avg_score,
            'projects': projects,
            'lastUpdate': datetime.now().isoformat()
        }
        
    except Exception as e:
        print(f"Database error: {e}")
        return {
            'completed': 0,
            'total': 51,
            'avgScore': 0,
            'projects': [],
            'error': str(e)
        }

def generate_dashboard():
    """Generate HTML dashboard with current data"""
    data = get_simple_data()
    
    html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI Jury Leaderboard</title>
    <meta http-equiv="refresh" content="30">
    <style>
        body {{ font-family: Arial, sans-serif; background: #1a1a2e; color: #eee; margin: 20px; }}
        .header {{ text-align: center; margin-bottom: 30px; padding: 20px; background: #16213e; border-radius: 10px; }}
        .header h1 {{ color: #00d4ff; margin-bottom: 10px; }}
        .stats {{ display: flex; justify-content: space-around; margin-bottom: 30px; }}
        .stat {{ text-align: center; padding: 15px; background: #0f3460; border-radius: 8px; }}
        .stat-number {{ font-size: 2em; color: #00d4ff; font-weight: bold; }}
        .leaderboard {{ background: #16213e; border-radius: 10px; overflow: hidden; }}
        .row {{ display: grid; grid-template-columns: 50px 120px 80px 80px 60px 1fr; gap: 10px; padding: 12px; border-bottom: 1px solid #333; align-items: center; }}
        .header-row {{ background: #0f3460; font-weight: bold; }}
        .rank {{ text-align: center; font-weight: bold; }}
        .gold {{ color: #ffd700; }}
        .silver {{ color: #c0c0c0; }}
        .bronze {{ color: #cd7f32; }}
        .project {{ color: #00d4ff; font-weight: bold; }}
        .score {{ font-weight: bold; }}
        .grade {{ padding: 4px 8px; border-radius: 12px; text-align: center; font-weight: bold; }}
        .A-plus {{ background: #4caf50; }}
        .A {{ background: #66bb6a; }}
        .A-minus {{ background: #8bc34a; }}
        .B-plus {{ background: #ffc107; color: #000; }}
        .B {{ background: #ff9800; color: #000; }}
        .B-minus {{ background: #ff5722; }}
        .feedback {{ font-size: 0.9em; }}
        .evaluating {{ background: #3d2914; }}
        .update-info {{ text-align: center; margin-top: 20px; opacity: 0.7; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>🎯 AI Jury Evaluation Leaderboard</h1>
        <p>Live rankings with detailed strengths & weaknesses analysis</p>
        <p><em>Auto-refreshes every 30 seconds</em></p>
    </div>
    
    <div class="stats">
        <div class="stat">
            <div class="stat-number">{data['completed']}</div>
            <div>Completed</div>
        </div>
        <div class="stat">
            <div class="stat-number">{(data['completed']/data['total']*100):.1f}%</div>
            <div>Progress</div>
        </div>
        <div class="stat">
            <div class="stat-number">{data['avgScore']:.1f}</div>
            <div>Avg Score</div>
        </div>
        <div class="stat">
            <div class="stat-number">{len([p for p in data['projects'] if not p.get('completed', True)])}</div>
            <div>Evaluating</div>
        </div>
    </div>
    
    <div class="leaderboard">
        <div class="row header-row">
            <div><strong>Rank</strong></div>
            <div><strong>Project</strong></div>
            <div><strong>Score</strong></div>
            <div><strong>%</strong></div>
            <div><strong>Grade</strong></div>
            <div><strong>Strengths & Weaknesses</strong></div>
        </div>"""
    
    for i, project in enumerate(data['projects']):
        rank = i + 1
        rank_icon = '🥇' if rank == 1 else '🥈' if rank == 2 else '🥉' if rank == 3 else str(rank)
        rank_class = 'gold' if rank == 1 else 'silver' if rank == 2 else 'bronze' if rank == 3 else ''
        
        is_evaluating = not project.get('completed', True)
        row_class = 'evaluating' if is_evaluating else ''
        
        score_display = f"{project['score']:.1f}" if project['score'] is not None else '--'
        percentage_display = f"{project['percentage']:.1f}" if project['percentage'] is not None else '--'
        grade_display = project['grade'] or '⏳'
        grade_class = project['grade'].replace('+', '-plus').replace('-', '-minus') if project['grade'] else ''
        
        html += f"""
        <div class="row {row_class}">
            <div class="rank {rank_class}">{rank_icon}</div>
            <div class="project">{project['name']}</div>
            <div class="score">{score_display}/220</div>
            <div>{percentage_display}%</div>
            <div class="grade {grade_class}">{grade_display}</div>
            <div class="feedback">{project['feedback']}</div>
        </div>"""
    
    html += f"""
    </div>
    
    <div class="update-info">
        📊 Last updated: {datetime.now().strftime('%H:%M:%S')} | 
        🔄 Next refresh: {(datetime.now().second + 30) % 60:02d} seconds
    </div>
</body>
</html>"""
    
    return html

if __name__ == "__main__":
    html = generate_dashboard()
    with open('leaderboard.html', 'w') as f:
        f.write(html)
    print("📊 Dashboard generated: leaderboard.html")