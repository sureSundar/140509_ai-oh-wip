#!/bin/bash

# Batch AI Jury Evaluation Script for 140509_01 to 140509_51
# 3 rounds with Claude and OpenAI providers

echo "🎯 Starting batch AI Jury evaluation for projects 140509_01 to 140509_51"
echo "📊 Configuration: 3 rounds per model, Claude provider (OpenAI quota exhausted)"
echo "💾 Results will be persisted to aieval_results.db"
echo ""

BASE_PATH="/home/vboxuser/Documents/140509_ai-oh-wip"
ENGINE_PATH="/home/vboxuser/Documents/140509_ai-oh-wip/140509_byoc/AIEvalEngine"
PROVIDERS="claude:claude-3-5-sonnet-20241022"

cd "$ENGINE_PATH"

for i in {1..51}; do
    PROJECT_NUM=$(printf "%02d" $i)
    PROJECT_PATH="$BASE_PATH/140509_$PROJECT_NUM"
    
    if [ -d "$PROJECT_PATH" ]; then
        echo "📁 Evaluating 140509_$PROJECT_NUM..."
        
        python3 AIEvalEngine_v3.py --multiround --rounds 3 \
            --providers "$PROVIDERS" \
            --type directory \
            "$PROJECT_PATH"
        
        if [ $? -eq 0 ]; then
            echo "✅ 140509_$PROJECT_NUM completed successfully"
        else
            echo "❌ 140509_$PROJECT_NUM failed"
        fi
        
        echo ""
        sleep 2  # Brief pause between evaluations
    else
        echo "⚠️  140509_$PROJECT_NUM not found"
    fi
done

echo "🏁 Batch evaluation completed!"
echo "📊 Check results with: python3 AIEvalEngine_v3.py --history --limit 0"