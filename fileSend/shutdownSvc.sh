#!/bin/bash

# 이 스크립트는 root 권한으로 실행해야 합니다.
if [ "$EUID" -ne 0 ]; then
  echo "오류: root 권한이 필요합니다. 'sudo ./shutdownSvc.sh'와 같이 실행해주세요."
  exit
fi

# --- 설정 변수 ---
SERVICE_NAME="lmagent"
# -----------------

SERVICE_FILE="/etc/systemd/system/${SERVICE_NAME}.service"

echo "[1/5] ${SERVICE_NAME} 서비스를 중지합니다..."
systemctl stop ${SERVICE_NAME}

echo "[2/5] 부팅 시 서비스가 자동으로 시작되지 않도록 비활성화합니다..."
systemctl disable ${SERVICE_NAME}

if [ -f "${SERVICE_FILE}" ]; then
  echo "[3/5] 서비스 파일을 삭제합니다..."
  rm ${SERVICE_FILE}
else
  echo "[3/5] 서비스 파일이 이미 삭제되었습니다."
fi

echo "[4/5] systemd 데몬을 리로드합니다..."
systemctl daemon-reload

echo "[5/5] 서비스 제거가 완료되었습니다."
