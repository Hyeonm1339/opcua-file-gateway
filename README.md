# Data-Bridge: File to OPC-UA

파일 시스템의 특정 폴더를 감시하여, 변경된 데이터 파일(Excel, CSV 등)을 처리하고 OPC-UA 서버로 전송하는 데이터 브릿지 시스템입니다.

## 주요 기능

- **안정적인 분리형 아키텍처**: 파일 수신(Web Server)과 파일 처리(Worker)를 독립된 프로세스로 분리하여 안정성을 극대화했습니다.
- **병렬 처리**: 여러 파일을 동시에 처리하여 대량의 파일도 빠르게 처리할 수 있습니다.
- **행 단위 변경점 추적**: 파일 전체가 아닌, 파일 내 마지막으로 처리된 행의 시간을 기준으로 새로운 데이터만 정확히 선별하여 전송합니다. 동일한 파일이 업데이트되어도 새로운 내용만 반영됩니다.
- **지능적 데이터 파싱**: 다중 헤더 엑셀 파일을 포함한 복잡한 데이터 구조를 처리하며, 이름 없는 컬럼(`Unnamed:`)이나 중복된 컬럼은 자동으로 무시하여 오류를 방지합니다.
- **간편한 관리**: 전체 시스템을 `start-all.sh`, `shutdown-all.sh` 스크립트로 한 번에 제어할 수 있습니다.

## 새로운 시스템 아키텍처

```
[lmagent.py] --(HTTP)--> [lmfilerecv.py] --(File System)--> [worker.py] --(OPC-UA)--> [OPC-UA Server]
```

1.  **`fileSend/lmagent.py` (File Sender)**: 지정된 폴더를 감시하여 파일 변경사항을 `lmfilerecv.py` 서버로 HTTP 전송합니다.
2.  **`fileRecv/lmfilerecv.py` (File Receiver)**: `lmagent`로부터 파일을 수신하여, 지정된 경로(`save_path`)에 안전하게 저장하는 역할만 담당하는 경량 웹 서버입니다.
3.  **`fileRecv/worker/worker.py` (File Processor)**: `save_path`에 저장된 파일을 주기적으로 스캔하여, 데이터 파싱, OPC-UA 태그 주소 생성, 데이터 전송 등 모든 핵심 비즈니스 로직을 수행합니다.

## 기술 스택

- Python 3
- `pandas`, `python-opcua`, `Flask`, `openpyxl`, `simpledbf`

## 설치

프로젝트에 필요한 라이브러리를 설치합니다.

```bash
pip install pandas opcua Flask openpyxl simpledbf
```

## 전체 시스템 실행

프로젝트 최상위 폴더에 위치한 마스터 스크립트를 사용하여 전체 시스템을 한 번에 관리할 수 있습니다.

- **전체 시작**
  ```bash
  ./start-all.sh
  ```
- **전체 종료**
  ```bash
  ./shutdown-all.sh
  ```
> 스크립트 실행 권한이 없는 경우 `chmod +x *.sh` 명령어로 권한을 부여해야 합니다.

## 개별 실행 및 상세 설명

각 컴포넌트의 상세한 설정 및 개별 실행 방법은 해당 폴더의 `README.md` 파일을 참고하십시오.

- **[File Receiver System (fileRecv/README.md)](./fileRecv/README.md)**
- **[File Sender (fileSend/README.md)](./fileSend/README.md)**