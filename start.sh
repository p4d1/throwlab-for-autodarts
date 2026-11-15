#!/usr/bin/env bash
# P4DI Dart Trainer Startup Script

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$DIR"

# 1. Ensure systemd user service is running (if available)
if command -v systemctl >/dev/null 2>&1; then
    systemctl --user start padi-dart-trainer.service >/dev/null 2>&1
fi

# 2. Fallback: If port 8075 is not responding, launch server in background
if ! curl -s --max-time 1 http://localhost:8075/ >/dev/null 2>&1; then
    nohup /usr/bin/python3 "$DIR/server.py" > /tmp/dart_trainer_server.log 2>&1 &
    disown
    sleep 0.5
fi

# 3. Open directly in a clean App-Window or default browser
if flatpak info com.google.Chrome >/dev/null 2>&1; then
    flatpak run com.google.Chrome --app="http://localhost:8075" >/dev/null 2>&1 &
elif command -v google-chrome >/dev/null 2>&1; then
    google-chrome --app="http://localhost:8075" >/dev/null 2>&1 &
elif command -v chromium >/dev/null 2>&1; then
    chromium --app="http://localhost:8075" >/dev/null 2>&1 &
elif command -v xdg-open >/dev/null 2>&1; then
    xdg-open "http://localhost:8075" >/dev/null 2>&1 &
fi
