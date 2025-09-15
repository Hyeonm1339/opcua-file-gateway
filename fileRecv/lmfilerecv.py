#-*- coding: utf-8 -*-
# lmfilerecv_new.py
# 이 스크립트는 두 가지 핵심 역할을 동시에 수행함.
# 1. 웹 서버 (Flask): lmagent로부터 파일과 메타데이터를 수신하여 지정된 경로에 저장.
# 2. 백그라운드 워커: 저장된 파일을 주기적으로 스캔하여 처리하고 OPC-UA 서버로 전송.

import os
import sys
import json
import time
import threading
import traceback
from datetime import datetime

# 필요한 라이브러리 목록
# pip install Flask opcua pandas openpyxl simpledbf
from flask import Flask, request, jsonify
import pandas as pd
from opcua import Client, ua
from simpledbf import Dbf5

# --- 전역 설정 변수 ---
CONFIG = {}
PROCESSED_FILES = set()

# --- 1. 데이터 처리 로직 (원본 lmfilerecv.py 기반) ---

def load_excel_data(filename, dataid, headerline):
    """
    .xls 또는 .xlsx 파일을 읽어 Pandas DataFrame으로 변환.
    headerline을 동적으로 적용하여 단일 및 다중 헤더를 모두 처리.
    """
    try:
        header_config = None
        is_multi_header = False

        # headerline 파라미터 파싱
        header_str = str(headerline)
        if header_str.startswith('[') and header_str.endswith(']'):
            try:
                # 문자열 "[1,2]"를 실제 리스트 [1,2]로 변환
                header_list = json.loads(header_str)
                # pandas는 0-based index를 사용하므로 각 항목에서 1을 빼줌
                header_config = [h - 1 for h in header_list]
                is_multi_header = True
            except json.JSONDecodeError:
                print(f"[WARNING] headerline 파싱 오류: {header_str}. 기본값(0)으로 설정합니다.")
                header_config = 0
        elif header_str.isdigit():
            header_config = int(header_str) - 1
        else:
            header_config = 0

        # 모든 시트를 읽어옴
        all_sheets_df = pd.read_excel(filename, header=header_config, sheet_name=None)
        
        processed_sheets = {}
        for sheet_name, sheet_df in all_sheets_df.items():
            if sheet_df.empty:
                continue

            # 다중 헤더인 경우, 컬럼명을 조합하는 로직 적용
            if is_multi_header:
                new_cols = []
                last_header_part = ""
                for col in sheet_df.columns:
                    # col은 튜플 형태 (예: ('TIC_R700', 'TT_R700'))
                    
                    # 첫 번째 헤더 처리 (병합된 셀 대응)
                    part1 = str(col[0])
                    if 'Unnamed:' in part1 or part1.strip() == '':
                        current_header_part1 = last_header_part
                    else:
                        current_header_part1 = part1
                        last_header_part = part1
                    
                    # 나머지 헤더 처리
                    remaining_parts = [str(p) for p in col[1:] if 'Unnamed:' not in str(p) and str(p).strip() != '']
                    
                    # 최종 컬럼명 조합
                    all_parts = [current_header_part1] + remaining_parts
                    combined_col = '.'.join(filter(None, all_parts))
                    new_cols.append(combined_col)
                
                sheet_df.columns = new_cols
                # TIME 컬럼 이름 변경 및 데이터 처리
                input_df = sheet_df.rename(columns={sheet_df.columns[0]: 'TIME'})

            else: # 단일 헤더인 경우
                input_df = sheet_df.rename(columns={sheet_df.columns[0]: 'TIME'})

            # TIME 컬럼 타입 변환 (필요시 여기에 로직 추가)
            # 예: input_df['TIME'] = pd.to_datetime(input_df['TIME'])
            
            processed_sheets[sheet_name] = input_df
        
        return processed_sheets

    except Exception as e:
        print(f"[ERROR] Excel 파일 로딩 실패: {filename}, {e}")
        traceback.print_exc()
        return None

def loaddata(filename, dataid, headerline):
    """
    파일 확장자와 dataid에 따라 적절한 데이터 로딩 함수를 호출.
    """
    ext = os.path.splitext(filename)[-1].lower()
    if ext in ['.xls', '.xlsx']:
        return load_excel_data(filename, dataid, headerline)
    # .dbf, .csv 등 다른 파일 형식에 대한 로더는 여기에 추가 가능
    else:
        print(f"[WARNING] 지원하지 않는 파일 형식: {ext}")
        return None

def sendopcua(filepath, params):
    """
    처리된 데이터를 OPC-UA 서버로 전송하는 함수.
    """
    global CONFIG
    dataid = params.get('dataid')
    headerline = params.get('headerline', 1)
    
    # config.json에서 단일 OPC-UA 서버 주소를 가져옴
    opc_server_url = CONFIG.get('opc_server_url')
    
    if not opc_server_url:
        print(f"[ERROR] config.json에 'opc_server_url'이 설정되지 않았습니다.")
        return False

    # 1. 파일에서 데이터 로드
    df_dict = loaddata(filepath, dataid, headerline)
    if not df_dict:
        print(f"[ERROR] 파일 데이터 로드 실패: {filepath}")
        return False

    # 2. OPC-UA 서버 접속
    client = Client(opc_server_url)
    try:
        client.connect()
        print(f"[INFO] OPC-UA 서버에 연결 성공: {opc_server_url}")

        # 3. 데이터 전송 (원본 로직 기반)
        for sheet_name, df in df_dict.items():
            if df.empty:
                continue
            
            # ... (원본 lmfilerecv.py의 sendopcua 함수 내 데이터 전송 로직) ...
            # 이 부분은 실제 태그 구조와 데이터 타입에 맞춰 원본 로직을 참고하여 상세 구현이 필요합니다.
            # 아래는 기본 골격 예시입니다.
            print(f"[INFO] 시트 '{sheet_name}'의 데이터 {len(df)}개를 전송합니다.")
            for _, row in df.iterrows():
                for col_name, value in row.items():
                    nodeid = f"ns=2;s={dataid}.{col_name}"
                    try:
                        node = client.get_node(nodeid)
                        # 데이터 타입에 맞는 Variant 생성 (실제 구현 시 원본 코드 참고)
                        variant_type = ua.VariantType.String 
                        variant = ua.Variant(str(value), variant_type)
                        dv = ua.DataValue(variant)
                        node.set_value(dv)
                    except Exception as node_e:
                        # print(f"[WARNING] NodeId {nodeid} 처리 중 오류: {node_e}")
                        pass # 특정 태그 실패는 무시하고 계속 진행
        
        client.disconnect()
        print(f"[INFO] OPC-UA 전송 완료 및 연결 해제.")
        return True

    except Exception as e:
        print(f"[ERROR] OPC-UA 처리 중 심각한 오류 발생: {e}")
        traceback.print_exc()
        if client:
            client.disconnect()
        return False


# --- 2. 백그라운드 워커 (파일 처리 및 OPC-UA 전송) ---

def load_processed_files():
    """프로그램 시작 시, 처리 완료된 파일 목록을 로그에서 로드."""
    global PROCESSED_FILES
    log_file = CONFIG.get('processed_log_file')
    if not log_file or not os.path.exists(log_file):
        return
    try:
        with open(log_file, 'r', encoding='utf-8') as f:
            PROCESSED_FILES = set(line.strip() for line in f)
        print(f"[INFO] 처리 완료된 파일 {len(PROCESSED_FILES)}개를 로그에서 로드했습니다.")
    except Exception as e:
        print(f"[ERROR] 처리 완료 로그 로드 실패: {e}")

def log_processed_file(filepath):
    """처리 완료된 파일을 로그에 기록."""
    global PROCESSED_FILES
    PROCESSED_FILES.add(filepath)
    log_file = CONFIG.get('processed_log_file')
    if not log_file:
        return
    try:
        with open(log_file, 'a', encoding='utf-8') as f:
            f.write(filepath + '\n')
    except Exception as e:
        print(f"[ERROR] 처리 완료 로그 기록 실패: {e}")

def worker_function():
    """
    저장된 파일을 주기적으로 스캔하여 처리하는 백그라운드 작업.
    """
    print("[INFO] 백그라운드 워커 시작.")
    while True:
        save_path = CONFIG.get('save_path')
        if not save_path or not os.path.isdir(save_path):
            print(f"[ERROR] 설정된 save_path를 찾을 수 없음: {save_path}")
            time.sleep(30)
            continue

        try:
            # deviceid 폴더들을 순회
            for deviceid_folder in os.listdir(save_path):
                deviceid_path = os.path.join(save_path, deviceid_folder)
                if not os.path.isdir(deviceid_path):
                    continue

                # dataid 폴더들을 순회
                for dataid_folder in os.listdir(deviceid_path):
                    dataid_path = os.path.join(deviceid_path, dataid_folder)
                    if not os.path.isdir(dataid_path):
                        continue
                    
                    # 폴더 내 파일들을 순회
                    for filename in os.listdir(dataid_path):
                        # .json 파라미터 파일은 건너뜀
                        if filename.endswith('.json'):
                            continue

                        filepath = os.path.join(dataid_path, filename)
                        
                        # 이미 처리된 파일이면 건너뜀
                        if filepath in PROCESSED_FILES:
                            continue
                        
                        # 파라미터 파일 경로
                        param_filepath = filepath + '.json'
                        if not os.path.exists(param_filepath):
                            print(f"[WARNING] 파라미터 파일(.json)을 찾을 수 없음: {filepath}")
                            continue

                        print(f"[INFO] 새로운 처리 대상 파일 발견: {filepath}")
                        
                        # 파라미터 파일 로드
                        with open(param_filepath, 'r', encoding='utf-8') as f:
                            params = json.load(f)

                        # OPC-UA 전송
                        success = sendopcua(filepath, params)
                        
                        if success:
                            print(f"[INFO] 파일 처리 및 전송 성공: {filepath}")
                            log_processed_file(filepath)
                        else:
                            print(f"[ERROR] 파일 처리 또는 전송 실패: {filepath}")
                            # 실패 시, 다음 사이클에서 재시도하기 위해 로그에 기록하지 않음.

        except Exception as e:
            print(f"[ERROR] 워커 실행 중 예외 발생: {e}")
            traceback.print_exc()

        time.sleep(10) # 10초마다 스캔


# --- 3. 웹 서버 (파일 수신) ---

app = Flask(__name__)

@app.route('/opcFileSave', methods=['POST'])
def file_receiver():
    """
    lmagent로부터 파일 및 파라미터를 수신하여 저장.
    """
    try:
        # 폼 데이터에서 파라미터 추출
        params = {key: request.form[key] for key in request.form}
        deviceid = params.get('deviceid')
        dataid = params.get('dataid')
        org_filename = params.get('orgfilename')

        if not deviceid or not dataid or not org_filename:
            return jsonify({"success": False, "error": "deviceid, dataid 또는 orgfilename이 누락됨"}), 400

        # 파일 저장 경로 설정
        save_path = CONFIG.get('save_path')
        if not save_path:
            return jsonify({"success": False, "error": "서버에 save_path가 설정되지 않음"}), 500
            
        target_dir = os.path.join(save_path, deviceid, dataid)
        os.makedirs(target_dir, exist_ok=True) # 폴더가 없으면 생성
        
        filepath = os.path.join(target_dir, org_filename)
        param_filepath = filepath + '.json'

        # 파일 저장
        file = request.files.get('filename')
        if file:
            file.save(filepath)
            print(f"[INFO] 파일 수신 및 저장 완료: {filepath}")
        else:
            return jsonify({"success": False, "error": "파일 데이터가 없음"}), 400

        # 파라미터 .json 파일로 저장
        with open(param_filepath, 'w', encoding='utf-8') as f:
            json.dump(params, f, indent=2)
        
        return jsonify({"success": True, "message": f"{org_filename} 저장 완료"})

    except Exception as e:
        print(f"[ERROR] 파일 수신 중 오류 발생: {e}")
        traceback.print_exc()
        return jsonify({"success": False, "error": str(e)}), 500


# --- 4. 메인 실행 블록 ---

if __name__ == '__main__':
    # 1. 설정 파일 로드
    try:
        with open('config.json', 'r', encoding='utf-8') as f:
            CONFIG = json.load(f)
    except FileNotFoundError:
        print("[CRITICAL] 서버 설정 파일(config.json)을 찾을 수 없습니다. 프로그램을 종료합니다.")
        sys.exit(1)
    except Exception as e:
        print(f"[CRITICAL] 서버 설정 파일(config.json) 읽기 오류: {e}. 프로그램을 종료합니다.")
        sys.exit(1)

    # 2. 처리 완료된 파일 목록 로드
    load_processed_files()

    # 3. 백그라운드 워커 쓰레드 시작
    worker_thread = threading.Thread(target=worker_function, daemon=True)
    worker_thread.start()

    # 4. Flask 웹 서버 시작
    print("[INFO] Flask 웹 서버를 0.0.0.0:8080에서 시작합니다.")
    app.run(host='0.0.0.0', port=8080)
