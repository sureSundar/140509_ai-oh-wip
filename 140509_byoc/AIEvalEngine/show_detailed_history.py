#!/usr/bin/env python3
"""
Enhanced History Display for AIEvalEngine showing complete rubric breakdown
"""

import sqlite3
from typing import List, Dict, Any

def show_detailed_history(db_path: str = "aieval_results.db", limit: int = 5):
    """Display evaluation history with complete rubric breakdown tables"""
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Get recent evaluations
    cursor.execute('''
        SELECT id, source_path, project_name, total_score, max_score, 
               percentage, grade, evaluation_date, llm_model
        FROM evaluations 
        ORDER BY created_at DESC 
        LIMIT ?
    ''', (limit,))
    
    evaluations = cursor.fetchall()
    
    if not evaluations:
        print("📊 No evaluation history found.")
        return
    
    print("📊 DETAILED EVALUATION HISTORY")
    print("=" * 80)
    
    for eval_data in evaluations:
        eval_id, source_path, project_name, total_score, max_score, percentage, grade, eval_date, llm_model = eval_data
        
        print(f"\n🎯 EVALUATION #{eval_id}: {project_name}")
        print(f"   Source: {source_path}")
        print(f"   Overall: {total_score}/{max_score} ({percentage:.1f}%) - Grade: {grade}")
        print(f"   Date: {eval_date[:10]} | AI: {llm_model}")
        
        # Get rubric info
        cursor.execute('SELECT rubric_version, total_points FROM rubric_configs WHERE evaluation_id = ?', (eval_id,))
        rubric_info = cursor.fetchone()
        if rubric_info:
            print(f"   Rubric: v{rubric_info[0]} ({rubric_info[1]} points)")
        
        # Category scores table
        print(f"\n   📊 CATEGORY SCORES:")
        print(f"   {'Category':<25} | {'Score':<8} | {'%':<6} | {'Weight'}")
        print(f"   {'-'*25}-+-{'-'*8}-+-{'-'*6}-+-{'-'*6}")
        
        cursor.execute('''
            SELECT category, total_score, max_score, percentage, weight 
            FROM category_scores WHERE evaluation_id = ? ORDER BY weight DESC
        ''', (eval_id,))
        
        for cat_row in cursor.fetchall():
            category, cat_score, cat_max, cat_pct, weight = cat_row
            print(f"   {category:<25} | {cat_score:2}/{cat_max:2}   | {cat_pct:5.1f}% | {weight:.2f}")
        
        # Subcategory details table
        print(f"\n   🔍 SUBCATEGORY BREAKDOWN:")
        print(f"   {'Category.Subcategory':<35} | {'Score':<8} | {'%':<6}")
        print(f"   {'-'*35}-+-{'-'*8}-+-{'-'*6}")
        
        cursor.execute('''
            SELECT category, subcategory, score, max_score, percentage 
            FROM evaluation_details WHERE evaluation_id = ? ORDER BY category, subcategory
        ''', (eval_id,))
        
        for sub_row in cursor.fetchall():
            category, subcategory, score, max_score, percentage = sub_row
            full_name = f"{category}.{subcategory}"
            print(f"   {full_name:<35} | {score:2}/{max_score:2}   | {percentage:5.1f}%")
        
        print("\n" + "="*80)
    
    conn.close()

if __name__ == "__main__":
    show_detailed_history()