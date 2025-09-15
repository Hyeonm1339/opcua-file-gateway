## File Receiver (lmfilerecv.py)

`lmagent`로부터 파일을 수신하여 파싱하고 OPC-UA 서버에 기록하는 핵심 서버 프로그램입니다.

### 상세 동작 방식

이 프로그램은 **웹 서버**와 **백그라운드 워커**라는 두 가지 핵심 요소가 동시에 동작합니다.

#### 1. 파일 수신 및 저장 (웹 서버)

- Flask 기반의 웹 서버가 `/opcFileSave` 엔드포인트에서 `lmagent`의 HTTP POST 요청을 대기합니다.
- 요청을 받으면, 파일 데이터와 함께 전송된 메타데이터(`deviceid`, `dataid`, `headerline` 등)를 추출합니다.
- 수신된 정보는 다음 규칙에 따라 `save_path`에 저장됩니다.
  - **데이터 파일**: `[save_path]/[deviceid]/[dataid]/[원본 파일명]` 경로에 저장됩니다.
  - **메타데이터 파일**: 전송된 모든 파라미터는 `[원본 파일명].json` 형태의 JSON 파일로 데이터 파일과 동일한 위치에 저장됩니다. 이 파일은 이후 데이터 처리 단계에서 설정값으로 사용됩니다.

#### 2. 데이터 처리 및 전송 (백그라운드 워커)

- 별도의 백그라운드 스레드가 주기적으로 `save_path`를 스캔하여 처리할 파일을 찾습니다.
- 데이터 파일을 발견하면, 해당 파일과 쌍을 이루는 `.json` 설정 파일을 함께 읽어옵니다.
- `.json` 파일에 저장된 `headerline` 정보를 포함한 여러 설정을 적용하여 데이터 파일(Excel, CSV 등)의 내용을 정확하게 파싱합니다.
- 최종적으로 파싱된 데이터를 OPC-UA 서버에 전송합니다.
- 처리가 성공적으로 완료되면, 해당 파일의 경로를 로그 파일(`processed_log_file`)에 기록하여 동일한 파일이 중복 처리되는 것을 방지합니다.

#### 3. OPC-UA 태그 매핑 규칙

파싱된 데이터는 아래의 규칙에 따라 OPC-UA 서버의 태그(Node)에 매핑됩니다.

- **태그 ID (Node ID)**

  - OPC-UA의 태그 ID는 `dataid`와 엑셀의 컬럼(열) 이름을 조합하여 생성됩니다.
  - **구조**: `ns=2;s=[dataid].[엑셀 컬럼명]`
  - **예시**: `dataid`가 `CHEONAN.JD16.GTC`이고 엑셀 컬럼명이 `TIC_101`이라면, 최종 태그 ID는 `ns=2;s=CHEONAN.JD16.GTC.TIC_101`이 됩니다.

- **값 (Value)**

  - 엑셀 시트의 각 행(Row)을 순회하며, 해당 컬럼에 있는 값을 태그의 값으로 사용합니다.
  - 현재 버전에서는 모든 값을 문자열(String) 형태로 변환하여 OPC-UA 서버에 전송합니다.

- **시간 (TIME)**
  - 엑셀 데이터의 첫 번째 열은 항상 `TIME`으로 인식됩니다.
  - `TIME` 열의 값 역시 다른 데이터와 마찬가지로, `ns=2;s=[dataid].TIME` 형식의 태그에 문자열로 기록됩니다.

### 설정 (`config.json`)

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

### 실행

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

- **시작**: `run.bat` 파일을 더블클릭하거나 터미널에서 실행합니다.
  ```bash
  run.bat
  ```
- **종료**: 실행된 콘솔 창을 직접 닫거나, `Ctrl + C`를 눌러 종료합니다.

#### 직접 실행 (테스트 및 디버깅용)

```bash
python lmfilerecv.py
```
