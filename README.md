# Excel to OPC-UA Bridge

지정된 폴더의 엑셀(Excel) 및 다양한 데이터 파일을 감지하여, 내용을 파싱하고 OPC-UA 서버로 전송하는 데이터 브릿지입니다. (CSV, TXT추가 작업예정..)

## 주요 기능

- **파일 시스템 모니터링**: 지정된 여러 폴더에서 새로운 파일 생성 또는 변경 사항을 실시간으로 감지합니다.
- **다양한 파일 형식 지원**: `.xlsx`, `.xls`, `.dbf`, `.csv` 등 다양한 데이터 파일을 처리할 수 있습니다.
- **복잡한 데이터 파싱**: 다중 라인 헤더(Multi-line Header)를 포함한 복잡한 구조의 엑셀 파일을 분석하고 정형화합니다.
- **유연한 설정**: `config.json` 파일을 통해 모니터링 경로, OPC-UA 서버 정보, 데이터 ID 등을 쉽게 설정할 수 있습니다.
- **안정적인 데이터 전송**: 전송 이력 관리를 통해 데이터의 중복 전송을 방지하고, 네트워크 오류 시 재시도를 수행합니다.

## 시스템 아키텍처

```
[데이터 파일]----(감지)----> [lmagent.py] ----(HTTP 전송)----> [lmfilerecv.py] ----(OPC-UA)----> [OPC-UA 서버]
```

### 1. `lmagent.py` (File Sender)

`lmagent.py`는 지정된 폴더를 감시하여 파일의 변경사항을 서버로 전송하는 경량 에이전트입니다.

- **초기화**: 시작 시 `config.json` 파일을 읽어 모니터링할 대상(`scan_path`, `dataid`, `headerline` 등)과 마지막으로 전송에 성공했던 시간(`lastchktime`)을 불러옵니다.
- **파일 스캔**: `scan_interval` 주기로 `scan_path`에 지정된 폴더들을 스캔하여 `lastchktime` 이후에 수정된 파일을 찾습니다.
- **전송**: 새로 수정된 파일들을 수정 시간 순서대로 정렬하여 가장 오래된 파일부터 하나씩 `lmfilerecv.py` 서버에 HTTP POST로 전송합니다. 파일 전송이 성공할 때마다 `lastchktime`을 해당 파일의 수정 시간으로 갱신하여, 중간에 통신이 끊겨도 데이터 유실 없이 다음 주기부터 재전송이 가능합니다.

### 2. `lmfilerecv.py` (File Receiver & Processor)

`lmfilerecv.py`는 `lmagent`로부터 파일을 수신하여 파싱하고 OPC-UA 서버에 기록하는 핵심 서버 프로그램입니다. 두 가지 요소가 동시에 동작합니다.

- **웹 서버 (Flask)**: `lmagent`로부터 파일과 메타데이터(dataid, headerline 등)를 HTTP 요청으로 수신합니다. 수신된 원본 파일과 메타데이터를 담은 `.json` 파일을 `save_path`에 저장하여 백그라운드 워커가 처리할 수 있도록 대기시킵니다.
- **백그라운드 워커 (Background Thread)**: `save_path`를 주기적으로 스캔하여 아직 처리되지 않은 새 파일을 찾습니다. 파일을 발견하면, 함께 저장된 `.json` 파라미터 파일을 읽어 `headerline` 등의 설정을 적용하여 엑셀, CSV 등의 데이터를 파싱합니다. 최종적으로 파싱된 데이터를 OPC-UA 서버에 전송하고, 성공적으로 처리된 파일은 로그에 기록하여 중복 처리를 방지합니다.

## 기술 스택

- Python 3
- `pandas`
- `python-opcua`
- `Flask`
- `requests`
- `simpledbf`
- `openpyxl`

## 설치

프로젝트 루트 경로에 `requirements.txt` 파일을 생성하고 아래 내용을 추가한 뒤, 라이브러리를 설치합니다.

**`requirements.txt`**
```
pandas
opcua
Flask
requests
simpledbf
openpyxl
```

**설치 명령어**
```bash
pip install -r requirements.txt
```

## 설정 및 실행

각 프로그램의 상세한 설정 및 실행 방법은 해당 폴더의 `README.md` 파일을 참고하십시오.

- **[File Receiver (fielRecv/README.md)](./fielRecv/README.md)**
- **[File Sender (fileSend/README.md)](./fileSend/README.md)**

### 서비스로 등록하여 실행 (Linux)

`systemd`를 사용하여 각 애플리케이션을 서비스로 등록하면, 시스템 부팅 시 자동으로 시작되고 안정적으로 관리할 수 있습니다.

1.  `install_service.sh` 스크립트에 실행 권한을 부여합니다.
    ```bash
    chmod +x install_service.sh
    ```
2.  스크립트를 `sudo` 권한으로 실행하여 서비스를 등록합니다.
    ```bash
    sudo sh install_service.sh
    ```
3.  서비스 삭제가 필요한 경우 `uninstall_service.sh`를 사용합니다.
    ```bash
    sudo sh uninstall_service.sh
    ```
> **주의**: `install_service.sh` 파일 내부의 `USER`와 `WorkingDirectory` 변수를 실제 환경에 맞게 수정해야 할 수 있습니다.

## License

[MIT](LICENSE)
