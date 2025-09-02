#!/usr/bin/env python3
"""
Real-time AI Jury Evaluation Dashboard Server
Serves live leaderboard with detailed feedback and rankings
"""

import sqlite3
import json
import threading
import time
from datetime import datetime
from http.server import HTTPServer, SimpleHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import os

class DashboardHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory="/home/vboxuser/Documents/140509_ai-oh-wip/140509_byoc/AIEvalEngine", **kwargs)
    
    def do_GET(self):
        parsed_path = urlparse(self.path)
        
        if parsed_path.path == '/api/dashboard-data':
            self.serve_dashboard_data()
        elif parsed_path.path == '/' or parsed_path.path == '/dashboard':
            self.path = '/dashboard.html'
            super().do_GET()
        else:
            super().do_GET()
    
    def serve_dashboard_data(self):
        """Serve real-time evaluation data as JSON"""
        try:
            data = get_dashboard_data()
            
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            
            self.wfile.write(json.dumps(data, indent=2).encode())
            
        except Exception as e:
            self.send_error(500, f"Server error: {str(e)}")

def get_dashboard_data():
    """Fetch current evaluation data from database"""
    db_path = "aieval_results.db"
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Get completed evaluations with detailed feedback
        cursor.execute("""
            SELECT 
                me.project_name,
                me.final_score,
                me.final_grade,
                me.document_type,
                me.document_purpose,
                me.document_completeness,
                me.created_at,
                ps.avg_score,
                ps.confidence_interval
            FROM multiround_evaluations me
            LEFT JOIN provider_statistics ps ON me.id = ps.evaluation_id
            WHERE me.final_score IS NOT NULL
            ORDER BY me.final_score DESC
        """)
        
        evaluations = cursor.fetchall()
        
        # Get category feedback for each project
        projects = []
        for eval_data in evaluations:
            project_name, final_score, final_grade, doc_type, doc_purpose, doc_completeness, created_at, avg_score, confidence = eval_data
            
            # Get detailed category scores for feedback
            cursor.execute("""
                SELECT 
                    category,
                    subcategory,
                    AVG(score) as avg_score,
                    weight
                FROM category_scores cs
                JOIN evaluation_rounds er ON cs.round_id = er.id
                JOIN multiround_evaluations me ON er.evaluation_id = me.id
                WHERE me.project_name = ?
                GROUP BY category, subcategory, weight
                ORDER BY avg_score DESC
            """, (project_name,))
            
            category_scores = cursor.fetchall()
            
            # Generate strengths and weaknesses based on scores
            strengths = []
            weaknesses = []
            
            for cat, subcat, score, weight in category_scores:
                score_pct = (score / weight) * 100 if weight > 0 else 0
                category_name = f"{cat}/{subcat}" if subcat else cat
                
                if score_pct >= 80:
                    strengths.append(f"Strong {category_name.replace('_', ' ')}")
                elif score_pct <= 50:
                    weaknesses.append(f"Weak {category_name.replace('_', ' ')}")
            
            feedback_parts = []
            if strengths:
                feedback_parts.append(f"<strong>Strengths:</strong> {', '.join(strengths[:3])}")
            if weaknesses:
                feedback_parts.append(f"<strong>Weaknesses:</strong> {', '.join(weaknesses[:3])}")
            
            feedback = ". ".join(feedback_parts) if feedback_parts else "Balanced performance across categories"
            
            projects.append({
                'name': project_name,
                'score': float(final_score) if final_score else 0,
                'percentage': (float(final_score) / 220 * 100) if final_score else 0,
                'grade': final_grade,
                'docType': doc_type or 'Unknown',
                'purpose': doc_purpose,
                'completeness': doc_completeness,
                'feedback': feedback,
                'confidence': confidence
            })
        
        # Get overall stats
        cursor.execute("SELECT COUNT(*) FROM multiround_evaluations WHERE final_score IS NOT NULL")
        completed_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM multiround_evaluations")
        total_evaluations = cursor.fetchone()[0]
        
        cursor.execute("SELECT AVG(final_score) FROM multiround_evaluations WHERE final_score IS NOT NULL")
        avg_score_result = cursor.fetchone()[0]
        avg_score = float(avg_score_result) if avg_score_result else 0
        
        # Get currently evaluating projects
        cursor.execute("""
            SELECT project_name 
            FROM multiround_evaluations 
            WHERE final_score IS NULL 
            ORDER BY created_at ASC
        """)
        
        evaluating = [row[0] for row in cursor.fetchall()]
        
        # Add currently evaluating projects to the list
        for project_name in evaluating:
            projects.append({
                'name': project_name,
                'score': None,
                'percentage': None,
                'grade': None,
                'docType': 'Evaluating...',
                'feedback': '🤖 Multi-round evaluation in progress...'
            })
        
        conn.close()
        
        return {
            'completed': completed_count,
            'total': 51,  # Expected total
            'avgScore': avg_score,
            'projects': projects,
            'evaluating': evaluating,
            'lastUpdate': datetime.now().isoformat()
        }
        
    except Exception as e:
        print(f"Dashboard data error: {e}")
        return {
            'completed': 0,
            'total': 51,
            'avgScore': 0,
            'projects': [],
            'error': str(e)
        }

def start_dashboard_server(port=8080):
    """Start the dashboard web server"""
    server_address = ('', port)
    httpd = HTTPServer(server_address, DashboardHandler)
    
    print(f"🌐 AI Jury Dashboard Server started at http://localhost:{port}")
    print(f"📊 Access leaderboard at http://localhost:{port}/dashboard.html")
    print("🔄 Auto-updates every 15 seconds")
    print("Press Ctrl+C to stop server")
    
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n🛑 Dashboard server stopped")
        httpd.shutdown()

if __name__ == "__main__":
    import sys
    port = 8081 if '--port' in sys.argv else 8080
    if '--port' in sys.argv:
        port_idx = sys.argv.index('--port') + 1
        if port_idx < len(sys.argv):
            port = int(sys.argv[port_idx])
    start_dashboard_server(port)