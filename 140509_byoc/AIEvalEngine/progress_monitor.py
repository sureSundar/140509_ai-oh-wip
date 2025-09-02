#!/usr/bin/env python3
"""
Real-time AI Jury Evaluation Progress Monitor
Shows live progress, statistics, and completion status
"""

import sqlite3
import time
import os
from datetime import datetime, timedelta

def clear_screen():
    os.system('clear')

def get_progress_stats(db_path: str):
    """Get current progress statistics"""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Total multiround evaluations
        cursor.execute("SELECT COUNT(*) FROM multiround_evaluations")
        total_evaluations = cursor.fetchone()[0]
        
        # Completed evaluations (with final scores)
        cursor.execute("SELECT COUNT(*) FROM multiround_evaluations WHERE final_score IS NOT NULL")
        completed_evaluations = cursor.fetchone()[0]
        
        # Total rounds completed
        cursor.execute("SELECT COUNT(*) FROM evaluation_rounds")
        completed_rounds = cursor.fetchone()[0]
        
        # Provider statistics
        cursor.execute("""
            SELECT provider, COUNT(*) as count, AVG(avg_score) as avg_score 
            FROM provider_statistics 
            GROUP BY provider
        """)
        provider_stats = cursor.fetchall()
        
        # Recent completions
        cursor.execute("""
            SELECT project_name, final_score, final_grade, providers, created_at
            FROM multiround_evaluations 
            WHERE final_score IS NOT NULL
            ORDER BY created_at DESC 
            LIMIT 5
        """)
        recent_completions = cursor.fetchall()
        
        # Current running evaluation
        cursor.execute("""
            SELECT project_name, providers, created_at
            FROM multiround_evaluations 
            WHERE final_score IS NULL
            ORDER BY created_at DESC 
            LIMIT 1
        """)
        current_eval = cursor.fetchone()
        
        conn.close()
        
        return {
            'total_evaluations': total_evaluations,
            'completed_evaluations': completed_evaluations,
            'completed_rounds': completed_rounds,
            'provider_stats': provider_stats,
            'recent_completions': recent_completions,
            'current_eval': current_eval
        }
        
    except Exception as e:
        return {'error': str(e)}

def format_duration(start_time):
    """Format duration since start time"""
    duration = datetime.now() - start_time
    hours, remainder = divmod(duration.seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"

def display_progress_dashboard(db_path: str, start_time: datetime):
    """Display real-time progress dashboard"""
    stats = get_progress_stats(db_path)
    
    if 'error' in stats:
        print(f"❌ Error: {stats['error']}")
        return
    
    clear_screen()
    
    # Header
    print("🎯 AI JURY EVALUATION PROGRESS MONITOR")
    print("=" * 80)
    print(f"⏱️  Runtime: {format_duration(start_time)}")
    print(f"📅 Started: {start_time.strftime('%H:%M:%S')}")
    print(f"🔄 Last Update: {datetime.now().strftime('%H:%M:%S')}")
    print()
    
    # Overall Progress
    total_projects = 51  # Expected total
    completed = stats['completed_evaluations']
    total_rounds_expected = total_projects * 2 * 3  # 51 projects × 2 models × 3 rounds = 306
    completed_rounds = stats['completed_rounds']
    
    progress_pct = (completed / total_projects) * 100 if total_projects > 0 else 0
    rounds_pct = (completed_rounds / total_rounds_expected) * 100 if total_rounds_expected > 0 else 0
    
    print(f"📊 PROJECT PROGRESS: {completed}/{total_projects} ({progress_pct:.1f}%)")
    print("🟩" * int(progress_pct // 2) + "⬜" * (50 - int(progress_pct // 2)))
    
    print(f"📊 ROUND PROGRESS: {completed_rounds}/{total_rounds_expected} ({rounds_pct:.1f}%)")
    print("🟦" * int(rounds_pct // 2) + "⬜" * (50 - int(rounds_pct // 2)))
    print()
    
    # Current Status
    if stats['current_eval']:
        project_name, providers, created_at = stats['current_eval']
        print(f"🔄 CURRENTLY EVALUATING: {project_name}")
        print(f"   Providers: {providers}")
        eval_start = datetime.fromisoformat(created_at)
        eval_duration = datetime.now() - eval_start
        print(f"   Duration: {eval_duration.seconds // 60}m {eval_duration.seconds % 60}s")
    else:
        print("✅ ALL EVALUATIONS COMPLETED!")
    print()
    
    # Provider Performance
    if stats['provider_stats']:
        print("🤖 PROVIDER PERFORMANCE:")
        print("-" * 40)
        for provider, count, avg_score in stats['provider_stats']:
            if avg_score:
                print(f"   {provider:>15}: {avg_score:5.1f} avg ({count} evaluations)")
        print()
    
    # Recent Completions
    if stats['recent_completions']:
        print("🎉 RECENT COMPLETIONS:")
        print("-" * 60)
        for project, score, grade, providers, created_at in stats['recent_completions']:
            print(f"   {project:>12}: {score:5.1f}/220 ({score/220*100:5.1f}%) - {grade}")
        print()
    
    # Statistics
    if completed > 0:
        avg_time_per_project = (datetime.now() - start_time).seconds / completed
        eta_seconds = avg_time_per_project * (total_projects - completed)
        eta = datetime.now() + timedelta(seconds=eta_seconds)
        print(f"⏱️  ETA: {eta.strftime('%H:%M:%S')} (avg {avg_time_per_project:.0f}s per project)")
    
    print("=" * 80)
    print("Press Ctrl+C to exit monitor")

def main():
    db_path = "aieval_results.db"
    start_time = datetime.now()
    
    print("🎯 Starting AI Jury Progress Monitor...")
    print("👀 Monitoring evaluation progress in real-time...")
    time.sleep(2)
    
    try:
        while True:
            display_progress_dashboard(db_path, start_time)
            time.sleep(10)  # Update every 10 seconds
            
    except KeyboardInterrupt:
        clear_screen()
        print("\n🛑 Progress monitor stopped.")
        print("📊 Final status:")
        stats = get_progress_stats(db_path)
        if 'completed_evaluations' in stats:
            print(f"   Projects completed: {stats['completed_evaluations']}")
            print(f"   Rounds completed: {stats['completed_rounds']}")

if __name__ == "__main__":
    main()