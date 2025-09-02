#!/usr/bin/env python3
"""
Dashboard Data Provider - Fetches real-time evaluation data from database
"""

import sqlite3
import json
from datetime import datetime

def get_dashboard_data():
    """Fetch current evaluation data from database with detailed feedback"""
    db_path = "aieval_results.db"
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Get completed evaluations with all details
        cursor.execute("""
            SELECT 
                me.project_name,
                me.final_score,
                me.final_grade,
                me.created_at,
                ps.avg_score,
                ps.confidence_interval
            FROM multiround_evaluations me
            LEFT JOIN provider_statistics ps ON me.id = ps.evaluation_id AND ps.provider = 'claude'
            WHERE me.final_score IS NOT NULL
            ORDER BY me.final_score DESC
        """)
        
        evaluations = cursor.fetchall()
        
        # Build projects list with detailed feedback
        projects = []
        total_score = 0
        
        for eval_data in evaluations:
            project_name, final_score, final_grade, created_at, avg_score, confidence = eval_data
            
            # Get detailed category scores for this project
            cursor.execute("""
                SELECT 
                    cs.category,
                    cs.subcategory,
                    AVG(cs.score) as avg_score,
                    cs.weight,
                    cs.feedback
                FROM category_scores cs
                JOIN evaluation_rounds er ON cs.round_id = er.id
                JOIN multiround_evaluations me ON er.evaluation_id = me.id
                WHERE me.project_name = ?
                GROUP BY cs.category, cs.subcategory, cs.weight
                ORDER BY avg_score DESC
            """, (project_name,))
            
            category_data = cursor.fetchall()
            
            # Analyze strengths and weaknesses
            strengths = []
            weaknesses = []
            feedback_details = []
            
            for cat, subcat, score, weight, feedback in category_data:
                score_pct = (score / weight) * 100 if weight > 0 else 0
                category_name = f"{cat.replace('_', ' ').title()}"
                if subcat:
                    category_name += f"/{subcat.replace('_', ' ').title()}"
                
                if score_pct >= 85:
                    strengths.append(f"Excellent {category_name}")
                elif score_pct >= 70:
                    strengths.append(f"Good {category_name}")
                elif score_pct <= 40:
                    weaknesses.append(f"Poor {category_name}")
                elif score_pct <= 60:
                    weaknesses.append(f"Needs improvement in {category_name}")
                    
                if feedback and feedback.strip():
                    feedback_details.append(f"{category_name}: {feedback}")
            
            # Build comprehensive feedback
            feedback_parts = []
            if strengths:
                feedback_parts.append(f"<strong>Strengths:</strong> {', '.join(strengths[:4])}")
            if weaknesses:
                feedback_parts.append(f"<strong>Weaknesses:</strong> {', '.join(weaknesses[:4])}")
            
            comprehensive_feedback = ". ".join(feedback_parts)
            if not comprehensive_feedback:
                comprehensive_feedback = "Balanced performance across all evaluation criteria"
            
            projects.append({
                'name': project_name,
                'score': float(final_score),
                'percentage': (float(final_score) / 220 * 100),
                'grade': final_grade,
                'docType': doc_type or 'Unknown',
                'purpose': doc_purpose or 'Not specified',
                'completeness': doc_completeness or 'Unknown',
                'feedback': comprehensive_feedback,
                'confidence': confidence,
                'categoryCount': len(category_data),
                'createdAt': created_at
            })
            
            total_score += float(final_score)
        
        # Get currently evaluating projects
        cursor.execute("""
            SELECT project_name, created_at
            FROM multiround_evaluations 
            WHERE final_score IS NULL 
            ORDER BY created_at ASC
        """)
        
        evaluating = cursor.fetchall()
        
        # Add evaluating projects to list
        for project_name, created_at in evaluating:
            eval_start = datetime.fromisoformat(created_at)
            duration = datetime.now() - eval_start
            duration_str = f"{duration.seconds // 60}m {duration.seconds % 60}s"
            
            projects.append({
                'name': project_name,
                'score': None,
                'percentage': None,
                'grade': None,
                'docType': 'Evaluating...',
                'feedback': f'🤖 Multi-round evaluation in progress ({duration_str})',
                'evaluating': True
            })
        
        # Overall statistics
        completed_count = len(evaluations)
        avg_score = total_score / completed_count if completed_count > 0 else 0
        
        # Get round completion stats
        cursor.execute("SELECT COUNT(*) FROM evaluation_rounds")
        completed_rounds = cursor.fetchone()[0]
        
        conn.close()
        
        return {
            'completed': completed_count,
            'total': 51,
            'avgScore': avg_score,
            'projects': projects,
            'completedRounds': completed_rounds,
            'expectedRounds': 51 * 3,  # 51 projects × 1 provider × 3 rounds
            'evaluating': [proj['name'] for proj in projects if proj.get('evaluating')],
            'lastUpdate': datetime.now().isoformat(),
            'status': 'running' if evaluating else 'completed'
        }
        
    except Exception as e:
        print(f"Dashboard data error: {e}")
        return {
            'completed': 0,
            'total': 51,
            'avgScore': 0,
            'projects': [],
            'error': str(e),
            'lastUpdate': datetime.now().isoformat()
        }

if __name__ == "__main__":
    # Test the data fetching
    data = get_dashboard_data()
    print(json.dumps(data, indent=2))