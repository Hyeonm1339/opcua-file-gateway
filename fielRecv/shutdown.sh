#!/bin/bash

# 스크립트가 위치한 디렉토리로 이동
cd "$(dirname "$0")"

PID_FILE="lmfilerecv.pid"

# PID 파일이 없으면, 종료할 프로세스가 없는 것으로 간주
if [ ! -f "$PID_FILE" ]; then
  echo "PID 파일을 찾을 수 없습니다. 서버가 실행 중이지 않은 것 같습니다."
  exit 1
fi

PID=$(cat $PID_FILE)
echo "PID ${PID}에 해당하는 서버를 중지합니다..."

# PID를 이용해 프로세스 종료
kill $PID

# PID 파일 삭제
rm $PID_FILE

echo "서버가 중지되었습니다."
