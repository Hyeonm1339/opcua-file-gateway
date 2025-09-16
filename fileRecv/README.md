## File Receiver System

`lmagent`로부터 파일을 수신, 저장, 처리하고 OPC-UA 서버에 전송하는 핵심 시스템입니다.

### 상세 동작 방식

이 시스템은 **파일 수신 서버**와 **파일 처리 워커**라는 두 개의 독립적인 프로세스로 구성되어, 안정성과 성능을 높였습니다.

#### 1. 파일 수신 서버 (`lmfilerecv.py`)

- Flask 기반의 웹 서버가 `/opcFileSave` 엔드포인트에서 `lmagent`의 HTTP POST 요청을 대기합니다.
- 요청을 받으면, 파일 데이터와 함께 전송된 메타데이터(`deviceid`, `dataid`, `orgfilename` 등)를 추출합니다.
- 수신된 정보는 `worker`가 처리할 수 있도록 다음 규칙에 따라 `save_path`에 저장됩니다.
  - **데이터 파일**: `[save_path]/[deviceid]/[dataid]/[원본 파일명]` 경로에 저장됩니다.
  - **메타데이터 파일**: 전송된 모든 파라미터는 `[원본 파일명].json` 형태의 JSON 파일로 데이터 파일과 동일한 위치에 저장됩니다.

#### 2. 파일 처리 워커 (`worker/worker.py`)

- **병렬 처리**: 여러 파일을 동시에 처리하여 대량의 파일도 빠르게 처리할 수 있습니다. (기본 5개 스레드)
- **주기적 스캔**: 백그라운드에서 계속 실행되며, 주기적으로 `save_path`를 스캔하여 처리할 파일을 찾습니다.
- **지능적 데이터 파싱**:
  - 데이터 파일을 발견하면, `.json` 설정 파일을 함께 읽어옵니다.
  - 다중 헤더, 단일 헤더 등 복잡한 구조의 엑셀 파일을 파싱합니다.
  - 이름이 없는 `Unnamed:` 컬럼은 처리 대상에서 자동으로 제외합니다.
  - 중복된 이름의 컬럼이 있을 경우, 첫 번째 컬럼만 사용하고 나머지는 무시합니다.
- **행 단위 변경점 추적**:
  - 파일 전체가 아닌, 파일 내부의 **행(row)** 단위로 처리 상태를 관리합니다.
  - `worker/last_row_info.json` 파일에 파일 및 시트별로 마지막으로 전송한 행의 시간(timestamp)을 기록합니다.
  - 이미 처리된 파일에 새로운 행이 추가되어 다시 전송될 경우, 마지막 처리 시간 이후의 **새로운 행만** 정확히 선별하여 OPC-UA 서버로 전송합니다.
- **데이터 타입 자동 변환**: 정수, 소수, 문자열 등 데이터 타입에 맞게 OPC-UA Variant 타입으로 변환하여 전송합니다. 소수점은 8자리까지 정밀도를 유지하며 깔끔하게 표시됩니다.
- **`TIME` 값 전송 안정화**: 각 행의 `TIME` 컬럼 값을 항상 마지막에 전송하여, OPC-UA 서버에서 시간 정보가 정확하게 기록되도록 합니다.

#### 3. OPC-UA 태그 매핑 규칙

- **태그 ID (Node ID)**
  - **기본 구조**: `ns=2;s=[dataid].[컬럼명]`
  - **시트 이름이 있는 경우**: `ns=2;s=[dataid].[시트명].[컬럼명]`
  - `Sheet1`과 같이 일반적인 시트 이름은 주소에 포함되지 않습니다.
  - **예시**: `dataid`가 `CHEONAN.JD12`이고, 시트 이름이 `P16_CAT`, 컬럼명이 `FI_C501A`라면, 최종 태그 ID는 `ns=2;s=CHEONAN.JD12.P16_CAT.FI_C501A`가 됩니다.

### 설정 (`config.json`)

`lmfilerecv.py`와 `worker/worker.py`는 각각 자신의 폴더에 있는 `config.json` 파일을 사용합니다.

```json
{
  "opc_server_url": "opc.tcp://127.0.0.1:4840/",
  "save_path": "/opcdata/save"
}
```

- `opc_server_url`: (워커용) 연결할 OPC-UA 서버의 주소입니다. 컨테이너 환경에서는 `127.0.0.1` 대신 실제 호스트 PC의 IP를 입력해야 합니다.
- `save_path`: (서버용) `lmagent`로부터 수신한 파일을 저장할 기본 경로입니다.

### 실행

각각의 `start.sh` 스크립트를 사용하여 서버와 워커를 개별적으로 시작하고 종료할 수 있습니다.

#### 1. 파일 수신 서버 (`lmfilerecv` 폴더)

- **시작**
  ```bash
  ./start.sh
  ```
- **종료**
  ```bash
  ./shutdown.sh
  ```
- **로그 확인**
  ```bash
  tail -f lmfilerecv.log
  ```

#### 2. 파일 처리 워커 (`worker` 폴더)

- **시작**
  ```bash
  ./worker/start.sh
  ```
- **종료**
  ```bash
  ./worker/shutdown.sh
  ```
- **로그 확인**
  ```bash
  tail -f worker/worker.log
  ```
- **종료**: 실행된 콘솔 창을 직접 닫거나, `Ctrl + C`를 눌러 종료합니다.

#### 직접 실행 (테스트 및 디버깅용)

```bash
python lmfilerecv.py
```

- **오류 기록용도**

```
Traceback (most recent call last):
  File "lmfilerecv.py", line 17, in <module>
    from flask import Flask, request, jsonify
ModuleNotFoundError: No module named 'flask'
파이썬 패키지 설치필요 pop install flask
```
