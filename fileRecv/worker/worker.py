#-*- coding: utf-8 -*-
# worker.py (Concurrent Version)
# 지정된 경로의 파일을 스캔하여 처리하고 OPC-UA 서버로 전송합니다.
# 여러 파일을 동시에 병렬로 처리하여 성능을 향상시킵니다.

import os
import sys
import json
import time
import traceback
import threading
from datetime import datetime
from os.path import basename
from concurrent.futures import ThreadPoolExecutor, as_completed

import numpy as np

# 필요한 라이브러리 목록
# pip install opcua pandas openpyxl simpledbf
import pandas as pd
from opcua import Client, ua
from simpledbf import Dbf5

# --- 전역 설정 변수 ---
CONFIG = {}
LAST_ROW_INFO_FILE = 'last_row_info.json' # 처리된 마지막 행 정보를 저장할 파일
MAX_WORKERS = 5 # 동시에 처리할 최대 파일 수

# --- 1. 데이터 처리 로직 (수정) ---

def parse_flexible_time(time_val, fdate=None):
    """
    여러 형식의 시간 문자열을 파싱하여 datetime 객체로 변환하는 함수.
    """
    if pd.isna(time_val):
        return pd.NaT
        
    time_str = str(time_val)

    # 시도할 형식과 전처리 로직의 리스트
    # 각 항목은 (전처리 함수, strptime 포맷)의 튜플
    # 전처리 함수는 (원본문자열, 파일날짜)를 인자로 받아 파싱할 문자열을 반환한다. 아무것도 반환하지 못할경우 에러처리.
    parsing_strategies = [
        # 형식 1: '24년1월1일 10시20분30초' -> '24-01-01 10:20:30'
        (lambda s, d: s.replace("년", "-").replace("월", "-").replace("일", " ").replace("시", ":").replace("분", ":").replace("초", ""), '%y-%m-%d %H:%M:%S'),
        
        # 형식 2: '2024/01/01 10:20' 또는 '10:20:30' (날짜가 없는경우 넘겨받은 파일의 날짜를 사용(fdata)
        (lambda s, d: f"{d} {s}" if d and len(s) < 12 and ':' in s else (s + ":00")[:19].replace("/", "-"), '%Y-%m-%d %H:%M:%S'),

        # 형식 3: '2024.01.01 10:20:30' 또는 '24.01.01 10:20:30'
        (lambda s, d: s.replace(".", "-"), '%Y-%m-%d %H:%M:%S'),
        (lambda s, d: s.replace(".", "-"), '%y-%m-%d %H:%M:%S'),
    ]

    for preprocess, fmt in parsing_strategies:
        try:
            processed_str = preprocess(time_str, fdate)
            return datetime.strptime(processed_str, fmt)
        except (ValueError, TypeError):
            continue
            
    # 모든 형식 변환 실패 시, pandas의 자동 파싱 기능을 마지막으로 시도
    # errors='coerce'는 파싱 실패 시 NaT (Not a Time)을 반환하여 오류를 방지
    return pd.to_datetime(time_str, errors='coerce')


def load_excel_data(filename, dataid, headerline, columnline):
    """
    .xls 또는 .xlsx 파일을 읽어 Pandas DataFrame으로 변환.
    columnline을 사용하여 데이터 시작점 이전의 행을 건너뛰고, 명시된 TIME 포맷으로 파싱합니다.
    """
    try:
        header_config = None
        is_multi_header = False
        effective_header_line_num = 1  # 기본값

        header_str = str(headerline)
        if header_str.startswith('[') and header_str.endswith(']'):
            try:
                header_list = json.loads(header_str)
                header_config = [h - 1 for h in header_list]
                is_multi_header = True
                effective_header_line_num = max(header_list)
            except (json.JSONDecodeError, ValueError):
                header_config = 0
                effective_header_line_num = 1
        elif header_str.isdigit():
            header_config = int(header_str) - 1
            effective_header_line_num = int(header_str)
        else:
            header_config = 0
            effective_header_line_num = 1

        all_sheets_df = pd.read_excel(filename, header=header_config, sheet_name=None)
        
        try:
            columnline_num = int(columnline)
            df_starts_at_line = effective_header_line_num + 1
            rows_to_skip = columnline_num - df_starts_at_line
            if rows_to_skip < 0:
                rows_to_skip = 0
        except (ValueError, TypeError):
            rows_to_skip = 0

        processed_sheets = {}
        for sheet_name, sheet_df in all_sheets_df.items():
            if sheet_df.empty:
                continue

            # columnline 로직 적용: DataFrame의 시작 부분에서 불필요한 행 건너뛰기
            if rows_to_skip > 0:
                if len(sheet_df) > rows_to_skip:
                    print(f"[INFO] 시트 '{sheet_name}'의 시작 데이터 행({columnline_num})에 따라 상위 {rows_to_skip}개 행을 건너뜁니다.")
                    sheet_df = sheet_df.iloc[rows_to_skip:].reset_index(drop=True)
                else:
                    print(f"[WARNING] 시트 '{sheet_name}'에서 건너뛸 행({rows_to_skip})이 전체 행 수({len(sheet_df)})보다 많아 데이터가 없습니다.")
                    continue

            if is_multi_header:
                new_cols = []
                last_header_part = ""
                for col in sheet_df.columns:
                    part1 = str(col[0])
                    if 'Unnamed:' in part1 or part1.strip() == '':
                        current_header_part1 = last_header_part
                    else:
                        current_header_part1 = part1
                        last_header_part = part1
                    
                    remaining_parts = [str(p) for p in col[1:] if 'Unnamed:' not in str(p) and str(p).strip() != '']
                    all_parts = [current_header_part1] + remaining_parts
                    combined_col = '.'.join(filter(None, all_parts))
                    new_cols.append(combined_col)
                sheet_df.columns = new_cols

            cols_to_keep = [col for col in sheet_df.columns if 'Unnamed:' not in str(col)]
            if len(cols_to_keep) < len(sheet_df.columns):
                dropped_cols = [col for col in sheet_df.columns if 'Unnamed:' in str(col)]
                print(f"[INFO] 시트 '{sheet_name}'에서 'Unnamed' 컬럼 {dropped_cols}을 무시합니다.")
            sheet_df = sheet_df[cols_to_keep]

            all_columns = sheet_df.columns.tolist()
            unique_columns = []
            seen_originals = set()
            for column in all_columns:
                original_col = column
                if isinstance(column, str) and len(column) > 2 and column[-2] == '.' and column[-1].isdigit():
                    original_col = column[:-2]
                if original_col not in seen_originals:
                    unique_columns.append(column)
                    seen_originals.add(original_col)
            
            if len(all_columns) > len(unique_columns):
                dropped_cols = [col for col in all_columns if col not in unique_columns]
                print(f"[INFO] 시트 '{sheet_name}'에서 중복 컬럼 {dropped_cols}을 무시합니다.")
            sheet_df = sheet_df[unique_columns]

            if sheet_df.empty or sheet_df.columns.empty:
                continue

            input_df = sheet_df.rename(columns={sheet_df.columns[0]: 'TIME'})
            
            # 파싱 전 TIME 컬럼이 비어있는 행을 먼저 제거
            input_df.dropna(subset=['TIME'], inplace=True)
            if input_df.empty:
                print(f"[INFO] 시트 '{sheet_name}'에 유효한 시간 데이터가 없어 건너뜁니다.")
                continue

            print(f"[DEBUG] 시트 '{sheet_name}'의 TIME 컬럼 파싱 시도 (원본 데이터 예시: {input_df['TIME'].iloc[0]})")
            
            original_time_column = input_df['TIME'].copy()
            
            # --- 유연한 시간 파싱 로직 ---
            # 파일명에서 날짜 추출 (시간만 있는 데이터에 사용)
            fdate = None
            try:
                fname = basename(filename).split(".")
                fdate_str = fname[0].split("_")[-1]
                # 'YYYY년MM월DD일' 또는 'YYYY-MM-DD' 같은 형식을 '%Y-%m-%d'로 통일
                cleaned_fdate_str = fdate_str.replace("년", "-").replace("월", "-").replace("일", "")
                fdate = datetime.strptime(cleaned_fdate_str, '%Y-%m-%d').strftime('%Y-%m-%d')
            except (ValueError, IndexError):
                print(f"[WARNING] 파일명 '{basename(filename)}'에서 날짜를 추출할 수 없습니다. 시간만 있는 데이터는 파싱에 실패할 수 있습니다.")

            # TIME값을 일괄 처리하기 위한 공통 함수를 호출한다.
            input_df['TIME'] = input_df['TIME'].apply(lambda x: parse_flexible_time(x, fdate=fdate))
            
            # 파싱에 실패한 행(NaT)이 있는지 확인하고 경고
            failed_mask = input_df['TIME'].isna()
            if failed_mask.any():
                failed_count = failed_mask.sum()
                failed_examples = original_time_column[failed_mask].head(3).tolist()
                print(f"[WARNING] 시트 '{sheet_name}'에서 TIME 컬럼 파싱 실패 (총 {failed_count}개). 예시: {failed_examples}")
                # 파싱 실패한 행 최종 제거
                input_df.dropna(subset=['TIME'], inplace=True)

            processed_sheets[sheet_name] = input_df
        
        return processed_sheets

    except Exception as e:
        print(f"[ERROR] Excel 파일 로딩 실패: {filename}, {e}")
        traceback.print_exc()
        return None

def loaddata(filepath, params):
    dataid = params.get('dataid')
    headerline = params.get('headerline', '1')
    columnline = params.get('columnline', '1')
    ext = os.path.splitext(filepath)[-1].lower()
    
    if ext in ['.xls', '.xlsx']:
        return load_excel_data(filepath, dataid, headerline, columnline)
    else:
        print(f"[WARNING] 지원하지 않는 파일 형식: {ext}")
        return None

# --- 2. OPC-UA 전송 태스크 (기존과 동일) ---

def sendopcua_task(filepath, params, last_row_info):
    """
    단일 파일에 대한 데이터 처리 및 OPC-UA 전송을 수행. (스레드에서 실행될 함수)
    성공 시 (파일-시트 키, 마지막 처리 시간) 튜플의 리스트를 반환.
    """
    dataid = params.get('dataid')
    
    df_dict = loaddata(filepath, params)
    if not df_dict:
        print(f"[ERROR] 파일 데이터 로드 실패: {filepath}")
        return None

    opc_server_url = CONFIG.get('opc_server_url')
    if not opc_server_url:
        print(f"[ERROR] config.json에 'opc_server_url'이 설정되지 않았습니다.")
        return None
        
    client = Client(opc_server_url)
    try:
        client.connect()
        
        results_for_this_file = []
        for sheet_name, df in df_dict.items():
            if df.empty:
                continue

            file_sheet_key = f"{filepath}|{sheet_name}"
            last_processed_time_str = last_row_info.get(file_sheet_key)
            
            if last_processed_time_str:
                try:
                    last_processed_time = datetime.strptime(last_processed_time_str, '%Y-%m-%d %H:%M:%S')
                    df_to_send = df[df['TIME'] > last_processed_time].copy()
                except ValueError:
                    print(f"[WARNING] 날짜 형식 오류로 '{file_sheet_key}'의 전체 데이터를 재처리합니다: {last_processed_time_str}")
                    df_to_send = df.copy()
            else:
                df_to_send = df.copy()

            if df_to_send.empty:
                continue

            print(f"[INFO] 스레드({threading.get_ident()})가 시트 '{sheet_name}'의 새로운 데이터 {len(df_to_send)}개를 처리합니다.")
            
            latest_time_in_batch = df_to_send['TIME'].max()

            current_sheet_name = sheet_name
            if current_sheet_name.startswith("Sheet"):
                current_sheet_name = ""

            # 전송 순서 조정을 위해 컬럼 목록을 가져와 TIME을 맨 뒤로 보냅니다.
            column_order = df_to_send.columns.tolist()
            if 'TIME' in column_order:
                column_order.remove('TIME')
                column_order.append('TIME')

            for _, row in df_to_send.iterrows():
                for col_name in column_order: # 수정된 순서대로 처리
                    value = row[col_name]
                    if current_sheet_name == "":
                        nodeid = f"ns=2;s={dataid}.{col_name}"
                    else:
                        nodeid = f"ns=2;s={dataid}.{current_sheet_name}.{col_name}"
                    
                    try:
                        node = client.get_node(nodeid)
                        
                        # --- 데이터 타입에 따른 Variant 생성 (소수점 처리) ---
                        if pd.isna(value):
                            continue

                        if isinstance(value, (int, np.integer)):
                            variant = ua.Variant(str(value), ua.VariantType.String)
                        elif isinstance(value, (float, np.floating)):
                            # 소수점 8자리까지 표현하고, 불필요한 0은 제거하여 문자열로 변환
                            formatted_float = f"{value:.8f}".rstrip('0').rstrip('.')
                            variant = ua.Variant(formatted_float, ua.VariantType.String)
                        elif isinstance(value, str):
                            variant = ua.Variant(value, ua.VariantType.String)
                        elif isinstance(value, datetime):
                            variant = ua.Variant(value.strftime('%Y-%m-%d %H:%M:%S'), ua.VariantType.String)
                        else:
                            variant = ua.Variant(str(value), ua.VariantType.String)
                        
                        dv = ua.DataValue(variant)
                        node.set_value(dv)
                        # --- 로직 끝 ---
                    except Exception as node_e:
                        print(f"[WARNING] NodeId {nodeid} 처리 중 오류: {node_e}")

            results_for_this_file.append((file_sheet_key, latest_time_in_batch.strftime('%Y-%m-%d %H:%M:%S')))

        client.disconnect()
        return results_for_this_file

    except Exception as e:
        print(f"[ERROR] 스레드({threading.get_ident()}) 실행 중 오류: {filepath}, {e}")
        traceback.print_exc()
        if client.uaclient:
            client.disconnect()
        return None

# --- 3. 메인 처리 함수 (기존과 동일) ---

def process_all_files():
    """
    파일을 스캔하고, ThreadPoolExecutor를 사용해 병렬로 처리.
    """
    print(f"---[{datetime.now()}] 워커 사이클 시작 ---")
    
    # 1. 마지막 처리 정보 로드
    last_row_info = {}
    if os.path.exists(LAST_ROW_INFO_FILE):
        with open(LAST_ROW_INFO_FILE, 'r', encoding='utf-8') as f:
            try:
                last_row_info = json.load(f)
            except json.JSONDecodeError:
                print(f"[WARNING] {LAST_ROW_INFO_FILE} 파일이 손상되었습니다. 새로 시작합니다.")

    # 2. 처리할 파일 목록 수집
    tasks = []
    save_path = CONFIG.get('save_path')
    if not save_path or not os.path.isdir(save_path):
        print(f"[ERROR] 설정된 save_path를 찾을 수 없음: {save_path}")
        return

    try:
        for deviceid_folder in os.listdir(save_path):
            deviceid_path = os.path.join(save_path, deviceid_folder)
            if not os.path.isdir(deviceid_path): continue
            for dataid_folder in os.listdir(deviceid_path):
                dataid_path = os.path.join(deviceid_path, dataid_folder)
                if not os.path.isdir(dataid_path): continue
                for filename in os.listdir(dataid_path):
                    if filename.endswith('.json') or filename.endswith('.tmp'): continue
                    
                    filepath = os.path.join(dataid_path, filename)
                    param_filepath = filepath + '.json'
                    if not os.path.exists(param_filepath): continue

                    try:
                        with open(param_filepath, 'r', encoding='utf-8') as f:
                            params = json.load(f)
                        tasks.append({'filepath': filepath, 'params': params})
                    except (json.JSONDecodeError, FileNotFoundError) as e:
                        print(f"[WARNING] 메타데이터 파일({param_filepath}) 처리 중 오류: {e}")

    except Exception as e:
        print(f"[ERROR] 파일 스캔 중 예외 발생: {e}")
        traceback.print_exc()
        return

    if not tasks:
        return

    print(f"[INFO] 총 {len(tasks)}개 파일을 병렬로 처리합니다. (최대 동시 작업: {MAX_WORKERS})")

    # 3. ThreadPoolExecutor로 병렬 처리
    new_results = {}
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        future_to_task = {executor.submit(sendopcua_task, task['filepath'], task['params'], last_row_info): task for task in tasks}
        
        for future in as_completed(future_to_task):
            task_filepath = future_to_task[future]['filepath']
            try:
                result_list = future.result()
                if result_list:
                    for file_sheet_key, new_time in result_list:
                        new_results[file_sheet_key] = new_time
            except Exception as e:
                print(f"[ERROR] 태스크 실행({task_filepath}) 결과 처리 중 오류: {e}")

    # 4. 모든 작업 완료 후, 마지막 처리 정보 일괄 업데이트
    if new_results:
        print(f"[INFO] 총 {len(new_results)}개의 파일/시트 정보가 갱신됩니다.")
        last_row_info.update(new_results)
        try:
            with open(LAST_ROW_INFO_FILE, 'w', encoding='utf-8') as f:
                json.dump(last_row_info, f, indent=2)
            print(f"[INFO] {LAST_ROW_INFO_FILE} 파일에 성공적으로 기록했습니다.")
        except Exception as e:
            print(f"[ERROR] {LAST_ROW_INFO_FILE} 파일 쓰기 오류: {e}")

# --- 4. 실행 블록 (기존과 동일) ---
if __name__ == '__main__':
    # 1. 설정 파일 로드
    try:
        with open('config.json', 'r', encoding='utf-8') as f:
            CONFIG = json.load(f)
    except FileNotFoundError:
        print("[CRITICAL] 설정 파일(config.json)을 찾을 수 없습니다. 프로그램을 종료합니다.")
        sys.exit(1)
    except Exception as e:
        print(f"[CRITICAL] 설정 파일(config.json) 읽기 오류: {e}. 프로그램을 종료합니다.")
        sys.exit(1)

    # 2. (중요) 네트워크 파일 시스템 초기화
    save_path_init = CONFIG.get('save_path')
    if save_path_init:
        try:
            os.listdir(save_path_init)
            print(f"[INFO] 파일 시스템 경로({save_path_init})에 접근 가능합니다.")
        except Exception as e:
            print(f"[WARNING] 파일 시스템 경로 초기화 실패: {e}")

    # 3. 메인 처리 루프 실행
    scan_interval = CONFIG.get('scan_interval', 10)
    print(f"[INFO] 워커가 지속적인 실행 모드로 시작됩니다. ({scan_interval}초 간격, 최대 스레드: {MAX_WORKERS})")
    while True:
        process_all_files()
        time.sleep(scan_interval)