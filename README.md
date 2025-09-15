# Excel to OPC-UA Bridge

지정된 폴더의 엑셀(Excel) 및 다양한 데이터 파일을 감지하여, 내용을 파싱하고 OPC-UA 서버로 전송하는 데이터 브릿지입니다.

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

1.  **`lmagent.py` (File Sender)**

    - 로컬 또는 원격 서버의 특정 폴더를 주기적으로 스캔합니다.
    - `config.json`에 명시된 `lastchktime` 이후로 변경된 파일을 감지합니다.
    - 감지된 파일을 `lmfilerecv.py` 서버로 HTTP POST를 통해 전송합니다.

2.  **`lmfilerecv.py` (File Receiver & Processor)**
    - `lmagent.py`로부터 파일을 수신하여 지정된 경로에 저장합니다.
    - 백그라운드 워커가 저장된 파일을 순차적으로 처리합니다.
    - 파일 형식과 `headerline` 설정에 맞춰 데이터를 파싱합니다.
    - 파싱된 데이터를 OPC-UA 서버의 해당 노드(태그)에 씁니다.

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

## 설정

#### File Receiver (`fielRecv/config.json`)

파일을 수신하여 OPC-UA 서버로 전송하는 서버의 설정입니다.

```json
{
  "opc_server_url": "opc.tcp://127.0.0.1:4840/",
  "save_path": "/path/to/save/received/files",
  "processed_log_file": "processed.log"
}
```

- `opc_server_url`: 연결할 OPC-UA 서버의 주소입니다.
- `save_path`: `lmagent`로부터 수신한 파일을 저장할 기본 경로입니다.
- `processed_log_file`: 처리가 완료된 파일 목록을 기록할 로그 파일 이름입니다.

#### File Sender (`fileSend/config.json`)

파일 변경을 감지하여 전송하는 에이전트의 설정입니다.

```json
{
  "gateway_url": "http://127.0.0.1:8080/opcFileSave",
  "deviceid": "YOUR_DEVICE_ID",
  "dataid": "DATAID_1,DATAID_2",
  "scan_path": "/path/to/monitor1,/path/to/monitor2",
  "scan_file": ".csv,.xls,.xlsx,.dbf",
  "scan_interval": 60,
  "lastchktime": "2025-09-01 00:00:00",
  "headerline": "1,[1,2]"
}
```

- `gateway_url`: `lmfilerecv.py` 서버의 파일 수신 주소입니다.
- `deviceid`: 데이터를 보내는 장비의 고유 ID입니다.
- `dataid`: `scan_path`의 각 경로에 매칭되는 데이터 ID 목록입니다. (콤마로 구분)
- `scan_path`: 모니터링할 폴더 경로 목록입니다. (콤마로 구분)
- `headerline`: `scan_path`의 각 경로에 해당하는 파일의 헤더 라인 정보입니다. (콤마로 구분, 다중 헤더는 `[1,2]` 형식)
- `scan_interval`: 폴더를 스캔할 주기(초)입니다.
- `lastchktime`: 에이전트가 마지막으로 파일을 확인한 시간입니다. 이 시간 이후에 수정된 파일만 전송됩니다.

## 실행

`fielRecv`와 `fileSend` 각 폴더에서 아래의 방법으로 실행할 수 있습니다.

### 1. 스크립트를 이용한 실행

#### Linux / macOS

- **시작**: `start.sh`를 실행하면 프로세스가 백그라운드에서 동작합니다.
  ```bash
  sh start.sh
  ```
- **종료**: `shutdown.sh`를 실행하면 백그라운드에서 동작 중인 프로세스를 종료합니다.
  ```bash
  sh shutdown.sh
  ```

#### Windows

- **시작**: `run.bat` 파일을 더블클릭하거나 터미널에서 실행합니다. 새로운 콘솔 창에서 실행됩니다.
  ```bash
  run.bat
  ```
- **종료**: 실행된 콘솔 창을 직접 닫거나, `Ctrl + C`를 눌러 종료합니다.

### 2. 서비스로 등록하여 실행 (Linux)

`systemd`를 사용하여 각 애플리케이션을 서비스로 등록하면, 시스템 부팅 시 자동으로 시작되고 안정적으로 관리할 수 있습니다.

1.  `install_service.sh` 스크립트에 실행 권한을 부여합니다.
    ```bash
    chmod +x install_service.sh
    ```
2.  스크립트를 `sudo` 권한으로 실행하여 서비스를 등록합니다. 이 스크립트는 `fielRecv`와 `fileSend`를 모두 서비스로 등록합니다.
    ```bash
    sudo sh install_service.sh
    ```
3.  서비스 삭제가 필요한 경우 `uninstall_service.sh`를 사용합니다.
    `bash
    sudo sh uninstall_service.sh
    `
    > **주의**: `install_service.sh` 파일 내부의 `USER`와 `WorkingDirectory` 변수를 실제 환경에 맞게 수정해야 할 수 있습니다.

### 3. 직접 실행 (테스트 및 디버깅용)

포그라운드에서 직접 실행하여 로그를 실시간으로 확인할 때 유용합니다.

- **File Receiver 서버 시작**

  ```bash
  cd fielRecv
  python lmfilerecv.py
  ```

- **File Sender 에이전트 시작**
  ```bash
  cd fileSend
  python lmagent.py
  ```

## License

[MIT](LICENSE)
