#!/usr/bin/env python3
"""
Auto-Updating Dashboard - Regenerates HTML every 20 seconds
"""

import time
import subprocess
import os
from datetime import datetime

def regenerate_dashboard():
    """Regenerate the dashboard HTML with latest data"""
    try:
        result = subprocess.run(['python3', 'quick_dashboard.py'], 
                              capture_output=True, text=True, cwd=os.getcwd())
        
        if result.returncode == 0:
            print(f"✅ Dashboard updated at {datetime.now().strftime('%H:%M:%S')}")
            return True
        else:
            print(f"❌ Dashboard update failed: {result.stderr}")
            return False
    except Exception as e:
        print(f"❌ Error updating dashboard: {e}")
        return False

def main():
    print("🔄 Starting Auto-Dashboard Updater")
    print("📊 Regenerating leaderboard.html every 20 seconds")
    print("🌐 Access at: http://localhost:8082/leaderboard.html")
    print("Press Ctrl+C to stop")
    print("=" * 60)
    
    try:
        while True:
            regenerate_dashboard()
            time.sleep(20)
    except KeyboardInterrupt:
        print("\n🛑 Auto-dashboard stopped")

if __name__ == "__main__":
    main()