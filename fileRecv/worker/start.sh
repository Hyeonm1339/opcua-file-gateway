#!/bin/bash
# worker.py를 백그라운드에서 실행하고 로그를 기록합니다.

# 스크립트가 위치한 디렉토리로 이동합니다.
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
cd "$DIR"

# 이미 실행 중인지 확인하고, 실행 중이 아니면 시작합니다.
if pgrep -f "worker.py" > /dev/null
then
    echo "worker.py is already running."
else
    echo "Starting worker.py in background..."
    # nohup을 사용하지 않고 직접 백그라운드 실행 및 로깅
    python3 worker.py >> worker.log 2>&1 &
    echo "worker.py started."
fi
