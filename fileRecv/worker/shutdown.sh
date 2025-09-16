#!/bin/bash
# worker.py 프로세스를 찾아 종료합니다.

PROCESS_NAME="worker.py"

# 프로세스 ID 찾기
PID=$(pgrep -f "${PROCESS_NAME}")

if [ -z "$PID" ]; then
    echo "${PROCESS_NAME} is not running."
else
    echo "Stopping ${PROCESS_NAME} (PID: $PID)..."
    kill $PID
    echo "Process stopped."
fi
