#!/bin/bash

# 이 스크립트는 root 권한으로 실행해야 합니다.
if [ "$EUID" -ne 0 ]; then
  echo "오류: root 권한이 필요합니다. 'sudo ./startSvc.sh'와 같이 실행해주세요."
  exit
fi

# --- 설정 변수 ---
SERVICE_NAME="lmfilerecv"
APP_DIR="/home/lnk/opc/1" # ★★★ 실제 서버의 경로에 맞게 수정하세요 ★★★
PYTHON_EXEC="/usr/bin/python3"
APP_USER="lnk"
# -----------------

SERVICE_FILE="/etc/systemd/system/${SERVICE_NAME}.service"

echo "[1/5] systemd 서비스 파일을 생성합니다: ${SERVICE_NAME}"

# systemd 서비스 파일 내용 작성
cat > ${SERVICE_FILE} << EOF
[Unit]
Description=LM File Receiver Service
After=network.target

[Service]
User=${APP_USER}
Group=${APP_USER}
WorkingDirectory=${APP_DIR}
ExecStart=${PYTHON_EXEC} ${APP_DIR}/lmfilerecv_new.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

echo "[2/5] systemd 데몬을 리로드합니다..."
systemctl daemon-reload

echo "[3/5] 부팅 시 서비스가 자동으로 시작되도록 활성화합니다..."
systemctl enable ${SERVICE_NAME}

echo "[4/5] 지금 서비스를 시작합니다..."
systemctl start ${SERVICE_NAME}

echo "[5/5] 설치가 완료되었습니다."
echo ""
echo "서비스 상태 확인: sudo systemctl status ${SERVICE_NAME}"
