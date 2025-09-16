#!/bin/bash
# lmfilerecv.py 서버를 백그라운드에서 실행하고 로그를 기록합니다.

# 스크립트가 위치한 디렉토리로 이동합니다.
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
cd "$DIR"

# 이미 실행 중인지 확인하고, 실행 중이 아니면 시작합니다.
if pgrep -f "lmfilerecv.py" > /dev/null
then
    echo "lmfilerecv.py is already running."
else
    echo "Starting lmfilerecv.py..."
    nohup python3 lmfilerecv.py > lmfilerecv.log 2>&1 &
    echo "lmfilerecv.py started."
fi