#!/bin/bash
# Record RetailAI Demo Video

echo "🎬 Starting video recording..."

# Set up virtual display
export DISPLAY=:99
Xvfb :99 -screen 0 1920x1080x24 &
XVFB_PID=$!

# Start window manager
fluxbox &
FLUXBOX_PID=$!

sleep 3

# Open demo page in Chrome
google-chrome --no-sandbox --disable-dev-shm-usage --start-maximized \
  --app=file://$(pwd)/demo_presentation.html &
CHROME_PID=$!

sleep 5

echo "🔴 Recording video (60 seconds)..."

# Record the screen
ffmpeg -f x11grab -video_size 1920x1080 -framerate 30 -i :99.0 \
  -c:v libx264 -preset fast -crf 23 -pix_fmt yuv420p \
  -t 60 RetailAI_Demo_Video.mp4 -y

# Cleanup
kill $CHROME_PID $FLUXBOX_PID $XVFB_PID 2>/dev/null

echo "✅ Video recording complete: RetailAI_Demo_Video.mp4"
ls -lh RetailAI_Demo_Video.mp4
