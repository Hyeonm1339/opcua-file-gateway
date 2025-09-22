## File Sender (lmagent.py)

지정된 폴더를 감시하여 파일의 변경사항을 File Receiver 서버로 전송하는 경량 에이전트입니다. 에이전트는 파일 전송 역할만 담당하며, 수신된 파일의 처리 및 OPC-UA 전송은 File Receiver 시스템에서 이루어집니다.

### 설정 (`config.json`)

```json
{
  "gateway_url": "http://127.0.0.1:8080/opcFileSave",
  "deviceid": "YOUR_DEVICE_ID",
  "dataid": "DATAID_1,DATAID_2",
  "scan_path": "/path/to/monitor1,/path/to/monitor2",
  "scan_file": ".csv,.xls,.xlsx,.dbf",
  "scan_interval": 60,
  "lastchktime": "2025-09-01 00:00:00",
  "headerline": "1,[1,2]",
  "columnline": "4,4"
}
```

- `gateway_url`: `lmfilerecv.py` 서버의 파일 수신 주소입니다.
- `deviceid`: 데이터를 보내는 장비의 고유 ID입니다.
- `dataid`: `scan_path`의 각 경로에 매칭되는 데이터 ID 목록입니다. (콤마로 구분)
- `scan_path`: 모니터링할 폴더 경로 목록입니다. (콤마로 구분)
- `headerline`: `scan_path`의 각 경로에 해당하는 파일의 헤더 라인 정보입니다. (콤마로 구분, 다중 헤더는 `[1,2]` 형식) 실제 행을 처리하므로 0부터가아닌 1부터 시작한다(index[x])
- `scan_interval`: 폴더를 스캔할 주기(초)입니다.
- `lastchktime`: 에이전트가 마지막으로 파일을 확인한 시간입니다. 이 시간 이후에 수정된 파일만 전송됩니다.
- `columnline`: 읽을 파일이 엑셀파일인 경우, 몇번쨰 행부터 데이터가 존재하는지 기준값, 값이 4인경우 4번째 값부터 스캔을 진행하기 위함.

### 실행

#### Linux / macOS

- **시작**: `start.sh`를 실행하면 프로세스가 백그라운드에서 동작합니다.
  ```bash
  ./start.sh
  ```
- **종료**: `shutdown.sh`를 실행하면 백그라운드에서 동작 중인 프로세스를 종료합니다.
  ```bash
  ./shutdown.sh
  ```

#### Windows

- **시작**: `run.bat` 파일을 더블클릭하거나 터미널에서 실행합니다.
  ```bash
  run.bat
  ```
- **종료**: 실행된 콘솔 창을 직접 닫거나, `Ctrl + C`를 눌러 종료합니다.

#### 직접 실행 (테스트 및 디버깅용)

```bash
python lmagent.py
```
