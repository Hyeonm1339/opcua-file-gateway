#!/bin/bash

# 스크립트가 위치한 디렉토리로 이동
cd "$(dirname "$0")"

PID_FILE="lmagent.pid"

# 이미 PID 파일이 존재하면, 스크립트가 실행 중인 것으로 간주하고 종료
if [ -f "$PID_FILE" ]; then
  echo "에이전트가 이미 실행 중입니다. 먼저 shutdown.sh를 실행해주세요."
  exit 1
fi

echo "lmagent.py를 백그라운드에서 시작합니다..."

# nohup을 사용하여 파이썬 스크립트를 백그라운드에서 실행하고, 모든 출력을 lmagent.log 파일로 리다이렉션
nohup python3 lmagent.py > lmagent.log 2>&1 &

# 방금 실행한 백그라운드 프로세스의 PID를 파일에 저장
echo $! > $PID_FILE

echo "에이전트가 PID $(cat $PID_FILE)로 시작되었습니다. 로그는 lmagent.log 파일에 기록됩니다."
