#!/usr/bin/env python3
"""
Live AI Jury Evaluation Ticker - Shows real-time progress updates
"""

import sqlite3
import time
from datetime import datetime

def show_live_ticker():
    """Show continuous progress updates"""
    db_path = "aieval_results.db"
    last_count = 0
    start_time = datetime.now()
    
    print("🚀 AI JURY LIVE TICKER - Updates every 15 seconds")
    print("=" * 70)
    
    while True:
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # Get current stats
            cursor.execute("SELECT COUNT(*) FROM multiround_evaluations")
            started = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM multiround_evaluations WHERE final_score IS NOT NULL")
            completed = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM evaluation_rounds")
            rounds_done = cursor.fetchone()[0]
            
            # Latest completion
            cursor.execute("""
                SELECT project_name, final_score, final_grade 
                FROM multiround_evaluations 
                WHERE final_score IS NOT NULL 
                ORDER BY created_at DESC LIMIT 1
            """)
            latest = cursor.fetchone()
            
            # Current time and duration
            now = datetime.now()
            duration = now - start_time
            duration_str = f"{duration.seconds//60}m{duration.seconds%60:02d}s"
            
            # Progress indicators
            progress = (completed / 51) * 100 if completed > 0 else 0
            rounds_progress = (rounds_done / 306) * 100 if rounds_done > 0 else 0
            
            # Status line
            status = f"[{now.strftime('%H:%M:%S')}] 📊 Projects: {completed}/51 ({progress:.1f}%) | 🔄 Rounds: {rounds_done}/306 ({rounds_progress:.1f}%) | ⏱️ {duration_str}"
            
            if completed > last_count:
                # New completion!
                if latest:
                    project, score, grade = latest
                    print(f"🎉 COMPLETED: {project} → {score:.1f}/220 ({score/220*100:.1f}%) Grade: {grade}")
                last_count = completed
            
            print(status)
            
            # Show current activity
            if started > completed:
                print(f"🤖 Active: {started - completed} evaluations running...")
            
            conn.close()
            
            # Exit if all done
            if completed >= 51:
                print("🏁 ALL EVALUATIONS COMPLETED!")
                break
                
            time.sleep(15)  # Update every 15 seconds
            
        except KeyboardInterrupt:
            print("\n⏹️  Ticker stopped by user")
            break
        except Exception as e:
            print(f"❌ Error: {e}")
            time.sleep(15)

if __name__ == "__main__":
    show_live_ticker()